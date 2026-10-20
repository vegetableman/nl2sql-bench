# mnemiq_verified: verifier outcomes

Judge = mnemiq's `SemanticJudge` with `max_tokens=1200` (patches/verifier-tokens.patch), fail-closed, threshold 0.5. Per-call data from the patch's log line; SQL of rejected answers re-executed (DuckDB over the same Postgres, i.e. mnemiq's executor) and re-scored against gold by `bench/mnemiq_verifier_analysis.py`.

Judge calls logged: 132; matched to attempts: 132; unmatched: 0; empty replies (reply_chars=0, the finish_reason=length signature): 0; calls returning more than one judge line per attempt: 0.

| set | attempts | checked & passed | rejected (declined: verification) | unavailable (verifier_unavailable) | other |
|---|---|---|---|---|---|
| 29 | 87 | 86 | 1 | 0 | 0 |
| holdout | 45 | 41 | 4 | 0 | 0 |

## Passed by the judge: correctness

| set | passed | of which EX exact | relaxed only | wrong_result | exec_error |
|---|---|---|---|---|---|
| 29 | 86 | 86 | 0 | 0 | 0 |
| holdout | 41 | 39 | 0 | 2 | 0 |

Non-exact answers the judge passed: holdout:ho14 r2 (wrong_result as scored, judge conf 0.86; re-executed: valid under gold boundary tie); holdout:ho14 r3 (wrong_result as scored, judge conf 0.92; re-executed: valid under gold boundary tie)

Gold-tie note: ho14's gold (`ORDER BY revenue DESC LIMIT 3`) has a four-way tie for 3rd place (weeks 8, 30, 39, 47, 22.77 each), and the gold arbitrarily keeps one, so a correct query can be scored `wrong_result` depending on the executor's tie order (it is not even stable between executions). Harness scoring is left unchanged; the 'valid under gold boundary tie' verdicts above re-check against every tie choice with the same `compare`. No other gold query in either set has a tie at its LIMIT boundary.

## Every rejected / unavailable answer: was its SQL actually right?

| set | id | run | outcome | judge conf | SQL vs gold | executed on | mnemiq_failopen same attempt | SQL the judge saw |
|---|---|---|---|---|---|---|---|---|
| 29 | h05 | 1 | rejected | 0.35 | RIGHT (exact) | duckdb (mnemiq's executor) | correct | `SELECT EXTRACT(MONTH FROM invoice_date) AS month, SUM(total) AS revenue, LAG(SUM(total)) OVER (ORDER BY EXTRACT(MONTH FROM invoice_date)) AS prev_month_revenue FROM invoice WHERE invoice_date >= CAST('2024-01-01' AS TIME` |
| holdout | ho13 | 1 | rejected | 0.1 | WRONG | duckdb (mnemiq's executor) | correct | `WITH q AS (SELECT ((MONTH(invoice_date) - 1) / 3) + 1 AS quarter, SUM(total) AS revenue FROM invoice WHERE YEAR(invoice_date) = 2024 GROUP BY 1) SELECT q.quarter, q.revenue, prev.revenue AS previous_quarter_revenue FROM ` |
| holdout | ho14 | 1 | rejected | 0.3 | WRONG / valid under gold boundary tie | duckdb (mnemiq's executor) | wrong_result | `SELECT EXTRACT(WEEK FROM invoice_date) AS week_number, SUM(total) AS revenue FROM invoice WHERE EXTRACT(YEAR FROM invoice_date) = 2023 GROUP BY week_number ORDER BY revenue DESC LIMIT 3` |
| holdout | ho10 | 3 | rejected | 0.4 | RIGHT (exact) | duckdb (mnemiq's executor) | correct | `SELECT EXTRACT(DAYOFWEEK FROM invoice_date) AS day_of_week, COUNT(*) AS invoice_count FROM invoice WHERE EXTRACT(YEAR FROM invoice_date) = 2024 GROUP BY day_of_week ORDER BY day_of_week LIMIT 1000` |
| holdout | ho13 | 3 | rejected | 0.15 | WRONG | duckdb (mnemiq's executor) | correct | `SELECT quarter, revenue, LAG(revenue) OVER (ORDER BY quarter) AS previous_quarter_revenue FROM (SELECT CAST(((EXTRACT(MONTH FROM invoice_date) - 1) / 3) + 1 AS INT) AS quarter, SUM(total) AS revenue FROM invoice WHERE EX` |

## Per question vs mnemiq_failopen (status per run r1/r2/r3)

| set | id | mnemiq_verified | mnemiq_failopen |
|---|---|---|---|
| 29 | h05 | 🚫✓✓ | ✓✓✓ |
| holdout | ho10 | ✓✓🚫 | ✓✓✓ |
| holdout | ho13 | 🚫✓🚫 | ✓✓✓ |
| holdout | ho14 | 🚫✗✗ | ✗✓✓ |

(Only questions where either system was not ✓✓✓ are listed; all others were exact in all 3 runs for both. ✓ exact, ≈ extra cols, ✗ wrong, 🚫 declined, ⚠ tool error.)
