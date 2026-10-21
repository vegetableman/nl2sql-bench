# Vanna + TypeSafe Jev answer check (vanna_jev, vanna_jev_retry)

Jev request = mnemiq_jev_v2's variant b (bench/jev_judge.py; parity-checked against the mnemiq patch by bench/jev_judge_parity.py). Schema = the DDL Vanna retrieved for the question. Threshold 0.5, fail-closed; Jev error -> fail-open; SQL that fails to execute is returned unjudged. Jev tokens/latency are Jev's own `usage` / measured round trip (Jev bypasses llm-meter). Cost = input tokens x $0.042/M.

| set | system | attempts | EX exact | tie-rule | LLM calls/q | Jev calls/q | passed | declined | fell open | exec failed (unjudged) | retried | rescued by retry | Jev input tok | Jev cost | Jev p50/p95 ms |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 29 | vanna_jev | 87 | 86/87 | 86/87 | 1.00 | 1.00 | 87 | 0 | 0 | 0 | 0 | 0 | 118,984 | $0.0050 | 150 / 187 |
| 29 | vanna_jev_retry | 87 | 87/87 | 87/87 | 1.00 | 1.00 | 87 | 0 | 0 | 0 | 0 | 0 | 118,916 | $0.0050 | 149 / 211 |
| holdout | vanna_jev | 45 | 42/45 | 45/45 | 1.00 | 1.00 | 45 | 0 | 0 | 0 | 0 | 0 | 60,355 | $0.0025 | 151 / 206 |
| holdout | vanna_jev_retry | 45 | 42/45 | 45/45 | 1.00 | 1.00 | 45 | 0 | 0 | 0 | 0 | 0 | 60,289 | $0.0025 | 158 / 204 |

## Every decline (each declined attempt; retry rows show both)

| set | system | id | run | attempt | Jev p | SQL right? | how | SQL |
|---|---|---|---|---|---|---|---|---|
| - | - | - | - | - | - | - | none | |

## Retries (vanna_jev_retry)

| set | system | id | run | 1st: p (SQL) | 2nd: p (SQL) | final status |
|---|---|---|---|---|---|---|
| - | - | - | - | - | none | |

## Every other miss (not a decline)

| set | system | id | run | status | SQL right? | Jev p (last attempt) | decision |
|---|---|---|---|---|---|---|---|
| 29 | vanna_jev | h02 | 2 | wrong_result | wrong | 0.84 | passed |
| holdout | vanna_jev | ho14 | 1 | wrong_result | RIGHT (valid under gold boundary tie) | 0.56 | passed |
| holdout | vanna_jev | ho14 | 2 | wrong_result | RIGHT (valid under gold boundary tie) | 0.57 | passed |
| holdout | vanna_jev | ho14 | 3 | wrong_result | RIGHT (exact) | 0.53 | passed |
| holdout | vanna_jev_retry | ho14 | 1 | wrong_result | RIGHT (valid under gold boundary tie) | 0.53 | passed |
| holdout | vanna_jev_retry | ho14 | 2 | wrong_result | RIGHT (valid under gold boundary tie) | 0.57 | passed |
| holdout | vanna_jev_retry | ho14 | 3 | wrong_result | RIGHT (valid under gold boundary tie) | 0.51 | passed |

## Offline same-SQL view: Jev variant b on plain `vanna`'s 132 saved SQLs

Judged 131 (1 exec failure not judged, as online); Jev HTTP [200]; fell open 0; input tokens 177,634 ($0.0075).

| set | right passed | right BLOCKED | wrong CAUGHT | wrong passed | not judged (exec error) |
|---|---|---|---|---|---|
| 29 | 84 | 0 | 0 | 2 | 1 |
| holdout | 45 | 0 | 0 | 0 | 0 |

Plain vanna's known misses under this check: 29:h02 r1 (wrong_result; wrong) -> p=0.81 passed; 29:h03 r1 (exec_error; exec error: syntax error at or near ")"
) -> not judged; 29:h02 r3 (wrong_result; wrong) -> p=0.84 passed; holdout:ho14 r1 (wrong_result; right: valid under gold boundary tie) -> p=0.56 passed; holdout:ho14 r2 (wrong_result; right: valid under gold boundary tie) -> p=0.56 passed; holdout:ho14 r3 (wrong_result; right: valid under gold boundary tie) -> p=0.51 passed
