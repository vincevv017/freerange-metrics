"""Session 8: deploy a semantic view from a model YAML file, this project's own path (never the enrich tool's).

    python snowflake/phase4_others/deploy_sv.py <file.yaml>            # dry run, then create or replace
    python snowflake/phase4_others/deploy_sv.py <file.yaml> --dry-run  # dry run only

Run as perso, USE SECONDARY ROLES NONE, LINKML_METRICS_ROLE. CALL SYSTEM$CREATE_SEMANTIC_VIEW_FROM_YAML (a stored
procedure: CALL, never SELECT), first with dry_run TRUE, then FALSE; it replaces an existing view of the YAML's name
and copies its grants. Then reads the object back (SYSTEM$READ_YAML_FROM_SEMANTIC_VIEW) and compares, per logical
table, the dimensions, metrics, is_enum and sample_values, and the verified query names, with the file.
"""

import argparse
from pathlib import Path

import snowflake.connector
import yaml


def members(d: dict) -> dict:
    out = {}
    for t in d["tables"]:
        n = t["name"].lower()
        for k in ("dimensions", "time_dimensions", "facts", "metrics"):
            for m in t.get(k, []):
                out[(n, m["name"].lower())] = (bool(m.get("is_enum")), [str(x) for x in m.get("sample_values", [])])
    for m in d.get("metrics", []):
        out[("view", m["name"].lower())] = (False, [])
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("yaml", type=Path)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    text = a.yaml.read_text()
    model = yaml.safe_load(text)
    con = snowflake.connector.connect(connection_name="perso")
    cur = con.cursor()
    for s in ("USE SECONDARY ROLES NONE", "USE ROLE LINKML_METRICS_ROLE", "USE WAREHOUSE LINKML_METRICS_WH"):
        cur.execute(s)
    cur.execute("CALL SYSTEM$CREATE_SEMANTIC_VIEW_FROM_YAML('LINKML_METRICS.RAW', %s, TRUE)", (text,))
    print("dry run:", cur.fetchone()[0], cur.sfqid)
    if a.dry_run:
        return
    cur.execute("CALL SYSTEM$CREATE_SEMANTIC_VIEW_FROM_YAML('LINKML_METRICS.RAW', %s, FALSE)", (text,))
    print("create:", cur.fetchone()[0], cur.sfqid)
    name = f"LINKML_METRICS.RAW.{model['name']}"
    back = yaml.safe_load(cur.execute(f"SELECT SYSTEM$READ_YAML_FROM_SEMANTIC_VIEW('{name}')").fetchone()[0])
    want, got = members(model), members(back)
    print("members in file:", len(want), "on the object:", len(got), "same names:", set(want) == set(got))
    diff = [k for k in want if k in got and want[k] != got[k]]
    print("is_enum / sample_values differing:", diff[:10] or "none")
    vq_file = sorted(v["name"].lower() for v in model.get("verified_queries", []))
    vq_obj = sorted(v["name"].lower() for v in back.get("verified_queries", []))
    print("verified queries:", vq_file, "on the object:", vq_obj)
    print(cur.execute(f"SHOW SEMANTIC VIEWS LIKE '{model['name']}' IN SCHEMA LINKML_METRICS.RAW").fetchall()[0][:4])
    print(cur.execute("SELECT CURRENT_ROLE(), CURRENT_SECONDARY_ROLES()").fetchone())


if __name__ == "__main__":
    main()
