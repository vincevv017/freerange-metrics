---
name: linkml-probe
description: Platform probe for the linkml-metrics project. Use only when the user asks to run the linkml probe. Do not use for any other request.
instructions: |
  Run each step exactly once, in order. Do not retry a step, do not fix errors, do not run any other tool.
  1. With bash, run exactly this command from this skill's folder and keep its full output, errors included:
     python3 probe.py; env | cut -d= -f1 | grep -i snowflake | sort
  2. With the Snowflake SQL tool, run exactly this statement and keep the result:
     SELECT CURRENT_ROLE(), CURRENT_SECONDARY_ROLES(), COUNT(*) FROM LINKML_METRICS.RAW.FCT_FORECAST
  Output contract: two fenced blocks, step 1 then step 2, each holding the raw output verbatim. Nothing before or after them.
---

# linkml-probe

A two-step platform probe. Run each step exactly once, in order. Do not retry a step, do not fix errors, do not run any other tool.

1. With bash, run exactly this command from this skill's folder and keep its full output, errors included:
   `python3 probe.py; env | cut -d= -f1 | grep -i snowflake | sort`
   (The second part prints environment variable NAMES only, never values.)
2. With the Snowflake SQL tool, run exactly this statement and keep the result:
   `SELECT CURRENT_ROLE(), CURRENT_SECONDARY_ROLES(), COUNT(*) FROM LINKML_METRICS.RAW.FCT_FORECAST`

Output contract: two fenced blocks, `step 1` then `step 2`, each holding the raw output verbatim. Nothing before or after them.
