# mnemiq_jev_v2: TypeSafe Jev as mnemiq's judge (fail-closed, threshold 0.5, truncation-aware request MNEMIQ_JEV_PROMPT=b; fresh rerun r2)

Jev log lines: 131; matched to attempts: 131; unmatched: 0; HTTP statuses: {'200': 131}; attempts with more than one Jev call: 0; attempts with none: 1.

Jev calls bypass llm-meter, so they are counted from the log; `input_tokens` is the API's own `usage.input_tokens` (not estimated). Cost = input tokens x $0.042 per million (output tokens are free).

| set | attempts | Jev calls | Jev input tokens (total) | avg per call | est. Jev cost | Jev latency p50 / p95 ms | passed | declined (verification) | judge unavailable | other |
|---|---|---|---|---|---|---|---|---|---|---|
| 29 | 87 | 87 | 234,544 | 2,696 | $0.0099 | 154 / 198 | 86 | 0 | 0 | 1 |
| holdout | 45 | 44 | 117,091 | 2,661 | $0.0049 | 168 / 248 | 39 | 6 | 0 | 0 |

## Every decline: was its SQL actually right?

| set | id | run | Jev noul | SQL right? | how | mnemiq_verified same attempt | mnemiq_failopen same attempt | SQL |
|---|---|---|---|---|---|---|---|---|
| holdout | ho10 | 1 | 0.49 | RIGHT | exact | correct | correct | `SELECT EXTRACT(DAYOFWEEK FROM invoice_date) AS day_of_week, COUNT(*) AS invoice_count FROM invoice WHERE EXTRACT(YEAR FROM invoice_date) = 2024 GROUP ` |
| holdout | ho12 | 1 | 0.48 | wrong | wrong | correct | correct | `SELECT a.name FROM artist AS a LEFT JOIN album AS al ON al.artist_id = a.artist_id LEFT JOIN track AS t ON t.album_id = al.album_id LEFT JOIN invoice_` |
| holdout | ho10 | 2 | 0.4 | RIGHT | exact | correct | correct | `SELECT CAST(EXTRACT(DAYOFWEEK FROM invoice_date) AS INT) AS day_of_week, COUNT(*) AS invoice_count FROM invoice WHERE EXTRACT(YEAR FROM invoice_date) ` |
| holdout | ho14 | 2 | 0.2 | RIGHT | valid under gold boundary tie | wrong_result | correct | `SELECT DATE_PART('week', invoice_date) AS week_number, SUM(total) AS revenue FROM invoice WHERE EXTRACT(YEAR FROM invoice_date) = 2023 GROUP BY week_n` |
| holdout | ho10 | 3 | 0.46 | RIGHT | exact | declined | correct | `SELECT EXTRACT(DAYOFWEEK FROM invoice_date) AS day_of_week, COUNT(*) AS invoice_count FROM invoice WHERE invoice_date >= CAST('2024-01-01 00:00:00' AS` |
| holdout | ho14 | 3 | 0.19 | RIGHT | valid under gold boundary tie | wrong_result | correct | `SELECT DATE_PART('week', invoice_date) AS week_number, SUM(total) AS revenue FROM invoice WHERE DATE_PART('year', invoice_date) = 2023 GROUP BY week_n` |

Declines: 6; SQL actually right: **5** (correct answers blocked); actually wrong: **1** (real mistakes caught).

Answers passed by Jev and scored `wrong_result` by the harness: holdout:ho14 r1 (noul 0.87; re-labelled: right, valid under gold boundary tie)

## Per question vs previous mnemiq_jev_v2 run, mnemiq_verified and mnemiq_failopen (r1 r2 r3)

| set | id | mnemiq_jev_v2 | previous v2 run | mnemiq_verified | mnemiq_failopen |
|---|---|---|---|---|---|
| 29 | h04 | ✓✓✓ | ✓T✓ | ✓✓✓ | ✓✓✓ |
| 29 | h05 | ✓✓✓ | ✓✓✓ | 🚫✓✓ | ✓✓✓ |
| 29 | h11 | 🚫✓✓ | ✓✓T | ✓✓✓ | ✓✓✓ |
| holdout | ho10 | 🚫🚫🚫 | 🚫🚫🚫 | ✓✓🚫 | ✓✓✓ |
| holdout | ho12 | 🚫✓✓ | ✓✓🚫 | ✓✓✓ | ✓✓✓ |
| holdout | ho13 | ✓✓✓ | ✓✓✓ | 🚫✓🚫 | ✓✓✓ |
| holdout | ho14 | ✗🚫🚫 | 🚫🚫✓ | 🚫✗✗ | ✗✓✓ |

(Listed only where any of the three is not ✓✓✓. ✓ exact, ✗ wrong, 🚫 declined, ⚠ tool error. Generation differs run to run, so this is attempt vs attempt; the same-SQL comparison is results/judge-comparison/.)
