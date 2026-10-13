"""Checks that the set-based SQL formula (DEFINITION.md section 5) matches the legacy cascade (24 windowed cumulative
metrics + CASE), and that the member spine keeps a member with forecast but no stock (T8)."""
import duckdb

H = 24


def legacy_cascade(stock, fc, horizon=H, avg_scope=None):
    """Faithful replica of the legacy metric: M_k = cumulative t+1..t+k-1, SC_n, then CASE."""
    if stock is None or stock == 0:
        return 0.0
    fc = (list(fc) + [0.0] * horizon)[:horizon]
    M = {k: sum(fc[: k - 1]) for k in range(2, horizon + 2)}  # M_02..M_25
    for n in range(1, horizon + 1):
        if stock <= M[n + 1]:
            if n == 1:
                return stock / M[2]
            return (stock - M[n]) / (M[n + 1] - M[n]) + (n - 1)
    scope = avg_scope if avg_scope is not None else fc
    nz = [x for x in scope if x != 0]
    return stock / (sum(nz) / len(nz)) if nz else None


SQL = """
WITH stock AS (SELECT * FROM (VALUES {stock_rows}) t(item, stock_qty)),
fc AS (SELECT * FROM (VALUES {fc_rows}) t(item, k, fc_qty)),
months AS (SELECT range AS k FROM range(1, {h} + 1)),
members AS ({members}),                      -- member spine (T8)
dense AS (                                   -- dense calendar: missing month = 0
    SELECT mb.item, m.k,
           COALESCE(s.stock_qty, 0) AS stock_qty,
           COALESCE(f.fc_qty, 0)    AS fc_qty
    FROM members mb CROSS JOIN months m
    LEFT JOIN stock s ON s.item = mb.item
    LEFT JOIN fc f    ON f.item = mb.item AND f.k = m.k
),
cum AS (
    SELECT *, SUM(fc_qty) OVER (PARTITION BY item ORDER BY k ROWS UNBOUNDED PRECEDING) AS cum_fc
    FROM dense
)
SELECT item,
       CASE
         WHEN ANY_VALUE(stock_qty) IS NULL OR ANY_VALUE(stock_qty) = 0 THEN 0
         WHEN MAX(cum_fc) >= ANY_VALUE(stock_qty) THEN
              SUM(CASE WHEN cum_fc - fc_qty >= stock_qty THEN 0
                       WHEN cum_fc <= stock_qty          THEN 1
                       ELSE (stock_qty - (cum_fc - fc_qty)) / fc_qty END)
         ELSE ANY_VALUE(stock_qty) / AVG(NULLIF(fc_qty, 0))
       END AS coverage_months
FROM cum GROUP BY item ORDER BY item
"""

cases = {
    "worked_example": (1000, [120, 90, 150, 110, 130, 100, 140, 80, 160, 100]),
    "exact_depletion": (360, [120, 90, 150, 0, 50]),          # stock == cumulative exactly, then a zero month
    "zero_month_before": (300, [100, 0, 150, 100]),        # zero month counts as covered
    "zero_stock": (0, [100, 100]),
    "beyond_horizon": (10000, [100] * 24),              # ELSE branch: stock / average
    "no_demand": (500, []),
    "forecast_no_stock": (None, [100, 100, 100]),           # T8: no stock row at all -> 0, row kept
}
SPINE = "SELECT item FROM stock UNION SELECT item FROM fc"
STOCK_DRIVEN = "SELECT item FROM stock"                      # the section 5 shape before the spine

stock_rows = ", ".join(f"('{n}', {s}::DOUBLE)" for n, (s, _) in cases.items() if s is not None)
fc_rows = ", ".join(f"('{n}', {k + 1}, {v}::DOUBLE)"
                    for n, (_, f) in cases.items() for k, v in enumerate(f) if v != 0)


def run(members):
    return dict(duckdb.sql(SQL.format(stock_rows=stock_rows, fc_rows=fc_rows, h=H, members=members)).fetchall())


res = run(SPINE)

ok = True
for n, (s, f) in cases.items():
    ref = legacy_cascade(s, f)
    got = res.get(n, "missing")
    same = got != "missing" and ((ref is None and got is None)
                                 or (ref is not None and got is not None and abs(ref - got) < 1e-9))
    ok &= same
    print(f"{n:18s} LEGACY={ref if ref is None else round(ref, 4)!s:>8}  SQL={got if got is None else round(got, 4)!s:>8}  {'OK' if same else 'MISMATCH'}")
lost = "forecast_no_stock" not in run(STOCK_DRIVEN)
ok &= lost
print(f"{'stock-driven members':18s} T8 member {'lost, as expected' if lost else 'KEPT: the T8 case no longer tests the spine'}")
print("ALL OK" if ok else "MISMATCHES")
raise SystemExit(0 if ok else 1)
