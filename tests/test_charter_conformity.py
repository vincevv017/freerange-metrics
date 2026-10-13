"""Charter conformity (session 8c, owner's decision 1): every sentence docs/configurations.md imposes on every
configuration is present word for word in the instructions of the six configurations, where the charter places it.

The sentences are read from the charter itself, not restated here:
- the common response instruction (section 1, "Response instruction (identical)"): the whole `response` text of each
  configuration, which carries the warnings sentence (version 7) and the data freshness line (version 10);
- the basis sentence (version 8, (a)) and the grain rule (version 9), in each configuration's `orchestration`.

Written before the fix of B2's generator: it failed on B2's grain rule (version 9 missed a generated target).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
CHARTER = (ROOT / "docs" / "configurations.md").read_text()
SPECS = {"A": "snowflake/phase4_others/a/agent_a.yaml", "B1": "snowflake/phase4_others/b1/agent_b1.yaml",
         "B2": "generated/agent_b2.yaml", "C": "generated/agent_c.yaml", "D": "snowflake/phase4_others/d/agent_d.yaml",
         "DP": "snowflake/phase4_others/d/agent_dp.yaml", "C_RAW": "generated/agent_c_raw.yaml"}   # C-raw: session 13


def norm(s: str) -> str:
    return " ".join(s.split())


def quoted(pattern: str) -> str:
    m = re.search(pattern, CHARTER)
    assert m, pattern
    return norm(m.group(1))


RESPONSE = quoted(r'Response instruction \(identical\) \| "([^"]*)"')
BASIS = quoted(r'\(a\) One basis sentence for every configuration.*?: "(Coverage is always in months\.[^"]*)"')
GRAIN = quoted(r'Replaced for every configuration by: "(The grain follows the question\.[^"]*)"')
WARNINGS = quoted(r'gains one sentence for every configuration: "([^"]*)"')
FRESHNESS = quoted(r'verbatim: "(When you give a figure, end with one line: \'Data freshness: <the latest month with '
                   r'stock data>\', taken from what a tool returned\.)"')


def instructions(cfg: str) -> dict:
    s = yaml.safe_load((ROOT / SPECS[cfg]).read_text())["instructions"]
    return {k: norm(v) for k, v in s.items()}


def test_the_charter_sentences_are_found():
    assert RESPONSE.startswith("Answer in two to five sentences.") and WARNINGS in RESPONSE and FRESHNESS in RESPONSE
    assert BASIS.endswith("Closing stock and forecast follow the same basis rule.")
    assert GRAIN.endswith("unless the question asks for them.")


@pytest.mark.parametrize("cfg", SPECS)
def test_common_response_word_for_word(cfg):
    assert instructions(cfg)["response"] == RESPONSE


@pytest.mark.parametrize("cfg", SPECS)
def test_basis_sentence_in_orchestration(cfg):
    assert BASIS in instructions(cfg)["orchestration"]


@pytest.mark.parametrize("cfg", SPECS)
def test_grain_rule_in_orchestration(cfg):
    assert GRAIN in instructions(cfg)["orchestration"]
