# nl2sql-bench holdout report (live run, 4 systems)

- Dataset: Chinook holdout 15 questions × 3 runs
- Systems: router, cube_v2, wrenai_mdl_noreason, dbgpt
- Source CSV: results/run-gptoss120b-holdout-r3/results.csv

| System | EX exact | EX relaxed | p50 s | p95 s | avg prompt tok | avg LLM calls |
|---|---|---|---|---|---|---|
| Router (cube_v2 → Wren noreason) | 39/45 (87%) | 39/45 (87%) | 3.54 | 7.77 | 11,327 | 1.9 |
| cube_v2 | 25/45 (56%) | 25/45 (56%) | 1.92 | 5.26 | 3,436 | 1.2 |
| WrenAI + semantic, no reasoning | 42/45 (93%) | 42/45 (93%) | 4.06 | 6.89 | 20,811 | 2.0 |
| DB-GPT 0.8.2 | 39/45 (87%) | 39/45 (87%) | 2.61 | 4.32 | 1,693 | 1.0 |

## Per question

| id | diff | router | cube_v2 | wrenai_mdl_noreason | dbgpt |
|---|---|---|---|---|---|
| ho01 | easy | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ |
| ho02 | easy | ✅ ✅ ✅ | ⛔ ⛔ ⛔ | ✅ ✅ ✅ | ✅ ✅ ✅ |
| ho03 | easy | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ |
| ho04 | easy | ✅ ✅ ❌ | ❌ ❌ ❌ | ✅ ✅ ✅ | ✅ ✅ ✅ |
| ho05 | medium | ✅ ✅ ✅ | ✅ ⛔ ⛔ | ✅ ✅ ✅ | ✅ ✅ ✅ |
| ho06 | medium | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ |
| ho07 | medium | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ |
| ho08 | medium | ✅ ✅ ✅ | ⛔ ⛔ ⛔ | ✅ ✅ ✅ | ✅ ✅ ✅ |
| ho09 | medium | ✅ ✅ ✅ | ✅ ❌ ❌ | ✅ ✅ ✅ | ✅ ✅ ✅ |
| ho10 | hard | ✅ ✅ ✅ | ✅ ✅ ⏱️ | ✅ ✅ ✅ | ✅ ✅ ✅ |
| ho11 | hard | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ |
| ho12 | hard | ❌ ❌ ❌ | ❌ 💥 ❌ | ✅ ✅ ✅ | ❌ ❌ ❌ |
| ho13 | hard | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ |
| ho14 | hard | ✅ ❌ ❌ | ✅ ✅ ✅ | ❌ ❌ ❌ | ❌ ❌ ❌ |
| ho15 | hard | ✅ ✅ ✅ | ⛔ ⛔ ⛔ | ✅ ✅ ✅ | ✅ ✅ ✅ |
