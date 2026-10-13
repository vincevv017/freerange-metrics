"""
Phase 2: deploy the generated custom DMFs to LINKML_METRICS.RAW and run every generated check once, ad hoc.

    python snowflake/phase2_dmf/run_dmf.py                      # connection "perso", project role forced
    python snowflake/phase2_dmf/run_dmf.py --results results.md # also writes the results table

Runs generated/dmf.sql as LINKML_METRICS_ROLE with no secondary role. Nothing is attached to a table and no
schedule is set. Each value is asserted against a number computed here from data/output/ with pandas, an
implementation independent of the DMF SQL. Two expectations must FIRE on the v0 data, each on its trap:
QE_ITEM_GRAIN on T7 and QE_FORECAST_DENSE on T2 (the horizon window of LATEST, equal to the procedure's
FORECAST_GAPS_FILLED for every member at LATEST). Every other check must be clean (0), except the freshness age,
which is a number of months with a TBD threshold. Exits 1 on any mismatch.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

import pandas as pd
import snowflake.connector
import yaml

ROOT = Path(__file__).resolve().parents[2]
ROLE, WAREHOUSE, DATABASE, SCHEMA = "LINKML_METRICS_ROLE", "LINKML_METRICS_WH", "LINKML_METRICS", "RAW"


def statements(sql: str) -> list[str]:
    out, cur = [], []
    for line in sql.splitlines():
        if not cur and (not line.strip() or line.startswith("--")):
            continue
        cur.append(line)
        if line.rstrip().endswith(";"):
            out.append("\n".join(cur).rstrip().rstrip(";"))
            cur = []
    return out


def month_add(d: dt.date, n: int) -> dt.date:
    y, m = divmod(d.month - 1 + n, 12)
    return dt.date(d.year + y, m + 1, 1)


def local_expected(out: Path, contract: dict) -> tuple[dict, dict]:
    """(expected value per expectation, evidence) computed with pandas from the produced dataset."""
    t = {p.stem: pd.read_parquet(p) for p in out.glob("*.parquet")}
    for name, df in t.items():
        for c in df.columns:
            if c.endswith("month") or c == "month_start":
                df[c] = pd.to_datetime(df[c]).dt.date
    exp = {q["id"]: 0 for q in contract["quality_expectations"]}
    ev = {}

    items = t["DIM_ITEM"]
    exp["QE_ITEM_GRAIN"] = int(len(items) - items.item_id.nunique())
    dup = items[items.duplicated("item_id", keep=False)]
    ev["QE_ITEM_GRAIN"] = f"duplicated item: {sorted(set(dup.sku_code))}, lifecycle_status {sorted(dup.lifecycle_status)}"

    st, fc = t["FCT_STOCK_SNAPSHOT"], t["FCT_FORECAST"]
    metric = contract["metrics"][0]
    h, k0 = metric["horizon_periods"], metric["window_start_offset"]
    latest = max(st.snapshot_month)                       # the horizon window of LATEST, as the procedure reads it
    lo, hi = month_add(latest, k0), month_add(latest, k0 + h - 1)
    periods = [month_add(latest, k) for k in range(k0, k0 + h)]
    win = fc[fc.forecast_month.isin(periods)]
    have = win.groupby(["item_id", "country_id"]).forecast_month.nunique()   # pairs with a row in the window
    missing = len(periods) - have
    exp["QE_FORECAST_DENSE"] = int(missing.sum())
    members = have
    sku = items.drop_duplicates("item_id").set_index("item_id").sku_code
    geo = t["DIM_GEO"].set_index("country_id").country_code
    heroes = {f"{sku[i]}/{geo[c]}": int(v) for (i, c), v in missing.items() if v and sku[i].startswith("SKU-H")}
    ev["QE_FORECAST_DENSE"] = (f"{exp['QE_FORECAST_DENSE']} member-months missing over {len(periods)} months "
                               f"({lo} to {hi}), {int((missing > 0).sum())} of {len(members)} members; "
                               f"heroes: {heroes}")
    ev["_heroes_dense"] = heroes
    key = lambda code, cc: (int(items[items.sku_code == code].item_id.iloc[0]),
                            int(t["DIM_GEO"][t["DIM_GEO"].country_code == cc].country_id.iloc[0]))
    ev["_ids"] = {"T7": key("SKU-H06", "SE"), "T2": key("SKU-H03", "DE")}

    latest = max(st.snapshot_month)
    ev["_latest"] = latest
    return exp, ev


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--connection", default="perso")
    p.add_argument("--out", type=Path, default=ROOT / "data" / "output")
    p.add_argument("--results", type=Path, help="write the results table (pasted into results.md)")
    a = p.parse_args()
    contract = yaml.safe_load((ROOT / "contract" / "stock_coverage.yaml").read_text())
    stmts = statements((ROOT / "generated" / "dmf.sql").read_text())
    creates = [s for s in stmts if s.startswith("CREATE")]
    checks = [s for s in stmts if s.startswith("SELECT")]

    con = snowflake.connector.connect(connection_name=a.connection, role=ROLE, warehouse=WAREHOUSE,
                                      database=DATABASE, schema=SCHEMA)
    cur = con.cursor()
    cur.execute("USE SECONDARY ROLES NONE")
    role, secondary = cur.execute("SELECT CURRENT_ROLE(), CURRENT_SECONDARY_ROLES()").fetchone()
    if role != ROLE or json.loads(secondary)["roles"] != "":
        raise SystemExit(f"refusing to run: role={role} secondary={secondary}")
    for s in creates:
        cur.execute(s)
    print(f"session role={role}, secondary none; {len(creates)} custom DMFs created, {len(checks)} checks")

    rows = []
    for s in checks:
        qid, target, value = cur.execute(s).fetchone()
        rows.append((qid, target, int(value), cur.sfqid))
    exp, ev = local_expected(a.out, contract)
    # Freshness is an age: expected = seconds from the latest local snapshot month to now, read in the same
    # session right after the DMF ran; a 300 s tolerance covers the time between the two statements.
    fresh_expected = cur.execute("SELECT DATEDIFF(second, %s::TIMESTAMP_LTZ, CURRENT_TIMESTAMP())",
                                 (ev["_latest"].isoformat(),)).fetchone()[0]
    # Attribution: the same DMF without the trap's own rows must lose exactly the trap's contribution.
    i7, _ = ev["_ids"]["T7"]
    i2, c2 = ev["_ids"]["T2"]
    # An ad hoc DMF argument must be a plain SELECT of columns (a WHERE makes it scalar, measured), so each trap's
    # rows are removed in a session-scoped TEMPORARY table, dropped with the session.
    db = f"{DATABASE}.{SCHEMA}"
    cur.execute(f"CREATE TEMPORARY TABLE {db}.TMP_ITEM_WITHOUT_T7 AS SELECT * FROM {db}.DIM_ITEM WHERE item_id <> {i7}")
    cur.execute(f"CREATE TEMPORARY TABLE {db}.TMP_FORECAST_WITHOUT_T2 AS SELECT * FROM {db}.FCT_FORECAST "
                f"WHERE NOT (item_id = {i2} AND country_id = {c2})")
    without_t7 = cur.execute(f"SELECT SNOWFLAKE.CORE.DUPLICATE_COUNT(SELECT item_id FROM {db}.TMP_ITEM_WITHOUT_T7)"
                             ).fetchone()[0]
    without_t2 = cur.execute(
        f"SELECT {db}.DMF_QE_FORECAST_DENSE((SELECT forecast_month, item_id, country_id FROM "
        f"{db}.TMP_FORECAST_WITHOUT_T2), (SELECT snapshot_month FROM {db}.FCT_STOCK_SNAPSHOT))").fetchone()[0]
    attached = sum(cur.execute(
        "SELECT COUNT(*) FROM TABLE(LINKML_METRICS.INFORMATION_SCHEMA.DATA_METRIC_FUNCTION_REFERENCES("
        f"REF_ENTITY_NAME => '{DATABASE}.{SCHEMA}.{tb['id']}', REF_ENTITY_DOMAIN => 'TABLE'))").fetchone()[0]
        for tb in contract["tables"])
    # Same count as the procedure's in-call check for a request that holds every member at LATEST (scope only differs).
    res = json.loads(cur.execute("CALL LINKML_METRICS.RAW.STOCK_COVERAGE('[\"LATEST\"]', 'QTY_EQ', "
                                 "'[\"sku_code\", \"country_code\"]', '{}', '[]')").fetchone()[0])
    proc_gaps = sum(w["count"] for w in res.get("warnings", []) if w.get("expectation") == "QE_FORECAST_DENSE")
    con.close()

    exp["QE_STOCK_FRESHNESS"] = fresh_expected
    ev["QE_STOCK_FRESHNESS"] = (f"latest snapshot {ev['_latest']}: {fresh_expected} s, about "
                                f"{fresh_expected / 86400 / 30.4375:.1f} months (threshold TBD)")
    qe = {q["id"]: q for q in contract["quality_expectations"]}
    by_qe: dict[str, int] = {}
    for qid, _, v, _ in rows:
        by_qe[qid] = by_qe.get(qid, 0) + v
    failures = 0
    lines = ["| Expectation | DMF | Target | Value | Expected (pandas) | On failure | Verdict |", "|---|---|---|---|---|---|---|"]
    for qid, target, v, _ in rows:
        n_targets = sum(1 for r in rows if r[0] == qid)
        e = exp[qid] if n_targets == 1 else (0 if exp[qid] == 0 else None)
        if qid == "QE_STOCK_FRESHNESS":
            ok = abs(v - e) <= 300
        else:
            ok = (by_qe[qid] == exp[qid]) if e is None else (v == e)
        failures += not ok
        fires = "fires" if v and qid != "QE_STOCK_FRESHNESS" else ("age" if qid == "QE_STOCK_FRESHNESS" else "clean")
        lines.append(f"| {qid} | `{qe[qid]['dmf']}` | {target} | {v} | {exp[qid] if e is not None else '-'} | "
                     f"{qe[qid]['on_failure']} | {'PASS' if ok else 'FAIL'} ({fires}) |")
    fired = sorted(q for q, v in by_qe.items() if v and q != "QE_STOCK_FRESHNESS")
    musts = [("QE_ITEM_GRAIN fires on T7", by_qe["QE_ITEM_GRAIN"] == 1),
             ("QE_FORECAST_DENSE fires on T2 (SKU-H03/DE: 2 missing months)",
              by_qe["QE_FORECAST_DENSE"] > 0 and ev["_heroes_dense"].get("SKU-H03/DE") == 2),
             ("only those two fire", fired == ["QE_FORECAST_DENSE", "QE_ITEM_GRAIN"]),
             (f"attribution T7: DUPLICATE_COUNT without SKU-H06 = 0 (got {without_t7})", without_t7 == 0),
             (f"attribution T2: QE_FORECAST_DENSE without SKU-H03/DE = {by_qe['QE_FORECAST_DENSE']} - 2 "
              f"(got {without_t2})", without_t2 == by_qe["QE_FORECAST_DENSE"] - 2),
             (f"no DMF attached to any of the {len(contract['tables'])} tables", attached == 0),
             (f"QE_FORECAST_DENSE = the procedure's FORECAST_GAPS_FILLED for every member at LATEST "
              f"({by_qe['QE_FORECAST_DENSE']} vs {proc_gaps})", by_qe["QE_FORECAST_DENSE"] == proc_gaps)]
    failures += sum(not ok for _, ok in musts)
    print("\n".join(lines))
    print()
    for label, ok in musts:
        print(f"{'PASS' if ok else 'FAIL'}  {label}")
    for k, v in ev.items():
        if not k.startswith("_"):
            print(f"  {k}: {v}")
    print(f"\n{len(rows)} checks, {failures} failure(s)")
    if a.results:
        a.results.write_text("\n".join(lines) + "\n\n" + "\n".join(f"- {'PASS' if ok else 'FAIL'}: {l}" for l, ok in musts)
                             + "\n\n" + "\n".join(f"- {k}: {v}" for k, v in ev.items() if not k.startswith("_")) + "\n")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
