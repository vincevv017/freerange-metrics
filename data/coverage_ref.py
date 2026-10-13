"""
Two independent reference implementations of stock coverage over the produced dataset (v0).

- `py_coverage`: pandas aggregation driven by attribute applicability + the legacy cascade (search for the
  first n with S <= C(n), as the legacy metrics did). No SQL.
- `sql_coverage`: the set-based SQL of DEFINITION.md section 5, run in DuckDB, with its member spine
  (stock members UNION forecast members) so that "forecast but no stock" keeps its row (T8).
  `spine=False` reproduces the earlier section 5 shape, which drove members from stock only.

They agree with each other AND with the hand-computed values in traps.yaml (see checks/check_dataset.py).
Agreement alone proves nothing about correctness; the hand-computed values do.

Wrong behaviours are opt-in switches, so the checks can prove each trap is detectable.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
import sys
from pathlib import Path

import duckdb
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from generated.schema import BASES, CONFORMED, HORIZON_MONTHS, SNAPSHOT_ONLY  # noqa: E402


def load(out_dir: Path) -> dict[str, pd.DataFrame]:
    return {p.stem: pd.read_parquet(p) for p in sorted(out_dir.glob("*.parquet"))}


def month_add(d: dt.date, n: int) -> dt.date:
    y, m = divmod(d.month - 1 + n, 12)
    return dt.date(d.year + y, m + 1, 1)


@dataclass(frozen=True)
class Result:
    value: float | None
    flag: str | None


# ------------------------------------------------------------------------------------------ algorithm

def cascade(stock: float, fc: list[float], avg_over: list[float] | None = None) -> Result:
    """Legacy-style search. fc[0] is month t+1. avg_over defaults to fc (average bounded to the window)."""
    if stock is None or stock == 0:
        return Result(0.0, "NO_STOCK")
    cum = 0.0
    for n, f in enumerate(fc, start=1):
        if stock <= cum + f:
            return Result((n - 1) + (stock - cum) / f, None)
        cum += f
    nz = [x for x in (avg_over if avg_over is not None else fc) if x != 0]
    if not nz:
        return Result(None, "NO_DEMAND")
    return Result(stock / (sum(nz) / len(nz)), "BEYOND_HORIZON")


# ------------------------------------------------------------------------------------------ joined views

def stock_view(t: dict[str, pd.DataFrame], dedupe_items: bool = True) -> pd.DataFrame:
    items = t["DIM_ITEM"].drop_duplicates("item_id") if dedupe_items else t["DIM_ITEM"]
    return (t["FCT_STOCK_SNAPSHOT"]
            .merge(items.drop(columns=["std_cost_eur", "cogs_eur", "qty_eq_factor"]), on="item_id")
            .merge(t["DIM_GEO"], on="country_id")
            .merge(t["DIM_BATCH"][["batch_id", "batch_status"]], on="batch_id")
            .merge(t["DIM_WAREHOUSE"][["warehouse_id", "warehouse_code", "warehouse_type"]], on="warehouse_id"))


def forecast_view(t: dict[str, pd.DataFrame], dedupe_items: bool = True) -> pd.DataFrame:
    items = t["DIM_ITEM"].drop_duplicates("item_id") if dedupe_items else t["DIM_ITEM"]
    return (t["FCT_FORECAST"]
            .merge(items.drop(columns=["std_cost_eur", "cogs_eur", "qty_eq_factor"]), on="item_id")
            .merge(t["DIM_GEO"], on="country_id"))


def _check_attrs(attrs) -> None:
    unknown = [a for a in attrs if a not in CONFORMED and a not in SNAPSHOT_ONLY]
    if unknown:
        raise ValueError(f"attribute(s) without a declared applicability class: {unknown}")


def _values(v) -> list:
    """A filter value is one value or a list of values (IN)."""
    return list(v) if isinstance(v, (list, tuple)) else [v]


def _columns(variant: str, raw_units: bool) -> tuple[str, str]:
    """A measure basis (contract 0.5.0). raw_units=True is the T5 wrong behaviour: the NATIVE columns (pack counts)
    read whatever the basis asked, so packs of different items are added."""
    return BASES["NATIVE" if raw_units else variant]


# ------------------------------------------------------------------------------------------ python path

def py_coverage(t, as_of: dt.date, grain: list[str], filters: dict, variant: str = "QTY_EQ", *,
                dedupe_items: bool = True, push_filters_to_forecast: bool = False,
                forecast_time_filter: bool = False, window_start_k: int = 1, dense: bool = True,
                avg_full_range: bool = False, raw_units: bool = False) -> dict[tuple, Result]:
    _check_attrs(list(grain) + list(filters))
    s_col, f_col = _columns(variant, raw_units)
    conf_grain = [g for g in grain if g in CONFORMED]

    s = stock_view(t, dedupe_items)
    s = s[s.snapshot_month == as_of]
    for a, v in filters.items():
        s = s[s[a].isin(_values(v))]
    S = s.groupby(grain)[s_col].sum().to_dict() if len(s) else {}

    f = forecast_view(t, dedupe_items)
    f = f.assign(k=[(m.year - as_of.year) * 12 + m.month - as_of.month for m in f.forecast_month])
    if forecast_time_filter:
        f = f[f.forecast_month == as_of]
    fc_filters = filters if push_filters_to_forecast else {a: v for a, v in filters.items() if a in CONFORMED}
    for a, v in fc_filters.items():
        f = f[f[a].isin(_values(v))] if a in f.columns else f.iloc[0:0]
    F = f.groupby(conf_grain + ["k"])[f_col].sum()

    def key(k):
        return k if isinstance(k, tuple) else (k,)

    members = {key(k) for k in S}
    if set(grain) <= set(CONFORMED):          # forecast-only members exist only on a conformed grain
        members |= {tuple(k[:-1]) for k in F.index}
    last_k = window_start_k + HORIZON_MONTHS - 1
    out = {}
    for m in sorted(members):
        stock = S.get(m if len(grain) > 1 else m[0], 0.0)
        ck = tuple(v for g, v in zip(grain, m) if g in CONFORMED)
        series = {k: F.get(ck + (k,), None) for k in range(window_start_k, 37)}
        if dense:
            window = [series[k] or 0.0 for k in range(window_start_k, last_k + 1)]
        else:                                  # wrong: "next n rows" over the rows that exist
            window = [series[k] for k in sorted(series) if series[k] is not None][:HORIZON_MONTHS]
        full = [series[k] or 0.0 for k in sorted(series)] if avg_full_range else None
        out[m] = cascade(float(stock), [float(x) for x in window], full)
    return out


# ------------------------------------------------------------------------------------------ SQL path

SQL = """
WITH months AS (SELECT range AS k FROM range(1, {h} + 1)),
s AS (
    SELECT {grain}, SUM({s_col}) AS stock_qty
    FROM stock_v WHERE snapshot_month = DATE '{as_of}' AND {all_filters}
    GROUP BY ALL
),
f AS (
    SELECT {conf_grain_sel} DATEDIFF('month', DATE '{as_of}', forecast_month) AS k, SUM({f_col}) AS fc_qty
    FROM fc_v
    WHERE forecast_month > DATE '{as_of}' AND forecast_month <= DATE '{as_of}' + INTERVAL {h} MONTH
      AND {conf_filters}
    GROUP BY ALL
),
members AS ({members}),
dense AS (
    SELECT m.*, mo.k, COALESCE(s.stock_qty, 0) AS stock_qty, COALESCE(f.fc_qty, 0) AS fc_qty
    FROM members m CROSS JOIN months mo
    LEFT JOIN s ON {join_s}
    LEFT JOIN f ON f.k = mo.k {join_f}
),
cum AS (
    SELECT *, SUM(fc_qty) OVER (PARTITION BY {grain} ORDER BY k ROWS UNBOUNDED PRECEDING) AS cum_fc
    FROM dense
)
SELECT {grain},
       CASE
         WHEN ANY_VALUE(stock_qty) = 0 THEN 0
         WHEN MAX(cum_fc) >= ANY_VALUE(stock_qty) THEN
              SUM(CASE WHEN cum_fc - fc_qty >= stock_qty THEN 0
                       WHEN cum_fc <= stock_qty THEN 1
                       ELSE (stock_qty - (cum_fc - fc_qty)) / fc_qty END)
         ELSE ANY_VALUE(stock_qty) / AVG(NULLIF(fc_qty, 0))
       END AS coverage_months,
       CASE
         WHEN ANY_VALUE(stock_qty) = 0 THEN 'NO_STOCK'
         WHEN MAX(cum_fc) >= ANY_VALUE(stock_qty) THEN NULL
         WHEN MAX(cum_fc) = 0 THEN 'NO_DEMAND'
         ELSE 'BEYOND_HORIZON'
       END AS flag
