# nl2sql-bench report (live run)

- Report generated: 2026-10-21 15:55 IST
- Dataset: Chinook 1.4.5 on Postgres 16.4; 15 questions x 3 run(s)
- LLM: `gpt-oss:120b` via `https://ollama.com/v1`, embeddings `nomic-embed-text` (same for all systems, via llm-meter)
- **arctic** does NOT use that LLM: it is its own model, Arctic-Text2SQL-R1-7B (`Snowflake/Arctic-Text2SQL-R1-7B`), served on a dedicated Hugging Face Inference Endpoint (1x nvidia-a10g, vLLM) via llm-meter /arctic/; no embeddings.
- EX(exact) = same result set as gold (column order free; row order checked only when the question requires it).
  EX(relaxed) also accepts extra columns. Latency = wall time of the tool's API call (question -> SQL / result).
  Tokens = measured by llm-meter proxy (chat prompt+completion; embeddings separate).
- Per-call wall-clock cap 180s: a call exceeding it is recorded as `timeout` and counts as a failure.

| System | EX exact | EX relaxed | wrong result | tool errors | exec errors | timeouts | unsupported | declined | p50 latency s | p95 latency s | avg prompt tok | avg completion tok |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Arctic-Text2SQL-R1-7B (dedicated HF nvidia-a10g endpoint, vLLM, Snowflake eval prompt) | 36/45 (80%) | 36/45 (80%) | 0 | 0 | 9 | 0 | 0 | 0 | 10.90 | 135.63 | 1112 | 811 |

## EX (exact) by difficulty

| System | easy | medium | hard |
|---|---|---|---|
| Arctic-Text2SQL-R1-7B (dedicated HF nvidia-a10g endpoint, vLLM, Snowflake eval prompt) | 12/12 | 15/15 | 9/18 |

## Per question (status per run)

| id | diff | arctic |
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
| ho10 | hard | 💥 💥 💥 |
| ho11 | hard | ✅ ✅ ✅ |
| ho12 | hard | ✅ ✅ ✅ |
| ho13 | hard | 💥 💥 💥 |
| ho14 | hard | 💥 💥 💥 |
| ho15 | hard | ✅ ✅ ✅ |

Legend: ✅ exact match, 🟡 match with extra columns, ❌ wrong result, 💥 SQL failed to execute, ⚠️ tool/API error, ⏱️ timeout (no answer within the per-call cap; counted as failure), ⛔ declared unsupported, 🚫 declined (mnemiq deferral; counts as not correct).
