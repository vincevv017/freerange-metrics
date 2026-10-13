"""
Session 8b: carry B2's value grounding over to a regenerated semantic view YAML, without running the enrich tool again.

    python snowflake/phase4_others/b2/apply_grounding.py

Reads generated/b2_native_sv.yaml (regenerated from the contract) and the deployed enriched YAML
(LINKML_B2_SV_enriched.yaml), copies is_enum and sample_values member by member (logical table, member name), and
writes the result over LINKML_B2_SV_enriched.yaml. Fails if a grounded member is missing from the regenerated YAML or
if anything other than is_enum and sample_values differs afterwards.
"""

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
GEN = ROOT / "generated" / "b2_native_sv.yaml"
ENR = Path(__file__).resolve().parent / "LINKML_B2_SV_enriched.yaml"
KEYS = ("is_enum", "sample_values")


def strip(d):
    if isinstance(d, dict):
        return {k: strip(v) for k, v in d.items() if k not in KEYS}
    return [strip(x) for x in d] if isinstance(d, list) else d


def main():
    gen, old = yaml.safe_load(GEN.read_text()), yaml.safe_load(ENR.read_text())
    grounding = {}
    for t in old["tables"]:
        for kind in ("dimensions", "time_dimensions", "facts", "metrics"):
            for m in t.get(kind, []):
                g = {k: m[k] for k in KEYS if k in m}
                if g:
                    grounding[(t["name"], kind, m["name"])] = g
    applied = 0
    for t in gen["tables"]:
        for kind in ("dimensions", "time_dimensions", "facts", "metrics"):
            for m in t.get(kind, []):
                g = grounding.pop((t["name"], kind, m["name"]), None)
                if g:
                    m.update(g)
                    applied += 1
    assert not grounding, f"grounded members missing from the regenerated YAML: {sorted(grounding)}"
    assert strip(gen) == strip(yaml.safe_load(GEN.read_text()))
    ENR.write_text(yaml.safe_dump(gen, sort_keys=False, allow_unicode=True, width=118))
    print(f"{applied} members grounded; written {ENR}")


if __name__ == "__main__":
    main()
