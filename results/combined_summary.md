# nl2sql-bench — combined report (4 systems)

- Generated 2026-10-19 15:35 IST by `bench/combine.py` from: `wrenai` ← `results/run-gptoss120b-r3`, `wrenai_mdl` ← `results/run-gptoss120b-wrenmdl-r3`, `dbgpt` ← `results/run-gptoss120b-r3`, `cube` ← `results/run-gptoss120b-r3`
- Chinook on Postgres 16.4, 29 questions x 3 runs per system; LLM `gpt-oss:120b` via `https://ollama.com/v1`, embeddings `nomic-embed-text` (local ollama); same scorer, 180 s per-call cap, tokens via llm-meter.
- `wrenai` (OOTB) and `wrenai_mdl` are two separate WrenAI 0.29.2 stacks with identical images/config; the only difference is the semantic layer in `wrenai_mdl/mdl/semantic_layer.yaml` (descriptions, relationship descriptions, 9 calculated fields, 9 generic instructions; no SQL pairs, no views).
- OOTB WrenAI tokens come from the separate 1-run re-measure `results/run-gptoss120b-wren-tokens` (r3 lost them to a meter-key bug); all other token numbers come from the accuracy runs.
- The OOTB/DB-GPT/Cube runs were executed earlier the same day than the `wrenai_mdl` run — Ollama Cloud latency may differ between sessions. WrenAI latencies cluster at ~1 s steps (6.06, 7.06 s …) because wren-ui polls the ai-service about once per second, so Wren p50 differences of ~1 s are within that granularity.

## Overall

| System | EX exact | EX relaxed | wrong | exec err | tool err | timeout | unsupported | p50 s | p95 s | mean s | avg prompt tok | avg completion tok | avg LLM calls | token source |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| WrenAI 0.29.2 (out of the box) | 79/87 (91%) | 81/87 (93%) | 4 | 2 | 0 | 0 | 0 | 7.06 | 9.09 | 6.97 | 14,572 | 1,058 | 3.0 | run-gptoss120b-wren-tokens (29 rows) |
| WrenAI 0.29.2 + semantic layer | 81/87 (93%) | 84/87 (97%) | 2 | 1 | 0 | 0 | 0 | 6.08 | 9.08 | 6.87 | 24,888 | 962 | 3.0 | run-gptoss120b-wrenmdl-r3 (87 rows) |
| DB-GPT 0.8.2 | 81/87 (93%) | 81/87 (93%) | 3 | 3 | 0 | 0 | 0 | 1.95 | 3.65 | 2.18 | 1,684 | 338 | 1.0 | run-gptoss120b-r3 (87 rows) |
| Cube Core 1.8.8 + LLM adapter (harness-built) | 58/87 (67%) | 65/87 (75%) | 7 | 0 | 0 | 0 | 15 | 1.64 | 3.34 | 1.92 | 1,336 | 276 | 1.0 | run-gptoss120b-r3 (87 rows) |

## EX exact by difficulty

| System | easy | medium | hard |
|---|---|---|---|
| WrenAI 0.29.2 (out of the box) | 24/24 (100%) | 23/27 (85%) | 32/36 (89%) |
| WrenAI 0.29.2 + semantic layer | 23/24 (96%) | 25/27 (93%) | 33/36 (92%) |
| DB-GPT 0.8.2 | 21/24 (88%) | 27/27 (100%) | 33/36 (92%) |
| Cube Core 1.8.8 + LLM adapter (harness-built) | 19/24 (79%) | 23/27 (85%) | 16/36 (44%) |

## Run-to-run variance

| System | EX exact per run | mean ± sd (of 29) | questions with mixed outcomes across runs | p50 latency per run (s) |
|---|---|---|---|---|
| WrenAI 0.29.2 (out of the box) | 27 / 24 / 28 | 26.3 ± 2.1 | 5 (m03, h01, h10, h11, h12) | 7.06 / 7.06 / 7.06 |
| WrenAI 0.29.2 + semantic layer | 25 / 28 / 28 | 27.0 ± 1.7 | 4 (e04, m08, h02, h09) | 6.07 / 7.06 / 7.06 |
| DB-GPT 0.8.2 | 27 / 27 / 27 | 27.0 ± 0.0 | 0 (-) | 1.96 / 1.92 / 2.03 |
| Cube Core 1.8.8 + LLM adapter (harness-built) | 20 / 19 / 19 | 19.3 ± 0.6 | 4 (e04, m09, h08, h10) | 1.77 / 1.65 / 1.55 |