FROM cum GROUP BY {grain} ORDER BY {grain}
"""


def _lit(v) -> str:
    return "'" + str(v).replace("'", "''") + "'"


def _in(a: str, v) -> str:
    return f"{a} IN ({', '.join(_lit(x) for x in _values(v))})"


def sql_coverage(t, as_of: dt.date, grain: list[str], filters: dict, variant: str = "QTY_EQ", *,
                 spine: bool = True) -> dict[tuple, Result]:
    _check_attrs(list(grain) + list(filters))
    s_col, f_col = BASES[variant]
    conf_grain = [g for g in grain if g in CONFORMED]
    con = duckdb.connect()
    con.register("stock_v", stock_view(t))
    con.register("fc_v", forecast_view(t))
    g = ", ".join(grain)
    members = f"SELECT {g} FROM s"
    if spine and set(grain) <= set(CONFORMED):
        members += f" UNION SELECT {g} FROM f"
    sql = SQL.format(
        h=HORIZON_MONTHS, as_of=as_of.isoformat(), grain=g, s_col=s_col, f_col=f_col,
        conf_grain_sel="".join(f"{c}, " for c in conf_grain),
        all_filters=" AND ".join([_in(a, v) for a, v in filters.items()] or ["TRUE"]),
        conf_filters=" AND ".join([_in(a, v) for a, v in filters.items() if a in CONFORMED] or ["TRUE"]),
        members=members,
        join_s=" AND ".join(f"s.{c} = m.{c}" for c in grain),
        join_f="".join(f" AND f.{c} = m.{c}" for c in conf_grain),
    )
    rows = con.sql(sql).fetchall()
    n = len(grain)
    return {tuple(r[:n]): Result(None if r[n] is None else float(r[n]), r[n + 1]) for r in rows}


# ------------------------------------------------------------------------------------------ basis and selection
# Session 8c-0 (contract 0.5.0): each row's item count and dimension count decide which bases it can be measured on;
# a member selection keeps detail rows by coverage and sets NO_STOCK and NO_DEMAND members apart. Two independent
# paths again: pandas (py_rows, select) and DuckDB SQL (sql_rows, sql_select). Neither reads any Snowflake object.

@dataclass(frozen=True)
class Row:
    value: float | None
    flag: str | None
    stock: float
    forecast: float          # forecast over the horizon window, on the basis asked
    n_items: int             # distinct items of the row: its stock items and the forecast items of its conformed key
    n_dims: int              # distinct dimensions of those items
    base_unit: str | None    # the base unit when n_dims == 1
    native_unit: str | None  # the item's own unit when n_items == 1


def stock_unit(basis: str, r: Row) -> str | None:
    """The unit of the row's stock and forecast on the basis, or None where the basis is not comparable."""
    if basis == "VALUE":
        return "EUR"
    if basis == "QTY_EQ":
        return r.base_unit if r.n_dims == 1 else None
    return r.native_unit if r.n_items == 1 else None


