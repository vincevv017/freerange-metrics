"""Session 9a, decision D066: the skill pre-check, a harness guard before each stage. No call: the stage is a fake cursor.

For every skill path named in the frozen specs (SKILLS_D and SKILLS_DP): LIST, stop if a repository file is missing or
0 B; GET to a temporary directory as LINKML_SVC, compare each file's sha256 with the repository, delete the copies. Any
mismatch halts the stage before its first call. LIST sizes and md5 are never compared (stored sizes are encrypted,
rounded up to the next multiple of 16: SKILL.md 3,369 B is listed 3,376, finding 49).
"""

from __future__ import annotations

import hashlib
import importlib.util
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("campaign", ROOT / "eval" / "campaign.py")
campaign = importlib.util.module_from_spec(_spec)
sys.modules["campaign"] = campaign
_spec.loader.exec_module(campaign)

SKILL = ROOT / "snowflake" / "phase4_others" / "skill" / "linkml-coverage"
PATHS = {"LINKML_D": "@LINKML_METRICS.RAW.SKILLS_D/skills/linkml-coverage",
         "LINKML_DP": "@LINKML_METRICS.RAW.SKILLS_DP/skills/linkml-coverage"}


def test_skill_sources_are_read_from_the_frozen_specs():
    src = campaign.skill_sources()
    assert src == {agent: [("linkml-coverage", path)] for agent, path in PATHS.items()}


