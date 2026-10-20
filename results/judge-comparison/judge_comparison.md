# Same-SQL judge comparison: TypeSafe Jev vs mnemiq's gpt-oss:120b judge

Each item is a (question, SQL) mnemiq produced. Its judge input is rebuilt with mnemiq's own code (`mnemiq/judge_rebuild.py`): the schema is `_judge_schema` of the packet `Runtime.ask` retrieves (same `retrieve` arguments + window fitter), and the result is the SQL run through mnemiq's own adapter (DuckDB over the same Postgres) rendered by `render_result(max_rows=5)`, exactly what the Verifier passes. Correct = EX-exact vs gold with the harness `compare` on the full result. **ho14: answers that are a valid top 3 under the gold's four-way tie for 3rd place are labelled correct** (known gold flaw). **ho12: DuckDB returns the same 110 rows as gold but in binary-collation order (Postgres' locale collation ignores spaces); these are labelled correct when the same SQL is exact on Postgres, which is how the harness scored them.** Pass = score >= 0.5 (mnemiq's Verifier defers below its 0.5 threshold).

Items: 264 (132 mnemiq_verified judge calls with logged gpt-oss confidence, 132 mnemiq_failopen answers). Scored by Jev: 264; missing/unscored: 0. Correct: 262, wrong: 2.

Jev calls: 264, input tokens (reported by the API's `usage.input_tokens`): 672,721 total, 2,548 avg; cost at $0.042/M input tokens: $0.0283. Latency p50 157 ms, p95 209 ms. Model reported: ['jev-1.14.0'].

Prompt variants of the Jev request (truncation-aware, larger samples) on these same items: **judge_variants.md**. The tables below are the original request (v1); mnemiq_jev_v2 ships variant b.

## At threshold 0.5

| judge | items | wrong caught | wrong passed | correct blocked | correct passed | AUROC (score vs correct) |
|---|---|---|---|---|---|---|
| gpt-oss:120b judge (logged, mnemiq_verified calls) | 132 | 2 | 0 | 3 | 127 | 1.000 |
| Jev, same mnemiq_verified calls | 132 | 1 | 1 | 15 | 115 | 0.929 |
| Jev, mnemiq_failopen answers | 132 | 0 | 0 | 14 | 118 | n/a |
| Jev, all items | 264 | 1 | 1 | 29 | 233 | 0.935 |

## Threshold sweep (blocked = score below threshold)

| threshold | gpt-oss: wrong caught / passed | gpt-oss: correct blocked | Jev (same calls): wrong caught / passed | Jev (same calls): correct blocked | Jev (all): wrong caught / passed | Jev (all): correct blocked |
|---|---|---|---|---|---|---|
| 0.1 | 0 / 2 | 0 | 1 / 1 | 0 | 1 / 1 | 0 |
| 0.2 | 2 / 0 | 0 | 1 / 1 | 0 | 1 / 1 | 0 |
| 0.3 | 2 / 0 | 0 | 1 / 1 | 3 | 1 / 1 | 4 |
| 0.4 | 2 / 0 | 2 | 1 / 1 | 12 | 1 / 1 | 21 |
| 0.5 | 2 / 0 | 3 | 1 / 1 | 15 | 1 / 1 | 29 |
| 0.6 | 2 / 0 | 4 | 2 / 0 | 26 | 2 / 0 | 49 |
| 0.7 | 2 / 0 | 7 | 2 / 0 | 46 | 2 / 0 | 91 |
| 0.8 | 2 / 0 | 13 | 2 / 0 | 71 | 2 / 0 | 140 |
| 0.9 | 2 / 0 | 25 | 2 / 0 | 109 | 2 / 0 | 219 |

## Every wrong answer, and every answer either judge blocks at 0.5

| source | set | id | run | correct? | detail | gpt-oss conf | Jev noul | SQL |
|---|---|---|---|---|---|---|---|---|
| mnemiq_failopen | 29 | e02 | 1 | yes | exact | – | 0.32 | `SELECT name FROM genre LIMIT 1000` |
| mnemiq_failopen | 29 | e02 | 2 | yes | exact | – | 0.31 | `SELECT name FROM genre LIMIT 1000` |
| mnemiq_failopen | 29 | e02 | 3 | yes | exact | – | 0.38 | `SELECT name FROM genre LIMIT 1000` |
| mnemiq_verified | 29 | e02 | 1 | yes | exact | 0.98 | 0.25 | `SELECT name FROM genre LIMIT 1000` |
| mnemiq_verified | 29 | e02 | 2 | yes | exact | 0.97 | 0.35 | `SELECT name FROM genre ORDER BY name LIMIT 1000` |
| mnemiq_verified | 29 | e02 | 3 | yes | exact | 0.98 | 0.35 | `SELECT name FROM genre LIMIT 1000` |
| mnemiq_failopen | 29 | e08 | 1 | yes | exact | – | 0.38 | `SELECT first_name, last_name, company FROM customer WHERE NOT company IS NULL AND company <> '' LIMIT 1000` |
| mnemiq_failopen | 29 | e08 | 2 | yes | exact | – | 0.38 | `SELECT first_name, last_name, company FROM customer WHERE NOT company IS NULL AND TRIM(company) <> '' LIMIT 1000` |
| mnemiq_failopen | 29 | e08 | 3 | yes | exact | – | 0.40 | `SELECT first_name, last_name, company FROM customer WHERE NOT company IS NULL AND company <> '' LIMIT 1000` |
| mnemiq_verified | 29 | e08 | 1 | yes | exact | 0.95 | 0.43 | `SELECT first_name, last_name, company FROM customer WHERE NOT company IS NULL LIMIT 1000` |
| mnemiq_verified | 29 | e08 | 2 | yes | exact | 0.97 | 0.37 | `SELECT first_name, last_name, company FROM customer WHERE NOT company IS NULL AND company <> '' LIMIT 1000` |
| mnemiq_verified | 29 | e08 | 3 | yes | exact | 0.95 | 0.36 | `SELECT first_name, last_name, company FROM customer WHERE NOT company IS NULL AND company <> '' LIMIT 1000` |
| mnemiq_verified | 29 | h05 | 1 | yes | exact | 0.35 | 0.55 | `SELECT EXTRACT(MONTH FROM invoice_date) AS month, SUM(total) AS revenue, LAG(SUM(total)) OVER (ORDER BY EXTRACT(MONTH FROM invoice_date)) AS prev_month_revenue ` |
| mnemiq_verified | 29 | h06 | 1 | yes | exact | 0.75 | 0.38 | `SELECT a.name, COUNT(DISTINCT t.genre_id) AS distinct_genres FROM track AS t JOIN album AS al ON t.album_id = al.album_id JOIN artist AS a ON al.artist_id = a.a` |
| mnemiq_failopen | 29 | m01 | 1 | yes | exact | – | 0.41 | `SELECT g.name AS genre_name, COUNT(t.track_id) AS track_count FROM track AS t JOIN genre AS g ON t.genre_id = g.genre_id GROUP BY g.name ORDER BY g.name LIMIT 1` |
| mnemiq_failopen | 29 | m01 | 2 | yes | exact | – | 0.49 | `SELECT g.name AS genre_name, COUNT(t.track_id) AS track_count FROM track AS t JOIN genre AS g ON t.genre_id = g.genre_id GROUP BY g.name ORDER BY g.name LIMIT 1` |
| mnemiq_failopen | 29 | m01 | 3 | yes | exact | – | 0.47 | `SELECT g.name, COUNT(t.track_id) AS track_count FROM track AS t JOIN genre AS g ON t.genre_id = g.genre_id GROUP BY g.name ORDER BY g.name LIMIT 1000` |
| mnemiq_verified | 29 | m01 | 1 | yes | exact | 0.97 | 0.46 | `SELECT g.name AS genre_name, COUNT(t.track_id) AS track_count FROM genre AS g LEFT JOIN track AS t ON g.genre_id = t.genre_id GROUP BY g.name ORDER BY g.name LI` |
| mnemiq_verified | 29 | m01 | 2 | yes | exact | 0.95 | 0.37 | `SELECT g.name AS genre_name, COUNT(t.track_id) AS track_count FROM genre AS g LEFT JOIN track AS t ON g.genre_id = t.genre_id GROUP BY g.name ORDER BY g.name LI` |
| mnemiq_verified | 29 | m06 | 2 | yes | exact | 0.75 | 0.48 | `SELECT a.title, COUNT(t.track_id) AS track_count FROM album AS a JOIN track AS t ON a.album_id = t.album_id GROUP BY a.title HAVING COUNT(t.track_id) > 20 ORDER` |
| mnemiq_failopen | holdout | ho10 | 1 | yes | exact | – | 0.35 | `SELECT CAST(STRFTIME(invoice_date, '%w') AS INT) AS day_of_week, COUNT(*) AS invoice_count FROM invoice WHERE invoice_date >= CAST('2024-01-01 00:00:00' AS TIME` |
| mnemiq_failopen | holdout | ho10 | 2 | yes | exact | – | 0.31 | `SELECT EXTRACT(DAYOFWEEK FROM invoice_date) AS day_of_week, COUNT(*) AS invoice_count FROM invoice WHERE invoice_date >= CAST('2024-01-01 00:00:00' AS TIMESTAMP` |
| mnemiq_failopen | holdout | ho10 | 3 | yes | exact | – | 0.31 | `SELECT CAST(EXTRACT(DAYOFWEEK FROM invoice_date) AS INT) AS day_of_week, COUNT(*) AS invoice_count FROM invoice WHERE CAST(EXTRACT(YEAR FROM invoice_date) AS IN` |
| mnemiq_verified | holdout | ho10 | 1 | yes | exact | 0.72 | 0.30 | `SELECT EXTRACT(DAYOFWEEK FROM invoice_date) AS day_of_week, COUNT(*) AS invoice_count FROM invoice WHERE EXTRACT(YEAR FROM invoice_date) = 2024 GROUP BY EXTRACT` |
| mnemiq_verified | holdout | ho10 | 2 | yes | exact | 0.58 | 0.29 | `SELECT EXTRACT(DAYOFWEEK FROM invoice_date) AS day_of_week, COUNT(*) AS invoice_count FROM invoice WHERE EXTRACT(YEAR FROM invoice_date) = 2024 GROUP BY day_of_` |
| mnemiq_verified | holdout | ho10 | 3 | yes | exact | 0.4 | 0.30 | `SELECT EXTRACT(DAYOFWEEK FROM invoice_date) AS day_of_week, COUNT(*) AS invoice_count FROM invoice WHERE EXTRACT(YEAR FROM invoice_date) = 2024 GROUP BY day_of_` |
| mnemiq_failopen | holdout | ho13 | 1 | yes | exact | – | 0.44 | `WITH agg AS (SELECT EXTRACT(YEAR FROM invoice_date) AS yr, EXTRACT(QUARTER FROM invoice_date) AS qtr, SUM(total) AS revenue FROM invoice WHERE EXTRACT(YEAR FROM` |
| mnemiq_verified | holdout | ho13 | 1 | NO | wrong | 0.1 | 0.07 | `WITH q AS (SELECT ((MONTH(invoice_date) - 1) / 3) + 1 AS quarter, SUM(total) AS revenue FROM invoice WHERE YEAR(invoice_date) = 2024 GROUP BY 1) SELECT q.quarte` |
| mnemiq_verified | holdout | ho13 | 3 | NO | wrong | 0.15 | 0.53 | `SELECT quarter, revenue, LAG(revenue) OVER (ORDER BY quarter) AS previous_quarter_revenue FROM (SELECT CAST(((EXTRACT(MONTH FROM invoice_date) - 1) / 3) + 1 AS ` |
| mnemiq_failopen | holdout | ho14 | 2 | yes | valid under gold boundary tie | – | 0.21 | `SELECT EXTRACT(WEEK FROM invoice_date) AS week_number, SUM(total) AS revenue FROM invoice WHERE EXTRACT(YEAR FROM invoice_date) = 2023 GROUP BY week_number ORDE` |
| mnemiq_verified | holdout | ho14 | 1 | yes | valid under gold boundary tie | 0.3 | 0.21 | `SELECT EXTRACT(WEEK FROM invoice_date) AS week_number, SUM(total) AS revenue FROM invoice WHERE EXTRACT(YEAR FROM invoice_date) = 2023 GROUP BY week_number ORDE` |
| mnemiq_verified | holdout | ho14 | 3 | yes | valid under gold boundary tie | 0.92 | 0.30 | `SELECT CAST(DATE_PART('week', invoice_date) AS INT) AS week_number, SUM(total) AS revenue FROM invoice WHERE DATE_PART('year', invoice_date) = 2023 GROUP BY wee` |

## Named cases

| case | correct? | gpt-oss conf | Jev noul |
|---|---|---|---|
| mnemiq_verified h05 r1 | yes (exact) | 0.35 | 0.55 |
| mnemiq_failopen h05 r1 | yes (exact) | – | 0.55 |
| mnemiq_verified ho10 r3 | yes (exact) | 0.4 | 0.30 |
| mnemiq_failopen ho10 r3 | yes (exact) | – | 0.31 |
| mnemiq_verified ho13 r1 | NO (wrong) | 0.1 | 0.07 |
| mnemiq_failopen ho13 r1 | yes (exact) | – | 0.44 |
| mnemiq_verified ho13 r3 | NO (wrong) | 0.15 | 0.53 |
| mnemiq_failopen ho13 r3 | yes (exact) | – | 0.86 |
| mnemiq_verified ho14 r1 | yes (valid under gold boundary tie) | 0.3 | 0.21 |
| mnemiq_failopen ho14 r1 | yes (exact) | – | 0.82 |
| mnemiq_verified ho14 r2 | yes (valid under gold boundary tie) | 0.86 | 0.82 |
| mnemiq_failopen ho14 r2 | yes (valid under gold boundary tie) | – | 0.21 |
| mnemiq_verified ho14 r3 | yes (valid under gold boundary tie) | 0.92 | 0.30 |
| mnemiq_failopen ho14 r3 | yes (valid under gold boundary tie) | – | 0.84 |
