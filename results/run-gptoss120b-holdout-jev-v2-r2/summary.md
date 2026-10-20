# nl2sql-bench report (live run)

- Report generated: 2026-10-20 13:27 IST
- Dataset: Chinook 1.4.5 on Postgres 16.4; 15 questions x 3 run(s)
- LLM: `gpt-oss:120b` via `https://ollama.com/v1`, embeddings `nomic-embed-text` (same for all systems, via llm-meter)
- EX(exact) = same result set as gold (column order free; row order checked only when the question requires it).
  EX(relaxed) also accepts extra columns. Latency = wall time of the tool's API call (question -> SQL / result).
  Tokens = measured by llm-meter proxy (chat prompt+completion; embeddings separate).
- Per-call wall-clock cap 180s: a call exceeding it is recorded as `timeout` and counts as a failure.

| System | EX exact | EX relaxed | wrong result | tool errors | exec errors | timeouts | unsupported | declined | p50 latency s | p95 latency s | avg prompt tok | avg completion tok |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| mnemiq, TypeSafe Jev judge v2 (truncation-aware, fail-closed) | 38/45 (84%) | 38/45 (84%) | 1 | 0 | 0 | 0 | 0 | 6 | 2.57 | 4.35 | 2804 | 401 |

## EX (exact) by difficulty

| System | easy | medium | hard |
|---|---|---|---|
| mnemiq, TypeSafe Jev judge v2 (truncation-aware, fail-closed) | 12/12 | 15/15 | 11/18 |

## Per question (status per run)

| id | diff | mnemiq_jev_v2 |
|---|---|---|
| ho01 | easy | ✅ ✅ ✅ |
| ho02 | easy | ✅ ✅ ✅ |
| ho03 | easy | ✅ ✅ ✅ |
| ho04 | easy | ✅ ✅ ✅ |
| ho05 | medium | ✅ ✅ ✅ |
| ho06 | medium | ✅ ✅ ✅ |
| ho07 | medium | ✅ ✅ ✅ |
| ho08 | medium | ✅ ✅ ✅ |
| ho09 | medium | ✅ ✅ ✅ |
| ho10 | hard | 🚫 🚫 🚫 |
| ho11 | hard | ✅ ✅ ✅ |
| ho12 | hard | 🚫 ✅ ✅ |
| ho13 | hard | ✅ ✅ ✅ |
| ho14 | hard | ❌ 🚫 🚫 |
| ho15 | hard | ✅ ✅ ✅ |

Legend: ✅ exact match, 🟡 match with extra columns, ❌ wrong result, 💥 SQL failed to execute, ⚠️ tool/API error, ⏱️ timeout (no answer within the per-call cap; counted as failure), ⛔ declared unsupported, 🚫 declined (mnemiq deferral; counts as not correct).
