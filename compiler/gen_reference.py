"""
Eighth generator: the reference of the vocabulary and of the traps -> docs/reference/.

    python compiler/gen_reference.py                         # writes docs/reference/metamodel.md and failure_modes.md
    python compiler/gen_reference.py --out-dir /tmp/ref      # writes elsewhere (the drift test uses this)

1. metamodel.md: LinkML's single-page data dictionary of contract/metamodel.yaml (gen-markdown-datadict, called
   through its Python class), post-processed so that it reads and links on GitHub: the Mermaid diagrams and LinkML's
   own metamodel version stamp are removed (the stamp changes with the installed LinkML); every explicit slot anchor
   gets a `slot-` prefix (two of them, `attributes` and `ownership`, collided with heading anchors); a link whose text
   names a class or an enum points to its heading, any other link to the attribute of the class it sits in, else to
   the top-level slot (the data dictionary pointed class attributes at anchors it never wrote). The generator fails if
   a link still does not resolve. Session 11c: each attribute that compiler/supported.py lists is marked in its
   description, Fixed (only one value is supported; another one is refused by the generators) or Documentation only.
2. failure_modes.md: the contract's failure modes (id, name, wrong and correct behaviour, reference question), for
   each the contract elements that declare `prevents` on it, and its trap in data/traps.yaml (the member, the correct
   answer, the value each named wrong behaviour returns). One heading per id, so `failure_modes.md#t1` links T1.

Read-only on the contract, the metamodel and data/traps.yaml. The output is deterministic: same inputs and LinkML
version, same bytes. tests/test_reference.py regenerates both and fails on any difference.
"""

from __future__ import annotations

import argparse
import re
from collections import Counter
from pathlib import Path

import yaml

try:
    from compiler import supported
except ImportError:                       # run as a script: compiler/ is on sys.path
    import supported

ROOT = Path(__file__).resolve().parents[1]
METAMODEL = ROOT / "contract" / "metamodel.yaml"
CONTRACT_PATH = ROOT / "contract" / "stock_coverage.yaml"
TRAPS_PATH = ROOT / "data" / "traps.yaml"
OUT_DIR = ROOT / "docs" / "reference"
LINK = re.compile(r"\[([^\]]+)\]\(#([^)]+)\)")


def github_slug(text: str) -> str:
    """The anchor GitHub gives a heading: link and tag markup dropped, lower case, punctuation other than - and _
    removed, spaces to hyphens."""
    t = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
    t = re.sub(r"<[^>]+>", "", t)
    t = re.sub(r"[^\w\- ]", "", t.strip().lower())
    return t.replace(" ", "-")


def anchors(markdown: str) -> set[str]:
    """Every anchor of a page: heading slugs (a repeated heading gets -1, -2...) and explicit <a id> anchors."""
    out, seen = set(), Counter()
    in_code = False
    for line in markdown.splitlines():
        if line.startswith("```"):
            in_code = not in_code
            continue
        m = re.match(r"^#{1,6} (.*)$", line)
        if m and not in_code:
            s = github_slug(m.group(1))
            out.add(s if seen[s] == 0 else f"{s}-{seen[s]}")
            seen[s] += 1
    return out | set(re.findall(r'<a id="([^"]+)"', markdown))


# ================================================================================================ metamodel.md