class FakeStage:
    """LIST and GET on the two stages, as LINKML_SVC. files: stage path -> {name: bytes}."""

    def __init__(self, files: dict[str, dict[str, bytes]], user="LINKML_SVC"):
        self.files, self.user, self.sql, self.out, self.got_dirs = files, user, [], [], []

    def execute(self, sql, params=None):
        self.sql.append(sql)
        m = re.match(r"(LIST|GET) (@\S+?)/? ?(?:'file://(.+?)/?')?$", sql)
        if sql.startswith("SELECT CURRENT_USER()"):
            self.out = [(self.user, "LINKML_METRICS_ROLE", "[]")]
        elif m and m.group(1) == "LIST":
            stage, sub = m.group(2)[1:].split("/", 1)
            short = stage.split(".")[-1].lower()
            self.out = [(f"{short}/{sub}/{n}", -(-len(b) // 16) * 16 if b else 0, "0" * 32, "Mon, 5 Oct 2026")
                        for n, b in self.files.get(m.group(2), {}).items()]
        elif m and m.group(1) == "GET":
            d = Path(m.group(3))
            self.got_dirs.append(d)
            self.out = []
            for n, b in self.files.get(m.group(2), {}).items():
                (d / n).write_bytes(b)
                self.out.append((n, len(b), "DOWNLOADED", ""))
        else:
            self.out = []
        return self

    def fetchall(self):
        return self.out

    def fetchone(self):
        return self.out[0] if self.out else None


def repo() -> dict[str, bytes]:
    return {p.name: p.read_bytes() for p in SKILL.iterdir() if not p.name.startswith(".")}


def test_an_equal_stage_passes_on_sha256_and_ignores_list_sizes_and_md5():
    cur = FakeStage({p: repo() for p in PATHS.values()})
    res = campaign.skill_precheck(cur)
    assert res["ok"] and res["caller"] == ["LINKML_SVC", "LINKML_METRICS_ROLE", "[]"]
    for agent, path in PATHS.items():
        files = {f["name"]: f for f in res["skills"][f"{agent} linkml-coverage"]["files"]}
        assert set(files) == {"SKILL.md", "coverage.py"}
        assert files["SKILL.md"]["list_size"] == 3376 and files["SKILL.md"]["size"] == 3369     # padded, not a drift
        assert files["SKILL.md"]["sha256"] == hashlib.sha256((SKILL / "SKILL.md").read_bytes()).hexdigest()
        assert all(f["equal"] for f in files.values())
    assert cur.sql[:2] == ["USE SECONDARY ROLES NONE", "SELECT CURRENT_USER(), CURRENT_ROLE(), CURRENT_SECONDARY_ROLES()"]
    assert cur.got_dirs and not any(d.exists() for d in cur.got_dirs)                   # the copies are deleted


@pytest.mark.parametrize("change, why", [
    (lambda f: f.pop("coverage.py"), "missing on the stage: coverage.py"),
    (lambda f: f.update({"SKILL.md": b""}), "0 B on the stage: SKILL.md"),
    (lambda f: f.update({"coverage.py": f["coverage.py"] + b"\n"}), "sha256 differs: coverage.py"),
    (lambda f: f.update({"notes.txt": b"x"}), "no repository file: notes.txt"),
])
def test_a_missing_empty_changed_or_extra_file_fails(change, why):
    files = {p: repo() for p in PATHS.values()}
    change(files[PATHS["LINKML_DP"]])
    cur = FakeStage(files)
    res = campaign.skill_precheck(cur)
    assert not res["ok"] and any(why in p for p in res["problems"]) and all("LINKML_DP" in p for p in res["problems"])
    assert not any(d.exists() for d in cur.got_dirs)


def test_a_missing_or_empty_file_stops_before_the_get():
    files = {p: repo() for p in PATHS.values()}
    files[PATHS["LINKML_D"]]["SKILL.md"] = b""
    cur = FakeStage(files)
    res = campaign.skill_precheck(cur)
    assert not res["ok"] and not any(s.startswith(f"GET {PATHS['LINKML_D']}") for s in cur.sql)


def test_another_caller_than_linkml_svc_fails():
    res = campaign.skill_precheck(FakeStage({p: repo() for p in PATHS.values()}, user="PERSO"))
    assert not res["ok"] and any("LINKML_SVC" in p for p in res["problems"])


# ------------------------------------------------------------------------------------------------ in the stage run

@pytest.fixture
def run_dir(monkeypatch, tmp_path):
    monkeypatch.setattr(campaign, "RUN", tmp_path)
    monkeypatch.setattr(campaign, "declared_version", lambda agent: campaign.frozen_versions()[agent])
    seen = []

    def run_turn(cfg, qid, rep, stage, blk, st):
        rec = st.d["turns"].setdefault(f"{cfg}|{qid}|{rep}", {"attempts": []})
        lab = campaign.label(cfg, qid, stage, rep, len(rec["attempts"]) + 1)
        rec["attempts"].append({"label": lab, "ok": True})
        rec["done"] = lab
        st.save()
        seen.append(lab)
        return {"calls": [{"status": 200}], "tokens": {}}, 1, False
    monkeypatch.setattr(campaign, "run_turn", run_turn)
    monkeypatch.setattr(campaign, "plan", lambda stage, cut=0: [
        {"config": "C", "cap": 26, "turns": [{"qid": "WARMUP", "rep": 1}, {"qid": "T1", "rep": 1}]}])
    return seen


def test_a_failed_precheck_halts_the_stage_before_its_first_call(run_dir, monkeypatch, capsys):
    monkeypatch.setattr(campaign, "skill_precheck", lambda cur=None: {"ok": False, "problems": ["LINKML_DP x: 0 B"]})
    campaign.run(1, 0, 1, None)
    st = campaign.State(1)
    assert run_dir == [] and "skill pre-check" in st.guard.halted and st.d["skill_checks"][-1]["ok"] is False
    assert "skill pre-check" in capsys.readouterr().out
    monkeypatch.setattr(campaign, "skill_precheck", lambda cur=None: {"ok": True, "problems": []})
    campaign.run(1, 0, 1, None)                                  # a halt is kept on resume: the owner decides
    assert run_dir == []


def test_a_passed_precheck_is_recorded_and_the_stage_runs(run_dir, monkeypatch):
    monkeypatch.setattr(campaign, "skill_precheck", lambda cur=None: {"ok": True, "problems": [], "at_utc": "x"})
    campaign.run(1, 0, 1, None)
    st = campaign.State(1)
    assert len(run_dir) == 2 and st.d["skill_checks"] == [{"ok": True, "problems": [], "at_utc": "x"}]
