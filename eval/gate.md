# Gate between the stages (session 8c, step 3)

Written before any campaign call. Code: `eval/gate.py` (reads the stage 1 grades, writes `eval/stage2.yaml`); tests:
`tests/test_gate.py`, on the recorded smoke answers of sessions 8 and 8b and on synthetic ones. Tags as in
`docs/phase5_notes.md`.

## 1. The rule that selects stage 2 questions

Inputs: the grades of stage 1 (`python eval/campaign.py grade --stage 1`, rubric 3.2), every turn with its answer text
and tables. Every manual verdict is decided by the owner first (`eval/manual_decisions.yaml`, by request id); the gate
refuses to run while one is open.

A stage 1 question **discriminates**, and goes to stage 2, if at least one of these holds across the six configurations:

| Reason | How it is read |
|---|---|
| A configuration fails it | verdict `wrong` |
| The answers differ in value beyond rounding to 0.05 | the answer's figure: the candidate number nearest to the expected value (months for coverage; for a drill or G2, per member, the numbers on the member's line); two figures more than 0.05 apart, or a figure on one side and none on the other. "8.45" against "8.5" is not a difference; "9" against "8.5" is, though the precision rule grades both correct. EUR amounts (a question whose expected unit is EUR: G2) are the same within 0.5 percent of the larger (owner, 2026-10-07) |
| The answers differ in the products a list gives | the set of SKU codes of a list answer (selection questions) |
| The answers differ in a parameter | what the answer says it used: the analysis month named (June 2026), the basis named (kg or L equivalent, value, own unit), the default scope stated (BULK excluded, for questions whose expected warnings carry DEFAULT_SCOPE_EXCLUDED); compared only among answers that give a figure. The basis named is not compared when every configuration is correct (owner, 2026-10-07) |
| The answers differ in the warnings relayed | `warnings_relayed` of the grader: yes, partial, no |
| The answers differ in refusal | one answer gives no figure and refuses or asks, another gives a figure |

**Never counted**: ROWS_COMMENTED and FRESHNESS_STATED (decision 7). A question with none of the reasons is not
selected.

**Forced by the owner** (session 9a closing, 2026-10-07): `python eval/gate.py <grades> --force <QID> ...
--forced-by "<who, date>"`. Each forced question is selected with the reason `forced` (the author and date), beside any
reason of its own, is listed under `forced` in `eval/stage2.yaml`, and never enters `drop_order`. Only a stage 1
question can be forced; a held-out or unknown id, or a forced question without `--forced-by`, stops the gate. Held-out questions were not asked in stage 1; `eval/campaign.py` adds them to stage 2 whatever the gate says.

Grain is not compared as such: tool parameters exist only for C (and the extraction queries of D′), and the SQL of the
semantic view configurations is not comparable with a procedure call. A grain read differently shows in the figure (a
family figure against an item row), in the products of a list, or in a failed verdict. [inferred]

Outputs in `eval/stage2.yaml`:
- `discriminating`: the selected questions, in the order of the reference file, with their `reasons` (the
  configurations behind each reason);
- `a_passed`: the selected questions A answered correctly in stage 1 (A's stage 2 repetitions, decision 6);
- `drop_order`: for cut 3, the questions where only one configuration differs, those that differ by warnings relayed
  only first, then by fewer failed configurations; never a held-out question;
- `not_selected`.

On the recorded smoke (T1, T6, T9, CS_LAST_MONTH_GAP of sessions 8 and 8b, rubric 3.2): T1 (C and D fail the wording
rule) and T9 (every configuration fails the wording rule of rubric 3.x; D and D′ name a different basis) are selected;
T6 (every configuration asks for the month) and CS_LAST_MONTH_GAP (every figure 0; A's and B1's 400 and 350 are
history, by the owner's rule) are not. [measured, `tests/test_gate.py`]

## 2. Stage 1 events that force a harness fix, and what is replayed

A harness event is a failure of the measuring path, not of the agent. It forces a harness fix (tests first, committed)
and a replay of **the touched questions of the touched configuration only**, under new attempt labels
(`campaign-s1-a<m>`), never the whole campaign (decision 5: D failing for a harness reason replays D alone).

| Event | Seen as | Replay |
|---|---|---|
| Non-200 status or timeout on a call (status 0) that the platform does not explain by the agent (429, 5xx, a dropped stream) | `calls[].status`, three in a row stop the block | the failed turns |
| A turn with no final `response` event, or a summary that is missing | `summary_<label>.json` absent or `text` empty with no tool refusal | the turn |
| A permission request the policy should have allowed (D, D′: the exact `coverage.py` command refused by `dp_allowed`) or options the runner does not know | `permission_requests[].decision` Deny on a script command; the runner's "unexpected permission options" exit | the turn |
| A client-side SQL execution failed by the client (connection, row limit), not by the statement | `client_sql.jsonl` status error with a client message | the turn |
| A thread file missing or wrong for BULK_SCOPE_DRILL | the drill answered without its parent | the drill and its parent |
| A label refused, a cap or a token ceiling set wrong in the runner | run_call exit with "label", "cap", or exit 3 on a turn whose tokens are within the smokes' range | the block's remaining turns |
| A trace that cannot be read after the stage (`campaign.py traces`) | empty trace for a completed turn | none: the turn stands, the trace gap is recorded |

Not harness events, recorded and never replayed: a wrong answer, a refusal, a clarifying question, a tool call the
policy rightly denied, a model that computes by itself, sorts or comments rows, a turn the token guard stopped because
the agent used more context than in the smokes (the block stops; its turns stand as they are).

## 3. Between the stages

- Any change to an agent spec, instruction, tool description, skill, procedure, view, contract or charter between
  the stages restarts the campaign (stage 1 included).
- A harness fix (runner, grader code, rubric) does not restart it; a rubric change after a graded turn is a new rubric
  version, applied to every turn of both stages, and recorded.
- The cost read between the stages (`eval/campaign.md`) gives the go or no-go of stage 2 and the cut to apply.
