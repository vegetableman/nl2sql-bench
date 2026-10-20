# mnemiq_jev_v2: TypeSafe Jev as mnemiq's judge (fail-closed, threshold 0.5, truncation-aware request MNEMIQ_JEV_PROMPT=b)

Jev log lines: 132; matched to attempts: 132; unmatched: 0; HTTP statuses: {'200': 132}; attempts with more than one Jev call: 0; attempts with none: 0.

Jev calls bypass llm-meter, so they are counted from the log; `input_tokens` is the API's own `usage.input_tokens` (not estimated). Cost = input tokens x $0.042 per million (output tokens are free).

| set | attempts | Jev calls | Jev input tokens (total) | avg per call | est. Jev cost | Jev latency p50 / p95 ms | passed | declined (verification) | judge unavailable | other |
|---|---|---|---|---|---|---|---|---|---|---|
| 29 | 87 | 87 | 234,385 | 2,694 | $0.0098 | 155 / 213 | 85 | 0 | 0 | 2 |
| holdout | 45 | 45 | 119,872 | 2,664 | $0.0050 | 145 / 206 | 39 | 6 | 0 | 0 |

## Every decline: was its SQL actually right?

| set | id | run | Jev noul | SQL right? | how | mnemiq_verified same attempt | mnemiq_failopen same attempt | SQL |
|---|---|---|---|---|---|---|---|---|
| holdout | ho10 | 1 | 0.4 | RIGHT | exact | correct | correct | `SELECT EXTRACT(DAYOFWEEK FROM invoice_date) AS day_of_week, COUNT(*) AS invoice_count FROM invoice WHERE invoice_date >= '2024-01-01' AND invoice_date` |
| holdout | ho14 | 1 | 0.2 | RIGHT | valid under gold boundary tie | declined | wrong_result | `SELECT DATE_PART('week', invoice_date) AS week_number, SUM(total) AS revenue FROM invoice WHERE DATE_PART('year', invoice_date) = 2023 GROUP BY week_n` |
| holdout | ho10 | 2 | 0.38 | RIGHT | exact | correct | correct | `SELECT EXTRACT(DAYOFWEEK FROM invoice_date) AS day_of_week, COUNT(invoice_id) AS invoice_count FROM invoice WHERE EXTRACT(YEAR FROM invoice_date) = 20` |
| holdout | ho14 | 2 | 0.19 | RIGHT | valid under gold boundary tie | wrong_result | correct | `SELECT DATE_PART('week', invoice_date) AS week_number, SUM(total) AS revenue FROM invoice WHERE DATE_PART('year', invoice_date) = 2023 GROUP BY week_n` |
| holdout | ho10 | 3 | 0.41 | RIGHT | exact | declined | correct | `SELECT EXTRACT(DAYOFWEEK FROM invoice_date) AS day_of_week, COUNT(*) AS invoice_count FROM invoice WHERE EXTRACT(YEAR FROM invoice_date) = 2024 GROUP ` |
| holdout | ho12 | 3 | 0.4 | wrong | wrong | correct | correct | `SELECT DISTINCT a.name FROM artist AS a LEFT JOIN album AS al ON a.artist_id = al.artist_id LEFT JOIN track AS t ON al.album_id = t.album_id LEFT JOIN` |

Declines: 6; SQL actually right: **5** (correct answers blocked); actually wrong: **1** (real mistakes caught).

Answers passed by Jev and scored `wrong_result` by the harness: none

## Per question vs mnemiq_jev (v1), mnemiq_verified and mnemiq_failopen (r1 r2 r3)

| set | id | mnemiq_jev_v2 | mnemiq_jev (v1) | mnemiq_verified | mnemiq_failopen |
|---|---|---|---|---|---|
| 29 | e02 | ✓✓✓ | 🚫🚫🚫 | ✓✓✓ | ✓✓✓ |
| 29 | e08 | ✓✓✓ | 🚫🚫🚫 | ✓✓✓ | ✓✓✓ |
| 29 | m01 | ✓✓✓ | 🚫🚫✓ | ✓✓✓ | ✓✓✓ |
| 29 | m06 | ✓✓✓ | 🚫✓✓ | ✓✓✓ | ✓✓✓ |
| 29 | h04 | ✓T✓ | ✓✓✓ | ✓✓✓ | ✓✓✓ |
| 29 | h05 | ✓✓✓ | ✓✓✓ | 🚫✓✓ | ✓✓✓ |
| 29 | h11 | ✓✓T | ✓✓✓ | ✓✓✓ | ✓✓✓ |
| holdout | ho10 | 🚫🚫🚫 | 🚫🚫🚫 | ✓✓🚫 | ✓✓✓ |
| holdout | ho12 | ✓✓🚫 | ✓✓✓ | ✓✓✓ | ✓✓✓ |
| holdout | ho13 | ✓✓✓ | ✓✓✓ | 🚫✓🚫 | ✓✓✓ |
| holdout | ho14 | 🚫🚫✓ | 🚫✗🚫 | 🚫✗✗ | ✗✓✓ |

(Listed only where any of the three is not ✓✓✓. ✓ exact, ✗ wrong, 🚫 declined, ⚠ tool error. Generation differs run to run, so this is attempt vs attempt; the same-SQL comparison is results/judge-comparison/.)
