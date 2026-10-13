"""Agent C evaluation (session 7, step 4): each reference question asked once to LINKML_C, as LINKML_SVC.

    python snowflake/phase4_agent_c/ask_questions.py --log-dir <scratch dir outside the repo>

Questions: every entry of generated/reference_questions.yaml with asked_to_agent_c true, in file order, the drill
asked in the thread of its parent (one thread file per parent). Then one out-of-scope question (closing stock, which
the coverage tool does not compute), asked only if every earlier call succeeded, so the session stays at 15 calls.
Each call goes through snowflake/probe_b/mount/run_call.py (budget c, cap 15, policy c). Raw events, traces and
summaries stay in --log-dir: they carry the account host.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
RUN_CALL = ROOT / "snowflake" / "probe_b" / "mount" / "run_call.py"
OUT_OF_SCOPE = ("CS_OUT_OF_SCOPE",
                "What was the closing stock of the oat cereal bar 1 kg (SKU-H11) in Switzerland for Q2 2026?")


def ask(qid: str, text: str, log_dir: Path, thread: Path | None = None, save: Path | None = None) -> dict:
    cmd = [sys.executable, str(RUN_CALL), "--agent", "LINKML_C", "--question", text, "--label", qid,
           "--budget", "c", "--policy", "c", "--log-dir", str(log_dir)]
    if thread:
        cmd += ["--thread", str(thread)]
    if save:
        cmd += ["--save-thread", str(save)]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL)
    tag = "".join(c if c.isalnum() else "_" for c in qid.lower()).strip("_")
    return json.loads((log_dir / f"summary_{tag}.json").read_text())


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--log-dir", type=Path, required=True)
    a = ap.parse_args()
    a.log_dir.mkdir(parents=True, exist_ok=True)
    qs = [q for q in yaml.safe_load((ROOT / "generated" / "reference_questions.yaml").read_text())["questions"]
          if q["asked_to_agent_c"]]
    parents = {q["follows"] for q in qs if q.get("follows")}
    clean = True
    for q in qs:
        thread = a.log_dir / f"thread_{q['follows']}.json" if q.get("follows") else None
        save = a.log_dir / f"thread_{q['id']}.json" if q["id"] in parents else None
        s = ask(q["id"], q["question"], a.log_dir, thread, save)
        ok = all(c["status"] < 400 for c in s["calls"]) and len(s["calls"]) == 1 and "stopped" not in s
        clean = clean and ok
        print(q["id"], "ok" if ok else "FAILED", [c["request_id"] for c in s["calls"]], flush=True)
    if clean:
        s = ask(*OUT_OF_SCOPE, a.log_dir)
        print(OUT_OF_SCOPE[0], [c["request_id"] for c in s["calls"]], flush=True)
    else:
        print(OUT_OF_SCOPE[0], "skipped: an earlier call failed")


if __name__ == "__main__":
    main()
