---
name: linkml-probe-py
description: Platform probe for the linkml-metrics project, written for the code_execution tool (Python). Use only when the user asks to run the linkml probe. Do not use for any other request.
instructions: |
  Use the code execution tool (Python) only. Run each step exactly once, in order. Do not retry a step, do not fix errors, do not run any other tool.
  1. Run this Python and keep its full output, errors included:
     import os
     print("cwd:", os.getcwd())
     hits = []
     for root, dirs, files in os.walk("/"):
         dirs[:] = [d for d in dirs if os.path.join(root, d) not in ("/proc", "/sys", "/usr")]
         for f in files:
             if f in ("probe.py", "SKILL.md"):
                 hits.append(os.path.join(root, f))
     print("\n".join(hits[:50]) or "no probe.py or SKILL.md found")
  2. If step 1 found a probe.py, run it with exec(open(<that path>).read()). Otherwise run this inline code. Keep the full output, errors included:
     import snowflake.connector as sc; print(sc.connect().cursor().execute("SELECT CURRENT_ROLE(), CURRENT_SECONDARY_ROLES(), COUNT(*) FROM LINKML_METRICS.RAW.FCT_FORECAST").fetchall())
  3. Run this Python and keep its output (environment variable NAMES only, never values):
     import os; print("\n".join(sorted(k for k in os.environ if "SNOWFLAKE" in k.upper())) or "none")
  Output contract: three fenced blocks, step 1, step 2, step 3, each holding the raw output verbatim, then one line saying whether probe.py was present and at which path. Nothing else.
---

# linkml-probe-py

A three-step platform probe for the code execution tool (Python). Run each step exactly once, in order. Do not retry a
step, do not fix errors, do not run any other tool.

1. Run this Python and keep its full output, errors included:

```python
import os
print("cwd:", os.getcwd())
hits = []
for root, dirs, files in os.walk("/"):
    dirs[:] = [d for d in dirs if os.path.join(root, d) not in ("/proc", "/sys", "/usr")]
    for f in files:
        if f in ("probe.py", "SKILL.md"):
            hits.append(os.path.join(root, f))
print("\n".join(hits[:50]) or "no probe.py or SKILL.md found")
```

2. If step 1 found a `probe.py`, run it with `exec(open(<that path>).read())`. Otherwise run this inline code. Keep
   the full output, errors included:

```python
import snowflake.connector as sc; print(sc.connect().cursor().execute("SELECT CURRENT_ROLE(), CURRENT_SECONDARY_ROLES(), COUNT(*) FROM LINKML_METRICS.RAW.FCT_FORECAST").fetchall())
```

3. Run this Python and keep its output (environment variable names only, never values):

```python
import os; print("\n".join(sorted(k for k in os.environ if "SNOWFLAKE" in k.upper())) or "none")
```

Output contract: three fenced blocks, `step 1`, `step 2`, `step 3`, each holding the raw output verbatim, then one
line saying whether probe.py was present and at which path. Nothing else.