def allowed_bases(rows) -> list[str]:
    """The bases valid for every returned row (BASIS_VALID_WHEN): NATIVE one item, QTY_EQ one dimension, VALUE always."""
    rows = list(rows)
    out = []
    if all(r.n_items <= 1 for r in rows):
        out.append("NATIVE")
    if all(r.n_dims <= 1 for r in rows):
        out.append("QTY_EQ")
    return out + ["VALUE"]


def stockout_month(as_of: dt.date, r: Row) -> dt.date | None:
    """t + ceil(coverage) months; none with NO_DEMAND or BEYOND_HORIZON (contract exhaustion_period)."""
    if r.value is None or r.flag in ("NO_DEMAND", "BEYOND_HORIZON"):
        return None
    n = int(r.value) if float(r.value).is_integer() else int(r.value) + 1
    return month_add(as_of, n)


def py_rows(t, as_of: dt.date, grain: list[str], filters: dict, basis: str = "QTY_EQ") -> dict[tuple, Row]:
    """pandas: the coverage of py_coverage plus stock, forecast over the horizon and the items of each row."""
    _check_attrs(list(grain) + list(filters))
    s_col, f_col = BASES[basis]
    conf = [g for g in grain if g in CONFORMED]
    cov = py_coverage(t, as_of, grain, filters, basis)
    s = stock_view(t)
    s = s[s.snapshot_month == as_of]
    for a, v in filters.items():
        s = s[s[a].isin(_values(v))]
    f = forecast_view(t)
    k = (f.forecast_month.map(lambda m: (m.year - as_of.year) * 12 + m.month - as_of.month))
    f = f[(k >= 1) & (k <= HORIZON_MONTHS)]
    for a, v in filters.items():
        if a in CONFORMED:
            f = f[f[a].isin(_values(v))]
    items = t["DIM_ITEM"].drop_duplicates("item_id").set_index("item_id")
    out = {}
    for key, res in cov.items():
        sk = s.loc[(s[grain] == pd.Series(key, index=grain)).all(axis=1)] if len(s) else s
        fk = f.loc[(f[conf] == pd.Series([v for g, v in zip(grain, key) if g in CONFORMED], index=conf)).all(axis=1)] \
            if conf and len(f) else (f if not conf else f.iloc[0:0])
        ids = sorted(set(sk.item_id) | set(fk.item_id))
        dims = sorted(set(items.loc[ids, "dimension"]))
        out[key] = Row(res.value, res.flag, float(sk[s_col].sum()), float(fk[f_col].sum()), len(ids), len(dims),
                       items.loc[ids[0], "base_unit"] if len(dims) == 1 else None,
                       items.loc[ids[0], "raw_unit"] if len(ids) == 1 else None)
    return out


