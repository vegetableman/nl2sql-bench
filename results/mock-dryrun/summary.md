# nl2sql-bench report (MOCK dry-run — numbers are NOT real tool results)

- Date: 2026-10-19 07:18 (box local time, IST)
- Dataset: Chinook 1.4.5 on Postgres 16.4; 29 questions x 2 run(s)
- LLM: `gpt-4o-mini` via `https://api.openai.com/v1`, embeddings `text-embedding-3-small` (same for all systems, via llm-meter)
- EX(exact) = same result set as gold (column order free; row order checked only when the question requires it).
  EX(relaxed) also accepts extra columns. Latency = wall time of the tool's API call (question -> SQL / result).
  Tokens = measured by llm-meter proxy (chat prompt+completion; embeddings separate).

| System | EX exact | EX relaxed | tool errors | exec errors | unsupported | p50 latency s | p95 latency s | avg prompt tok | avg completion tok |
|---|---|---|---|---|---|---|---|---|---|
| WrenAI 0.29.2 | 48/58 (83%) | 48/58 (83%) | 4 | 3 | 0 | 0.03 | 0.05 | 0 | 0 |
| DB-GPT 0.8.2 | 47/58 (81%) | 47/58 (81%) | 8 | 1 | 0 | 0.03 | 0.05 | 0 | 0 |
| Cube Core 1.8.8 + LLM adapter (harness-built) | 44/58 (76%) | 46/58 (79%) | 0 | 0 | 12 | 0.01 | 0.02 | 0 | 0 |

## EX (exact) by difficulty

| System | easy | medium | hard |
|---|---|---|---|
| WrenAI 0.29.2 | 13/16 | 15/18 | 20/24 |
| DB-GPT 0.8.2 | 12/16 | 16/18 | 19/24 |
| Cube Core 1.8.8 + LLM adapter (harness-built) | 16/16 | 16/18 | 12/24 |

Cube: EX on the 23 questions expressible in the Cube model: 44/46. Not expressible as a single Cube query: h03, h04, h05, h07, h09, h11.

## Per question (status per run)

| id | diff | wrenai | dbgpt | cube |
|---|---|---|---|---|
| e01 | easy | 💥 ✅ | ✅ ✅ | ✅ ✅ |
| e02 | easy | ✅ ✅ | ✅ ⚠️ | ✅ ✅ |
| e03 | easy | ✅ ✅ | ⚠️ ⚠️ | ✅ ✅ |
| e04 | easy | ✅ ⚠️ | ✅ ✅ | ✅ ✅ |
| e05 | easy | ✅ ✅ | ✅ ⚠️ | ✅ ✅ |
| e06 | easy | ✅ ✅ | ✅ ✅ | ✅ ✅ |
| e07 | easy | ✅ ⚠️ | ✅ ✅ | ✅ ✅ |
| e08 | easy | ✅ ✅ | ✅ ✅ | ✅ ✅ |
| m01 | medium | ✅ ✅ | ✅ ✅ | ✅ ✅ |
| m02 | medium | ✅ ✅ | ✅ ✅ | ✅ ✅ |
| m03 | medium | ⚠️ ✅ | ✅ ✅ | ✅ ✅ |
| m04 | medium | ✅ ✅ | ✅ ✅ | ✅ ✅ |
| m05 | medium | ✅ ✅ | ⚠️ ✅ | ✅ ✅ |
| m06 | medium | ✅ ✅ | ✅ ✅ | ✅ ✅ |
| m07 | medium | 💥 ✅ | ✅ 💥 | 🟡 🟡 |
| m08 | medium | ✅ ✅ | ✅ ✅ | ✅ ✅ |
| m09 | medium | ✅ 💥 | ✅ ✅ | ✅ ✅ |
| h01 | hard | ✅ ❌ | ✅ ✅ | ✅ ✅ |
| h02 | hard | ✅ ✅ | ✅ ❌ | ✅ ✅ |
| h03 | hard | ✅ ✅ | ✅ ✅ | ⛔ ⛔ |
| h04 | hard | ✅ ✅ | ✅ ✅ | ⛔ ⛔ |
| h05 | hard | ✅ ✅ | ⚠️ ✅ | ⛔ ⛔ |
| h06 | hard | ✅ ✅ | ✅ ✅ | ✅ ✅ |
| h07 | hard | ✅ ✅ | ✅ ❌ | ⛔ ⛔ |
| h08 | hard | ✅ ✅ | ✅ ✅ | ✅ ✅ |
| h09 | hard | ✅ ✅ | ✅ ✅ | ⛔ ⛔ |
| h10 | hard | ✅ ❌ | ✅ ⚠️ | ✅ ✅ |
| h11 | hard | ✅ ✅ | ✅ ✅ | ⛔ ⛔ |
| h12 | hard | ❌ ⚠️ | ⚠️ ✅ | ✅ ✅ |

Legend: ✅ exact match, 🟡 match with extra columns, ❌ wrong result, 💥 SQL failed to execute, ⚠️ tool/API error, ⛔ declared unsupported.
