# nl2sql-bench — combined report (13 systems)

- Generated 2026-10-20 13:31 IST by `bench/combine.py` from: `wrenai` ← `results/run-gptoss120b-r3`, `wrenai_mdl` ← `results/run-gptoss120b-wrenmdl-r3`, `wrenai_mdl_noreason` ← `results/run-gptoss120b-wrenmdl-noreason-r3`, `dbgpt` ← `results/run-gptoss120b-r3`, `cube` ← `results/run-gptoss120b-r3`, `cube_v2` ← `results/run-gptoss120b-cubev2-r3`, `router` ← `results/run-gptoss120b-router-r3`, `mnemiq` ← `results/run-gptoss120b-mnemiq-r3`, `mnemiq_failopen` ← `results/run-gptoss120b-mnemiq-r3`, `mnemiq_verified` ← `results/run-gptoss120b-mnemiq-r3`, `mnemiq_jev` ← `results/run-gptoss120b-mnemiq-r3`, `mnemiq_jev_v2` ← `results/run-gptoss120b-mnemiq-r3`, `mnemiq_jev_v2_r2` ← `results/run-gptoss120b-mnemiq-jev-v2-r2`
- Chinook on Postgres 16.4, 29 questions x 3 runs per system; LLM `gpt-oss:120b` via `https://ollama.com/v1`, embeddings `nomic-embed-text` (local ollama); same scorer, 180 s per-call cap, tokens via llm-meter.
- `wrenai` (OOTB) and `wrenai_mdl` are two separate WrenAI 0.29.2 stacks with identical images/config; the only difference is the semantic layer in `wrenai_mdl/mdl/semantic_layer.yaml` (descriptions, relationship descriptions, 9 calculated fields, 9 generic instructions; no SQL pairs, no views).
- `wrenai_mdl_noreason` = the same 2nd stack, same project / deployed MDL (hash checked) / instructions, with the single wren-ai-service setting `allow_sql_generation_reasoning: false` (`make wren-mdl-noreason`; `make wren-mdl-restore` switches back). Intent classification stays on. Per-stage timings: `results/stage-latency/stage_latency.md`.
- `cube` (baseline) = Cube Core 1.8.8, model `cube/model`, LLM writes one REST `/v1/load` JSON query. `cube_v2` = same Cube release, richer model `cube_v2/model` (views, subquery dimensions, segments, rolling-window and multi-stage measures), LLM writes one Cube SQL API query (Postgres wire protocol, push-down on) over the views; both are harness-built adapters with 1 repair retry. Hand-written reference queries (`make verify`, never shown to the LLM) reproduce gold for 23/29 questions with the baseline REST model and 29/29 with cube_v2's SQL API.
- `router` = try cube_v2 first (prompt copy that may reply `CANNOT_EXPRESS`), fall back to `wrenai_mdl_noreason` on unsupported / Cube error / empty result. Does not use gold for routing. Tokens: Cube under llm-meter `/router/`, Wren under `/wrenmdlnr/` (summed only on fallback). Latency and tokens count both paths when fallback fires.
- OOTB WrenAI tokens come from the separate 1-run re-measure `results/run-gptoss120b-wren-tokens` (r3 lost them to a meter-key bug); all other token numbers come from the accuracy runs.
- The OOTB/DB-GPT/Cube runs, the `wrenai_mdl` run and the `wrenai_mdl_noreason` run were executed sequentially at different times the same day — Ollama Cloud latency may differ between sessions. WrenAI latencies cluster at ~1 s steps (6.06, 7.06 s …) because wren-ui polls the ai-service about once per second, so Wren p50 differences of ~1 s are within that granularity.

## Overall

| System | EX exact | EX relaxed | wrong | exec err | tool err | timeout | unsupported | declined | p50 s | p95 s | mean s | avg prompt tok | avg completion tok | avg LLM calls | token source |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| WrenAI 0.29.2 (out of the box) | 79/87 (91%) | 81/87 (93%) | 4 | 2 | 0 | 0 | 0 | 0 | 7.06 | 9.09 | 6.97 | 14,572 | 1,058 | 3.0 | run-gptoss120b-wren-tokens (29 rows) |
| WrenAI 0.29.2 + semantic layer | 81/87 (93%) | 84/87 (97%) | 2 | 1 | 0 | 0 | 0 | 0 | 6.08 | 9.08 | 6.87 | 24,888 | 962 | 3.0 | run-gptoss120b-wrenmdl-r3 (87 rows) |
| WrenAI 0.29.2 + semantic layer, no reasoning | 86/87 (99%) | 87/87 (100%) | 0 | 0 | 0 | 0 | 0 | 0 | 4.05 | 6.07 | 4.29 | 20,941 | 604 | 2.0 | run-gptoss120b-wrenmdl-noreason-r3 (87 rows) |
| DB-GPT 0.8.2 | 81/87 (93%) | 81/87 (93%) | 3 | 3 | 0 | 0 | 0 | 0 | 1.95 | 3.65 | 2.18 | 1,684 | 338 | 1.0 | run-gptoss120b-r3 (87 rows) |
| Cube Core 1.8.8 + LLM adapter (baseline) | 58/87 (67%) | 65/87 (75%) | 7 | 0 | 0 | 0 | 15 | 0 | 1.64 | 3.34 | 1.92 | 1,336 | 276 | 1.0 | run-gptoss120b-r3 (87 rows) |
| Cube Core 1.8.8 + rich model + LLM adapter v2 (harness-built) | 85/87 (98%) | 85/87 (98%) | 2 | 0 | 0 | 0 | 0 | 0 | 1.58 | 3.36 | 1.90 | 3,137 | 265 | 1.1 | run-gptoss120b-cubev2-r3 (87 rows) |
| Router (cube_v2 → WrenAI semantic, no reasoning) | 86/87 (99%) | 86/87 (99%) | 1 | 0 | 0 | 0 | 0 | 0 | 2.09 | 4.49 | 2.25 | 3,106 | 263 | 1.0 | run-gptoss120b-router-r3 (87 rows) |
| mnemiq a453b05 (defaults) | 20/87 (23%) | 20/87 (23%) | 0 | 0 | 65 | 0 | 0 | 2 | 3.26 | 5.27 | 3.66 | 4,863 | 495 | 2.3 | run-gptoss120b-mnemiq-r3 (87 rows) |
| mnemiq a453b05, judge fail-open variant | 87/87 (100%) | 87/87 (100%) | 0 | 0 | 0 | 0 | 0 | 0 | 4.37 | 6.48 | 4.60 | 5,184 | 640 | 3.0 | run-gptoss120b-mnemiq-r3 (87 rows) |
| mnemiq a453b05, judge 1200-token variant (fail-closed) | 86/87 (99%) | 86/87 (99%) | 0 | 0 | 0 | 0 | 0 | 1 | 4.97 | 7.43 | 5.09 | 5,267 | 722 | 3.0 | run-gptoss120b-mnemiq-r3 (87 rows) |
| mnemiq a453b05, TypeSafe Jev judge (fail-closed) | 78/87 (90%) | 78/87 (90%) | 0 | 0 | 0 | 0 | 0 | 9 | 3.41 | 5.15 | 3.46 | 2,848 | 395 | 1.9 | run-gptoss120b-mnemiq-r3 (87 rows) |
| mnemiq a453b05, Jev judge v2 (truncation-aware) | 85/87 (98%) | 85/87 (98%) | 0 | 0 | 0 | 2 | 0 | 0 | 8.04 | 22.11 | 13.16 | 2,923 | 410 | 2.0 | run-gptoss120b-mnemiq-r3 (87 rows) |
| mnemiq a453b05, Jev judge v2, rerun r2 | 86/87 (99%) | 86/87 (99%) | 0 | 0 | 0 | 0 | 0 | 1 | 3.42 | 8.50 | 4.15 | 3,012 | 454 | 2.0 | run-gptoss120b-mnemiq-jev-v2-r2 (87 rows) |

## EX exact by difficulty

| System | easy | medium | hard |
|---|---|---|---|
| WrenAI 0.29.2 (out of the box) | 24/24 (100%) | 23/27 (85%) | 32/36 (89%) |
| WrenAI 0.29.2 + semantic layer | 23/24 (96%) | 25/27 (93%) | 33/36 (92%) |
| WrenAI 0.29.2 + semantic layer, no reasoning | 23/24 (96%) | 27/27 (100%) | 36/36 (100%) |
| DB-GPT 0.8.2 | 21/24 (88%) | 27/27 (100%) | 33/36 (92%) |
| Cube Core 1.8.8 + LLM adapter (baseline) | 19/24 (79%) | 23/27 (85%) | 16/36 (44%) |
| Cube Core 1.8.8 + rich model + LLM adapter v2 (harness-built) | 24/24 (100%) | 27/27 (100%) | 34/36 (94%) |
| Router (cube_v2 → WrenAI semantic, no reasoning) | 24/24 (100%) | 27/27 (100%) | 35/36 (97%) |
| mnemiq a453b05 (defaults) | 14/24 (58%) | 6/27 (22%) | 0/36 (0%) |
| mnemiq a453b05, judge fail-open variant | 24/24 (100%) | 27/27 (100%) | 36/36 (100%) |
| mnemiq a453b05, judge 1200-token variant (fail-closed) | 24/24 (100%) | 27/27 (100%) | 35/36 (97%) |
| mnemiq a453b05, TypeSafe Jev judge (fail-closed) | 18/24 (75%) | 24/27 (89%) | 36/36 (100%) |
| mnemiq a453b05, Jev judge v2 (truncation-aware) | 24/24 (100%) | 27/27 (100%) | 34/36 (94%) |
| mnemiq a453b05, Jev judge v2, rerun r2 | 24/24 (100%) | 27/27 (100%) | 35/36 (97%) |

## Run-to-run variance

| System | EX exact per run | mean ± sd (of 29) | questions with mixed outcomes across runs | p50 latency per run (s) |
|---|---|---|---|---|
| WrenAI 0.29.2 (out of the box) | 27 / 24 / 28 | 26.3 ± 2.1 | 5 (m03, h01, h10, h11, h12) | 7.06 / 7.06 / 7.06 |
| WrenAI 0.29.2 + semantic layer | 25 / 28 / 28 | 27.0 ± 1.7 | 4 (e04, m08, h02, h09) | 6.07 / 7.06 / 7.06 |
| WrenAI 0.29.2 + semantic layer, no reasoning | 28 / 29 / 29 | 28.7 ± 0.6 | 1 (e04) | 4.06 / 4.05 / 4.05 |
| DB-GPT 0.8.2 | 27 / 27 / 27 | 27.0 ± 0.0 | 0 (-) | 1.96 / 1.92 / 2.03 |
| Cube Core 1.8.8 + LLM adapter (baseline) | 20 / 19 / 19 | 19.3 ± 0.6 | 4 (e04, m09, h08, h10) | 1.77 / 1.65 / 1.55 |
| Cube Core 1.8.8 + rich model + LLM adapter v2 (harness-built) | 28 / 29 / 28 | 28.3 ± 0.6 | 1 (h10) | 2.06 / 1.55 / 1.46 |
| Router (cube_v2 → WrenAI semantic, no reasoning) | 29 / 28 / 29 | 28.7 ± 0.6 | 1 (h10) | 2.08 / 2.09 / 2.18 |
| mnemiq a453b05 (defaults) | 7 / 7 / 6 | 6.7 ± 0.6 | 6 (e06, e07, e08, m03, m04, m05) | 3.43 / 3.13 / 3.29 |
| mnemiq a453b05, judge fail-open variant | 29 / 29 / 29 | 29.0 ± 0.0 | 0 (-) | 4.59 / 4.37 / 4.19 |
| mnemiq a453b05, judge 1200-token variant (fail-closed) | 28 / 29 / 29 | 28.7 ± 0.6 | 1 (h05) | 4.53 / 5.03 / 5.06 |
| mnemiq a453b05, TypeSafe Jev judge (fail-closed) | 25 / 26 / 27 | 26.0 ± 1.0 | 2 (m01, m06) | 3.41 / 3.74 / 3.19 |
| mnemiq a453b05, Jev judge v2 (truncation-aware) | 29 / 28 / 28 | 28.3 ± 0.6 | 2 (h04, h11) | 9.27 / 10.37 / 5.26 |
| mnemiq a453b05, Jev judge v2, rerun r2 | 28 / 29 / 29 | 28.7 ± 0.6 | 1 (h11) | 4.78 / 3.29 / 2.85 |