def select(rows: dict[tuple, Row], below=None, above=None, rank_first=None):
    """pandas-free selection: kept [(key, row)] in coverage order (ties by the grain codes), apart {flag: [keys]}.
    Without a criterion every row is kept in grain order and nothing is set apart."""
    if below is None and above is None and rank_first is None:
        return sorted(rows.items()), {}
    apart = {fl: sorted(k for k, r in rows.items() if r.flag == fl) for fl in ("NO_STOCK", "NO_DEMAND")}
    kept = [(k, r) for k, r in rows.items() if r.flag not in ("NO_STOCK", "NO_DEMAND")
            and (below is None or 0 < r.value <= below) and (above is None or r.value > above)]
    kept.sort(key=lambda kr: (kr[1].value, kr[0]))
    return (kept[:rank_first] if rank_first is not None else kept), apart


def summary(kept, basis: str) -> dict:
    """Count of kept rows and their stock per unit of the basis; none on NATIVE across several items."""
    out = {"count": len(kept)}
    units = [stock_unit(basis, r) for _, r in kept]
    if basis == "NATIVE" and len(kept) > 1:
        out["stock"] = None
    else:
        out["stock"] = [{"unit": u, "amount": sum(r.stock for (_, r), x in zip(kept, units) if x == u)}
                        for u in sorted(set(units), key=str)]
    return out


