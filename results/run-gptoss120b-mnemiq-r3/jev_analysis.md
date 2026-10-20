# mnemiq_jev: TypeSafe Jev as mnemiq's judge (fail-closed, threshold 0.5, original request)

Jev log lines: 132; matched to attempts: 132; unmatched: 0; HTTP statuses: {'200': 132}; attempts with more than one Jev call: 0; attempts with none: 0.

Jev calls bypass llm-meter, so they are counted from the log; `input_tokens` is the API's own `usage.input_tokens` (not estimated). Cost = input tokens x $0.042 per million (output tokens are free).

| set | attempts | Jev calls | Jev input tokens (total) | avg per call | est. Jev cost | Jev latency p50 / p95 ms | passed | declined (verification) | judge unavailable | other |
|---|---|---|---|---|---|---|---|---|---|---|
| 29 | 87 | 87 | 221,670 | 2,548 | $0.0093 | 170 / 232 | 78 | 9 | 0 | 0 |
| holdout | 45 | 45 | 114,523 | 2,545 | $0.0048 | 175 / 234 | 40 | 5 | 0 | 0 |

## Every decline: was its SQL actually right?

| set | id | run | Jev noul | SQL right? | how | mnemiq_verified same attempt | mnemiq_failopen same attempt | SQL |
|---|---|---|---|---|---|---|---|---|
| 29 | e02 | 1 | 0.26 | RIGHT | exact | correct | correct | `SELECT name FROM genre LIMIT 1000` |
| 29 | e08 | 1 | 0.41 | RIGHT | exact | correct | correct | `SELECT first_name, last_name, company FROM customer WHERE NOT company IS NULL AND company <> '' LIMIT 1000` |
| 29 | m01 | 1 | 0.32 | RIGHT | exact | correct | correct | `SELECT g.name AS genre_name, COUNT(t.track_id) AS track_count FROM genre AS g LEFT JOIN track AS t ON t.genre_id = g.genre_id GROUP BY g.name ORDER BY` |
| 29 | m06 | 1 | 0.31 | RIGHT | exact | correct | correct | `SELECT a.title, COUNT(*) AS track_count FROM track AS t JOIN album AS a ON t.album_id = a.album_id GROUP BY a.title HAVING COUNT(*) > 20 LIMIT 1000` |
| 29 | e02 | 2 | 0.32 | RIGHT | exact | correct | correct | `SELECT name FROM genre LIMIT 1000` |
| 29 | e08 | 2 | 0.39 | RIGHT | exact | correct | correct | `SELECT first_name, last_name, company FROM customer WHERE NOT company IS NULL AND company <> '' LIMIT 1000` |
| 29 | m01 | 2 | 0.44 | RIGHT | exact | correct | correct | `SELECT g.name AS genre_name, COUNT(t.track_id) AS track_count FROM track AS t JOIN genre AS g ON t.genre_id = g.genre_id GROUP BY g.name ORDER BY g.na` |
| 29 | e02 | 3 | 0.34 | RIGHT | exact | correct | correct | `SELECT name FROM genre LIMIT 1000` |
| 29 | e08 | 3 | 0.39 | RIGHT | exact | correct | correct | `SELECT first_name, last_name, company FROM customer WHERE NOT company IS NULL AND company <> '' LIMIT 1000` |
| holdout | ho10 | 1 | 0.32 | RIGHT | exact | correct | correct | `SELECT EXTRACT(DAYOFWEEK FROM invoice_date) AS day_of_week, COUNT(*) AS invoice_count FROM invoice WHERE EXTRACT(YEAR FROM invoice_date) = 2024 GROUP ` |
| holdout | ho14 | 1 | 0.16 | RIGHT | valid under gold boundary tie | declined | wrong_result | `SELECT EXTRACT(WEEK FROM invoice_date) AS week_number, SUM(total) AS revenue FROM invoice WHERE invoice_date >= CAST('2023-01-01 00:00:00' AS TIMESTAM` |
| holdout | ho10 | 2 | 0.37 | RIGHT | exact | correct | correct | `SELECT CAST(STRFTIME(invoice_date, '%w') AS INT) AS day_of_week, COUNT(*) AS invoice_count FROM invoice WHERE invoice_date >= CAST('2024-01-01 00:00:0` |
| holdout | ho10 | 3 | 0.3 | RIGHT | exact | declined | correct | `SELECT EXTRACT(DAYOFWEEK FROM invoice_date) AS day_of_week, COUNT(*) AS invoice_count FROM invoice WHERE EXTRACT(YEAR FROM invoice_date) = 2024 GROUP ` |
| holdout | ho14 | 3 | 0.2 | RIGHT | valid under gold boundary tie | wrong_result | correct | `SELECT EXTRACT(WEEK FROM invoice_date) AS week_number, SUM(total) AS revenue FROM invoice WHERE EXTRACT(YEAR FROM invoice_date) = 2023 GROUP BY week_n` |

Declines: 14; SQL actually right: **14** (correct answers blocked); actually wrong: **0** (real mistakes caught).

Answers passed by Jev and scored `wrong_result` by the harness: holdout:ho14 r2 (noul 0.83; re-labelled: right, valid under gold boundary tie)

## Per question vs mnemiq_verified and mnemiq_failopen (r1 r2 r3)

| set | id | mnemiq_jev | mnemiq_verified | mnemiq_failopen |
|---|---|---|---|---|
| 29 | e02 | 🚫🚫🚫 | ✓✓✓ | ✓✓✓ |
| 29 | e08 | 🚫🚫🚫 | ✓✓✓ | ✓✓✓ |
| 29 | m01 | 🚫🚫✓ | ✓✓✓ | ✓✓✓ |
| 29 | m06 | 🚫✓✓ | ✓✓✓ | ✓✓✓ |
| 29 | h05 | ✓✓✓ | 🚫✓✓ | ✓✓✓ |
| holdout | ho10 | 🚫🚫🚫 | ✓✓🚫 | ✓✓✓ |
| holdout | ho13 | ✓✓✓ | 🚫✓🚫 | ✓✓✓ |
| holdout | ho14 | 🚫✗🚫 | 🚫✗✗ | ✗✓✓ |

(Listed only where any of the three is not ✓✓✓. ✓ exact, ✗ wrong, 🚫 declined, ⚠ tool error. Generation differs run to run, so this is attempt vs attempt; the same-SQL comparison is results/judge-comparison/.)