def metamodel_md() -> str:
    from linkml.generators.markdowndatadictgen import MarkdownDataDictGen

    meta = yaml.safe_load(METAMODEL.read_text())
    named = set(meta["classes"]) | set(meta["enums"])
    text = MarkdownDataDictGen(str(METAMODEL)).serialize()
    text = re.sub(r"```mermaid\n.*?```\n?", "", text, flags=re.S)
    text = re.sub(r"## Class Diagram\n.*?(?=## Classes\n)", "", text, flags=re.S)
    text = "\n".join(l for l in text.splitlines() if not l.startswith("**metamodel version:**"))
    ids = set(re.findall(r'<a id="([^"]+)"', text))
    text = re.sub(r'<a id="([^"]+)"', r'<a id="slot-\1"', text)

    out, section, cls = [], None, None
    for line in text.splitlines():
        if line.startswith("## "):
            section, cls = line[3:].strip(), None
        elif line.startswith("### ") and section == "Classes":
            cls = line[4:].strip()

        def target(m: re.Match) -> str:
            label, frag = m.group(1), m.group(2)
            if label in named:
                return f"[{label}](#{github_slug(label)})"
            t = label.lower()
            if cls and f"{cls.lower()}__{t}" in ids:
                return f"[{label}](#slot-{cls.lower()}__{t})"
            if t in ids:
                return f"[{label}](#slot-{t})"
            if frag in ids:
                return f"[{label}](#slot-{frag})"
            return m.group(0)
        out.append(LINK.sub(target, line))
    body = re.sub(r"\n{4,}", "\n\n\n", "\n".join(out)).strip("\n")
    body = body.replace("# METRIC_SEMANTICS", "# Metamodel reference: metric_semantics", 1)
    head = ("<!-- GENERATED from contract/metamodel.yaml by compiler/gen_reference.py (LinkML gen-markdown-datadict, "
            "post-processed for GitHub). Do not edit: change the metamodel and run `python compiler/gen_reference.py`. "
            "tests/test_reference.py regenerates this file and fails on any difference. -->\n")
    intro = ("\nThe vocabulary of a metric contract: every class, its attributes (cardinality, range, description), "
             "every top-level slot and every enum with its values. `contract/stock_coverage.yaml` is an instance of it. "
             "The traps the contract guards against are in [failure_modes.md](failure_modes.md).\n\n"
             "An attribute marked **Fixed** is not read by the compiler: the generated objects are written for one value, "
             "and a contract holding another one is refused by the generators that write its behaviour "
             "(`compiler/supported.py`). One marked **Documentation only** carries no behaviour.\n")
    title, rest = body.split("\n", 1)
    rest = mark_fixed(rest, yaml.safe_load(CONTRACT_PATH.read_text()))
    page = head + title + "\n" + intro + rest + "\n"
    unresolved = sorted({f for _, f in LINK.findall(page)} - anchors(page))
    if unresolved:
        raise ValueError(f"metamodel.md: links that do not resolve: {unresolved[:10]}")
    return page


def mark_fixed(text: str, contract: dict) -> str:
    """Append the mark of compiler/supported.py to the description of each listed attribute: in its class's table and
    in the slots table."""
    marks = {e.key: f"**Fixed: only {e.shown(contract)} is supported by this compiler.**" for e in supported.FIXED}
    marks.update({k: "**Documentation only.**" for k in supported.DOCUMENTATION_ONLY})
    anchors = {f"slot-{k.split('.')[0].lower()}__{k.split('.')[1]}": m for k, m in marks.items()}
    out, done = [], set()
    for line in text.splitlines():
        m = re.search(r'\(#(slot-[a-z]+__[a-z_]+)\)|<a id="(slot-[a-z]+__[a-z_]+)"', line)
        a = m and (m.group(1) or m.group(2))
        if a in anchors and line.startswith("|") and line.rstrip().endswith("|"):
            cells = line.rstrip()[:-1].rstrip()
            if a.startswith("slot-") and '<a id="' in line:          # slots table: the description ends the first cell
                head, sep, tail = line.partition(" | ")
                line = f"{head} {anchors[a]}{sep}{tail}"
            else:                                                    # class table: the description is the last cell
                line = f"{cells} {anchors[a]} |"
            done.add(a)
        out.append(line)
    missing = sorted(set(anchors) - done)
    if missing:
        raise ValueError(f"metamodel.md: marked attributes not found: {missing}")
    return "\n".join(out)


# ================================================================================================ failure_modes.md

SECTION_LABEL = {
    "measures": "measure", "attributes": "attribute", "measure_bases": "basis", "metrics": "metric",
    "totals_rules": "totals rule", "member_set_rules": "member-set rule", "default_scopes": "default scope",
    "analysis_periods": "analysis periods", "refusal_codes": "refusal code", "quality_expectations": "quality expectation",
    "invariants": "invariant",
}
NESTED_LABEL = {"period_aggregation": "period aggregation", "beyond_horizon": "beyond-horizon rule",
                "member_selection": "member selection", "basis_model": "basis model"}


def preventers(c: dict) -> dict[str, list[str]]:
    """failure mode id -> the contract elements that declare prevents on it, in the contract's order."""
    out: dict[str, list[str]] = {}

    def add(fm_ids, label):
        for f in fm_ids or []:
            out.setdefault(f, []).append(label)

    def walk(node, label):
        add(node.get("prevents"), label)
        for key, sub in node.items():
            if key in NESTED_LABEL and isinstance(sub, dict):
                walk(sub, f"{NESTED_LABEL[key]} `{sub.get('id', key)}`")
            elif key == "outcomes":
                for o in sub:
                    add(o.get("prevents"), f"outcome {o['order']} `{o['condition']}`")

    for key, section in c.items():
        if key in SECTION_LABEL:
            for e in section:
                walk(e, f"{SECTION_LABEL[key]} `{e['id']}`")
        elif key in NESTED_LABEL and isinstance(section, dict):
            walk(section, f"{NESTED_LABEL[key]} `{section['id']}`")
    return out