SQL_ROWS = """
WITH months AS (SELECT range AS k FROM range(1, {h} + 1)),
sr AS (SELECT {grain}, item_id, {s_col} AS q FROM stock_v WHERE snapshot_month = DATE '{as_of}' AND {all_filters}),
fr AS (
    SELECT {conf_sel} item_id, DATEDIFF('month', DATE '{as_of}', forecast_month) AS k, {f_col} AS q
    FROM fc_v WHERE forecast_month > DATE '{as_of}' AND forecast_month <= DATE '{as_of}' + INTERVAL {h} MONTH
      AND {conf_filters}
),
s AS (SELECT {grain}, SUM(q) AS stock_qty FROM sr GROUP BY ALL),
f AS (SELECT {conf_sel} k, SUM(q) AS fc_qty FROM fr GROUP BY ALL),
members AS ({members}),
dense AS (
    SELECT m.*, mo.k, COALESCE(s.stock_qty, 0) AS stock_qty, COALESCE(f.fc_qty, 0) AS fc_qty
    FROM members m CROSS JOIN months mo LEFT JOIN s ON {join_s} LEFT JOIN f ON f.k = mo.k {join_f}
),
cov AS (
    SELECT {grain}, ANY_VALUE(stock_qty) AS stock, SUM(fc_qty) AS fc,
           CASE WHEN ANY_VALUE(stock_qty) = 0 THEN 'NO_STOCK' WHEN SUM(fc_qty) = 0 THEN 'NO_DEMAND' END AS flag0
    FROM dense GROUP BY {grain}
),
mi AS (
    SELECT {grain_m}, sr.item_id FROM members m JOIN sr ON {join_sr}
    UNION
    SELECT {grain_m}, fr.item_id FROM members m JOIN fr ON TRUE {join_fr}
),
it AS (SELECT DISTINCT item_id, dimension, base_unit, raw_unit FROM items_v)
SELECT {grain_c}, c.stock, c.fc, COUNT(DISTINCT mi.item_id) AS n_items, COUNT(DISTINCT it.dimension) AS n_dims,
       MIN(it.base_unit) AS base_unit, MIN(it.raw_unit) AS native_unit
FROM cov c JOIN mi ON {join_cm} JOIN it ON it.item_id = mi.item_id
GROUP BY ALL
"""


def sql_rows(t, as_of: dt.date, grain: list[str], filters: dict, basis: str = "QTY_EQ") -> dict[tuple, Row]:
    """DuckDB: the coverage of sql_coverage plus stock, forecast over the horizon and the items of each row."""
    s_col, f_col = BASES[basis]
    conf = [g for g in grain if g in CONFORMED]
    cov = sql_coverage(t, as_of, grain, filters, basis)
    con = duckdb.connect()
    con.register("stock_v", stock_view(t))
    con.register("fc_v", forecast_view(t))
    con.register("items_v", t["DIM_ITEM"])
    g = ", ".join(grain)
    members = f"SELECT {g} FROM s" + (f" UNION SELECT {g} FROM f" if set(grain) <= set(CONFORMED) else "")
    sql = SQL_ROWS.format(
        h=HORIZON_MONTHS, as_of=as_of.isoformat(), grain=g, s_col=s_col, f_col=f_col,
        conf_sel="".join(f"{c}, " for c in conf),
        all_filters=" AND ".join([_in(a, v) for a, v in filters.items()] or ["TRUE"]),
        conf_filters=" AND ".join([_in(a, v) for a, v in filters.items() if a in CONFORMED] or ["TRUE"]),
        members=members, join_s=" AND ".join(f"s.{c} = m.{c}" for c in grain),
        join_f="".join(f" AND f.{c} = m.{c}" for c in conf),
        grain_m=", ".join(f"m.{c}" for c in grain), grain_c=", ".join(f"c.{c}" for c in grain),
        join_sr=" AND ".join(f"sr.{c} = m.{c}" for c in grain), join_fr="".join(f" AND fr.{c} = m.{c}" for c in conf),
        join_cm=" AND ".join(f"mi.{c} = c.{c}" for c in grain))
    n = len(grain)
    out = {}
    for r in con.sql(sql).fetchall():
        key = tuple(r[:n])
        res = cov[key]
        out[key] = Row(res.value, res.flag, float(r[n]), float(r[n + 1]), int(r[n + 2]), int(r[n + 3]),
                       r[n + 4] if r[n + 3] == 1 else None, r[n + 5] if r[n + 2] == 1 else None)
    return out


