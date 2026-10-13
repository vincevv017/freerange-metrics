"""
Session 11c: the generated reference (docs/reference/) and the links of the published guides.

- drift: compiler/gen_reference.py regenerates docs/reference/metamodel.md and failure_modes.md into a temporary
  folder; the committed files must be byte-identical.
- links: every relative link and #anchor in README.md, docs/GUIDE.md, docs/CONTRACT.md and docs/reference/ resolves:
  the file exists, and an anchor is a heading of the target in GitHub's slug form or an explicit <a id> anchor. The
  slug is computed here, independently of the generator.
"""

from __future__ import annotations

import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PAGES = ["README.md", "docs/GUIDE.md", "docs/CONTRACT.md", *sorted(
    str(p.relative_to(ROOT)) for p in (ROOT / "docs" / "reference").glob("*.md"))]


def test_reference_does_not_drift(tmp_path):
    r = subprocess.run([sys.executable, "compiler/gen_reference.py", "--out-dir", str(tmp_path)], cwd=ROOT,
                       capture_output=True, text=True, timeout=300)
    assert r.returncode == 0, r.stdout + r.stderr
    for name in ("metamodel.md", "failure_modes.md"):
        assert (tmp_path / name).read_bytes() == (ROOT / "docs" / "reference" / name).read_bytes(), \
            f"docs/reference/{name} differs: run python compiler/gen_reference.py"


def slug(heading: str) -> str:
    t = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", heading)        # a link keeps its text
    t = re.sub(r"<[^>]+>", "", t).strip().lower()               # tags dropped
    t = "".join(ch for ch in t if ch.isalnum() or ch in "-_ ")  # punctuation dropped, - and _ kept
    return t.replace(" ", "-")


def page_text(path: Path) -> str:
    """The page without HTML comments and fenced code, where nothing is a link or a heading."""
    text = re.sub(r"<!--.*?-->", "", path.read_text(encoding="utf-8"), flags=re.S)
    return re.sub(r"^```.*?^```", "", text, flags=re.S | re.M)


def page_anchors(path: Path) -> set[str]:
    text, seen, out = page_text(path), Counter(), set()
    for h in re.findall(r"^#{1,6} (.+?)\s*$", text, flags=re.M):
        s = slug(h)
        out.add(s if seen[s] == 0 else f"{s}-{seen[s]}")
        seen[s] += 1
    return out | set(re.findall(r'<a id="([^"]+)"', text))


def links(path: Path) -> list[str]:
    text = page_text(path)
    md = re.findall(r"\]\(([^)\s]+)\)", text)
    html = re.findall(r'(?:src|srcset|href)="([^"]+)"', text)
    return [x for x in md + html if not re.match(r"^[a-z]+:", x)]          # http, https, mailto: not checked here


@pytest.mark.parametrize("page", PAGES)
def test_every_relative_link_and_anchor_resolves(page):
    src = ROOT / page
    bad = []
    for link in links(src):
        target, _, frag = link.partition("#")
        dest = (src.parent / target).resolve() if target else src
        if not dest.exists():
            bad.append(f"{link}: no such file")
            continue
        if frag and dest.suffix == ".md" and frag not in page_anchors(dest):
            bad.append(f"{link}: no such anchor in {dest.relative_to(ROOT)}")
    assert not bad, bad


def test_the_reference_pages_are_checked():
    assert {"docs/reference/metamodel.md", "docs/reference/failure_modes.md"} <= set(PAGES)