## WrenAI: out of the box vs + semantic layer (per question, EX exact over 3 runs)

| id | diff | question | OOTB | +MDL | OOTB statuses | +MDL statuses | change |
|---|---|---|---|---|---|---|---|
| e01 | easy | How many tracks are there in total? | 3/3 | 3/3 | ✅ ✅ ✅ | ✅ ✅ ✅ |  |
| e02 | easy | List the names of all music genres. | 3/3 | 3/3 | ✅ ✅ ✅ | ✅ ✅ ✅ |  |
| e03 | easy | How many customers are from Brazil? | 3/3 | 3/3 | ✅ ✅ ✅ | ✅ ✅ ✅ |  |
| e04 | easy | Which tracks are longer than 20 minutes? Return the track names. | 3/3 | 2/3 | ✅ ✅ ✅ | 🟡 ✅ ✅ | worse |
| e05 | easy | What is the highest unit price of any track? | 3/3 | 3/3 | ✅ ✅ ✅ | ✅ ✅ ✅ |  |
| e06 | easy | List the first and last names of employees whose title is 'Sales Suppo | 3/3 | 3/3 | ✅ ✅ ✅ | ✅ ✅ ✅ |  |
| e07 | easy | How many invoices were issued in the year 2023? | 3/3 | 3/3 | ✅ ✅ ✅ | ✅ ✅ ✅ |  |
| e08 | easy | Which customers have a company listed? Return their first name, last n | 3/3 | 3/3 | ✅ ✅ ✅ | ✅ ✅ ✅ |  |
| m01 | medium | How many tracks are there in each genre? Return the genre name and the | 3/3 | 3/3 | ✅ ✅ ✅ | ✅ ✅ ✅ |  |
| m02 | medium | Which 5 artists have the most albums? Return the artist name and album | 0/3 | 3/3 | ❌ ❌ ❌ | ✅ ✅ ✅ | **fixed** |
| m03 | medium | What are the total sales (sum of invoice totals) for each billing coun | 2/3 | 3/3 | ✅ 💥 ✅ | ✅ ✅ ✅ | better |
| m04 | medium | Which customers are supported by the employee Jane Peacock? Return the | 3/3 | 3/3 | ✅ ✅ ✅ | ✅ ✅ ✅ |  |
| m05 | medium | What is the average track length in minutes for each media type? Retur | 3/3 | 3/3 | ✅ ✅ ✅ | ✅ ✅ ✅ |  |
| m06 | medium | Which albums have more than 20 tracks? Return the album title and the  | 3/3 | 3/3 | ✅ ✅ ✅ | ✅ ✅ ✅ |  |
| m07 | medium | Which genre has the most tracks? Return the genre name. | 3/3 | 3/3 | ✅ ✅ ✅ | ✅ ✅ ✅ |  |
| m08 | medium | How many tracks are in the playlist named '90’s Music'? | 3/3 | 1/3 | ✅ ✅ ✅ | 🟡 ✅ 🟡 | worse |
| m09 | medium | What is the total invoice revenue for each year? Return the year and r | 3/3 | 3/3 | ✅ ✅ ✅ | ✅ ✅ ✅ |  |
| h01 | hard | What are the top 3 genres by sales revenue, where revenue is unit pric | 2/3 | 3/3 | ✅ 🟡 ✅ | ✅ ✅ ✅ | better |
| h02 | hard | For each sales support agent, what is the total invoice amount from th | 3/3 | 1/3 | ✅ ✅ ✅ | ❌ ❌ ✅ | worse |
| h03 | hard | Which customers have spent more in total than the average total spend  | 3/3 | 3/3 | ✅ ✅ ✅ | ✅ ✅ ✅ |  |
| h04 | hard | For each country, which customer has the highest total spend? Include  | 3/3 | 3/3 | ✅ ✅ ✅ | ✅ ✅ ✅ |  |
| h05 | hard | For each month of 2024, show the total invoice revenue and the previou | 3/3 | 3/3 | ✅ ✅ ✅ | ✅ ✅ ✅ |  |
| h06 | hard | Which artists have tracks in more than 3 different genres? Return the  | 3/3 | 3/3 | ✅ ✅ ✅ | ✅ ✅ ✅ |  |
| h07 | hard | How many tracks have never been purchased (never appear on any invoice | 3/3 | 3/3 | ✅ ✅ ✅ | ✅ ✅ ✅ |  |
| h08 | hard | List every employee together with the name of the manager they report  | 3/3 | 3/3 | ✅ ✅ ✅ | ✅ ✅ ✅ |  |
| h09 | hard | How many customers made at least one purchase in 2025 but made no purc | 3/3 | 2/3 | ✅ ✅ ✅ | 💥 ✅ ✅ | worse |
| h10 | hard | For each month of 2023, show the year-to-date running total of invoice | 2/3 | 3/3 | ❌ ✅ ✅ | ✅ ✅ ✅ | better |
| h11 | hard | What percentage of total sales revenue (unit price times quantity) com | 2/3 | 3/3 | ✅ 💥 ✅ | ✅ ✅ ✅ | better |
| h12 | hard | Which 5 artists generated the most sales revenue (unit price times qua | 2/3 | 3/3 | ✅ 🟡 ✅ | ✅ ✅ ✅ | better |

- fixed (0/3 → 3/3): m02; broke (3/3 → 0/3): none
- partially better: m03, h01, h10, h11, h12; partially worse: e04, m08, h02, h09

## WrenAI + semantic layer: every non-exact attempt

| run | id | status | reason / error |
|---|---|---|---|
| 1 | e04 | correct_extra_cols | match with 1 extra column(s) |
| 1 | m08 | correct_extra_cols | match with 2 extra column(s) |
| 1 | h02 | wrong_result | row count 8 != gold 3 |
| 1 | h09 | exec_error | UndefinedTable: missing FROM-clause entry for table "customers_2025" LINE 1: ...:00:00' AS TIMESTAMPTZ)) AS customers_2024) WHERE customers_...                  |
| 2 | h02 | wrong_result | row count 8 != gold 3 |
| 3 | m08 | correct_extra_cols | match with 1 extra column(s) |

## Per question, all systems (status per run)

| id | diff | WrenAI 0.29.2 (out of the box) | WrenAI 0.29.2 + semantic layer | DB-GPT 0.8.2 | Cube Core 1.8.8 + LLM adapter (harness-built) |
|---|---|---|---|---|---|
| e01 | easy | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ |
| e02 | easy | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ |
| e03 | easy | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ |
| e04 | easy | ✅ ✅ ✅ | 🟡 ✅ ✅ | ❌ ❌ ❌ | ✅ ❌ ❌ |
| e05 | easy | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ |
| e06 | easy | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ |
| e07 | easy | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | 🟡 🟡 🟡 |
| e08 | easy | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ |
| m01 | medium | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ |
| m02 | medium | ❌ ❌ ❌ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ |
| m03 | medium | ✅ 💥 ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ |
| m04 | medium | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ |
| m05 | medium | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ |
| m06 | medium | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ |
| m07 | medium | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | 🟡 🟡 🟡 |
| m08 | medium | ✅ ✅ ✅ | 🟡 ✅ 🟡 | ✅ ✅ ✅ | ✅ ✅ ✅ |
| m09 | medium | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ❌ |
| h01 | hard | ✅ 🟡 ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ |
| h02 | hard | ✅ ✅ ✅ | ❌ ❌ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ |
| h03 | hard | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ⛔ ⛔ ⛔ |
| h04 | hard | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ⛔ ⛔ ⛔ |
| h05 | hard | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ⛔ ⛔ ⛔ |
| h06 | hard | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ |
| h07 | hard | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ❌ ❌ ❌ |
| h08 | hard | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ❌ ✅ ✅ |
| h09 | hard | ✅ ✅ ✅ | 💥 ✅ ✅ | ✅ ✅ ✅ | ⛔ ⛔ ⛔ |
| h10 | hard | ❌ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ 🟡 ✅ |
| h11 | hard | ✅ 💥 ✅ | ✅ ✅ ✅ | 💥 💥 💥 | ⛔ ⛔ ⛔ |
| h12 | hard | ✅ 🟡 ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ |

Legend: ✅ exact, 🟡 extra columns, ❌ wrong result, 💥 SQL exec error, ⚠️ tool/API error, ⏱️ timeout (failure), ⛔ declared unsupported.