def sql_select(rows: dict[tuple, Row], grain: list[str], below=None, above=None, rank_first=None):
    """DuckDB: the same selection as select(), written as SQL over the rows (QUALIFY on a ROW_NUMBER)."""
    if below is None and above is None and rank_first is None:
        return sorted(rows.items()), {}
    df = pd.DataFrame([dict(zip(grain, k)) | {"value": r.value, "flag": r.flag, "i": i}
                       for i, (k, r) in enumerate(rows.items())])
    keys = list(rows)
    con = duckdb.connect()
    con.register("r", df)
    order = ", ".join(f"{g} ASC" for g in grain)
    cond = " AND ".join(["(flag IS NULL OR flag = 'BEYOND_HORIZON')"]
                        + ([f"value > 0 AND value <= {float(below)!r}"] if below is not None else [])
                        + ([f"value > {float(above)!r}"] if above is not None else []))
    q = (f"SELECT i FROM r WHERE {cond} QUALIFY ROW_NUMBER() OVER (ORDER BY value ASC, {order}) "
         f"<= {rank_first if rank_first is not None else 'COUNT(*) OVER ()'} ORDER BY value ASC, {order}")
    kept = [(keys[i], rows[keys[i]]) for (i,) in con.sql(q).fetchall()]
    apart = {fl: sorted(keys[i] for (i,) in con.sql(f"SELECT i FROM r WHERE flag = '{fl}'").fetchall())
             for fl in ("NO_STOCK", "NO_DEMAND")}
    return kept, apart


# ------------------------------------------------------------------------------------------ closing stock
# Session 9b: DEFINITION.md section 7, two independent paths again. The closing stock of a period is the snapshot of its
# last month; a member with a snapshot in some month of the period and none in its last month closes at 0; every item
# type (the default scope is a coverage rule). A member with no snapshot at all in the period has no row in either path:
# the reason the owner reworded N2 to the months of Q2 2026 (2026-10-07).

def closing_stock(t, as_of: dt.date, grain: list[str], filters: dict, period_k, *,
                  last_known: bool = False, column: str = "stock_qty_eq") -> dict[tuple, float]:
    """pandas: closing stock per member of the period (offsets period_k from the analysis month, inclusive), in QTY_EQ
    (session 13: another stock column with `column`, for example stock_value_eur).
    last_known=True is the wrong behaviour: each item and country carried at its last snapshot up to the period's end."""
    months = [month_add(as_of, k) for k in range(period_k[0], period_k[1] + 1)]
    sv = stock_view(t)
    for a, v in filters.items():
        sv = sv[sv[a].isin(_values(v))]
    rows = sv[sv.snapshot_month.isin(months)]
    members = sorted({tuple(r) for r in rows[grain].itertuples(index=False)})
    if last_known:
        h = sv[sv.snapshot_month <= months[-1]]
        src = h[h.snapshot_month == h.groupby(["item_id", "country_id"]).snapshot_month.transform("max")]
    else:
        src = rows[rows.snapshot_month == months[-1]]
    s = src.groupby(grain)[column].sum()
    return {m: float(s.get(m if len(grain) > 1 else m[0], 0.0)) for m in members}


SQL_CLOSING = """
WITH p AS (SELECT * FROM stock_v WHERE snapshot_month BETWEEN DATE '{first}' AND DATE '{last}' AND {filters}),
members AS (SELECT DISTINCT {grain} FROM p),
closing AS (SELECT {grain}, SUM({column}) AS q FROM p WHERE snapshot_month = DATE '{last}' GROUP BY ALL)
SELECT {grain_m}, COALESCE(c.q, 0) FROM members m LEFT JOIN closing c ON {join} ORDER BY ALL
"""


def sql_closing_stock(t, as_of: dt.date, grain: list[str], filters: dict, period_k,
                      column: str = "stock_qty_eq") -> dict[tuple, float]:
    """DuckDB: the same closing stock, set-based: the period's members LEFT JOIN the snapshot of its last month."""
    con = duckdb.connect()
    con.register("stock_v", stock_view(t))
    sql = SQL_CLOSING.format(
        first=month_add(as_of, period_k[0]).isoformat(), last=month_add(as_of, period_k[1]).isoformat(),
        filters=" AND ".join([_in(a, v) for a, v in filters.items()] or ["TRUE"]), grain=", ".join(grain), column=column,
        grain_m=", ".join(f"m.{c}" for c in grain), join=" AND ".join(f"c.{c} = m.{c}" for c in grain))
    n = len(grain)
    return {tuple(r[:n]): float(r[n]) for r in con.sql(sql).fetchall()}