def num(v) -> str:
    if v is None:
        return "no value (null)"
    if isinstance(v, bool):
        return str(v).lower()
    if isinstance(v, (int, float)):
        return f"{v:,.4f}".rstrip("0").rstrip(".")
    if isinstance(v, dict):
        return "; ".join(f"{k} {num(x)}" for k, x in v.items())
    return str(v)


def trap_lines(t: dict, kind: str, heroes: dict) -> list[str]:
    q = t["query"]
    member = []
    for a, v in q["filters"].items():
        vals = v if isinstance(v, list) else [v]
        member.append(f"{a} " + ", ".join(f"{x} ({heroes[x]})" if x in heroes else str(x) for x in vals))
    where = "; ".join(member) if member else "no filter"
    lines = [f"- **Trap** (`data/traps.yaml`, {kind}): {where}; grain {', '.join(q.get('grain', []))}"
             + (f"; basis {q['basis']}" if q.get("basis") else "") + "."]
    if "expected_refusal" in t:
        allowed = t.get("expected_allowed_bases")
        lines.append(f"- **Correct answer:** refusal `{t['expected_refusal']}`"
                     + (f", bases allowed {', '.join(allowed)}" if allowed else "") + ".")
    else:
        unit = " months" if kind == "coverage" else " (closing stock, quantity equivalent)"
        extra = []
        if t.get("expected_flag"):
            extra.append(f"flag `{t['expected_flag']}`")
        for w, n in (t.get("expected_warnings") or {}).items():
            extra.append(f"warning `{w}` ({num(n)})")
        lines.append(f"- **Correct answer:** {num(t['expected'])}{unit if t['expected'] is not None else ''}"
                     + (", " + ", ".join(extra) if extra else "") + ".")
    wrong = t.get("wrong") or {}
    if wrong:
        lines.append("- **Wrong answers:** " + "; ".join(f"{k.replace('_', ' ')}: {num(v)}" for k, v in wrong.items()) + ".")
    return lines


def failure_modes_md() -> str:
    c = yaml.safe_load(CONTRACT_PATH.read_text())
    traps = yaml.safe_load(TRAPS_PATH.read_text())
    heroes = {h["sku"]: h["name"] for h in traps["hero_items"]}
    by_id = {t["id"]: ("coverage", t) for t in traps["traps"]}
    by_id.update({t["id"]: ("closing stock", t) for t in traps.get("closing_stock", [])})
    prev = preventers(c)
    fms = c["failure_modes"]
    out = [
        "<!-- GENERATED from contract/stock_coverage.yaml and data/traps.yaml by compiler/gen_reference.py. Do not edit: "
        "run `python compiler/gen_reference.py`. tests/test_reference.py regenerates this file and fails on any "
        "difference. -->",
        "# Failure modes",
        "",
        f"The {len(fms)} failure modes of `contract/stock_coverage.yaml` (contract {c['id']}, version {c['version']}): "
        "known ways to get the metric wrong. For each: the wrong behaviour it guards against, the correct one, its "
        "reference question, the contract elements that declare `prevents` on it, and its trap in `data/traps.yaml`: "
        "the member that forces the behaviour, the correct answer and the value each named wrong behaviour returns, "
        "at the analysis month AS_OF. The keys are explained in [metamodel.md](metamodel.md).",
        "",
        "| Id | Name | Wrong behaviour |",
        "|---|---|---|",
    ]
    out += [f"| [{f['id']}](#{github_slug(f['id'])}) | {f['name']} | {f['wrong_behaviour']} |" for f in fms]
    for f in fms:
        out += ["", f"## {f['id']}", "", f"**{f['name']}**", "",
                f"- **Wrong behaviour:** {f['wrong_behaviour']}.",
                f"- **Correct behaviour:** {f['correct_behaviour']}.",
                f"- **Reference question:** \"{f['reference_question']}\"." if f.get("reference_question") else
                "- **Reference question:** none.",
                f"- **Source:** `{f['source']}`.",
                "- **Prevented by:** " + ("; ".join(prev.get(f["id"], [])) or "nothing (a gap)") + "."]
        if f["id"] in by_id:
            kind, t = by_id[f["id"]]
            out += trap_lines(t, kind, heroes)
    page = "\n".join(out) + "\n"
    unresolved = sorted({fr for _, fr in LINK.findall(page)} - anchors(page))
    if unresolved:
        raise ValueError(f"failure_modes.md: links that do not resolve: {unresolved}")
    return page


def render() -> dict[str, str]:
    return {"metamodel.md": metamodel_md(), "failure_modes.md": failure_modes_md()}


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--out-dir", type=Path, default=OUT_DIR)
    a = p.parse_args()
    a.out_dir.mkdir(parents=True, exist_ok=True)
    for name, text in render().items():
        (a.out_dir / name).write_text(text)
        print(f"wrote {a.out_dir / name}")


if __name__ == "__main__":
    main()