## WrenAI: out of the box (wrenai) vs + semantic layer (wrenai_mdl) (per question, EX exact over 3 runs)

| id | diff | question | wrenai | wrenai_mdl | wrenai statuses | wrenai_mdl statuses | change |
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


## Cube: baseline (cube) vs rich model + adapter v2 (cube_v2) (per question, EX exact over 3 runs)

| id | diff | question | cube | cube_v2 | cube statuses | cube_v2 statuses | change |
|---|---|---|---|---|---|---|---|
| e01 | easy | How many tracks are there in total? | 3/3 | 3/3 | ✅ ✅ ✅ | ✅ ✅ ✅ |  |
| e02 | easy | List the names of all music genres. | 3/3 | 3/3 | ✅ ✅ ✅ | ✅ ✅ ✅ |  |
| e03 | easy | How many customers are from Brazil? | 3/3 | 3/3 | ✅ ✅ ✅ | ✅ ✅ ✅ |  |
| e04 | easy | Which tracks are longer than 20 minutes? Return the track names. | 1/3 | 3/3 | ✅ ❌ ❌ | ✅ ✅ ✅ | better |
| e05 | easy | What is the highest unit price of any track? | 3/3 | 3/3 | ✅ ✅ ✅ | ✅ ✅ ✅ |  |
| e06 | easy | List the first and last names of employees whose title is 'Sales Suppo | 3/3 | 3/3 | ✅ ✅ ✅ | ✅ ✅ ✅ |  |
| e07 | easy | How many invoices were issued in the year 2023? | 0/3 | 3/3 | 🟡 🟡 🟡 | ✅ ✅ ✅ | **fixed** |
| e08 | easy | Which customers have a company listed? Return their first name, last n | 3/3 | 3/3 | ✅ ✅ ✅ | ✅ ✅ ✅ |  |
| m01 | medium | How many tracks are there in each genre? Return the genre name and the | 3/3 | 3/3 | ✅ ✅ ✅ | ✅ ✅ ✅ |  |
| m02 | medium | Which 5 artists have the most albums? Return the artist name and album | 3/3 | 3/3 | ✅ ✅ ✅ | ✅ ✅ ✅ |  |
| m03 | medium | What are the total sales (sum of invoice totals) for each billing coun | 3/3 | 3/3 | ✅ ✅ ✅ | ✅ ✅ ✅ |  |
| m04 | medium | Which customers are supported by the employee Jane Peacock? Return the | 3/3 | 3/3 | ✅ ✅ ✅ | ✅ ✅ ✅ |  |
| m05 | medium | What is the average track length in minutes for each media type? Retur | 3/3 | 3/3 | ✅ ✅ ✅ | ✅ ✅ ✅ |  |
| m06 | medium | Which albums have more than 20 tracks? Return the album title and the  | 3/3 | 3/3 | ✅ ✅ ✅ | ✅ ✅ ✅ |  |
| m07 | medium | Which genre has the most tracks? Return the genre name. | 0/3 | 3/3 | 🟡 🟡 🟡 | ✅ ✅ ✅ | **fixed** |
| m08 | medium | How many tracks are in the playlist named '90’s Music'? | 3/3 | 3/3 | ✅ ✅ ✅ | ✅ ✅ ✅ |  |
| m09 | medium | What is the total invoice revenue for each year? Return the year and r | 2/3 | 3/3 | ✅ ✅ ❌ | ✅ ✅ ✅ | better |
| h01 | hard | What are the top 3 genres by sales revenue, where revenue is unit pric | 3/3 | 3/3 | ✅ ✅ ✅ | ✅ ✅ ✅ |  |
| h02 | hard | For each sales support agent, what is the total invoice amount from th | 3/3 | 3/3 | ✅ ✅ ✅ | ✅ ✅ ✅ |  |
| h03 | hard | Which customers have spent more in total than the average total spend  | 0/3 | 3/3 | ⛔ ⛔ ⛔ | ✅ ✅ ✅ | **fixed** |
| h04 | hard | For each country, which customer has the highest total spend? Include  | 0/3 | 3/3 | ⛔ ⛔ ⛔ | ✅ ✅ ✅ | **fixed** |
| h05 | hard | For each month of 2024, show the total invoice revenue and the previou | 0/3 | 3/3 | ⛔ ⛔ ⛔ | ✅ ✅ ✅ | **fixed** |
| h06 | hard | Which artists have tracks in more than 3 different genres? Return the  | 3/3 | 3/3 | ✅ ✅ ✅ | ✅ ✅ ✅ |  |
| h07 | hard | How many tracks have never been purchased (never appear on any invoice | 0/3 | 3/3 | ❌ ❌ ❌ | ✅ ✅ ✅ | **fixed** |
| h08 | hard | List every employee together with the name of the manager they report  | 2/3 | 3/3 | ❌ ✅ ✅ | ✅ ✅ ✅ | better |
| h09 | hard | How many customers made at least one purchase in 2025 but made no purc | 0/3 | 3/3 | ⛔ ⛔ ⛔ | ✅ ✅ ✅ | **fixed** |
| h10 | hard | For each month of 2023, show the year-to-date running total of invoice | 2/3 | 1/3 | ✅ 🟡 ✅ | ❌ ✅ ❌ | worse |
| h11 | hard | What percentage of total sales revenue (unit price times quantity) com | 0/3 | 3/3 | ⛔ ⛔ ⛔ | ✅ ✅ ✅ | **fixed** |
| h12 | hard | Which 5 artists generated the most sales revenue (unit price times qua | 3/3 | 3/3 | ✅ ✅ ✅ | ✅ ✅ ✅ |  |

- fixed (0/3 → 3/3): e07, m07, h03, h04, h05, h07, h09, h11; broke (3/3 → 0/3): none
- partially better: e04, m09, h08; partially worse: h10


## WrenAI + semantic layer: with reasoning (wrenai_mdl) vs no reasoning (wrenai_mdl_noreason) (per question, EX exact over 3 runs)

| id | diff | question | wrenai_mdl | wrenai_mdl_noreason | wrenai_mdl statuses | wrenai_mdl_noreason statuses | change |
|---|---|---|---|---|---|---|---|
| e01 | easy | How many tracks are there in total? | 3/3 | 3/3 | ✅ ✅ ✅ | ✅ ✅ ✅ |  |
| e02 | easy | List the names of all music genres. | 3/3 | 3/3 | ✅ ✅ ✅ | ✅ ✅ ✅ |  |
| e03 | easy | How many customers are from Brazil? | 3/3 | 3/3 | ✅ ✅ ✅ | ✅ ✅ ✅ |  |
| e04 | easy | Which tracks are longer than 20 minutes? Return the track names. | 2/3 | 2/3 | 🟡 ✅ ✅ | 🟡 ✅ ✅ |  |
| e05 | easy | What is the highest unit price of any track? | 3/3 | 3/3 | ✅ ✅ ✅ | ✅ ✅ ✅ |  |
| e06 | easy | List the first and last names of employees whose title is 'Sales Suppo | 3/3 | 3/3 | ✅ ✅ ✅ | ✅ ✅ ✅ |  |
| e07 | easy | How many invoices were issued in the year 2023? | 3/3 | 3/3 | ✅ ✅ ✅ | ✅ ✅ ✅ |  |
| e08 | easy | Which customers have a company listed? Return their first name, last n | 3/3 | 3/3 | ✅ ✅ ✅ | ✅ ✅ ✅ |  |
| m01 | medium | How many tracks are there in each genre? Return the genre name and the | 3/3 | 3/3 | ✅ ✅ ✅ | ✅ ✅ ✅ |  |
| m02 | medium | Which 5 artists have the most albums? Return the artist name and album | 3/3 | 3/3 | ✅ ✅ ✅ | ✅ ✅ ✅ |  |
| m03 | medium | What are the total sales (sum of invoice totals) for each billing coun | 3/3 | 3/3 | ✅ ✅ ✅ | ✅ ✅ ✅ |  |
| m04 | medium | Which customers are supported by the employee Jane Peacock? Return the | 3/3 | 3/3 | ✅ ✅ ✅ | ✅ ✅ ✅ |  |
| m05 | medium | What is the average track length in minutes for each media type? Retur | 3/3 | 3/3 | ✅ ✅ ✅ | ✅ ✅ ✅ |  |
| m06 | medium | Which albums have more than 20 tracks? Return the album title and the  | 3/3 | 3/3 | ✅ ✅ ✅ | ✅ ✅ ✅ |  |
| m07 | medium | Which genre has the most tracks? Return the genre name. | 3/3 | 3/3 | ✅ ✅ ✅ | ✅ ✅ ✅ |  |
| m08 | medium | How many tracks are in the playlist named '90’s Music'? | 1/3 | 3/3 | 🟡 ✅ 🟡 | ✅ ✅ ✅ | better |
| m09 | medium | What is the total invoice revenue for each year? Return the year and r | 3/3 | 3/3 | ✅ ✅ ✅ | ✅ ✅ ✅ |  |
| h01 | hard | What are the top 3 genres by sales revenue, where revenue is unit pric | 3/3 | 3/3 | ✅ ✅ ✅ | ✅ ✅ ✅ |  |
| h02 | hard | For each sales support agent, what is the total invoice amount from th | 1/3 | 3/3 | ❌ ❌ ✅ | ✅ ✅ ✅ | better |
| h03 | hard | Which customers have spent more in total than the average total spend  | 3/3 | 3/3 | ✅ ✅ ✅ | ✅ ✅ ✅ |  |
| h04 | hard | For each country, which customer has the highest total spend? Include  | 3/3 | 3/3 | ✅ ✅ ✅ | ✅ ✅ ✅ |  |
| h05 | hard | For each month of 2024, show the total invoice revenue and the previou | 3/3 | 3/3 | ✅ ✅ ✅ | ✅ ✅ ✅ |  |
| h06 | hard | Which artists have tracks in more than 3 different genres? Return the  | 3/3 | 3/3 | ✅ ✅ ✅ | ✅ ✅ ✅ |  |
| h07 | hard | How many tracks have never been purchased (never appear on any invoice | 3/3 | 3/3 | ✅ ✅ ✅ | ✅ ✅ ✅ |  |
| h08 | hard | List every employee together with the name of the manager they report  | 3/3 | 3/3 | ✅ ✅ ✅ | ✅ ✅ ✅ |  |
| h09 | hard | How many customers made at least one purchase in 2025 but made no purc | 2/3 | 3/3 | 💥 ✅ ✅ | ✅ ✅ ✅ | better |
| h10 | hard | For each month of 2023, show the year-to-date running total of invoice | 3/3 | 3/3 | ✅ ✅ ✅ | ✅ ✅ ✅ |  |
| h11 | hard | What percentage of total sales revenue (unit price times quantity) com | 3/3 | 3/3 | ✅ ✅ ✅ | ✅ ✅ ✅ |  |
| h12 | hard | Which 5 artists generated the most sales revenue (unit price times qua | 3/3 | 3/3 | ✅ ✅ ✅ | ✅ ✅ ✅ |  |

- fixed (0/3 → 3/3): none; broke (3/3 → 0/3): none
- partially better: m08, h02, h09; partially worse: none


## Cube v2 vs Router (cube_v2 → WrenAI semantic, no reasoning) (per question, EX exact over 3 runs)

| id | diff | question | cube_v2 | router | cube_v2 statuses | router statuses | change |
|---|---|---|---|---|---|---|---|
| e01 | easy | How many tracks are there in total? | 3/3 | 3/3 | ✅ ✅ ✅ | ✅ ✅ ✅ |  |
| e02 | easy | List the names of all music genres. | 3/3 | 3/3 | ✅ ✅ ✅ | ✅ ✅ ✅ |  |
| e03 | easy | How many customers are from Brazil? | 3/3 | 3/3 | ✅ ✅ ✅ | ✅ ✅ ✅ |  |
| e04 | easy | Which tracks are longer than 20 minutes? Return the track names. | 3/3 | 3/3 | ✅ ✅ ✅ | ✅ ✅ ✅ |  |
| e05 | easy | What is the highest unit price of any track? | 3/3 | 3/3 | ✅ ✅ ✅ | ✅ ✅ ✅ |  |
| e06 | easy | List the first and last names of employees whose title is 'Sales Suppo | 3/3 | 3/3 | ✅ ✅ ✅ | ✅ ✅ ✅ |  |
| e07 | easy | How many invoices were issued in the year 2023? | 3/3 | 3/3 | ✅ ✅ ✅ | ✅ ✅ ✅ |  |
| e08 | easy | Which customers have a company listed? Return their first name, last n | 3/3 | 3/3 | ✅ ✅ ✅ | ✅ ✅ ✅ |  |
| m01 | medium | How many tracks are there in each genre? Return the genre name and the | 3/3 | 3/3 | ✅ ✅ ✅ | ✅ ✅ ✅ |  |
| m02 | medium | Which 5 artists have the most albums? Return the artist name and album | 3/3 | 3/3 | ✅ ✅ ✅ | ✅ ✅ ✅ |  |
| m03 | medium | What are the total sales (sum of invoice totals) for each billing coun | 3/3 | 3/3 | ✅ ✅ ✅ | ✅ ✅ ✅ |  |
| m04 | medium | Which customers are supported by the employee Jane Peacock? Return the | 3/3 | 3/3 | ✅ ✅ ✅ | ✅ ✅ ✅ |  |
| m05 | medium | What is the average track length in minutes for each media type? Retur | 3/3 | 3/3 | ✅ ✅ ✅ | ✅ ✅ ✅ |  |
| m06 | medium | Which albums have more than 20 tracks? Return the album title and the  | 3/3 | 3/3 | ✅ ✅ ✅ | ✅ ✅ ✅ |  |
| m07 | medium | Which genre has the most tracks? Return the genre name. | 3/3 | 3/3 | ✅ ✅ ✅ | ✅ ✅ ✅ |  |
| m08 | medium | How many tracks are in the playlist named '90’s Music'? | 3/3 | 3/3 | ✅ ✅ ✅ | ✅ ✅ ✅ |  |
| m09 | medium | What is the total invoice revenue for each year? Return the year and r | 3/3 | 3/3 | ✅ ✅ ✅ | ✅ ✅ ✅ |  |
| h01 | hard | What are the top 3 genres by sales revenue, where revenue is unit pric | 3/3 | 3/3 | ✅ ✅ ✅ | ✅ ✅ ✅ |  |
| h02 | hard | For each sales support agent, what is the total invoice amount from th | 3/3 | 3/3 | ✅ ✅ ✅ | ✅ ✅ ✅ |  |
| h03 | hard | Which customers have spent more in total than the average total spend  | 3/3 | 3/3 | ✅ ✅ ✅ | ✅ ✅ ✅ |  |
| h04 | hard | For each country, which customer has the highest total spend? Include  | 3/3 | 3/3 | ✅ ✅ ✅ | ✅ ✅ ✅ |  |
| h05 | hard | For each month of 2024, show the total invoice revenue and the previou | 3/3 | 3/3 | ✅ ✅ ✅ | ✅ ✅ ✅ |  |
| h06 | hard | Which artists have tracks in more than 3 different genres? Return the  | 3/3 | 3/3 | ✅ ✅ ✅ | ✅ ✅ ✅ |  |
| h07 | hard | How many tracks have never been purchased (never appear on any invoice | 3/3 | 3/3 | ✅ ✅ ✅ | ✅ ✅ ✅ |  |
| h08 | hard | List every employee together with the name of the manager they report  | 3/3 | 3/3 | ✅ ✅ ✅ | ✅ ✅ ✅ |  |
| h09 | hard | How many customers made at least one purchase in 2025 but made no purc | 3/3 | 3/3 | ✅ ✅ ✅ | ✅ ✅ ✅ |  |
| h10 | hard | For each month of 2023, show the year-to-date running total of invoice | 1/3 | 2/3 | ❌ ✅ ❌ | ✅ ❌ ✅ | better |
| h11 | hard | What percentage of total sales revenue (unit price times quantity) com | 3/3 | 3/3 | ✅ ✅ ✅ | ✅ ✅ ✅ |  |
| h12 | hard | Which 5 artists generated the most sales revenue (unit price times qua | 3/3 | 3/3 | ✅ ✅ ✅ | ✅ ✅ ✅ |  |

- fixed (0/3 → 3/3): none; broke (3/3 → 0/3): none
- partially better: h10; partially worse: none


## Router fallback / silent-wrong

- Fallback rate: 0/87 (0%)
- Triggers: none (Cube answered every attempt)
- Silent-wrong (Cube path, no fallback, not EX exact): 1: h10@r2
- Fallback attempts latency p50/p95: n/a

## WrenAI 0.29.2 + semantic layer: every non-exact attempt

| run | id | status | reason / error |
|---|---|---|---|
| 1 | e04 | correct_extra_cols | match with 1 extra column(s) |
| 1 | m08 | correct_extra_cols | match with 2 extra column(s) |
| 1 | h02 | wrong_result | row count 8 != gold 3 |
| 1 | h09 | exec_error | UndefinedTable: missing FROM-clause entry for table "customers_2025" LINE 1: ...:00:00' AS TIMESTAMPTZ)) AS customers_2024) WHERE customers_...                  |
| 2 | h02 | wrong_result | row count 8 != gold 3 |
| 3 | m08 | correct_extra_cols | match with 1 extra column(s) |

## WrenAI 0.29.2 + semantic layer, no reasoning: every non-exact attempt

| run | id | status | reason / error |
|---|---|---|---|
| 1 | e04 | correct_extra_cols | match with 1 extra column(s) |

## Cube Core 1.8.8 + rich model + LLM adapter v2 (harness-built): every non-exact attempt

| run | id | status | reason / error |
|---|---|---|---|
| 1 | h10 | wrong_result | no predicted column matches gold column 0 |
| 3 | h10 | wrong_result | no predicted column matches gold column 0 |

## Router (cube_v2 → WrenAI semantic, no reasoning): every non-exact attempt

| run | id | status | reason / error |
|---|---|---|---|
| 2 | h10 | wrong_result | no predicted column matches gold column 0 |

## mnemiq a453b05 (defaults): every non-exact attempt

| run | id | status | reason / error |
|---|---|---|---|
| 1 | e04 | tool_error | mnemiq failed: verifier_unavailable: I could not check this answer: the verifier answered with a reply I could not read. I am not giving you a result I cannot s |
| 1 | e05 | tool_error | mnemiq failed: verifier_unavailable: I could not check this answer: the verifier answered with a reply I could not read. I am not giving you a result I cannot s |
| 1 | e08 | tool_error | mnemiq failed: verifier_unavailable: I could not check this answer: the verifier answered with a reply I could not read. I am not giving you a result I cannot s |
| 1 | m01 | tool_error | mnemiq failed: verifier_unavailable: I could not check this answer: the verifier answered with a reply I could not read. I am not giving you a result I cannot s |
| 1 | m02 | tool_error | mnemiq failed: verifier_unavailable: I could not check this answer: the verifier answered with a reply I could not read. I am not giving you a result I cannot s |
| 1 | m05 | tool_error | mnemiq failed: verifier_unavailable: I could not check this answer: the verifier answered with a reply I could not read. I am not giving you a result I cannot s |
| 1 | m06 | tool_error | mnemiq failed: verifier_unavailable: I could not check this answer: the verifier answered with a reply I could not read. I am not giving you a result I cannot s |
| 1 | m07 | tool_error | mnemiq failed: verifier_unavailable: I could not check this answer: the verifier answered with a reply I could not read. I am not giving you a result I cannot s |
| 1 | m08 | tool_error | mnemiq failed: verifier_unavailable: I could not check this answer: the verifier answered with a reply I could not read. I am not giving you a result I cannot s |
| 1 | m09 | tool_error | mnemiq failed: verifier_unavailable: I could not check this answer: the verifier answered with a reply I could not read. I am not giving you a result I cannot s |
| 1 | h01 | tool_error | mnemiq failed: verifier_unavailable: I could not check this answer: the verifier answered with a reply I could not read. I am not giving you a result I cannot s |
| 1 | h02 | tool_error | mnemiq failed: verifier_unavailable: I could not check this answer: the verifier answered with a reply I could not read. I am not giving you a result I cannot s |
| 1 | h03 | tool_error | mnemiq failed: verifier_unavailable: I could not check this answer: the verifier answered with a reply I could not read. I am not giving you a result I cannot s |
| 1 | h04 | tool_error | mnemiq failed: verifier_unavailable: I could not check this answer: the verifier answered with a reply I could not read. I am not giving you a result I cannot s |
| 1 | h05 | tool_error | mnemiq failed: verifier_unavailable: I could not check this answer: the verifier answered with a reply I could not read. I am not giving you a result I cannot s |
| 1 | h06 | tool_error | mnemiq failed: verifier_unavailable: I could not check this answer: the verifier answered with a reply I could not read. I am not giving you a result I cannot s |
| 1 | h07 | tool_error | mnemiq failed: verifier_unavailable: I could not check this answer: the verifier answered with a reply I could not read. I am not giving you a result I cannot s |
| 1 | h08 | tool_error | mnemiq failed: verifier_unavailable: I could not check this answer: the verifier answered with a reply I could not read. I am not giving you a result I cannot s |
| 1 | h09 | tool_error | mnemiq failed: verifier_unavailable: I could not check this answer: the verifier answered with a reply I could not read. I am not giving you a result I cannot s |
| 1 | h10 | tool_error | mnemiq failed: verifier_unavailable: I could not check this answer: the verifier answered with a reply I could not read. I am not giving you a result I cannot s |
| 1 | h11 | tool_error | mnemiq failed: verifier_unavailable: I could not check this answer: the verifier answered with a reply I could not read. I am not giving you a result I cannot s |
| 1 | h12 | tool_error | mnemiq failed: verifier_unavailable: I could not check this answer: the verifier answered with a reply I could not read. I am not giving you a result I cannot s |
| 2 | e04 | tool_error | mnemiq failed: verifier_unavailable: I could not check this answer: the verifier answered with a reply I could not read. I am not giving you a result I cannot s |
| 2 | e05 | tool_error | mnemiq failed: verifier_unavailable: I could not check this answer: the verifier answered with a reply I could not read. I am not giving you a result I cannot s |
| 2 | m01 | tool_error | mnemiq failed: verifier_unavailable: I could not check this answer: the verifier answered with a reply I could not read. I am not giving you a result I cannot s |
| 2 | m02 | tool_error | mnemiq failed: verifier_unavailable: I could not check this answer: the verifier answered with a reply I could not read. I am not giving you a result I cannot s |
| 2 | m03 | tool_error | mnemiq failed: verifier_unavailable: I could not check this answer: the verifier answered with a reply I could not read. I am not giving you a result I cannot s |
| 2 | m04 | tool_error | mnemiq failed: verifier_unavailable: I could not check this answer: the verifier answered with a reply I could not read. I am not giving you a result I cannot s |
| 2 | m06 | tool_error | mnemiq failed: verifier_unavailable: I could not check this answer: the verifier answered with a reply I could not read. I am not giving you a result I cannot s |
| 2 | m07 | tool_error | mnemiq failed: verifier_unavailable: I could not check this answer: the verifier answered with a reply I could not read. I am not giving you a result I cannot s |
| 2 | m08 | tool_error | mnemiq failed: verifier_unavailable: I could not check this answer: the verifier answered with a reply I could not read. I am not giving you a result I cannot s |
| 2 | m09 | tool_error | mnemiq failed: verifier_unavailable: I could not check this answer: the verifier answered with a reply I could not read. I am not giving you a result I cannot s |
| 2 | h01 | tool_error | mnemiq failed: verifier_unavailable: I could not check this answer: the verifier answered with a reply I could not read. I am not giving you a result I cannot s |
| 2 | h02 | tool_error | mnemiq failed: verifier_unavailable: I could not check this answer: the verifier answered with a reply I could not read. I am not giving you a result I cannot s |
| 2 | h03 | tool_error | mnemiq failed: verifier_unavailable: I could not check this answer: the verifier answered with a reply I could not read. I am not giving you a result I cannot s |
| 2 | h04 | tool_error | mnemiq failed: verifier_unavailable: I could not check this answer: the verifier answered with a reply I could not read. I am not giving you a result I cannot s |
| 2 | h05 | tool_error | mnemiq failed: verifier_unavailable: I could not check this answer: the verifier answered with a reply I could not read. I am not giving you a result I cannot s |
| 2 | h06 | tool_error | mnemiq failed: verifier_unavailable: I could not check this answer: the verifier answered with a reply I could not read. I am not giving you a result I cannot s |
| 2 | h07 | tool_error | mnemiq failed: verifier_unavailable: I could not check this answer: the verifier answered with a reply I could not read. I am not giving you a result I cannot s |
| 2 | h08 | tool_error | mnemiq failed: verifier_unavailable: I could not check this answer: the verifier answered with a reply I could not read. I am not giving you a result I cannot s |
| 2 | h09 | tool_error | mnemiq failed: verifier_unavailable: I could not check this answer: the verifier answered with a reply I could not read. I am not giving you a result I cannot s |
| 2 | h10 | tool_error | mnemiq failed: verifier_unavailable: I could not check this answer: the verifier answered with a reply I could not read. I am not giving you a result I cannot s |
| 2 | h11 | tool_error | mnemiq failed: verifier_unavailable: I could not check this answer: the verifier answered with a reply I could not read. I am not giving you a result I cannot s |
| 2 | h12 | tool_error | mnemiq failed: verifier_unavailable: I could not check this answer: the verifier answered with a reply I could not read. I am not giving you a result I cannot s |
| 3 | e04 | tool_error | mnemiq failed: verifier_unavailable: I could not check this answer: the verifier answered with a reply I could not read. I am not giving you a result I cannot s |
| 3 | e05 | tool_error | mnemiq failed: verifier_unavailable: I could not check this answer: the verifier answered with a reply I could not read. I am not giving you a result I cannot s |
| 3 | e06 | declined | declined: verification: The result may not correctly answer the question. |
| 3 | e07 | declined | declined: verification: The result may not correctly answer the question. |
| 3 | e08 | tool_error | mnemiq failed: verifier_unavailable: I could not check this answer: the verifier answered with a reply I could not read. I am not giving you a result I cannot s |
| 3 | m01 | tool_error | mnemiq failed: verifier_unavailable: I could not check this answer: the verifier answered with a reply I could not read. I am not giving you a result I cannot s |
| 3 | m02 | tool_error | mnemiq failed: verifier_unavailable: I could not check this answer: the verifier answered with a reply I could not read. I am not giving you a result I cannot s |
| 3 | m06 | tool_error | mnemiq failed: verifier_unavailable: I could not check this answer: the verifier answered with a reply I could not read. I am not giving you a result I cannot s |
| 3 | m07 | tool_error | mnemiq failed: verifier_unavailable: I could not check this answer: the verifier answered with a reply I could not read. I am not giving you a result I cannot s |
| 3 | m08 | tool_error | mnemiq failed: verifier_unavailable: I could not check this answer: the verifier answered with a reply I could not read. I am not giving you a result I cannot s |
| 3 | m09 | tool_error | mnemiq failed: verifier_unavailable: I could not check this answer: the verifier answered with a reply I could not read. I am not giving you a result I cannot s |
| 3 | h01 | tool_error | mnemiq failed: verifier_unavailable: I could not check this answer: the verifier answered with a reply I could not read. I am not giving you a result I cannot s |
| 3 | h02 | tool_error | mnemiq failed: verifier_unavailable: I could not check this answer: the verifier answered with a reply I could not read. I am not giving you a result I cannot s |
| 3 | h03 | tool_error | mnemiq failed: verifier_unavailable: I could not check this answer: the verifier answered with a reply I could not read. I am not giving you a result I cannot s |
| 3 | h04 | tool_error | mnemiq failed: verifier_unavailable: I could not check this answer: the verifier answered with a reply I could not read. I am not giving you a result I cannot s |
| 3 | h05 | tool_error | mnemiq failed: verifier_unavailable: I could not check this answer: the verifier answered with a reply I could not read. I am not giving you a result I cannot s |
| 3 | h06 | tool_error | mnemiq failed: verifier_unavailable: I could not check this answer: the verifier answered with a reply I could not read. I am not giving you a result I cannot s |
| 3 | h07 | tool_error | mnemiq failed: verifier_unavailable: I could not check this answer: the verifier answered with a reply I could not read. I am not giving you a result I cannot s |
| 3 | h08 | tool_error | mnemiq failed: verifier_unavailable: I could not check this answer: the verifier answered with a reply I could not read. I am not giving you a result I cannot s |
| 3 | h09 | tool_error | mnemiq failed: verifier_unavailable: I could not check this answer: the verifier answered with a reply I could not read. I am not giving you a result I cannot s |
| 3 | h10 | tool_error | mnemiq failed: verifier_unavailable: I could not check this answer: the verifier answered with a reply I could not read. I am not giving you a result I cannot s |
| 3 | h11 | tool_error | mnemiq failed: verifier_unavailable: I could not check this answer: the verifier answered with a reply I could not read. I am not giving you a result I cannot s |
| 3 | h12 | tool_error | mnemiq failed: verifier_unavailable: I could not check this answer: the verifier answered with a reply I could not read. I am not giving you a result I cannot s |

## mnemiq a453b05, judge fail-open variant: every non-exact attempt

| run | id | status | reason / error |
|---|---|---|---|

## mnemiq a453b05, judge 1200-token variant (fail-closed): every non-exact attempt

| run | id | status | reason / error |
|---|---|---|---|
| 1 | h05 | declined | declined: verification: The result may not correctly answer the question. |

## mnemiq a453b05, TypeSafe Jev judge (fail-closed): every non-exact attempt

| run | id | status | reason / error |
|---|---|---|---|
| 1 | e02 | declined | declined: verification: The result may not correctly answer the question. |
| 1 | e08 | declined | declined: verification: The result may not correctly answer the question. |
| 1 | m01 | declined | declined: verification: The result may not correctly answer the question. |
| 1 | m06 | declined | declined: verification: The result may not correctly answer the question. |
| 2 | e02 | declined | declined: verification: The result may not correctly answer the question. |
| 2 | e08 | declined | declined: verification: The result may not correctly answer the question. |
| 2 | m01 | declined | declined: verification: The result may not correctly answer the question. |
| 3 | e02 | declined | declined: verification: The result may not correctly answer the question. |
| 3 | e08 | declined | declined: verification: The result may not correctly answer the question. |

## mnemiq a453b05, Jev judge v2 (truncation-aware): every non-exact attempt

| run | id | status | reason / error |
|---|---|---|---|
| 2 | h04 | timeout | timeout: no response within 180s |
| 3 | h11 | timeout | timeout: no response within 180s |

## mnemiq a453b05, Jev judge v2, rerun r2: every non-exact attempt

| run | id | status | reason / error |
|---|---|---|---|
| 1 | h11 | declined | declined: invalid_query: Could not produce a valid query after 3 attempts. The source rejected this query. |

## WrenAI per-stage latency (wrenai_mdl vs wrenai_mdl_noreason)

Generated by `bench/stage_latency.py`; per-attempt data in `results/stage-latency/stages.csv`. Medians over the 87 attempts per system (seconds).
Stage boundaries are the 'pipeline is running' log lines (see script docstring). wren-ui (`/api/v1/generate_sql`) polls wren-ai-service every 1 s (`setTimeout(…,1000)` in `wren-ui/src/pages/api/v1/generate_sql.ts`); the harness itself makes one blocking call, it does not poll.

| stage (median s) | wrenai_mdl | wrenai_mdl_noreason |
|---|---|---|
| pre-retrieval (historical Q / SQL pairs / instructions) | 0.06 | 0.06 |
| intent classification | 1.55 | 1.41 |
| schema retrieval (Ask Retrieval) | 0.07 | 0.07 |
| SQL generation reasoning | 2.16 | 0.00 |
| SQL generation incl. validation, up to wren-ui's last poll | 2.53 | 2.49 |
| = wren-ai-service span (POST /v1/asks → last poll) | 6.03 | 4.02 |
| wren-ui overhead (e2e − span: ask call, dialect conversion via ibis, response) | 0.03 | 0.03 |
| **end-to-end (harness latency)** | 6.08 | 4.05 |
| polls per question (GET …/result) | 7.00 | 5.00 |
| …of which wren-ui before POST /v1/asks | – | 0.01 |
| …of which wren-ui after last poll | – | 0.02 |
| SQL generation: until end of last LLM call (meter) | – | 1.96 |
| last poll − end of last LLM call (validation + poll wait) | – | 0.52 |
| …as % of end-to-end | – | 12.87 |
| LLM calls per question (meter, in ask window) | – | 2.00 |
| time between the last two polls (s) | 1.00 | 1.00 |

| check | wrenai_mdl | wrenai_mdl_noreason |
|---|---|---|
| attempts where 'SQL Generation Reasoning pipeline' ran | 87/87 | 0/87 |
| attempts where 'Intent Classification pipeline' ran | 87/87 | 87/87 |
| SQL correction pipeline runs | 0 | 1 |
| mean stage sum (s): pre+intent+schema+reasoning+generation | 6.84 | 4.25 |
| mean e2e (s) | 6.87 | 4.29 |

Polling: the time between the ask actually finishing and wren-ui's next poll is ≤ 1 s per question. Where meter timing exists, `last poll − end of last LLM call` measures it (upper bound, includes the post-LLM dry-run validation).


## Per question, all systems (status per run)

| id | diff | WrenAI 0.29.2 (out of the box) | WrenAI 0.29.2 + semantic layer | WrenAI 0.29.2 + semantic layer, no reasoning | DB-GPT 0.8.2 | Cube Core 1.8.8 + LLM adapter (baseline) | Cube Core 1.8.8 + rich model + LLM adapter v2 (harness-built) | Router (cube_v2 → WrenAI semantic, no reasoning) | mnemiq a453b05 (defaults) | mnemiq a453b05, judge fail-open variant | mnemiq a453b05, judge 1200-token variant (fail-closed) | mnemiq a453b05, TypeSafe Jev judge (fail-closed) | mnemiq a453b05, Jev judge v2 (truncation-aware) | mnemiq a453b05, Jev judge v2, rerun r2 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| e01 | easy | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ |
| e02 | easy | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | 🚫 🚫 🚫 | ✅ ✅ ✅ | ✅ ✅ ✅ |
| e03 | easy | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ |
| e04 | easy | ✅ ✅ ✅ | 🟡 ✅ ✅ | 🟡 ✅ ✅ | ❌ ❌ ❌ | ✅ ❌ ❌ | ✅ ✅ ✅ | ✅ ✅ ✅ | ⚠️ ⚠️ ⚠️ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ |
| e05 | easy | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ⚠️ ⚠️ ⚠️ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ |
| e06 | easy | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ 🚫 | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ |
| e07 | easy | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | 🟡 🟡 🟡 | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ 🚫 | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ |
| e08 | easy | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ⚠️ ✅ ⚠️ | ✅ ✅ ✅ | ✅ ✅ ✅ | 🚫 🚫 🚫 | ✅ ✅ ✅ | ✅ ✅ ✅ |
| m01 | medium | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ⚠️ ⚠️ ⚠️ | ✅ ✅ ✅ | ✅ ✅ ✅ | 🚫 🚫 ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ |
| m02 | medium | ❌ ❌ ❌ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ⚠️ ⚠️ ⚠️ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ |
| m03 | medium | ✅ 💥 ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ⚠️ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ |
| m04 | medium | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ⚠️ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ |
| m05 | medium | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ⚠️ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ |
| m06 | medium | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ⚠️ ⚠️ ⚠️ | ✅ ✅ ✅ | ✅ ✅ ✅ | 🚫 ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ |
| m07 | medium | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | 🟡 🟡 🟡 | ✅ ✅ ✅ | ✅ ✅ ✅ | ⚠️ ⚠️ ⚠️ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ |
| m08 | medium | ✅ ✅ ✅ | 🟡 ✅ 🟡 | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ⚠️ ⚠️ ⚠️ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ |
| m09 | medium | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ❌ | ✅ ✅ ✅ | ✅ ✅ ✅ | ⚠️ ⚠️ ⚠️ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ |
| h01 | hard | ✅ 🟡 ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ⚠️ ⚠️ ⚠️ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ |
| h02 | hard | ✅ ✅ ✅ | ❌ ❌ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ⚠️ ⚠️ ⚠️ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ |
| h03 | hard | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ⛔ ⛔ ⛔ | ✅ ✅ ✅ | ✅ ✅ ✅ | ⚠️ ⚠️ ⚠️ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ |
| h04 | hard | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ⛔ ⛔ ⛔ | ✅ ✅ ✅ | ✅ ✅ ✅ | ⚠️ ⚠️ ⚠️ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ⏱️ ✅ | ✅ ✅ ✅ |
| h05 | hard | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ⛔ ⛔ ⛔ | ✅ ✅ ✅ | ✅ ✅ ✅ | ⚠️ ⚠️ ⚠️ | ✅ ✅ ✅ | 🚫 ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ |
| h06 | hard | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ⚠️ ⚠️ ⚠️ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ |
| h07 | hard | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ❌ ❌ ❌ | ✅ ✅ ✅ | ✅ ✅ ✅ | ⚠️ ⚠️ ⚠️ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ |
| h08 | hard | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ❌ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ⚠️ ⚠️ ⚠️ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ |
| h09 | hard | ✅ ✅ ✅ | 💥 ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ⛔ ⛔ ⛔ | ✅ ✅ ✅ | ✅ ✅ ✅ | ⚠️ ⚠️ ⚠️ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ |
| h10 | hard | ❌ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ 🟡 ✅ | ❌ ✅ ❌ | ✅ ❌ ✅ | ⚠️ ⚠️ ⚠️ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ |
| h11 | hard | ✅ 💥 ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | 💥 💥 💥 | ⛔ ⛔ ⛔ | ✅ ✅ ✅ | ✅ ✅ ✅ | ⚠️ ⚠️ ⚠️ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ⏱️ | 🚫 ✅ ✅ |
| h12 | hard | ✅ 🟡 ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ⚠️ ⚠️ ⚠️ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ |

Legend: ✅ exact, 🟡 extra columns, ❌ wrong result, 💥 SQL exec error, ⚠️ tool/API error, ⏱️ timeout (failure), ⛔ declared unsupported, 🚫 declined (mnemiq deferral, counts as not correct).

## Held-out set (15 new questions)

Source: `bench/questions_holdout.yaml`. Models/prompts/MDL **unchanged** (not tuned to these questions). 15 q × 3 runs each for `router`, `cube_v2`, `wrenai_mdl_noreason`, `dbgpt`, `mnemiq`, `mnemiq_failopen`, `mnemiq_verified`, `mnemiq_jev`, `mnemiq_jev_v2`, `mnemiq_jev_v2_r2`.
Results: `results/run-gptoss120b-holdout-r3/`. Chart: `results/holdout_summary.png`.

| System | EX exact | EX relaxed | wrong | exec err | tool err | timeout | unsupported | declined | p50 s | p95 s | avg prompt tok | avg LLM calls |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Router (cube_v2 → Wren noreason) | 39/45 (87%) | 39/45 (87%) | 6 | 0 | 0 | 0 | 0 | 0 | 3.54 | 7.77 | 11,327 | 1.9 |
| cube_v2 | 25/45 (56%) | 25/45 (56%) | 7 | 1 | 0 | 1 | 11 | 0 | 1.92 | 5.26 | 3,436 | 1.2 |
| WrenAI + semantic, no reasoning | 42/45 (93%) | 42/45 (93%) | 3 | 0 | 0 | 0 | 0 | 0 | 4.06 | 6.89 | 20,811 | 2.0 |
| DB-GPT 0.8.2 | 39/45 (87%) | 39/45 (87%) | 6 | 0 | 0 | 0 | 0 | 0 | 2.61 | 4.32 | 1,693 | 1.0 |
| mnemiq a453b05 (defaults) | 5/45 (11%) | 5/45 (11%) | 0 | 0 | 40 | 0 | 0 | 0 | 3.33 | 5.40 | 4,830 | 2.2 |
| mnemiq a453b05, judge fail-open variant | 44/45 (98%) | 44/45 (98%) | 1 | 0 | 0 | 0 | 0 | 0 | 4.10 | 7.41 | 5,237 | 3.1 |
| mnemiq a453b05, judge 1200-token variant (fail-closed) | 39/45 (87%) | 39/45 (87%) | 2 | 0 | 0 | 0 | 0 | 4 | 5.13 | 9.79 | 5,250 | 3.0 |
| mnemiq a453b05, TypeSafe Jev judge (fail-closed) | 39/45 (87%) | 39/45 (87%) | 1 | 0 | 0 | 0 | 0 | 5 | 3.14 | 4.88 | 2,823 | 1.9 |
| mnemiq a453b05, Jev judge v2 (truncation-aware) | 39/45 (87%) | 39/45 (87%) | 0 | 0 | 0 | 0 | 0 | 6 | 4.24 | 9.16 | 2,929 | 1.9 |
| mnemiq a453b05, Jev judge v2, rerun r2 | 38/45 (84%) | 38/45 (84%) | 1 | 0 | 0 | 0 | 0 | 6 | 2.57 | 4.35 | 2,804 | 1.9 |

### Router fallback / silent-wrong (holdout)

- Fallback rate: **17/45 (38%)**
- Triggers: cube_error=1, cube_unsupported=16
- Cube-answered path: EX 22/28 (79%), p50/p95 2.40/5.86 s
- Fallback path: EX 17/17 (100%), p50/p95 5.28/10.53 s
- Silent-wrong (Cube answered, no fallback, not EX): 6 — ho12@r1, ho12@r2, ho14@r2, ho04@r3, ho12@r3, ho14@r3
- Fell back but Wren still wrong: 0 — none

### DB-GPT 0.8.2: non-exact attempts (holdout)

| run | id | status | reason / error |
|---|---|---|---|
| 1 | ho12 | wrong_result | row count 50 != gold 110 |
| 1 | ho14 | wrong_result | no predicted column matches gold column 0 |
| 2 | ho12 | wrong_result | row count 50 != gold 110 |
| 2 | ho14 | wrong_result | no predicted column matches gold column 0 |
| 3 | ho12 | wrong_result | row count 50 != gold 110 |
| 3 | ho14 | wrong_result | no predicted column matches gold column 0 |

### mnemiq a453b05 (defaults): non-exact attempts (holdout)

| run | id | status | reason / error |
|---|---|---|---|
| 1 | ho03 | tool_error | mnemiq failed: verifier_unavailable: I could not check this answer: the verifier answered with a reply I could not read. I am not giving you a result  |
| 1 | ho04 | tool_error | mnemiq failed: verifier_unavailable: I could not check this answer: the verifier answered with a reply I could not read. I am not giving you a result  |
| 1 | ho05 | tool_error | mnemiq failed: verifier_unavailable: I could not check this answer: the verifier answered with a reply I could not read. I am not giving you a result  |
| 1 | ho06 | tool_error | mnemiq failed: verifier_unavailable: I could not check this answer: the verifier answered with a reply I could not read. I am not giving you a result  |
| 1 | ho07 | tool_error | mnemiq failed: verifier_unavailable: I could not check this answer: the verifier answered with a reply I could not read. I am not giving you a result  |
| 1 | ho09 | tool_error | mnemiq failed: verifier_unavailable: I could not check this answer: the verifier answered with a reply I could not read. I am not giving you a result  |
| 1 | ho10 | tool_error | mnemiq failed: verifier_unavailable: I could not check this answer: the verifier answered with a reply I could not read. I am not giving you a result  |
| 1 | ho11 | tool_error | mnemiq failed: verifier_unavailable: I could not check this answer: the verifier answered with a reply I could not read. I am not giving you a result  |
| 1 | ho12 | tool_error | mnemiq failed: verifier_unavailable: I could not check this answer: the verifier answered with a reply I could not read. I am not giving you a result  |
| 1 | ho13 | tool_error | mnemiq failed: verifier_unavailable: I could not check this answer: the verifier answered with a reply I could not read. I am not giving you a result  |
| 1 | ho14 | tool_error | mnemiq failed: verifier_unavailable: I could not check this answer: the verifier answered with a reply I could not read. I am not giving you a result  |
| 1 | ho15 | tool_error | mnemiq failed: verifier_unavailable: I could not check this answer: the verifier answered with a reply I could not read. I am not giving you a result  |
| 2 | ho01 | tool_error | mnemiq failed: verifier_unavailable: I could not check this answer: the verifier answered with a reply I could not read. I am not giving you a result  |
| 2 | ho02 | tool_error | mnemiq failed: verifier_unavailable: I could not check this answer: the verifier answered with a reply I could not read. I am not giving you a result  |
| 2 | ho03 | tool_error | mnemiq failed: verifier_unavailable: I could not check this answer: the verifier answered with a reply I could not read. I am not giving you a result  |
| 2 | ho04 | tool_error | mnemiq failed: verifier_unavailable: I could not check this answer: the verifier answered with a reply I could not read. I am not giving you a result  |
| 2 | ho05 | tool_error | mnemiq failed: verifier_unavailable: I could not check this answer: the verifier answered with a reply I could not read. I am not giving you a result  |
| 2 | ho06 | tool_error | mnemiq failed: verifier_unavailable: I could not check this answer: the verifier answered with a reply I could not read. I am not giving you a result  |
| 2 | ho07 | tool_error | mnemiq failed: verifier_unavailable: I could not check this answer: the verifier answered with a reply I could not read. I am not giving you a result  |
| 2 | ho09 | tool_error | mnemiq failed: verifier_unavailable: I could not check this answer: the verifier answered with a reply I could not read. I am not giving you a result  |
| 2 | ho10 | tool_error | mnemiq failed: verifier_unavailable: I could not check this answer: the verifier answered with a reply I could not read. I am not giving you a result  |
| 2 | ho11 | tool_error | mnemiq failed: verifier_unavailable: I could not check this answer: the verifier answered with a reply I could not read. I am not giving you a result  |
| 2 | ho12 | tool_error | mnemiq failed: verifier_unavailable: I could not check this answer: the verifier answered with a reply I could not read. I am not giving you a result  |
| 2 | ho13 | tool_error | mnemiq failed: verifier_unavailable: I could not check this answer: the verifier answered with a reply I could not read. I am not giving you a result  |
| 2 | ho14 | tool_error | mnemiq failed: verifier_unavailable: I could not check this answer: the verifier answered with a reply I could not read. I am not giving you a result  |
| 2 | ho15 | tool_error | mnemiq failed: verifier_unavailable: I could not check this answer: the verifier answered with a reply I could not read. I am not giving you a result  |
| 3 | ho01 | tool_error | mnemiq failed: verifier_unavailable: I could not check this answer: the verifier answered with a reply I could not read. I am not giving you a result  |
| 3 | ho02 | tool_error | mnemiq failed: verifier_unavailable: I could not check this answer: the verifier answered with a reply I could not read. I am not giving you a result  |
| 3 | ho03 | tool_error | mnemiq failed: verifier_unavailable: I could not check this answer: the verifier answered with a reply I could not read. I am not giving you a result  |
| 3 | ho04 | tool_error | mnemiq failed: verifier_unavailable: I could not check this answer: the verifier answered with a reply I could not read. I am not giving you a result  |
| 3 | ho05 | tool_error | mnemiq failed: verifier_unavailable: I could not check this answer: the verifier answered with a reply I could not read. I am not giving you a result  |
| 3 | ho06 | tool_error | mnemiq failed: verifier_unavailable: I could not check this answer: the verifier answered with a reply I could not read. I am not giving you a result  |
| 3 | ho07 | tool_error | mnemiq failed: verifier_unavailable: I could not check this answer: the verifier answered with a reply I could not read. I am not giving you a result  |
| 3 | ho08 | tool_error | mnemiq failed: verifier_unavailable: I could not check this answer: the verifier answered with a reply I could not read. I am not giving you a result  |
| 3 | ho09 | tool_error | mnemiq failed: verifier_unavailable: I could not check this answer: the verifier answered with a reply I could not read. I am not giving you a result  |
| 3 | ho10 | tool_error | mnemiq failed: verifier_unavailable: I could not check this answer: the verifier answered with a reply I could not read. I am not giving you a result  |
| 3 | ho11 | tool_error | mnemiq failed: verifier_unavailable: I could not check this answer: the verifier answered with a reply I could not read. I am not giving you a result  |
| 3 | ho12 | tool_error | mnemiq failed: verifier_unavailable: I could not check this answer: the verifier answered with a reply I could not read. I am not giving you a result  |
| 3 | ho13 | tool_error | mnemiq failed: verifier_unavailable: I could not check this answer: the verifier answered with a reply I could not read. I am not giving you a result  |
| 3 | ho14 | tool_error | mnemiq failed: verifier_unavailable: I could not check this answer: the verifier answered with a reply I could not read. I am not giving you a result  |

### mnemiq a453b05, judge fail-open variant: non-exact attempts (holdout)

| run | id | status | reason / error |
|---|---|---|---|
| 1 | ho14 | wrong_result | no predicted column matches gold column 0 |

### mnemiq a453b05, judge 1200-token variant (fail-closed): non-exact attempts (holdout)

| run | id | status | reason / error |
|---|---|---|---|
| 1 | ho13 | declined | declined: verification: The result may not correctly answer the question. |
| 1 | ho14 | declined | declined: verification: The result may not correctly answer the question. |
| 2 | ho14 | wrong_result | no predicted column matches gold column 0 |
| 3 | ho10 | declined | declined: verification: The result may not correctly answer the question. |
| 3 | ho13 | declined | declined: verification: The result may not correctly answer the question. |
| 3 | ho14 | wrong_result | no predicted column matches gold column 0 |

### mnemiq a453b05, TypeSafe Jev judge (fail-closed): non-exact attempts (holdout)

| run | id | status | reason / error |
|---|---|---|---|
| 1 | ho10 | declined | declined: verification: The result may not correctly answer the question. |
| 1 | ho14 | declined | declined: verification: The result may not correctly answer the question. |
| 2 | ho10 | declined | declined: verification: The result may not correctly answer the question. |
| 2 | ho14 | wrong_result | no predicted column matches gold column 0 |
| 3 | ho10 | declined | declined: verification: The result may not correctly answer the question. |
| 3 | ho14 | declined | declined: verification: The result may not correctly answer the question. |

### mnemiq a453b05, Jev judge v2 (truncation-aware): non-exact attempts (holdout)

| run | id | status | reason / error |
|---|---|---|---|
| 1 | ho10 | declined | declined: verification: The result may not correctly answer the question. |
| 1 | ho14 | declined | declined: verification: The result may not correctly answer the question. |
| 2 | ho10 | declined | declined: verification: The result may not correctly answer the question. |
| 2 | ho14 | declined | declined: verification: The result may not correctly answer the question. |
| 3 | ho10 | declined | declined: verification: The result may not correctly answer the question. |
| 3 | ho12 | declined | declined: verification: The result may not correctly answer the question. |

### mnemiq a453b05, Jev judge v2, rerun r2: non-exact attempts (holdout)

| run | id | status | reason / error |
|---|---|---|---|
| 1 | ho10 | declined | declined: verification: The result may not correctly answer the question. |
| 1 | ho12 | declined | declined: verification: The result may not correctly answer the question. |
| 1 | ho14 | wrong_result | no predicted column matches gold column 0 |
| 2 | ho10 | declined | declined: verification: The result may not correctly answer the question. |
| 2 | ho14 | declined | declined: verification: The result may not correctly answer the question. |
| 3 | ho10 | declined | declined: verification: The result may not correctly answer the question. |
| 3 | ho14 | declined | declined: verification: The result may not correctly answer the question. |

### Per-question statuses (holdout)

| id | diff | question | Router (cube_v2 → Wren noreason) | cube_v2 | WrenAI + semantic, no reasoning | DB-GPT 0.8.2 | mnemiq a453b05 (defaults) | mnemiq a453b05, judge fail-open variant | mnemiq a453b05, judge 1200-token variant (fail-closed) | mnemiq a453b05, TypeSafe Jev judge (fail-closed) | mnemiq a453b05, Jev judge v2 (truncation-aware) | mnemiq a453b05, Jev judge v2, rerun r2 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ho01 | easy | How many distinct media types are there? | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ⚠️ ⚠️ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ |
| ho02 | easy | How many customers have a fax number recorded? | ✅ ✅ ✅ | ⛔ ⛔ ⛔ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ⚠️ ⚠️ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ |
| ho03 | easy | How many tracks are larger than 15 megabytes (bytes > 15 * 1 | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ⚠️ ⚠️ ⚠️ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ |
| ho04 | easy | How many invoices have a billing address that contains the w | ✅ ✅ ❌ | ❌ ❌ ❌ | ✅ ✅ ✅ | ✅ ✅ ✅ | ⚠️ ⚠️ ⚠️ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ |
| ho05 | medium | What is the average track file size in bytes for each media  | ✅ ✅ ✅ | ✅ ⛔ ⛔ | ✅ ✅ ✅ | ✅ ✅ ✅ | ⚠️ ⚠️ ⚠️ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ |
| ho06 | medium | How many playlists contain tracks from at least 10 different | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ⚠️ ⚠️ ⚠️ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ |
| ho07 | medium | List employees born in the 1970s. Return first name, last na | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ⚠️ ⚠️ ⚠️ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ |
| ho08 | medium | How many customers have a phone number that starts with '+55 | ✅ ✅ ✅ | ⛔ ⛔ ⛔ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ⚠️ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ |
| ho09 | medium | What percentage of total sales revenue (unit price times qua | ✅ ✅ ✅ | ✅ ❌ ❌ | ✅ ✅ ✅ | ✅ ✅ ✅ | ⚠️ ⚠️ ⚠️ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ |
| ho10 | hard | For each day of the week in 2024, how many invoices were iss | ✅ ✅ ✅ | ✅ ✅ ⏱️ | ✅ ✅ ✅ | ✅ ✅ ✅ | ⚠️ ⚠️ ⚠️ | ✅ ✅ ✅ | ✅ ✅ 🚫 | 🚫 🚫 🚫 | 🚫 🚫 🚫 | 🚫 🚫 🚫 |
| ho11 | hard | For each support representative, which customer has the high | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ⚠️ ⚠️ ⚠️ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ |
| ho12 | hard | Which artists have never had any track appear on an invoice  | ❌ ❌ ❌ | ❌ 💥 ❌ | ✅ ✅ ✅ | ❌ ❌ ❌ | ⚠️ ⚠️ ⚠️ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ 🚫 | 🚫 ✅ ✅ |
| ho13 | hard | For each quarter of 2024, show the total invoice revenue and | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ⚠️ ⚠️ ⚠️ | ✅ ✅ ✅ | 🚫 ✅ 🚫 | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ |
| ho14 | hard | Which ISO week numbers of 2023 had the highest invoice reven | ✅ ❌ ❌ | ✅ ✅ ✅ | ❌ ❌ ❌ | ❌ ❌ ❌ | ⚠️ ⚠️ ⚠️ | ❌ ✅ ✅ | 🚫 ❌ ❌ | 🚫 ❌ 🚫 | 🚫 🚫 ✅ | ❌ 🚫 🚫 |
| ho15 | hard | How many distinct billing postal codes appear on invoices bi | ✅ ✅ ✅ | ⛔ ⛔ ⛔ | ✅ ✅ ✅ | ✅ ✅ ✅ | ⚠️ ⚠️ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ | ✅ ✅ ✅ |

Legend: ✅ exact, 🟡 extra columns, ❌ wrong, 💥 exec error, ⚠️ tool/API error, ⏱️ timeout, ⛔ unsupported (Cube), 🚫 declined (mnemiq deferral).


## mnemiq_jev: Jev judge outcomes (29 + holdout)

Jev log lines: 132; matched to attempts: 132; unmatched: 0; HTTP statuses: {'200': 132}; attempts with more than one Jev call: 0; attempts with none: 0.

Jev calls bypass llm-meter, so they are counted from the log; `input_tokens` is the API's own `usage.input_tokens` (not estimated). Cost = input tokens x $0.042 per million (output tokens are free).

| set | attempts | Jev calls | Jev input tokens (total) | avg per call | est. Jev cost | Jev latency p50 / p95 ms | passed | declined (verification) | judge unavailable | other |
|---|---|---|---|---|---|---|---|---|---|---|
| 29 | 87 | 87 | 221,670 | 2,548 | $0.0093 | 170 / 232 | 78 | 9 | 0 | 0 |
| holdout | 45 | 45 | 114,523 | 2,545 | $0.0048 | 175 / 234 | 40 | 5 | 0 | 0 |

### Every decline: was its SQL actually right?

| set | id | run | Jev noul | SQL right? | how | mnemiq_verified same attempt | mnemiq_failopen same attempt | SQL |
|---|---|---|---|---|---|---|---|---|
| 29 | e02 | 1 | 0.26 | RIGHT | exact | correct | correct | `SELECT name FROM genre LIMIT 1000` |
| 29 | e08 | 1 | 0.41 | RIGHT | exact | correct | correct | `SELECT first_name, last_name, company FROM customer WHERE NOT company IS NULL AND company <> '' LIMIT 1000` |
| 29 | m01 | 1 | 0.32 | RIGHT | exact | correct | correct | `SELECT g.name AS genre_name, COUNT(t.track_id) AS track_count FROM genre AS g LEFT JOIN track AS t ON t.genre_id = g.genre_id GROUP BY g.name ORDER BY` |
| 29 | m06 | 1 | 0.31 | RIGHT | exact | correct | correct | `SELECT a.title, COUNT(*) AS track_count FROM track AS t JOIN album AS a ON t.album_id = a.album_id GROUP BY a.title HAVING COUNT(*) > 20 LIMIT 1000` |
| 29 | e02 | 2 | 0.32 | RIGHT | exact | correct | correct | `SELECT name FROM genre LIMIT 1000` |
| 29 | e08 | 2 | 0.39 | RIGHT | exact | correct | correct | `SELECT first_name, last_name, company FROM customer WHERE NOT company IS NULL AND company <> '' LIMIT 1000` |
| 29 | m01 | 2 | 0.44 | RIGHT | exact | correct | correct | `SELECT g.name AS genre_name, COUNT(t.track_id) AS track_count FROM track AS t JOIN genre AS g ON t.genre_id = g.genre_id GROUP BY g.name ORDER BY g.na` |
| 29 | e02 | 3 | 0.34 | RIGHT | exact | correct | correct | `SELECT name FROM genre LIMIT 1000` |
| 29 | e08 | 3 | 0.39 | RIGHT | exact | correct | correct | `SELECT first_name, last_name, company FROM customer WHERE NOT company IS NULL AND company <> '' LIMIT 1000` |
| holdout | ho10 | 1 | 0.32 | RIGHT | exact | correct | correct | `SELECT EXTRACT(DAYOFWEEK FROM invoice_date) AS day_of_week, COUNT(*) AS invoice_count FROM invoice WHERE EXTRACT(YEAR FROM invoice_date) = 2024 GROUP ` |
| holdout | ho14 | 1 | 0.16 | RIGHT | valid under gold boundary tie | declined | wrong_result | `SELECT EXTRACT(WEEK FROM invoice_date) AS week_number, SUM(total) AS revenue FROM invoice WHERE invoice_date >= CAST('2023-01-01 00:00:00' AS TIMESTAM` |
| holdout | ho10 | 2 | 0.37 | RIGHT | exact | correct | correct | `SELECT CAST(STRFTIME(invoice_date, '%w') AS INT) AS day_of_week, COUNT(*) AS invoice_count FROM invoice WHERE invoice_date >= CAST('2024-01-01 00:00:0` |
| holdout | ho10 | 3 | 0.3 | RIGHT | exact | declined | correct | `SELECT EXTRACT(DAYOFWEEK FROM invoice_date) AS day_of_week, COUNT(*) AS invoice_count FROM invoice WHERE EXTRACT(YEAR FROM invoice_date) = 2024 GROUP ` |
| holdout | ho14 | 3 | 0.2 | RIGHT | valid under gold boundary tie | wrong_result | correct | `SELECT EXTRACT(WEEK FROM invoice_date) AS week_number, SUM(total) AS revenue FROM invoice WHERE EXTRACT(YEAR FROM invoice_date) = 2023 GROUP BY week_n` |

Declines: 14; SQL actually right: **14** (correct answers blocked); actually wrong: **0** (real mistakes caught).

Answers passed by Jev and scored `wrong_result` by the harness: holdout:ho14 r2 (noul 0.83; re-labelled: right, valid under gold boundary tie)

### Per question vs mnemiq_verified and mnemiq_failopen (r1 r2 r3)

| set | id | mnemiq_jev | mnemiq_verified | mnemiq_failopen |
|---|---|---|---|---|
| 29 | e02 | 🚫🚫🚫 | ✓✓✓ | ✓✓✓ |
| 29 | e08 | 🚫🚫🚫 | ✓✓✓ | ✓✓✓ |
| 29 | m01 | 🚫🚫✓ | ✓✓✓ | ✓✓✓ |
| 29 | m06 | 🚫✓✓ | ✓✓✓ | ✓✓✓ |
| 29 | h05 | ✓✓✓ | 🚫✓✓ | ✓✓✓ |
| holdout | ho10 | 🚫🚫🚫 | ✓✓🚫 | ✓✓✓ |
| holdout | ho13 | ✓✓✓ | 🚫✓🚫 | ✓✓✓ |
| holdout | ho14 | 🚫✗🚫 | 🚫✗✗ | ✗✓✓ |

(Listed only where any of the three is not ✓✓✓. ✓ exact, ✗ wrong, 🚫 declined, ⚠ tool error. Generation differs run to run, so this is attempt vs attempt; the same-SQL comparison is results/judge-comparison/.)


## mnemiq_jev_v2: truncation-aware Jev judge outcomes (29 + holdout)

Jev log lines: 132; matched to attempts: 132; unmatched: 0; HTTP statuses: {'200': 132}; attempts with more than one Jev call: 0; attempts with none: 0.

Jev calls bypass llm-meter, so they are counted from the log; `input_tokens` is the API's own `usage.input_tokens` (not estimated). Cost = input tokens x $0.042 per million (output tokens are free).

| set | attempts | Jev calls | Jev input tokens (total) | avg per call | est. Jev cost | Jev latency p50 / p95 ms | passed | declined (verification) | judge unavailable | other |
|---|---|---|---|---|---|---|---|---|---|---|
| 29 | 87 | 87 | 234,385 | 2,694 | $0.0098 | 155 / 213 | 85 | 0 | 0 | 2 |
| holdout | 45 | 45 | 119,872 | 2,664 | $0.0050 | 145 / 206 | 39 | 6 | 0 | 0 |

### Every decline: was its SQL actually right?

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

### Per question vs mnemiq_jev (v1), mnemiq_verified and mnemiq_failopen (r1 r2 r3)

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


## Jev prompt variants (offline, same 264 items)

Labels and judge inputs as in judge_comparison.md (mnemiq's own schema/preview rebuild; ho14 tie and ho12 collation rules). Each variant is JevJudge with `MNEMIQ_JEV_PROMPT=<v>` (mnemiq/patches/jev-judge.patch); pass = noul >= 0.5. **Only 2 of the 132 same-call items (ho13 r1, r3) are wrong, so 'wrong caught' is a 0-2 count and must not drive the choice on its own; the decision metric is correct answers blocked.**

| variant | what changes | same 132 calls: wrong caught / passed | correct blocked | correct passed | all 264: wrong caught / passed | correct blocked | ho13 r1 | ho13 r3 | avg input tok | Jev cost (264 calls) |
|---|---|---|---|---|---|---|---|---|---|---|
| gpt-oss:120b judge (logged) | baseline | 2 / 0 | 3 | 127 | – | – | 0.10 | 0.15 | – | – |
| v1 (original run) | original prompt, 5-row preview (the run committed earlier) | 1 / 1 | 15 | 115 | 1 / 1 | 29 | 0.07 | 0.53 | 2,548 | $0.0283 |
| v1 (repeat) | same prompt, re-scored now (noise control) | 1 / 1 | 16 | 114 | 1 / 1 | 30 | 0.06 | 0.59 | 2,548 | $0.0283 |
| a | SQL-logic instruction + row counts / truncation flag + note, 5-row preview | 1 / 1 | 5 | 125 | 1 / 1 | 9 | 0.18 | 0.68 | 2,648 | $0.0294 |
| b | as a, 50-row sample | 1 / 1 | 5 | 125 | 1 / 1 | 9 | 0.10 | 0.57 | 2,687 | $0.0298 |
| c | as a, full result (<=250 rows; all items fit) | 1 / 1 | 5 | 125 | 1 / 1 | 9 | 0.16 | 0.77 | 2,714 | $0.0301 |

### Best threshold per variant (all 264 items)

Chosen as: fewest wrong passed, then fewest correct blocked, then the highest threshold. With 2 wrong items this is descriptive, not a tuned operating point.

| variant | threshold | wrong caught / passed | correct blocked | at the shipped 0.5: correct blocked |
|---|---|---|---|---|
| v1 (original run) | 0.55 | 2 / 0 | 35 | 29 |
| v1 (repeat) | 0.60 | 2 / 0 | 52 | 30 |
| a | 0.69 | 2 / 0 | 18 | 9 |
| b | 0.62 | 2 / 0 | 10 | 9 |
| c | 0.78 | 2 / 0 | 57 | 9 |

**Jev noise (v1 original vs v1 repeat, identical requests):** mean |delta noul| 0.027, max 0.21, pass/block flips at 0.5: 5 of 264.

| variant | correct answers blocked: 5-row preview was truncated (n=84) | not truncated (n=178) |
|---|---|---|
| v1 (original run) | 24 | 5 |
| v1 (repeat) | 24 | 6 |
| a | 5 | 4 |
| b | 5 | 4 |
| c | 5 | 4 |

### Correct answers still blocked at 0.5, per variant (same 132 calls)

| variant | blocked correct items (id rN, noul) |
|---|---|
| v1 (original run) | e02 r1 (0.25), e08 r1 (0.43), m01 r1 (0.46), h06 r1 (0.38), e02 r2 (0.35), e08 r2 (0.37), m01 r2 (0.37), m06 r2 (0.48), e02 r3 (0.35), e08 r3 (0.36), ho10 r1 (0.30), ho14 r1 (0.21), ho10 r2 (0.29), ho10 r3 (0.30), ho14 r3 (0.30) |
| v1 (repeat) | e02 r1 (0.32), e08 r1 (0.44), m01 r1 (0.42), h06 r1 (0.46), e02 r2 (0.26), e08 r2 (0.40), m01 r2 (0.48), h06 r2 (0.34), e02 r3 (0.37), e08 r3 (0.38), m01 r3 (0.30), ho10 r1 (0.32), ho14 r1 (0.34), ho10 r2 (0.29), ho10 r3 (0.31), ho14 r3 (0.23) |
| a | ho10 r1 (0.41), ho14 r1 (0.42), ho10 r2 (0.35), ho10 r3 (0.39), ho14 r3 (0.16) |
| b | ho10 r1 (0.42), ho14 r1 (0.15), ho10 r2 (0.42), ho10 r3 (0.41), ho14 r3 (0.16) |
| c | ho10 r1 (0.43), ho14 r1 (0.16), ho10 r2 (0.40), ho10 r3 (0.45), ho14 r3 (0.14) |


## Same-SQL judge comparison: Jev vs gpt-oss (offline)

Each item is a (question, SQL) mnemiq produced. Its judge input is rebuilt with mnemiq's own code (`mnemiq/judge_rebuild.py`): the schema is `_judge_schema` of the packet `Runtime.ask` retrieves (same `retrieve` arguments + window fitter), and the result is the SQL run through mnemiq's own adapter (DuckDB over the same Postgres) rendered by `render_result(max_rows=5)`, exactly what the Verifier passes. Correct = EX-exact vs gold with the harness `compare` on the full result. **ho14: answers that are a valid top 3 under the gold's four-way tie for 3rd place are labelled correct** (known gold flaw). **ho12: DuckDB returns the same 110 rows as gold but in binary-collation order (Postgres' locale collation ignores spaces); these are labelled correct when the same SQL is exact on Postgres, which is how the harness scored them.** Pass = score >= 0.5 (mnemiq's Verifier defers below its 0.5 threshold).

Items: 264 (132 mnemiq_verified judge calls with logged gpt-oss confidence, 132 mnemiq_failopen answers). Scored by Jev: 264; missing/unscored: 0. Correct: 262, wrong: 2.

Jev calls: 264, input tokens (reported by the API's `usage.input_tokens`): 672,721 total, 2,548 avg; cost at $0.042/M input tokens: $0.0283. Latency p50 157 ms, p95 209 ms. Model reported: ['jev-1.14.0'].

Prompt variants of the Jev request (truncation-aware, larger samples) on these same items: **judge_variants.md**. The tables below are the original request (v1); mnemiq_jev_v2 ships variant b.

### At threshold 0.5

| judge | items | wrong caught | wrong passed | correct blocked | correct passed | AUROC (score vs correct) |
|---|---|---|---|---|---|---|
| gpt-oss:120b judge (logged, mnemiq_verified calls) | 132 | 2 | 0 | 3 | 127 | 1.000 |
| Jev, same mnemiq_verified calls | 132 | 1 | 1 | 15 | 115 | 0.929 |
| Jev, mnemiq_failopen answers | 132 | 0 | 0 | 14 | 118 | n/a |
| Jev, all items | 264 | 1 | 1 | 29 | 233 | 0.935 |

### Threshold sweep (blocked = score below threshold)

| threshold | gpt-oss: wrong caught / passed | gpt-oss: correct blocked | Jev (same calls): wrong caught / passed | Jev (same calls): correct blocked | Jev (all): wrong caught / passed | Jev (all): correct blocked |
|---|---|---|---|---|---|---|
| 0.1 | 0 / 2 | 0 | 1 / 1 | 0 | 1 / 1 | 0 |
| 0.2 | 2 / 0 | 0 | 1 / 1 | 0 | 1 / 1 | 0 |
| 0.3 | 2 / 0 | 0 | 1 / 1 | 3 | 1 / 1 | 4 |
| 0.4 | 2 / 0 | 2 | 1 / 1 | 12 | 1 / 1 | 21 |
| 0.5 | 2 / 0 | 3 | 1 / 1 | 15 | 1 / 1 | 29 |
| 0.6 | 2 / 0 | 4 | 2 / 0 | 26 | 2 / 0 | 49 |
| 0.7 | 2 / 0 | 7 | 2 / 0 | 46 | 2 / 0 | 91 |
| 0.8 | 2 / 0 | 13 | 2 / 0 | 71 | 2 / 0 | 140 |
| 0.9 | 2 / 0 | 25 | 2 / 0 | 109 | 2 / 0 | 219 |

### Every wrong answer, and every answer either judge blocks at 0.5

| source | set | id | run | correct? | detail | gpt-oss conf | Jev noul | SQL |
|---|---|---|---|---|---|---|---|---|
| mnemiq_failopen | 29 | e02 | 1 | yes | exact | – | 0.32 | `SELECT name FROM genre LIMIT 1000` |
| mnemiq_failopen | 29 | e02 | 2 | yes | exact | – | 0.31 | `SELECT name FROM genre LIMIT 1000` |
| mnemiq_failopen | 29 | e02 | 3 | yes | exact | – | 0.38 | `SELECT name FROM genre LIMIT 1000` |
| mnemiq_verified | 29 | e02 | 1 | yes | exact | 0.98 | 0.25 | `SELECT name FROM genre LIMIT 1000` |
| mnemiq_verified | 29 | e02 | 2 | yes | exact | 0.97 | 0.35 | `SELECT name FROM genre ORDER BY name LIMIT 1000` |
| mnemiq_verified | 29 | e02 | 3 | yes | exact | 0.98 | 0.35 | `SELECT name FROM genre LIMIT 1000` |
| mnemiq_failopen | 29 | e08 | 1 | yes | exact | – | 0.38 | `SELECT first_name, last_name, company FROM customer WHERE NOT company IS NULL AND company <> '' LIMIT 1000` |
| mnemiq_failopen | 29 | e08 | 2 | yes | exact | – | 0.38 | `SELECT first_name, last_name, company FROM customer WHERE NOT company IS NULL AND TRIM(company) <> '' LIMIT 1000` |
| mnemiq_failopen | 29 | e08 | 3 | yes | exact | – | 0.40 | `SELECT first_name, last_name, company FROM customer WHERE NOT company IS NULL AND company <> '' LIMIT 1000` |
| mnemiq_verified | 29 | e08 | 1 | yes | exact | 0.95 | 0.43 | `SELECT first_name, last_name, company FROM customer WHERE NOT company IS NULL LIMIT 1000` |
| mnemiq_verified | 29 | e08 | 2 | yes | exact | 0.97 | 0.37 | `SELECT first_name, last_name, company FROM customer WHERE NOT company IS NULL AND company <> '' LIMIT 1000` |
| mnemiq_verified | 29 | e08 | 3 | yes | exact | 0.95 | 0.36 | `SELECT first_name, last_name, company FROM customer WHERE NOT company IS NULL AND company <> '' LIMIT 1000` |
| mnemiq_verified | 29 | h05 | 1 | yes | exact | 0.35 | 0.55 | `SELECT EXTRACT(MONTH FROM invoice_date) AS month, SUM(total) AS revenue, LAG(SUM(total)) OVER (ORDER BY EXTRACT(MONTH FROM invoice_date)) AS prev_month_revenue ` |
| mnemiq_verified | 29 | h06 | 1 | yes | exact | 0.75 | 0.38 | `SELECT a.name, COUNT(DISTINCT t.genre_id) AS distinct_genres FROM track AS t JOIN album AS al ON t.album_id = al.album_id JOIN artist AS a ON al.artist_id = a.a` |
| mnemiq_failopen | 29 | m01 | 1 | yes | exact | – | 0.41 | `SELECT g.name AS genre_name, COUNT(t.track_id) AS track_count FROM track AS t JOIN genre AS g ON t.genre_id = g.genre_id GROUP BY g.name ORDER BY g.name LIMIT 1` |
| mnemiq_failopen | 29 | m01 | 2 | yes | exact | – | 0.49 | `SELECT g.name AS genre_name, COUNT(t.track_id) AS track_count FROM track AS t JOIN genre AS g ON t.genre_id = g.genre_id GROUP BY g.name ORDER BY g.name LIMIT 1` |
| mnemiq_failopen | 29 | m01 | 3 | yes | exact | – | 0.47 | `SELECT g.name, COUNT(t.track_id) AS track_count FROM track AS t JOIN genre AS g ON t.genre_id = g.genre_id GROUP BY g.name ORDER BY g.name LIMIT 1000` |
| mnemiq_verified | 29 | m01 | 1 | yes | exact | 0.97 | 0.46 | `SELECT g.name AS genre_name, COUNT(t.track_id) AS track_count FROM genre AS g LEFT JOIN track AS t ON g.genre_id = t.genre_id GROUP BY g.name ORDER BY g.name LI` |
| mnemiq_verified | 29 | m01 | 2 | yes | exact | 0.95 | 0.37 | `SELECT g.name AS genre_name, COUNT(t.track_id) AS track_count FROM genre AS g LEFT JOIN track AS t ON g.genre_id = t.genre_id GROUP BY g.name ORDER BY g.name LI` |
| mnemiq_verified | 29 | m06 | 2 | yes | exact | 0.75 | 0.48 | `SELECT a.title, COUNT(t.track_id) AS track_count FROM album AS a JOIN track AS t ON a.album_id = t.album_id GROUP BY a.title HAVING COUNT(t.track_id) > 20 ORDER` |
| mnemiq_failopen | holdout | ho10 | 1 | yes | exact | – | 0.35 | `SELECT CAST(STRFTIME(invoice_date, '%w') AS INT) AS day_of_week, COUNT(*) AS invoice_count FROM invoice WHERE invoice_date >= CAST('2024-01-01 00:00:00' AS TIME` |
| mnemiq_failopen | holdout | ho10 | 2 | yes | exact | – | 0.31 | `SELECT EXTRACT(DAYOFWEEK FROM invoice_date) AS day_of_week, COUNT(*) AS invoice_count FROM invoice WHERE invoice_date >= CAST('2024-01-01 00:00:00' AS TIMESTAMP` |
| mnemiq_failopen | holdout | ho10 | 3 | yes | exact | – | 0.31 | `SELECT CAST(EXTRACT(DAYOFWEEK FROM invoice_date) AS INT) AS day_of_week, COUNT(*) AS invoice_count FROM invoice WHERE CAST(EXTRACT(YEAR FROM invoice_date) AS IN` |
| mnemiq_verified | holdout | ho10 | 1 | yes | exact | 0.72 | 0.30 | `SELECT EXTRACT(DAYOFWEEK FROM invoice_date) AS day_of_week, COUNT(*) AS invoice_count FROM invoice WHERE EXTRACT(YEAR FROM invoice_date) = 2024 GROUP BY EXTRACT` |
| mnemiq_verified | holdout | ho10 | 2 | yes | exact | 0.58 | 0.29 | `SELECT EXTRACT(DAYOFWEEK FROM invoice_date) AS day_of_week, COUNT(*) AS invoice_count FROM invoice WHERE EXTRACT(YEAR FROM invoice_date) = 2024 GROUP BY day_of_` |
| mnemiq_verified | holdout | ho10 | 3 | yes | exact | 0.4 | 0.30 | `SELECT EXTRACT(DAYOFWEEK FROM invoice_date) AS day_of_week, COUNT(*) AS invoice_count FROM invoice WHERE EXTRACT(YEAR FROM invoice_date) = 2024 GROUP BY day_of_` |
| mnemiq_failopen | holdout | ho13 | 1 | yes | exact | – | 0.44 | `WITH agg AS (SELECT EXTRACT(YEAR FROM invoice_date) AS yr, EXTRACT(QUARTER FROM invoice_date) AS qtr, SUM(total) AS revenue FROM invoice WHERE EXTRACT(YEAR FROM` |
| mnemiq_verified | holdout | ho13 | 1 | NO | wrong | 0.1 | 0.07 | `WITH q AS (SELECT ((MONTH(invoice_date) - 1) / 3) + 1 AS quarter, SUM(total) AS revenue FROM invoice WHERE YEAR(invoice_date) = 2024 GROUP BY 1) SELECT q.quarte` |
| mnemiq_verified | holdout | ho13 | 3 | NO | wrong | 0.15 | 0.53 | `SELECT quarter, revenue, LAG(revenue) OVER (ORDER BY quarter) AS previous_quarter_revenue FROM (SELECT CAST(((EXTRACT(MONTH FROM invoice_date) - 1) / 3) + 1 AS ` |
| mnemiq_failopen | holdout | ho14 | 2 | yes | valid under gold boundary tie | – | 0.21 | `SELECT EXTRACT(WEEK FROM invoice_date) AS week_number, SUM(total) AS revenue FROM invoice WHERE EXTRACT(YEAR FROM invoice_date) = 2023 GROUP BY week_number ORDE` |
| mnemiq_verified | holdout | ho14 | 1 | yes | valid under gold boundary tie | 0.3 | 0.21 | `SELECT EXTRACT(WEEK FROM invoice_date) AS week_number, SUM(total) AS revenue FROM invoice WHERE EXTRACT(YEAR FROM invoice_date) = 2023 GROUP BY week_number ORDE` |
| mnemiq_verified | holdout | ho14 | 3 | yes | valid under gold boundary tie | 0.92 | 0.30 | `SELECT CAST(DATE_PART('week', invoice_date) AS INT) AS week_number, SUM(total) AS revenue FROM invoice WHERE DATE_PART('year', invoice_date) = 2023 GROUP BY wee` |

### Named cases

| case | correct? | gpt-oss conf | Jev noul |
|---|---|---|---|
| mnemiq_verified h05 r1 | yes (exact) | 0.35 | 0.55 |
| mnemiq_failopen h05 r1 | yes (exact) | – | 0.55 |
| mnemiq_verified ho10 r3 | yes (exact) | 0.4 | 0.30 |
| mnemiq_failopen ho10 r3 | yes (exact) | – | 0.31 |
| mnemiq_verified ho13 r1 | NO (wrong) | 0.1 | 0.07 |
| mnemiq_failopen ho13 r1 | yes (exact) | – | 0.44 |
| mnemiq_verified ho13 r3 | NO (wrong) | 0.15 | 0.53 |
| mnemiq_failopen ho13 r3 | yes (exact) | – | 0.86 |
| mnemiq_verified ho14 r1 | yes (valid under gold boundary tie) | 0.3 | 0.21 |
| mnemiq_failopen ho14 r1 | yes (exact) | – | 0.82 |
| mnemiq_verified ho14 r2 | yes (valid under gold boundary tie) | 0.86 | 0.82 |
| mnemiq_failopen ho14 r2 | yes (valid under gold boundary tie) | – | 0.21 |
| mnemiq_verified ho14 r3 | yes (valid under gold boundary tie) | 0.92 | 0.30 |
| mnemiq_failopen ho14 r3 | yes (valid under gold boundary tie) | – | 0.84 |


## mnemiq_verified: verifier outcomes (29 + holdout)

Judge = mnemiq's `SemanticJudge` with `max_tokens=1200` (patches/verifier-tokens.patch), fail-closed, threshold 0.5. Per-call data from the patch's log line; SQL of rejected answers re-executed (DuckDB over the same Postgres, i.e. mnemiq's executor) and re-scored against gold by `bench/mnemiq_verifier_analysis.py`.

Judge calls logged: 132; matched to attempts: 132; unmatched: 0; empty replies (reply_chars=0, the finish_reason=length signature): 0; calls returning more than one judge line per attempt: 0.

| set | attempts | checked & passed | rejected (declined: verification) | unavailable (verifier_unavailable) | other |
|---|---|---|---|---|---|
| 29 | 87 | 86 | 1 | 0 | 0 |
| holdout | 45 | 41 | 4 | 0 | 0 |

### Passed by the judge: correctness

| set | passed | of which EX exact | relaxed only | wrong_result | exec_error |
|---|---|---|---|---|---|
| 29 | 86 | 86 | 0 | 0 | 0 |
| holdout | 41 | 39 | 0 | 2 | 0 |

Non-exact answers the judge passed: holdout:ho14 r2 (wrong_result as scored, judge conf 0.86; re-executed: valid under gold boundary tie); holdout:ho14 r3 (wrong_result as scored, judge conf 0.92; re-executed: valid under gold boundary tie)

Gold-tie note: ho14's gold (`ORDER BY revenue DESC LIMIT 3`) has a four-way tie for 3rd place (weeks 8, 30, 39, 47, 22.77 each), and the gold arbitrarily keeps one, so a correct query can be scored `wrong_result` depending on the executor's tie order (it is not even stable between executions). Harness scoring is left unchanged; the 'valid under gold boundary tie' verdicts above re-check against every tie choice with the same `compare`. No other gold query in either set has a tie at its LIMIT boundary.

### Every rejected / unavailable answer: was its SQL actually right?

| set | id | run | outcome | judge conf | SQL vs gold | executed on | mnemiq_failopen same attempt | SQL the judge saw |
|---|---|---|---|---|---|---|---|---|
| 29 | h05 | 1 | rejected | 0.35 | RIGHT (exact) | duckdb (mnemiq's executor) | correct | `SELECT EXTRACT(MONTH FROM invoice_date) AS month, SUM(total) AS revenue, LAG(SUM(total)) OVER (ORDER BY EXTRACT(MONTH FROM invoice_date)) AS prev_month_revenue FROM invoice WHERE invoice_date >= CAST('2024-01-01' AS TIME` |
| holdout | ho13 | 1 | rejected | 0.1 | WRONG | duckdb (mnemiq's executor) | correct | `WITH q AS (SELECT ((MONTH(invoice_date) - 1) / 3) + 1 AS quarter, SUM(total) AS revenue FROM invoice WHERE YEAR(invoice_date) = 2024 GROUP BY 1) SELECT q.quarter, q.revenue, prev.revenue AS previous_quarter_revenue FROM ` |
| holdout | ho14 | 1 | rejected | 0.3 | WRONG / valid under gold boundary tie | duckdb (mnemiq's executor) | wrong_result | `SELECT EXTRACT(WEEK FROM invoice_date) AS week_number, SUM(total) AS revenue FROM invoice WHERE EXTRACT(YEAR FROM invoice_date) = 2023 GROUP BY week_number ORDER BY revenue DESC LIMIT 3` |
| holdout | ho10 | 3 | rejected | 0.4 | RIGHT (exact) | duckdb (mnemiq's executor) | correct | `SELECT EXTRACT(DAYOFWEEK FROM invoice_date) AS day_of_week, COUNT(*) AS invoice_count FROM invoice WHERE EXTRACT(YEAR FROM invoice_date) = 2024 GROUP BY day_of_week ORDER BY day_of_week LIMIT 1000` |
| holdout | ho13 | 3 | rejected | 0.15 | WRONG | duckdb (mnemiq's executor) | correct | `SELECT quarter, revenue, LAG(revenue) OVER (ORDER BY quarter) AS previous_quarter_revenue FROM (SELECT CAST(((EXTRACT(MONTH FROM invoice_date) - 1) / 3) + 1 AS INT) AS quarter, SUM(total) AS revenue FROM invoice WHERE EX` |

### Per question vs mnemiq_failopen (status per run r1/r2/r3)

| set | id | mnemiq_verified | mnemiq_failopen |
|---|---|---|---|
| 29 | h05 | 🚫✓✓ | ✓✓✓ |
| holdout | ho10 | ✓✓🚫 | ✓✓✓ |
| holdout | ho13 | 🚫✓🚫 | ✓✓✓ |
| holdout | ho14 | 🚫✗✗ | ✗✓✓ |

(Only questions where either system was not ✓✓✓ are listed; all others were exact in all 3 runs for both. ✓ exact, ≈ extra cols, ✗ wrong, 🚫 declined, ⚠ tool error.)

