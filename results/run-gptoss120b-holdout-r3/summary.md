# nl2sql-bench report (live run)

- Report generated: 2026-10-19 21:32 IST
- Dataset: Chinook 1.4.5 on Postgres 16.4; 15 questions x 3 run(s)
- LLM: `gpt-oss:120b` via `https://ollama.com/v1`, embeddings `nomic-embed-text` (same for all systems, via llm-meter)
- EX(exact) = same result set as gold (column order free; row order checked only when the question requires it).
  EX(relaxed) also accepts extra columns. Latency = wall time of the tool's API call (question -> SQL / result).
  Tokens = measured by llm-meter proxy (chat prompt+completion; embeddings separate).
- Per-call wall-clock cap 180s: a call exceeding it is recorded as `timeout` and counts as a failure.

| System | EX exact | EX relaxed | wrong result | tool errors | exec errors | timeouts | unsupported | p50 latency s | p95 latency s | avg prompt tok | avg completion tok |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Router (cube_v2 → WrenAI semantic, no reasoning) | 39/45 (87%) | 39/45 (87%) | 6 | 0 | 0 | 0 | 0 | 3.54 | 7.77 | 11327 | 539 |
| Cube Core 1.8.8 + rich model + LLM adapter v2 (harness-built) | 25/45 (56%) | 25/45 (56%) | 7 | 0 | 1 | 1 | 11 | 1.92 | 5.26 | 3436 | 378 |
| WrenAI 0.29.2 + semantic layer, no reasoning | 42/45 (93%) | 42/45 (93%) | 3 | 0 | 0 | 0 | 0 | 4.06 | 6.89 | 20811 | 631 |

## EX (exact) by difficulty

| System | easy | medium | hard |
|---|---|---|---|
| Router (cube_v2 → WrenAI semantic, no reasoning) | 11/12 | 15/15 | 13/18 |
| Cube Core 1.8.8 + rich model + LLM adapter v2 (harness-built) | 6/12 | 8/15 | 11/18 |
| WrenAI 0.29.2 + semantic layer, no reasoning | 12/12 | 15/15 | 15/18 |

## Router path / fallback

- Fallback rate: 17/45 (38% of attempts)
- Triggers: cube_error=1, cube_unsupported=16
- Fallback latency p50/p95 (s): 5.28 / 10.53
- Cube-path latency p50/p95 (s): 2.40 / 5.86

- Silent-wrong (cube answered, no fallback, not EX exact): 6: ho12@r1, ho12@r2, ho14@r2, ho04@r3, ho12@r3, ho14@r3


## Per question (status per run)

| id | diff | router | cube_v2 | wrenai_mdl_noreason |
|---|---|---|---|---|
| ho01 | easy | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ |
| ho02 | easy | ✅ ✅ ✅ | ⛔ ⛔ ⛔ | ✅ ✅ ✅ |
| ho03 | easy | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ |
| ho04 | easy | ✅ ✅ ❌ | ❌ ❌ ❌ | ✅ ✅ ✅ |
| ho05 | medium | ✅ ✅ ✅ | ✅ ⛔ ⛔ | ✅ ✅ ✅ |
| ho06 | medium | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ |
| ho07 | medium | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ |
| ho08 | medium | ✅ ✅ ✅ | ⛔ ⛔ ⛔ | ✅ ✅ ✅ |
| ho09 | medium | ✅ ✅ ✅ | ✅ ❌ ❌ | ✅ ✅ ✅ |
| ho10 | hard | ✅ ✅ ✅ | ✅ ✅ ⏱️ | ✅ ✅ ✅ |
| ho11 | hard | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ |
| ho12 | hard | ❌ ❌ ❌ | ❌ 💥 ❌ | ✅ ✅ ✅ |
| ho13 | hard | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ |
| ho14 | hard | ✅ ❌ ❌ | ✅ ✅ ✅ | ❌ ❌ ❌ |
| ho15 | hard | ✅ ✅ ✅ | ⛔ ⛔ ⛔ | ✅ ✅ ✅ |

Legend: ✅ exact match, 🟡 match with extra columns, ❌ wrong result, 💥 SQL failed to execute, ⚠️ tool/API error, ⏱️ timeout (no answer within the per-call cap; counted as failure), ⛔ declared unsupported.
