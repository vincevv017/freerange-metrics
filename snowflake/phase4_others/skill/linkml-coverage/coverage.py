"""Stock coverage in months: the algorithm of the stock coverage definition, section 2.

Two ways to give the inputs, the same computation:

  numbers passed in (agent with code execution only):
    python3 coverage.py --as-of 2026-06-01 --stock 1400 --forecast '[["2026-07-01", 500], ["2026-08-01", 500]]'

  queries run by the script itself (agent with the coding toolset, Snowflake connection from the sandbox):
    python3 coverage.py --as-of 2026-06-01 --stock-sql "SELECT ..." --forecast-sql "SELECT ..."
    --stock-sql returns one row, one number: the stock at the analysis month.
    --forecast-sql returns rows (forecast month, quantity), the months after the analysis month.

The horizon is the 24 months after the analysis month (t+1 to t+24). A month of the horizon with no forecast counts
as 0. Prints one JSON object: the inputs as used, the coverage in months and the case that produced it.
"""

import argparse
import datetime as dt
import json
import re

H = 24


def add_months(d: dt.date, n: int) -> dt.date:
    y, m = divmod(d.month - 1 + n, 12)
    return dt.date(d.year + y, m + 1, 1)


def as_date(x) -> dt.date:
    if isinstance(x, dt.datetime):
        return x.date()
    if isinstance(x, dt.date):
        return x
    return dt.date.fromisoformat(str(x)[:10])


def coverage(stock, monthly: list) -> tuple:
    """Section 2. stock: S at the analysis month. monthly: f(1) .. f(24), the forecast of t+1 .. t+24."""
    if stock is None or stock == 0:
        return 0.0, "S is null or 0"
    if stock < 0:                                 # the definition does not define coverage for a negative stock
        raise SystemExit(f"negative stock ({stock}): coverage is not defined for a negative stock; check the inputs")
    total = 0.0                                   # C(n-1)
    for n, f in enumerate(monthly, start=1):
        if stock <= total + f:                    # first n with S <= C(n); f(n) > 0 here
            return (n - 1) + (stock - total) / f, "depleted within the horizon"
        total += f
    nonzero = [f for f in monthly if f > 0]
    if not nonzero:
        return None, "no forecast at all: coverage undefined"
    return stock / (sum(nonzero) / len(nonzero)), "stock outlasts the horizon: S over the mean non-zero monthly forecast"


def horizon(as_of: dt.date, pairs) -> tuple:
    """f(1)..f(24) from (month, quantity) pairs; months outside t+1..t+24 are ignored, missing months are 0."""
    months = [add_months(as_of, k) for k in range(1, H + 1)]
    by_month = {}
    for m, q in pairs:
        d = as_date(m)
        by_month[d] = by_month.get(d, 0.0) + float(q or 0)
    return [by_month.get(m, 0.0) for m in months], sum(1 for m in months if m not in by_month), months


def run_sql(cur, sql: str) -> list:
    if not re.match(r"^\s*(WITH|SELECT)\b", sql, re.I) or ";" in sql.strip().rstrip(";"):
        raise SystemExit("only one SELECT statement is accepted")
    return cur.execute(sql).fetchall()


def main() -> None:
    ap = argparse.ArgumentParser(description="Stock coverage in months (definition, section 2).")
    ap.add_argument("--as-of", required=True, help="analysis month, YYYY-MM-01")
    ap.add_argument("--stock", type=float)
    ap.add_argument("--forecast", help='JSON list of [month, quantity] pairs')
    ap.add_argument("--stock-sql")
    ap.add_argument("--forecast-sql")
    a = ap.parse_args()
    as_of = dt.date.fromisoformat(a.as_of)
    if as_of.day != 1:
        raise SystemExit("--as-of must be the first day of a month")
    queries = {}
    if a.stock_sql or a.forecast_sql:
        import snowflake.connector                # the sandbox's connection, under the caller's role
        cur = snowflake.connector.connect().cursor()
        rows = run_sql(cur, a.stock_sql)
        stock = None if not rows or rows[0][0] is None else float(rows[0][0])
        queries["stock"] = {"sql": a.stock_sql, "query_id": cur.sfqid}
        pairs = run_sql(cur, a.forecast_sql)
        queries["forecast"] = {"sql": a.forecast_sql, "query_id": cur.sfqid, "rows": len(pairs)}
    else:
        stock = a.stock
        pairs = json.loads(a.forecast or "[]")
    monthly, missing, months = horizon(as_of, pairs)
    value, case = coverage(stock, monthly)
    print(json.dumps({"analysis_month": as_of.isoformat(), "horizon": [months[0].isoformat(), months[-1].isoformat()],
                      "stock": stock, "forecast_by_month": monthly, "months_without_forecast_counted_as_0": missing,
                      "coverage_months": None if value is None else round(value, 4), "case": case,
                      "queries": queries or None}))


if __name__ == "__main__":
    main()
