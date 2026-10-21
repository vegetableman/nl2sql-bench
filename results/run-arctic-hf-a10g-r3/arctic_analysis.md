# Arctic-Text2SQL-R1-7B (system `arctic`)

Dedicated HF Inference Endpoint (aws us-east-1, 1x nvidia-a10g, vLLM), Snowflake's eval prompt, temperature 0, full 11-table DDL. Latency = harness wall time per question through llm-meter (endpoint already warm; cold start excluded). Tie rule: misses re-executed and re-labelled (ho14 gold tie / ho12 collation) as for the other systems.

| set | attempts | EX strict | EX relaxed | tie rule | timeouts | no-SQL | exec errors | p50 / p95 s | TTFT p50 s | gen tok/s p50 | avg prompt tok | avg output tok (incl. thinking) | max output tok |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 29 | 87 | 67/87 | 67/87 | 67/87 | 4 | 0 | 13 | 10.71 / 135.61 | 0.78 | 30.9 | 1109 | 569 | 4096 |
| holdout | 45 | 36/45 | 36/45 | 36/45 | 0 | 0 | 9 | 10.90 / 135.63 | 0.80 | 30.8 | 1112 | 811 | 4096 |

## Every non-exact attempt

| set | run | id | status | tie-rule label | error / reason | SQL |
|---|---|---|---|---|---|---|
| 29 | 1 | e07 | exec_error | exec_error | UndefinedFunction: function strftime(unknown, timestamp without time zone) does not exist
LINE 3: WHERE strfti | `SELECT COUNT(*)  FROM invoice  WHERE strftime('%Y', invoice_date) = '2023';` |
| 29 | 1 | m04 | timeout | timeout | timeout: no response within 180s | `` |
| 29 | 1 | m09 | exec_error | exec_error | UndefinedFunction: function strftime(unknown, timestamp without time zone) does not exist
LINE 2:   strftime(' | `SELECT    strftime('%Y', invoice_date) AS year,    SUM(total) AS revenue FROM    invoice GROUP BY    strftime('%Y', invoice_date) ORDER BY    year;` |
| 29 | 1 | h03 | wrong_result | wrong | row count 59 != gold 22 | `SELECT      c.first_name,      c.last_name,      SUM(i.total) AS total_spend FROM      customer c JOIN      invoice i ON c.customer_id = i.customer_id GROUP BY      c.customer_id, c.first_name, c.last` |
| 29 | 1 | h05 | exec_error | exec_error | UndefinedFunction: function strftime(unknown, timestamp without time zone) does not exist
LINE 2:     strftime | `SELECT      strftime('%m', invoice_date) AS month_number,     SUM(total) AS revenue,     LAG(SUM(total)) OVER (ORDER BY strftime('%m', invoice_date)) AS previous_month_revenue FROM      invoice WHERE ` |
| 29 | 1 | h09 | exec_error | exec_error | UndefinedFunction: function strftime(unknown, timestamp without time zone) does not exist
LINE 3: WHERE strfti | `SELECT COUNT(DISTINCT i.customer_id) AS customer_count FROM invoice i WHERE strftime('%Y', i.invoice_date) = '2025' AND i.customer_id NOT IN (     SELECT i2.customer_id     FROM invoice i2     WHERE s` |
| 29 | 1 | h10 | timeout | timeout | timeout: no response within 180s | `` |
| 29 | 2 | e07 | exec_error | exec_error | UndefinedFunction: function strftime(unknown, timestamp without time zone) does not exist
LINE 3: WHERE strfti | `SELECT COUNT(*)  FROM invoice  WHERE strftime('%Y', invoice_date) = '2023';` |
| 29 | 2 | m09 | timeout | timeout | timeout: no response within 180s | `` |
| 29 | 2 | h03 | wrong_result | wrong | row count 59 != gold 22 | `SELECT      c.first_name,      c.last_name,      SUM(i.total) AS total_spend FROM      customer c JOIN      invoice i ON c.customer_id = i.customer_id GROUP BY      c.customer_id, c.first_name, c.last` |
| 29 | 2 | h05 | exec_error | exec_error | UndefinedFunction: function strftime(unknown, timestamp without time zone) does not exist
LINE 2:   strftime(' | `SELECT    strftime('%m', invoice_date) AS month_number,   SUM(total) AS revenue,   LAG(SUM(total)) OVER (ORDER BY strftime('%m', invoice_date)) AS previous_month_revenue FROM    invoice WHERE    strft` |
| 29 | 2 | h09 | exec_error | exec_error | UndefinedFunction: function strftime(unknown, timestamp without time zone) does not exist
LINE 5:   WHERE strf | `SELECT COUNT(*)  FROM (   SELECT customer_id    FROM invoice    WHERE strftime('%Y', invoice_date) = '2025'   AND customer_id NOT IN (     SELECT customer_id      FROM invoice      WHERE strftime('%Y'` |
| 29 | 2 | h10 | exec_error | exec_error | UndefinedFunction: function strftime(unknown, timestamp without time zone) does not exist
LINE 3:         strf | `WITH MonthlyRevenue AS (     SELECT         strftime('%Y-%m', invoice_date) AS month,         SUM(total) AS revenue     FROM         invoice     WHERE         strftime('%Y', invoice_date) = '2023'    ` |
| 29 | 3 | e07 | exec_error | exec_error | UndefinedFunction: function strftime(unknown, timestamp without time zone) does not exist
LINE 3: WHERE strfti | `SELECT COUNT(*)  FROM invoice  WHERE strftime('%Y', invoice_date) = '2023';` |
| 29 | 3 | m03 | timeout | timeout | timeout: no response within 180s | `` |
| 29 | 3 | m09 | exec_error | exec_error | UndefinedFunction: function strftime(unknown, timestamp without time zone) does not exist
LINE 2:   strftime(' | `SELECT    strftime('%Y', invoice_date) AS year,    SUM(total) AS revenue FROM    invoice GROUP BY    strftime('%Y', invoice_date) ORDER BY    year;` |
| 29 | 3 | h03 | wrong_result | wrong | row count 59 != gold 22 | `SELECT      c.first_name,      c.last_name,      SUM(i.total) AS total_spend FROM      customer c JOIN      invoice i ON c.customer_id = i.customer_id GROUP BY      c.customer_id, c.first_name, c.last` |
| 29 | 3 | h05 | exec_error | exec_error | UndefinedFunction: function strftime(unknown, timestamp without time zone) does not exist
LINE 2:   strftime(' | `SELECT    strftime('%m', invoice_date) AS month_number,   SUM(total) AS revenue,   LAG(SUM(total)) OVER (ORDER BY strftime('%m', invoice_date)) AS previous_month_revenue FROM    invoice WHERE    strft` |
| 29 | 3 | h09 | exec_error | exec_error | UndefinedFunction: function strftime(unknown, timestamp without time zone) does not exist
LINE 5:   WHERE strf | `SELECT COUNT(*)  FROM (   SELECT customer_id    FROM invoice    WHERE strftime('%Y', invoice_date) = '2025'   AND customer_id NOT IN (     SELECT customer_id      FROM invoice      WHERE strftime('%Y'` |
| 29 | 3 | h10 | exec_error | exec_error | UndefinedFunction: function strftime(unknown, timestamp without time zone) does not exist
LINE 3:         strf | `WITH MonthlyRevenue AS (     SELECT         strftime('%Y-%m', invoice_date) AS month,         SUM(total) AS revenue     FROM         invoice     WHERE         strftime('%Y', invoice_date) = '2023'    ` |
| holdout | 1 | ho10 | exec_error | exec_error | UndefinedFunction: function strftime(unknown, timestamp without time zone) does not exist
LINE 2:     strftime | `SELECT      strftime('%w', invoice_date) AS day_of_week,      COUNT(*) AS invoice_count FROM      invoice WHERE      strftime('%Y', invoice_date) = '2024' GROUP BY      strftime('%w', invoice_date) OR` |
| holdout | 1 | ho13 | exec_error | exec_error | UndefinedFunction: function strftime(unknown, timestamp without time zone) does not exist
LINE 2:   strftime(' | `SELECT    strftime('%q', invoice_date) AS quarter,   SUM(total) AS revenue,   LAG(SUM(total)) OVER (ORDER BY strftime('%q', invoice_date)) AS previous_quarter_revenue FROM    invoice WHERE    strftime` |
| holdout | 1 | ho14 | exec_error | exec_error | UndefinedFunction: function strftime(unknown, timestamp without time zone) does not exist
LINE 2:     strftime | `SELECT      strftime('%W', invoice_date) AS week_number,      SUM(total) AS revenue FROM      invoice WHERE      strftime('%Y', invoice_date) = '2023' GROUP BY      week_number ORDER BY      revenue D` |
| holdout | 2 | ho10 | exec_error | exec_error | UndefinedFunction: function strftime(unknown, timestamp without time zone) does not exist
LINE 2:     strftime | `SELECT      strftime('%w', invoice_date) AS day_of_week,      COUNT(*) AS invoice_count FROM      invoice WHERE      invoice_date BETWEEN '2024-01-01' AND '2024-12-31' GROUP BY      strftime('%w', inv` |
| holdout | 2 | ho13 | exec_error | exec_error | UndefinedFunction: function strftime(unknown, timestamp without time zone) does not exist
LINE 2:   strftime(' | `SELECT    strftime('%q', invoice_date) AS quarter,   SUM(total) AS revenue,   LAG(SUM(total)) OVER (ORDER BY strftime('%q', invoice_date)) AS previous_quarter_revenue FROM    invoice WHERE    strftime` |
| holdout | 2 | ho14 | exec_error | exec_error | UndefinedFunction: function strftime(unknown, timestamp without time zone) does not exist
LINE 2:     strftime | `SELECT      strftime('%W', invoice_date) AS week_number,      SUM(total) AS revenue FROM      invoice WHERE      strftime('%Y', invoice_date) = '2023' GROUP BY      week_number ORDER BY      revenue D` |
| holdout | 3 | ho10 | exec_error | exec_error | UndefinedFunction: function strftime(unknown, timestamp without time zone) does not exist
LINE 2:     strftime | `SELECT      strftime('%w', invoice_date) AS day_of_week,      COUNT(*) AS invoice_count FROM      invoice WHERE      invoice_date BETWEEN '2024-01-01' AND '2024-12-31' GROUP BY      strftime('%w', inv` |
| holdout | 3 | ho13 | exec_error | exec_error | UndefinedFunction: function strftime(unknown, timestamp without time zone) does not exist
LINE 2:   strftime(' | `SELECT    strftime('%q', invoice_date) AS quarter,   SUM(total) AS revenue,   LAG(SUM(total)) OVER (ORDER BY strftime('%q', invoice_date)) AS previous_quarter_revenue FROM    invoice WHERE    strftime` |
| holdout | 3 | ho14 | exec_error | exec_error | UndefinedFunction: function strftime(unknown, timestamp without time zone) does not exist
LINE 2:     strftime | `SELECT      strftime('%W', invoice_date) AS week_number,      SUM(total) AS revenue FROM      invoice WHERE      strftime('%Y', invoice_date) = '2023' GROUP BY      week_number ORDER BY      revenue D` |

## Side view: timed-out attempts re-scored from their partial completion (not the headline)

| set | run | id | output tokens at cutoff | last complete ```sql block | label |
|---|---|---|---|---|---|
| 29 | 1 | m04 | n/a | n/a | harness-side 180 s cut fired first; partial completion not recorded |
| 29 | 1 | h10 | n/a | n/a | harness-side 180 s cut fired first; partial completion not recorded |
| 29 | 2 | m09 | n/a | n/a | harness-side 180 s cut fired first; partial completion not recorded |
| 29 | 3 | m03 | n/a | n/a | harness-side 180 s cut fired first; partial completion not recorded |
