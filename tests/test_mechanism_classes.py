"""Session 13, step 1c: every campaign question has one mechanism class, and the recount by class sums to the totals."""

import importlib.util
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_s = importlib.util.spec_from_file_location("mechanism_recount", ROOT / "eval" / "mechanism_recount.py")
mr = importlib.util.module_from_spec(_s)
_s.loader.exec_module(mr)
FIXTURES = {1: ROOT / "eval" / "fixtures" / "grades_campaign-s1.json",
            2: ROOT / "eval" / "fixtures" / "grades_campaign-s2.json"}


def test_every_question_has_one_class():
    classes = mr.load_classes()
    for path in FIXTURES.values():
        for g in json.loads(path.read_text()):
            assert classes[g["question_id"]]["class"] in mr.CLASSES, g["question_id"]
    for qid, c in classes.items():
        assert set(c) <= {"class", "gapfill_dependent", "reason", "also", "also_reason"}, qid
        assert ("also" in c) == ("also_reason" in c), qid
        assert isinstance(c["gapfill_dependent"], bool) and bool(c.get("reason")) == c["gapfill_dependent"], qid


def test_recount_sums_to_the_fixture_totals():
    classes = mr.load_classes()
    for stage, path in FIXTURES.items():
        grades = json.loads(path.read_text())
        for key in ("verdict", "verdict_figure_only"):
            table = mr.counts(grades, classes, key)
            assert mr.sums_match(table)
            want = Counter((g["config"], g[key]) for g in grades)
            got = Counter({(cfg, v): t["TOTAL"][v] for cfg, t in table.items() for v in mr.VERDICTS if t["TOTAL"][v]})
            assert got == want, (stage, key)
        # The fixtures are the 3.2 grades of record: their totals are the published ones.
        table = mr.counts(grades, classes)
        assert {cfg: (t["TOTAL"]["correct"], t["TOTAL"]["wrong"]) for cfg, t in table.items()} == mr.PUBLISHED[stage]["3.2"]
        fo = mr.counts(grades, classes, "verdict_figure_only")
        assert {cfg: (t["TOTAL"]["correct"], t["TOTAL"]["wrong"]) for cfg, t in fo.items()} == \
            mr.PUBLISHED[stage]["figure_only"]


def test_gapfill_dependent_questions():
    classes = mr.load_classes()
    assert {q for q, c in classes.items() if c["gapfill_dependent"]} == \
        {"T9", "CS_LAST_MONTH_GAP", "CS_FAMILY", "N1", "N2"}


def test_n1_and_n2_also_carry_coverage():
    """Owner, session 13 step 3: N1 and N2 stay CLOSING_STOCK (the sums hold) and are marked also COVERAGE, because
    their graded answer carries a coverage criterion; the recount shows them on a line of their own."""
    import json
    classes = mr.load_classes()
    marked = {q for q, v in classes.items() if v.get("also")}
    assert marked == {"N1", "N2"} and all(classes[q]["also"] == "COVERAGE" and classes[q]["class"] == "CLOSING_STOCK"
                                          for q in marked)
    s2 = json.loads((ROOT / "eval" / "fixtures" / "grades_campaign-s2.json").read_text())
    for g in (x for x in s2 if x["question_id"] in marked):
        assert "coverage" in g["criteria"] and "closing_stock" in g["criteria"], g["label"]
    extra = mr.also(s2, classes)["COVERAGE"]
    assert {c: sum(v.values()) for c, v in extra.items()} == {"B2": 4, "C": 4}
