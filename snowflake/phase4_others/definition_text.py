"""Session 8 (charter version 5): the sections of docs/DEFINITION.md given verbatim as agent instructions, without
the lines that start with "Provenance:" (session decisions, data/traps.yaml and trap names, the contract's internal
names), which are for the reader of the repository, not for the model."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def extract(sections: tuple[int, ...]) -> str:
    text = (ROOT / "docs" / "DEFINITION.md").read_text()
    parts = re.split(r"(?m)^## (\d+)\. ", text)
    sec = {int(parts[i]): parts[i] + ". " + parts[i + 1].strip() for i in range(1, len(parts), 2)}
    out = "\n\n".join(sec[n] for n in sections)
    out = "\n".join(line for line in out.splitlines() if not line.startswith("Provenance:"))
    return re.sub(r"\n{3,}", "\n\n", out).strip()
