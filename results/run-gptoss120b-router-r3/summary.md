# nl2sql-bench report (live run)

- Report generated: 2026-10-19 20:49 IST
- Dataset: Chinook 1.4.5 on Postgres 16.4; 29 questions x 3 run(s)
- LLM: `gpt-oss:120b` via `https://ollama.com/v1`, embeddings `nomic-embed-text` (same for all systems, via llm-meter)
- EX(exact) = same result set as gold (column order free; row order checked only when the question requires it).
  EX(relaxed) also accepts extra columns. Latency = wall time of the tool's API call (question -> SQL / result).
  Tokens = measured by llm-meter proxy (chat prompt+completion; embeddings separate).
- Per-call wall-clock cap 180s: a call exceeding it is recorded as `timeout` and counts as a failure.

| System | EX exact | EX relaxed | wrong result | tool errors | exec errors | timeouts | unsupported | p50 latency s | p95 latency s | avg prompt tok | avg completion tok |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Router (cube_v2 → WrenAI semantic, no reasoning) | 86/87 (99%) | 86/87 (99%) | 1 | 0 | 0 | 0 | 0 | 2.09 | 4.49 | 3106 | 263 |

## EX (exact) by difficulty

| System | easy | medium | hard |
|---|---|---|---|
| Router (cube_v2 → WrenAI semantic, no reasoning) | 24/24 | 27/27 | 35/36 |

## Router path / fallback

- Fallback rate: 0/87 (0% of attempts)
- Triggers: none
- Fallback latency: n/a
- Cube-path latency p50/p95 (s): 2.09 / 4.49

- Silent-wrong (cube answered, no fallback, not EX exact): 1: h10@r2


## Per question (status per run)

| id | diff | router |
|---|---|---|
| e01 | easy | ✅ ✅ ✅ |
| e02 | easy | ✅ ✅ ✅ |
| e03 | easy | ✅ ✅ ✅ |
| e04 | easy | ✅ ✅ ✅ |
| e05 | easy | ✅ ✅ ✅ |
| e06 | easy | ✅ ✅ ✅ |
| e07 | easy | ✅ ✅ ✅ |
| e08 | easy | ✅ ✅ ✅ |
| m01 | medium | ✅ ✅ ✅ |
| m02 | medium | ✅ ✅ ✅ |
| m03 | medium | ✅ ✅ ✅ |
| m04 | medium | ✅ ✅ ✅ |
| m05 | medium | ✅ ✅ ✅ |
| m06 | medium | ✅ ✅ ✅ |
| m07 | medium | ✅ ✅ ✅ |
| m08 | medium | ✅ ✅ ✅ |
| m09 | medium | ✅ ✅ ✅ |
| h01 | hard | ✅ ✅ ✅ |
| h02 | hard | ✅ ✅ ✅ |
| h03 | hard | ✅ ✅ ✅ |
| h04 | hard | ✅ ✅ ✅ |
| h05 | hard | ✅ ✅ ✅ |
| h06 | hard | ✅ ✅ ✅ |
| h07 | hard | ✅ ✅ ✅ |
| h08 | hard | ✅ ✅ ✅ |
| h09 | hard | ✅ ✅ ✅ |
| h10 | hard | ✅ ❌ ✅ |
| h11 | hard | ✅ ✅ ✅ |
| h12 | hard | ✅ ✅ ✅ |

Legend: ✅ exact match, 🟡 match with extra columns, ❌ wrong result, 💥 SQL failed to execute, ⚠️ tool/API error, ⏱️ timeout (no answer within the per-call cap; counted as failure), ⛔ declared unsupported.
