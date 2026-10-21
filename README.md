# nl2sql-bench — WrenAI (out of the box / + semantic layer / + semantic layer, no reasoning) vs DB-GPT vs Cube Core (+LLM adapter: baseline / rich model + SQL API v2) vs Router (cube_v2 → Wren noreason)

Same natural-language questions, same Postgres database, same LLM, measured the same way.

| System | How questions reach it | API used by the harness |
|---|---|---|
| **WrenAI 0.29.2 (out of the box)** — system `wrenai` (official docker compose) | NL → SQL; project = tables + PK/FK relationships only | `POST http://localhost:3000/api/v1/generate_sql` `{question, returnSqlDialect:true}` (wren-ui wraps wren-ai-service `/v1/asks` + polling; ibis converts Wren SQL to native Postgres SQL) |
| **WrenAI 0.29.2 + semantic layer** — system `wrenai_mdl` (2nd, identical WrenAI stack, compose project `wrenai-mdl`) | NL → SQL; project additionally carries the MDL in `wrenai_mdl/mdl/semantic_layer.yaml` (see below) | `POST http://localhost:3001/api/v1/generate_sql` (same API) |
| **WrenAI 0.29.2 + semantic layer, no reasoning** — system `wrenai_mdl_noreason` (same 2nd stack, switched with `make wren-mdl-noreason`) | identical to `wrenai_mdl` except wren-ai-service setting `allow_sql_generation_reasoning: false` | `POST http://localhost:3001/api/v1/generate_sql` |
| **DB-GPT 0.8.2** (official `dbgpt-openai` image + psycopg2) | NL → SQL (chat_data mode) | `POST http://localhost:5670/api/v2/chat/completions` `{chat_mode:"chat_data", chat_param:"chinook", stream:false}`; SQL is parsed out of the `<chart-view content=…>` block in the reply |
| **Cube Core 1.8.8 + LLM adapter (baseline)** — system `cube` | Cube Core has **no OSS NL interface** (the AI API / D3 is Cube Cloud-only; OSS v1.8.8 api-gateway only has `/v1/load, /sql, /meta, /cubesql, /dry-run, …`). The harness gives the same LLM the `/v1/meta` model + join list and asks for a Cube REST query JSON (1 self-correction retry on Cube errors) | `POST http://localhost:4000/cubejs-api/v1/load` |
| **Cube Core 1.8.8 + rich model + LLM adapter v2 (harness-built)** — system `cube_v2` (service `cube_v2`, REST :4001, SQL API :15432) | same LLM gets the *views* of `cube_v2/model` (with descriptions) from `/v1/meta` and writes ONE Cube SQL API query (Postgres dialect, `MEASURE()`, push-down/post-processing); 1 repair retry on Cube errors | Cube SQL API (Postgres wire protocol) at `localhost:15432` — executed by Cube, never directly on Postgres |
| **mnemiq @ a453b05** — systems `mnemiq` (defaults), `mnemiq_failopen`, `mnemiq_verified`, `mnemiq_jev` and `mnemiq_jev_v2` (one-change variants) | NL → SQL; its own enrichment (`mnemiq enrich`: profiling + one LLM description pass, 11 tables) and retrieval index (`mnemiq build`, nomic-embed-text); default mode `thinking` (1 candidate, corrector, deterministic sanity + LLM judge) | `POST http://localhost:8090/v1/ask` `{question}` (`mnemiq serve --http`; variants on :8091–:8094); a deferral is scored `declined` |
| **Router** — system `router` | try cube_v2 first (prompt copy that may reply `CANNOT_EXPRESS`); fall back to WrenAI + semantic layer, no reasoning on unsupported / Cube error / empty result. No gold used for routing. | cube_v2 SQL API + `POST http://localhost:3001/api/v1/generate_sql`; tokens under `/router/` (+ `/wrenmdlnr/` on fallback) |
| **Vanna 2.0.2** — system `vanna` (`vanna/server.py`, :8095) | NL → SQL with Vanna's classic `generate_sql` (`vanna.legacy`: OpenAI_Chat + ChromaDB_VectorStore), trained on the 11 Chinook `CREATE TABLE`s only; 1 LLM call, SQL only (no execution, no retry) | `POST http://localhost:8095/v1/generate` `{question}` → `{sql}`; the harness executes it |
| **Vanna 2.0.2 + Jev answer check** — systems `vanna_jev` (:8096) and `vanna_jev_retry` (:8097) | same Vanna generation; the service executes the SQL read-only and asks TypeSafe Jev (mnemiq_jev_v2's variant-b request) whether it answers the question; < 0.5 → declined (`_retry`: one regenerate + re-judge first) | same `POST /v1/generate`; response adds `decision` and per-attempt Jev results |

Fairness controls
* One Postgres (Chinook 1.4.5) container; WrenAI, DB-GPT and Cube connect to it as the same **read-only role `bench`**.
* All LLM/embedding traffic of all three goes through **llm-meter** (`meter/`, port 8089), a pass-through OpenAI-compatible proxy that sends chat calls to `LLM_UPSTREAM_BASE` and embedding calls to `EMBEDDING_UPSTREAM_BASE`, and counts tokens per tool (neither tool reports usage in its API). Same chat model for all three (`LLM_MODEL`, default **`gpt-oss:120b` on Ollama Cloud**), temperature 0; same embedding model for Wren and DB-GPT (**`nomic-embed-text`, 768-d, local `ollama` container** — Ollama Cloud has no embeddings API: `/v1/embeddings` 404, `/api/embed` 401).
* Tools run with their default pipelines (WrenAI: intent classification, reasoning, SQL correction; DB-GPT: ChatWithDbExecute).
* Vanna (added later) follows the same rules: read-only `bench` role, all chat and embedding calls through llm-meter (`/vanna/`), gpt-oss:120b at temperature 0, nomic-embed-text.
* Every generated SQL is re-executed by the harness on the same Postgres in a `READ ONLY` transaction (30 s statement timeout) and compared with the gold result.

## Quick start

```bash
cd /workspace/nl2sql-bench
cp .env.example .env            # first time only (make up does this too)
# put your key in .env:  LLM_API_KEY=<Ollama Cloud key>   (chmod 600 .env; .env is git-ignored)
make up                          # docker up + connect WrenAI/DB-GPT to Postgres + deploy/index schema
make verify                      # gold SQL check, Cube reference queries, API probe
make bench REPEATS=3             # real run → results/<timestamp>/{results.csv,summary.md,raw.jsonl}
.venv/bin/python bench/chart.py results/<run>   # single-run chart (make report builds the combined 4-system results/summary.png)
make mock                        # dry run without any LLM key (mock WrenAI/DB-GPT; Cube via reference queries)
make bench SYSTEMS=wrenai,dbgpt  # subset of systems
make wren-mdl                    # (after make up) start 2nd WrenAI stack (:3001/:5556) + build/deploy the semantic layer
make bench SYSTEMS=wrenai_mdl REPEATS=3
make wren-mdl-noreason           # switch 2nd stack to the no-reasoning variant, then:
make bench SYSTEMS=wrenai_mdl_noreason REPEATS=3
make bench-router REPEATS=3      # router (needs noreason variant; make target switches it)
make mnemiq-install && make bench-mnemiq REPEATS=3   # mnemiq (pinned commit) on the 29 + the 15 holdout
make bench-mnemiq-failopen REPEATS=3                 # mnemiq judge fail-open variant (see below)
make bench-vanna REPEATS=3                           # Vanna 2.0.2 (:8095, meter /vanna/) on the 29 + the 15 holdout; make vanna-down stops it
make bench-vanna-jev REPEATS=3                       # Vanna + Jev answer check (:8096, /vannaj/; needs TYPESAFE_API_KEY)
make bench-vanna-jev-retry REPEATS=3                 # Vanna + Jev check + 1 retry (:8097, /vannajr/)
make vanna-jev-offline                               # Jev variant b on plain vanna's saved SQLs (same-SQL view)
make bench-mnemiq-verified REPEATS=3                 # mnemiq judge 1200-token variant, fail-closed (patched worktree)
.venv/bin/python bench/mnemiq_verifier_analysis.py   # verifier outcomes + re-scored SQL of rejected answers
make bench-mnemiq-jev REPEATS=3                      # mnemiq with TypeSafe Jev as judge, original request (MNEMIQ_JEV_PROMPT=v1)
make bench-mnemiq-jev2 REPEATS=3                     # same, truncation-aware request (MNEMIQ_JEV_PROMPT=b, the patch default)
# offline Jev prompt variants: MNEMIQ_JEV_PROMPT=<v1|a|b|c> MNEMIQ_VARIANT=jev mnemiq/run.sh py mnemiq/judge_rebuild.py items.jsonl rebuilt_<v>.jsonl; bench/judge_comparison.py variants
.venv/bin/python bench/mnemiq_jev_analysis.py         # Jev calls/tokens/cost + every decline checked against gold
# offline same-SQL judge comparison (no reruns): bench/judge_comparison.py items -> mnemiq/judge_rebuild.py -> judge_comparison.py score
make bench-holdout REPEATS=3     # 15 held-out q × router,cube_v2,wrenai_mdl_noreason → results/run-gptoss120b-holdout-r3/
make wren-mdl-restore            # switch back (wrenai_mdl); config.yaml is re-rendered byte-identically
.venv/bin/python bench/stage_latency.py   # per-stage latency from wren-ai-service logs (see below)
make report                      # combined report → results/combined_summary.md + results/summary.png
make down / make clean           # stop / stop + delete volumes
```

After changing the key or model in `.env`, run `make up` again: it re-renders `wrenai/.env` + `wrenai/config.yaml`,
recreates the containers whose env changed, re-deploys Wren (schema indexing) and re-embeds DB-GPT's schema.

### LLM settings (`.env`)
| var | default | meaning |
|---|---|---|
| `LLM_API_KEY` | *(empty — required)* | key for `LLM_UPSTREAM_BASE`; injected into WrenAI/DB-GPT as `OPENAI_API_KEY` (the env name their OpenAI-compatible clients read) and used by the Cube adapter |
| `LLM_MODEL` | `gpt-oss:120b` | chat model for all systems (name as listed by `GET https://ollama.com/v1/models`) |
| `LLM_UPSTREAM_BASE` | `https://ollama.com/v1` | any OpenAI-compatible endpoint (OpenAI, Groq, OpenRouter, vLLM…) |
| `LLM_CONTEXT_WINDOW` | 128000 | told to WrenAI's litellm config |
| `EMBEDDING_MODEL` / `EMBEDDING_DIM` / `EMBEDDING_UPSTREAM_BASE` | `nomic-embed-text` / 768 / `http://ollama:11434/v1` | embeddings (WrenAI + DB-GPT schema retrieval). For OpenAI use `text-embedding-3-small` / 1536 / `https://api.openai.com/v1` and `STRIP_AUTH_FOR_EMBEDDINGS=0`. Wren's qdrant collections are recreated at ai-service start (`recreate_index: true`), so a dimension change only needs `make up`. |

### Using a different database
1. Edit `BENCH_PG_HOST/PORT/DB/USER/PASSWORD` (address as seen **from containers**; for a DB on this machine use the host IP / `host.docker.internal`) and `BENCH_DB_URL` (as seen from the harness on the host), e.g.
   `BENCH_DB_URL=postgresql://user:pass@db.example.com:5432/mydb`.
2. `make up` (WrenAI is re-onboarded with `--force` via `cd bench && ../.venv/bin/python setup_connections.py --force`; DB-GPT datasource is named after `BENCH_PG_DB`).
3. Provide a matching question file (`--questions my.yaml`, same format as `bench/questions.yaml`) and, for Cube, a model under `cube/model/` (+ optionally `bench/cube_reference_queries.yaml`).
   Only Postgres is wired today (Wren type `POSTGRES`, DB-GPT `postgresql`, Cube `postgres`).

## Layout
```
docker-compose.yml          postgres, llm-meter, ollama, dbgpt, cube, cube_v2   (network nl2sql-net)
wrenai/                     upstream WrenAI 0.29.2 compose + override joining nl2sql-net; .env/config.yaml are rendered
wrenai_mdl/                 2nd WrenAI stack (symlinked compose, own override/.env/config.yaml) + mdl/semantic_layer.yaml, mdl/deployed_mdl.json
dbgpt/                      Dockerfile (+psycopg2) and dbgpt-bench.toml
cube/model/cubes/chinook.yml  generic Chinook semantic model (12 cubes incl. a `manager` self-join cube)
meter/                      llm-meter proxy
db/                         Chinook SQL + read-only role
bench/questions.yaml        29 questions (8 easy / 9 medium / 12 hard) with gold SQL
bench/questions_holdout.yaml 15 held-out questions (models/prompts/MDL left unchanged)
bench/cube_reference_queries.yaml  hand-written Cube REST queries proving the baseline model covers 23/29 questions
cube_v2/model/              cube_v2 model (cubes/ + views/)    bench/cube_v2_reference_sql.yaml + verify_cube_v2.py  SQL API references (29/29)
mnemiq/run.sh, mnemiq/authz.json  mnemiq launcher (pinned commit, env from .env) + access policy; engine/state are git-ignored
mnemiq/patches/verifier-tokens.patch  the only engine code change (mnemiq_verified only, applied to a separate worktree)
bench/mnemiq_verifier_analysis.py  judge-outcome analysis -> results/run-gptoss120b-mnemiq-r3/verifier_analysis.md
mnemiq/patches/jev-judge.patch  JevJudge (TypeSafe Jev as mnemiq's judge), mnemiq_jev only, separate worktree mnemiq/engine-jev
bench/mnemiq_jev_analysis.py, bench/judge_comparison.py, mnemiq/judge_rebuild.py  Jev run analysis; same-SQL judge comparison -> results/judge-comparison/
vanna/                      Vanna service (server.py, run.sh, requirements.txt pinning vanna 2.0.2), build_ddl.py + training/ddl.sql; .venv/state git-ignored
bench/jev_judge.py          Jev variant-b request (shared; parity with the mnemiq patch: bench/jev_judge_parity.py)
bench/vanna_jev_offline.py, bench/vanna_jev_analysis.py  Vanna + Jev same-SQL view and run analysis
bench/holdout_report.py     holdout section + results/holdout_summary.png (called by combine.py)
bench/harness.py            runner, scoring, report     bench/clients.py  per-system API clients (incl. router)
bench/setup_connections.py  connects tools to the DB    bench/verify_gold.py, bench/probe.py
bench/wren_mdl.py           builds/deploys the Wren semantic layer   bench/combine.py  combined 5-system report + summary.png
bench/stage_latency.py      per-stage WrenAI latency from wren-ai-service logs (+ llm-meter timing events)
```

## WrenAI + semantic layer (`wrenai_mdl`)

Results (all four systems, OOTB vs MDL per question, by difficulty, latency, tokens, variance): `results/combined_summary.md`, `results/summary.png`.

**Why a second stack:** the out-of-the-box project (`wrenai/`, UI :3000, AI :5555, meter prefix `/wren/`) is left exactly as it was
benchmarked. `wrenai_mdl/` reuses the same upstream compose/config files (symlinks to `../wrenai/`), the same image digests, LLM,
embedding model and `config.yaml` pipeline settings; only the compose project (`wrenai-mdl`), host ports (UI **3001**, AI **5556**) and
the llm-meter prefix (`/wrenmdl/`, so tokens are counted separately) differ. It is not attached to `nl2sql-net` (same service names
would collide); it reaches Postgres and llm-meter through `host.docker.internal` (published ports 5432/8089).

**How it is built (`make wren-mdl` → `bench/wren_mdl.py`)** — only WrenAI's own modelling API (the GraphQL mutations the Wren UI calls),
driven from `wrenai_mdl/mdl/semantic_layer.yaml`; idempotent; ends with `deploy` = `SUCCESS` and dumps the deployed MDL to
`wrenai_mdl/mdl/deployed_mdl.json` (hash recorded there):
1. Data source + all 11 tables + 10 primary keys + 11 FK relationships (MANY_TO_ONE from the referencing table), same code as OOTB.
2. `updateModelMetadata`: display name + description for **all 11 models and all 64 columns**, description for all 11 relationships.
3. `createCalculatedField` — 9 per-entity rollups (Wren 0.29.2 allows one aggregate/math function over a column reached through relationships):
   `customer.lifetime_spend` = SUM(invoice.total), `customer.invoice_count` = COUNT(invoice.invoice_id),
   `invoice.units_on_invoice` = SUM(invoice_line.quantity), `track.units_sold` = SUM(invoice_line.quantity),
   `album.track_count` = COUNT(track.track_id), `artist.album_count` = COUNT(album.album_id), `genre.track_count` = COUNT(track.track_id),
   `playlist.track_count` = COUNT(playlist_track.track_id), `employee.supported_customer_count` = COUNT(customer.customer_id).
4. `createInstruction` (global, `isDefault: true`) — 9 generic rules, verbatim in the YAML: revenue definition (line level
   `unit_price*quantity` for catalogue entities, `invoice.total` for customers/countries/periods); track minutes = ms/60000.0; support rep =
   `customer.support_rep_id`, manager = `employee.reports_to`; dates = `invoice.invoice_date` with half-open year ranges; return only the requested
   columns; top-N = `ORDER BY … LIMIT N` (RANK/DENSE_RANK only when ties are asked for); no LIMIT unless a number is asked for; names are
   not unique → group by id too; Postgres rounding `ROUND(CAST(x AS NUMERIC), n)`.

**Not added, and why**
* **SQL pairs: none** (0 in `sql_pairs`). **Views: none** — a Wren view is stored and indexed as a question + SQL (`view_questions`), and the
  obvious candidates (revenue by artist / genre / country / month) would paraphrase benchmark questions.
* Metrics: WrenAI 0.29.2's UI/GraphQL has no metric-creation mutation (metrics exist only in the raw MDL schema), so none were added.
* Row-level calculated fields (line revenue `unit_price*quantity`, full name concat, duration in minutes) cannot be expressed with the
  0.29.2 calculated-field functions; they are described in column descriptions/instructions instead.

**Leakage check:** no element copies or paraphrases any of the 29 benchmark questions or gold SQL. Caveat: the generic rollups and
instructions are things a real modeller of Chinook would add, and some of them coincide with what certain questions need (e.g.
`genre.track_count`, `artist.album_count`, `album.track_count`, `playlist.track_count`, the revenue definition, the ties/LIMIT rules) — that
is the intended benefit of a semantic layer, but it means the comparison measures "WrenAI with a sensible, Chinook-aware model", authored
by someone who had seen the question set.

## WrenAI + semantic layer, no reasoning (`wrenai_mdl_noreason`)

One change versus `wrenai_mdl`: wren-ai-service `settings.allow_sql_generation_reasoning: false` (a documented setting in WrenAI
0.29.2's `docker/config.example.yaml`, read by `src/config.py` → `AskService`; when false, `ask.py` skips the
`sql_generation_reasoning` pipeline and calls SQL generation with `sql_generation_reasoning=None`). Intent classification,
retrieval, SQL functions/knowledge retrieval, correction, the project, deployed MDL, instructions, LLM, embeddings and wren-ui
(1 s polling) are unchanged.

How the switch works (`bench/render_config.py --mdl-variant {semantic|noreason}`, Make targets `wren-mdl-noreason` /
`wren-mdl-restore`):
* re-renders `wrenai_mdl/config.yaml`; the only diff is that setting plus the llm-meter prefix (`/wrenmdlnr/` instead of `/wrenmdl/`)
  so tokens are attributed separately (the meter strips the prefix; upstream requests are identical);
* recreates `wren-ai-service` (its qdrant collections are recreated at start, `recreate_index: true`), re-deploys the unchanged
  project and re-indexes the 9 instructions (`bench/wren_mdl.py --redeploy`), and fails unless the deployed MDL hash equals
  `wrenai_mdl/mdl/deployed_mdl.json` (453930b9…) and qdrant holds 9 instructions / 0 SQL pairs;
* writes `wrenai_mdl/.variant`; the harness refuses to run `wrenai_mdl` while `noreason` is live and vice versa.
* `make wren-mdl-restore` (or `make render`) renders the default variant; the restored `wrenai_mdl/config.yaml` has the same sha256
  (4f09a2c0…) as during the `wrenai_mdl` benchmark run (with the same `.env`).

Verification: in the benchmark run the "SQL Generation Reasoning pipeline is running" line appears 0 times in the wren-ai-service log
(vs 87/87 attempts for `wrenai_mdl`); "Intent Classification pipeline" ran 87/87.

**Per-stage latency** (`bench/stage_latency.py` → `results/stage-latency/stage_latency.md`, `stages.csv`): stage boundaries
come from wren-ai-service's "… pipeline is running" log lines; the end of an ask is not logged, it is seen at wren-ui's last
`GET /v1/asks/<id>/result` poll. For the no-reasoning run llm-meter also recorded per-request timing (`GET /meter/events`,
saved as `results/stage-latency/wrenai_mdl_noreason.meter-events.json`), which measures the gap between the last LLM call ending
and the poll that picks the result up. Raw logs are saved next to it.

## Metrics
* **EX exact**: result multiset equals gold (column order free; numbers rounded to 2 dp; dates normalised; row order checked only for `order_matters` questions, on the sort key so ties don't count). **EX relaxed**: additionally allows extra columns.
* **Latency**: wall-clock of the API call (p50/p95 over all questions × repeats). WrenAI's `generate_sql` returns SQL only; DB-GPT's chat_data also executes the SQL inside DB-GPT; Cube adapter = LLM call + Cube execution.
* **Tokens**: prompt/completion per question from llm-meter (embedding tokens separately). Background LLM work a tool does between questions is attributed to the next question.
* Status per attempt: `correct`, `correct_extra_cols`, `wrong_result`, `exec_error`, `tool_error`, `unsupported` (Cube adapter declined).

## Cube v2 (`cube_v2`): rich model + SQL API adapter

**Why the SQL API (not REST, not hybrid).** A REST `/v1/load` query is one aggregation shape (measures × dimensions +
filters), so comparisons against an aggregate of aggregates, per-group top-N, LAG, anti-joins / set differences and
share-of-total over arbitrary groupings cannot be expressed in a single query (the baseline's 15 `unsupported`).
Cube's SQL API (enabled with `CUBEJS_PG_SQL_PORT=15432`; query push-down is on by default since 1.0 and set explicitly,
`CUBESQL_SQL_PUSH_DOWN=true`) turns each `SELECT … FROM <view>` into a Cube query and runs window functions,
subqueries, EXCEPT etc. as post-processing / push-down — still compiled and executed by Cube against Postgres. Every
REST query shape is also expressible as an SQL API query, so a REST fallback would add a second prompt format without
adding coverage; v2 therefore uses the SQL API only. Cube stays at **v1.8.8** (the latest release on Docker Hub on
2026-10-19; no upgrade needed or possible). Tesseract (needed for multi-stage measures) is on by default in 1.8.8
(`CUBEJS_TESSERACT_SQL_PLANNER=true`, also set explicitly).

**Data model** (`cube_v2/model/`, the baseline model `cube/model/` is untouched):
* 13 cubes (`cubes/catalog.yml`, `cubes/sales.yml`) with descriptions on cubes and members: artist, album, genre, media_type,
  track, playlist, playlist_track, employee, `manager` and `support_rep` (both `extends: employee`), customer, invoice, invoice_line.
* Joins: many_to_one along every FK (album→artist, track→album/genre/media_type, playlist_track→playlist/track,
  invoice_line→invoice/track, invoice→customer, customer→support_rep, employee→manager) plus one_to_many where a
  rollup needs it (artist→album, track→invoice_line, customer→invoice). Cube joins are LEFT JOINs; the employees view
  description says the top manager has NULL manager fields.
* Subquery dimensions (`sub_query: true`): `track.units_sold` (COALESCE(units sold, 0)), `customer.lifetime_spend`,
  `customer.invoice_count`, `customer.first_purchase_date`, `customer.last_purchase_date`.
* Derived dimension: `track.duration_minutes` (= milliseconds / 60000.0).
* Measures: count on every cube; track total/avg duration, max/min/avg list price, distinct genres / albums;
  playlist_track count + distinct tracks; customer avg lifetime spend; invoice total_sales, avg invoice total,
  purchasing customers, first/last invoice date; invoice_line revenue (unit_price × quantity), quantity_sold, line count.
* Rolling windows: `invoice.total_sales_running_total` (trailing unbounded), `total_sales_year_to_date` (to_date year),
  `total_sales_trailing_3_months`.
* Multi-stage measures (Tesseract): `invoice.total_sales_prior_month` and `total_sales_prior_year` (time_shift, prior),
  `invoice_line.revenue_share_of_total_pct` (= 100 × revenue / grand total via a hidden helper with `grain: {keep_only: []}`).
  A generic multi-stage `rank` measure was tried and dropped: without naming the dimension to rank over
  (`grain.exclude`), it returned 1 for every row.
* Segments: `track.is_video`, `employee.has_manager`, `customer.is_business`.
* Views (`views/business.yml`) = the business entities the LLM sees: `sales` (line level, with invoice, customer, support
  rep, track, album, artist, genre, media type), `invoices`, `customers`, `tracks`, `albums`, `artists`, `genres`,
  `media_types`, `playlists`, `employees` (with manager). Members from joined cubes get explicit aliases (`artist_name`,
  `support_rep_first_name`, `manager_id`, …).

**Adapter v2 prompt** (`CUBE_V2_SYSTEM` in `bench/clients.py`; the LLM also gets every view's dimensions, measures
and segments with their types and descriptions from `/v1/meta`). It returns `{"sql": …}` or `{"unsupported": …}`.
Rules, in short:
1. Query only the listed views; one view per SELECT, no joins between views.
2. Wrap measures in MEASURE().
3. Selected dimensions go in GROUP BY; a dimensions-only SELECT without GROUP BY is ungrouped.
4. Cube drops GROUP BY keys that are not selected. For one row per entity, select the id in an inner query and only
   the requested columns in an outer query.
5. Window functions, CASE, EXCEPT and similar go in an outer query over a view subquery; no correlated subqueries.
6. Filter measures in an outer WHERE.
7. Use half-open date ranges and DATE_TRUNC grouping, with EXTRACT in an outer query when a number is asked for;
   rolling and prior-period measures need DATE_TRUNC.
8. Return only the requested columns.
9. No LIMIT unless a number is asked for; top-N → ORDER BY … LIMIT N; ties only when asked.
10. View joins are LEFT JOINs.
11. Anti-joins: use EXCEPT or NOT IN.

Rules 4, 5 and 11 come from testing Cube 1.8.8 directly:
* `SELECT name … GROUP BY track_id, name` returned 207 rows, not 212.
* A window function written directly over a view, or a correlated subquery, fails with "Can't detect Cube query".
* **`NOT EXISTS` is planned as `EXISTS`.** `EXPLAIN` shows `Subquery: types=[Exists]` with the NOT dropped, and
  `LEFT JOIN … IS NULL` returns 0. Both give wrong results silently, while `EXCEPT` and `NOT IN` are correct.

**Leakage check.** No member, view, segment or prompt rule is named after a benchmark question, and no question
or gold SQL is in the prompt. `bench/cube_v2_reference_sql.yaml` is used only by `make verify` and `--mock`.
These generic elements line up with what particular questions need (they are what a Chinook modeller would add,
but the author had seen the question set):
* `track.units_sold` and rule 11 → h07, h09
* `customer.lifetime_spend` → h03, h04
* `total_sales_prior_month` → h05
* `revenue_share_of_total_pct` → h11
* `total_sales_year_to_date` → h10
* `duration_minutes` → e04, m05
* `has_manager` / LEFT JOIN rule 10 → h08
* `is_business` → e08
* `distinct_genres` → h06
* rule 4 → e04
* rules 8 and 9 → e07, m07, h10, e04

**Expressibility.** `make verify` runs `bench/verify_cube_v2.py`, which executes the hand-written SQL API query for
every question through cube_v2 and compares it with gold: 29/29 reproduce gold. The baseline REST model covers
23/29 (h03, h04, h05, h07, h09 and h11 are not expressible as one REST query). One caveat: the prior-month measure
uses true calendar shifting, so for January 2024 it returns December 2023's revenue rather than NULL, unlike a LAG
within 2024.

## Router (`router`): cube_v2 first, WrenAI semantic no-reasoning fallback

**Idea.** Send every question to the cube_v2 path first (same Cube 1.8.8 model + SQL API as `cube_v2`, but a **prompt copy**
`CUBE_V2_ROUTER_SYSTEM` that may reply `{"unsupported": "CANNOT_EXPRESS: …"}`). Fall back to WrenAI + semantic layer with
reasoning off (`wrenai_mdl_noreason`, `make wren-mdl-noreason`) when the sentinel comes back, when Cube returns an error, or
when Cube returns an empty result. **Gold answers are never used for routing.** Latency and llm-meter tokens count both
paths when fallback fires (Cube under `/router/`, Wren under `/wrenmdlnr/`).

**What this run measured** (`results/run-gptoss120b-router-r3/`, 29 q × 3): EX exact **86/87 (99%)**, EX relaxed 86/87,
p50 **2.09 s** / p95 **4.49 s**, avg prompt tokens ~3106, avg LLM calls ~1.0. **Fallback rate 0/87** — with this model and
prompt the LLM never declined, and Cube never errored or returned empty on these questions, so every attempt stayed on the
Cube path. The one miss is a **silent-wrong**: `h10` run 2 (Cube returned non-empty wrong month labels via `EXTRACT(MONTH)`;
no empty/error/sentinel, so no fallback). Same accuracy band as `wrenai_mdl_noreason` (86/87) at roughly cube_v2 latency.

**Caveat (same as cube_v2 / Wren semantic layer).** Both the cube_v2 model and the WrenAI semantic layer were authored after
seeing the question set. The router inherits that leakage; it does not invent a third model. A router only helps when Cube
declines or fails loudly — silent wrongs (valid-looking wrong rows) still pass through.


## mnemiq (`mnemiq`, `mnemiq_failopen`, `mnemiq_verified`, `mnemiq_jev`)

[agenticfabriq/mnemiq](https://github.com/agenticfabriq/mnemiq) (Apache-2.0) has no releases or tags. It is pinned to
commit `a453b05` (main, 2026-10-19; see `VERSIONS.md`) and runs as a host Python service (`uv sync --extra server`,
`mnemiq serve --http`). It has no docker image for the engine; its compose file only starts a demo Postgres.

**Configuration** (`mnemiq/run.sh`, all values from `.env`, never echoed): the source is the same Postgres Chinook as
the read-only `bench` user. Chat goes to `gpt-oss:120b` and embeddings to the local `nomic-embed-text`, both through
llm-meter `/mnemiq/` (so tokens and calls are counted). `MNEMIQ_LLM_CONTEXT_WINDOW=128000` is the same window WrenAI is
told about; Ollama Cloud doesn't report it, and mnemiq uses it only for its window/trim checks. Everything else is the
engine default: mode `thinking`, `retrieval_k` 24, verifier threshold 0.5, judge on, fail-closed. Enrichment is the
default tier (no facts or examples, no glossary or dictionary). Deep mode's 5-candidate vote was not used, because it
isn't the default.

Two setup facts, neither tuned to the questions:
* **Access policy.** mnemiq requires one and ships no default. `mnemiq/authz.json` grants the 11 tables *and*
  `pii_clearance: [pii, phi]`, mirroring what the Postgres `bench` role can read. With a plain table list, mnemiq's
  enrichment tags person-name and contact columns as `pii` and hides them. A smoke test then declined m02 with
  "the artist table lacks a name column".
* **DuckDB extensions.** DuckDB's `INSTALL` downloads over plain `http://`, which this box blocks, so they were
  pre-seeded with mnemiq's own `mnemiq extensions fetch` (HTTPS, signature-checked on load). mnemiq executes through
  DuckDB's Postgres scanner. The harness scores mnemiq's own returned rows. When the preview is cut at 100 rows (e04,
  ho12), it re-executes the returned SQL read-only on Postgres instead.

**Model compatibility problem (the main finding).** mnemiq's LLM judge asks for `max_tokens=200` and only reserves extra
budget for reasoning models whose name matches `gpt-5`. gpt-oss:120b is also a reasoning model. On most real judge
prompts it spends all 200 tokens reasoning and returns empty content (`finish_reason=length`; reproduced with mnemiq's
own `SemanticJudge`). The fail-closed verifier then withholds the answer as `verifier_unavailable`. So the
out-of-the-box result measures this incompatibility more than SQL quality. Two labelled variants each change one
thing:

* `mnemiq` — defaults. `verifier_unavailable` is scored `tool_error`.
* `mnemiq_failopen` — identical (same pinned engine, copied store, same policy), plus `MNEMIQ_VERIFY_FAIL_CLOSED=0`:
  an unreadable judge returns the answer unchecked. Port 8091, meter `/mnemiqfo/`. Only 22/87 (main) and 5/45
  (holdout) of its answers were actually judged; the rest shipped with `verified: unavailable`.
* `mnemiq_verified` — identical to the defaults (**fail-closed ON**, mode `thinking`, same policy, same 128000 window,
  copied store), except the judge call's output budget is **1200 tokens** instead of 200. mnemiq has no knob for this
  (`SemanticJudge(judge_client)` is built with its hard-coded `max_tokens=200`; the `gpt-5` reasoning reserve can't be
  reused without also changing the generator budget and the token parameter name). So
  `mnemiq/patches/verifier-tokens.patch` makes the smallest change: `runtime.py` passes
  `max_tokens=int(MNEMIQ_VERIFY_MAX_TOKENS or 200)` to the judge (unset = upstream behaviour). `judge.py` gets one
  observational log line per judge call (max_tokens, reply length, parsed confidence, question prefix, the SQL it
  judged) and no behaviour change. The patch is applied by `mnemiq/run.sh install-verified` to a separate git worktree
  (`mnemiq/engine-verified`, same commit), so `mnemiq` and `mnemiq_failopen` keep running the unpatched engine.
  Port 8092, meter `/mnemiqv/`, `MNEMIQ_VERIFY_MAX_TOKENS=1200`.

| set | system | EX exact | EX relaxed | p50 s | p95 s | avg prompt tok | avg LLM calls | declined | tool err (verifier_unavailable) |
|---|---|---|---|---|---|---|---|---|---|
| 29 | mnemiq (defaults) | 20/87 (23%) | 20/87 (23%) | 3.26 | 5.27 | 4,863 | 2.3 | 2 | 65 |
| 29 | mnemiq fail-open variant | 87/87 (100%) | 87/87 (100%) | 4.37 | 6.48 | 5,184 | 3.0 | 0 | 0 |
| 15 holdout | mnemiq (defaults) | 5/45 (11%) | 5/45 (11%) | 3.33 | 5.40 | 4,830 | 2.2 | 0 | 40 |
| 15 holdout | mnemiq fail-open variant | 44/45 (98%) | 44/45 (98%) | 4.10 | 7.41 | 5,237 | 3.1 | 0 | 0 |
| 29 | **mnemiq judge 1200 tok (fail-closed)** | 86/87 (99%) | 86/87 (99%) | 4.97 | 7.43 | 5,267 | 3.0 | 1 | 0 |
| 15 holdout | **mnemiq judge 1200 tok (fail-closed)** | 39/45 (87%) | 39/45 (87%) | 5.13 | 9.79 | 5,250 | 3.0 | 4 | 0 |

**What the judge does once it can answer** (`mnemiq_verified`; full table in
`results/run-gptoss120b-mnemiq-r3/verifier_analysis.md`, produced by `bench/mnemiq_verifier_analysis.py`):

* **All 132 judge calls returned a parsed confidence**: 0 empty replies (the `finish_reason=length` signature) and 0
  `verifier_unavailable`. 1200 was enough; nothing higher was needed.
* **29 set:** 86 passed (all EX-exact) and 1 rejected: h05 r1, conf 0.35. Its SQL is **right**: re-executed it is
  EX-exact against gold.
* **Holdout:** 41 passed and 4 rejected.
  * Passed: 39 EX-exact, plus ho14 r2/r3, which are scored `wrong_result` but are valid answers under the ho14 gold
    tie (below).
  * Rejected **genuinely wrong** SQL: ho13 r1 (conf 0.10) and r3 (0.15). Both compute the quarter by division,
    which in DuckDB (mnemiq's executor) is float division, giving 12 fractional and 5 rounded "quarters".
  * Rejected **correct** SQL: ho10 r3 (conf 0.40; EX-exact on re-execution) and ho14 r1 (0.30; valid under the tie).
* **Net:** 2 real mistakes caught and 3 correct answers blocked. **No genuinely wrong answer was passed.** Rejected
  SQL was re-executed through DuckDB over the same Postgres, because mnemiq's SQL can be DuckDB dialect
  (e.g. `EXTRACT(DAYOFWEEK ...)`).
* **Per question vs `mnemiq_failopen`:** the two differ only on h05 (🚫✓✓ vs ✓✓✓), ho10 (✓✓🚫 vs ✓✓✓), ho13 (🚫✓🚫
  vs ✓✓✓) and ho14 (🚫✗✗ vs ✗✓✓). Generation isn't replayed: the hosted model isn't deterministic across runs even at
  temperature 0, so on ho13 the fail-open runs happened to generate correct SQL while two verified runs generated the
  float-division bug.
* **Cost of the check vs fail-open:** p50 +0.60 s (29) / +1.03 s (holdout); prompt tokens +83 / +13 per question;
  the same ~3 LLM calls (generate, judge, answer wording).

* The 2 declines (defaults, e06 and e07 run 3) were judge confidence below 0.5 on answerable questions, so neither was
  a correct decline. Every question in both sets is answerable from Chinook.
* The fail-open variant's one miss, ho14 run 1, is the gold tie below, not the ISO-year (`%G`) filter as first
  reported: re-executed, that SQL returns a valid calendar-2023 top 3.
* **ho14 gold defect (affects all systems).** `ORDER BY revenue DESC LIMIT 3` has a four-way tie for 3rd place
  (weeks 8, 30, 39 and 47, 22.77 each). The gold keeps an arbitrary one (39), so a correct query can be scored
  `wrong_result`, and the tie pick isn't even stable between executions of the same SQL. Re-executed, every ho14
  attempt from WrenAI semantic no-reasoning (×3), DB-GPT (×3) and all mnemiq variants returns a valid top 3 (25, 16,
  then one of the tied weeks). The router/cube_v2 Cube-path attempts were not re-checkable this way. **Scoring was
  left unchanged** so every system is scored identically. No other gold query in either set has a tie at its LIMIT
  boundary (checked).
* LLM calls include enrichment-free per-question work: generation, the judge (when it runs) and the answer-wording call.
  The one-off `enrich` (11 chat calls) and `build` are not counted per question.
* Caveat: mnemiq was added after the question set and both other semantic layers existed. Its own pipeline was not
  tuned to these questions, but its prompts and enrichment were built and tested by its authors on other benchmarks.
  Its access policy and the fail-open switch are our choices and are stated above.

### `mnemiq_jev`: TypeSafe Jev as mnemiq's judge

**Headline: mnemiq out of the box vs mnemiq with Jev as its judge.** Both are fail-closed, mode `thinking`, threshold 0.5,
same policy/window/store, with SQL generated by gpt-oss:120b. Only the judge differs.

| set | system | EX exact | EX relaxed | p50 / p95 s | avg prompt tok (gpt-oss) | avg gpt-oss calls | Jev calls | Jev input tok (total) | est. Jev cost | declined | tool err |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 29 | mnemiq (defaults, gpt-oss judge @200 tok) | 20/87 (23%) | 20/87 (23%) | 3.26 / 5.27 | 4,863 | 2.3 | – | – | – | 2 | 65 |
| 29 | **mnemiq_jev** | **78/87 (90%)** | 78/87 (90%) | 3.41 / 5.15 | 2,848 | 1.9 | 87 | 221,670 | $0.0093 | 9 | 0 |
| 29 | *mnemiq_verified (gpt-oss judge @1200 tok)* | 86/87 (99%) | 86/87 (99%) | 4.97 / 7.43 | 5,267 | 3.0 | – | – | – | 1 | 0 |
| 29 | *mnemiq_failopen (no effective check)* | 87/87 (100%) | 87/87 (100%) | 4.37 / 6.48 | 5,184 | 3.0 | – | – | – | 0 | 0 |
| holdout | mnemiq (defaults) | 5/45 (11%) | 5/45 (11%) | 3.33 / 5.40 | 4,830 | 2.2 | – | – | – | 0 | 40 |
| holdout | **mnemiq_jev** | **39/45 (87%)** | 39/45 (87%) | 3.14 / 4.88 | 2,823 | 1.9 | 45 | 114,523 | $0.0048 | 5 | 0 |
| holdout | *mnemiq_verified* | 39/45 (87%) | 39/45 (87%) | 5.13 / 9.79 | 5,250 | 3.0 | – | – | – | 4 | 0 |
| holdout | *mnemiq_failopen* | 44/45 (98%) | 44/45 (98%) | 4.10 / 7.41 | 5,237 | 3.1 | – | – | – | 0 | 0 |

(mnemiq_verified / mnemiq_failopen are the existing runs, not rerun.) Jev calls go direct to TypeSafe, not through
llm-meter, so the gpt-oss prompt tokens/calls exclude the judge; Jev's input tokens are the API's own
`usage.input_tokens`, read from the per-call log (`results/run-gptoss120b-mnemiq-r3/jev_calls.log`). Cost at
$0.042/M input tokens (output free). Full analysis: `results/run-gptoss120b-mnemiq-r3/jev_analysis.md`.

**Setup.** `mnemiq/patches/jev-judge.patch` (applied by `mnemiq/run.sh install-jev` to a separate worktree
`mnemiq/engine-jev` at the same commit) adds `JevJudge` to `verify/judge.py`. It has SemanticJudge's interface
(`read(question, schema, sql, preview) -> JudgeRead`, `score`, the calls/errors/unparsed counters) and `runtime.py` uses it when
`MNEMIQ_VERIFY_BACKEND=jev`. One request per judge call: `POST https://api.typesafe.ai/v1/systemone`, model
`jev-1.14.0` (the current `jev-preview`; `jev-latest` still points at 1.13), `state = {question, schema, sql, result}`
(the same schema and `render_result(max_rows=5)` preview the gpt-oss judge gets), one `noul` question reusing mnemiq's
own criteria: *"`sql` was run and returned `result`. Does `result` correctly and completely answer `question`, given
`schema`? Check the right tables and joins, every filter the question implies, and the right aggregation and grain. A
plausible-looking number can still be wrong."* Score = the noul probability. An API error gives
`JudgeRead(1.0, fell_open=True, reason="error")` and an unreadable body gives `reason="unparsed"`, so the Verifier's
fail-closed path and 0.5 threshold are unchanged. The key comes from `TYPESAFE_API_KEY` in `.env` and is never logged.
A single smoke request matched the documented shape (`answers.<id> = {type: noul, noul}`, `usage.input_tokens`). In
the run, all 132 calls returned HTTP 200 (no 429s, nothing fell open), at p50 ~170 ms / p95 ~230 ms per call.

**Every Jev decline was a correct answer.** 14 declines (9 on the 29, 5 on the holdout). Each declined SQL was
re-executed the way mnemiq does and checked against gold, and all 14 were right: e02×3, e08×3, m01×2, m06×1, ho10×3,
and ho14×2 (valid under the gold tie). Jev caught no real mistakes in this run, but no genuinely wrong SQL reached it
either (ho13 generated correctly in all three runs). The one `wrong_result` it passed, ho14 r2, is valid under the
tie. Jev's low latency puts mnemiq_jev's p50 1.56 s (29) and 1.99 s (holdout) below mnemiq_verified's.

**Same-SQL comparison (the fair head-to-head).** `results/judge-comparison/` (CSV + md) re-scores, offline and without
rerunning any system, every (question, SQL) the gpt-oss judge scored in mnemiq_verified (132, with its logged
confidence) plus every mnemiq_failopen answer (132). The judge inputs are rebuilt with mnemiq's own code
(`mnemiq/judge_rebuild.py`): `retrieve` + window fitter → `_judge_schema`, the SQL through mnemiq's DuckDB adapter →
`render_result(max_rows=5)`. Correctness is EX-exact vs gold with the harness `compare`, with two documented label
rules. **ho14** answers that are a valid top 3 under the gold tie count as correct. **ho12** answers count as correct
when DuckDB returns the gold rows in binary-collation order and the same SQL is exact on Postgres, which is how the
harness scored them. Result: 262 correct and only 2 wrong items (ho13 r1/r3), so the "wrong" side is tiny and the
AUROCs are not meaningful.

| judge, at threshold 0.5 | items | wrong caught | wrong passed | correct blocked | correct passed |
|---|---|---|---|---|---|
| gpt-oss:120b (logged, mnemiq_verified calls) | 132 | 2 | 0 | 3 | 127 |
| Jev, same 132 calls | 132 | 1 | 1 | 15 | 115 |
| Jev, mnemiq_failopen answers | 132 | 0 | 0 | 14 | 118 |
| Jev, all items | 264 | 1 | 1 | 29 | 233 |

Named cases (gpt-oss conf / Jev noul): h05 r1 correct 0.35 / 0.55, so Jev passes the answer gpt-oss blocked. ho10 r3
correct 0.40 / 0.30: both block. ho13 r1 wrong 0.10 / 0.07: both catch it. ho13 r3 wrong 0.15 / **0.53**: Jev passes
the float-division bug. ho14 r1/r2/r3 (all tie-valid) 0.30/0.21, 0.86/0.82, 0.92/0.30. A threshold sweep is in the md:
no Jev threshold catches both wrong answers without blocking 26+ of the 130 correct ones on the same calls (at 0.6).
**Pattern:** Jev's blocks concentrate on correct multi-row answers whose 5-row preview says `(truncated)`: it blocks 24
of 84 such correct answers vs 5 of 178 with a complete preview (gpt-oss: 2/42 vs 1/88). That is consistent with the
instruction's "completely answer" being read against a cut preview. It is an observation; the instruction was used as
specified and not tuned. Offline comparison cost: 264 Jev calls, 672,721 input tokens, ~$0.028.

### `mnemiq_jev_v2`: truncation-aware Jev request

The original Jev request (v1) blocked 15 correct answers on the same 132 calls where gpt-oss blocked 3, mostly correct
list answers whose 5-row preview said `(truncated)`. I tried three request variants **offline, on the same 264 items**
(no system rerun; `results/judge-comparison/judge_variants.md`). Each is `JevJudge` with `MNEMIQ_JEV_PROMPT=<v>`:

* **a**: `state` gains `result_rows_shown`, `result_total_rows`, `result_preview_truncated` and, when truncated, a note
  *"preview_truncated: true -- judge the correctness of the SQL logic, not the completeness of the preview"*. The noul
  instruction is reworded to ask whether **`sql` correctly answers `question`** (tables, joins, filters, aggregation,
  grain, ordering and limit), "not the completeness of the shown rows". 5-row preview.
* **b**: as a, with a 50-row result sample.
* **c**: as a, with the full result (≤ 250 rows; every item fits, the largest is 212 rows).

| Jev request | same 132 calls: wrong caught / passed | correct blocked | all 264: correct blocked | ho13 r1 / r3 noul | avg input tok |
|---|---|---|---|---|---|
| gpt-oss judge (logged) | 2 / 0 | **3** | – | 0.10 / 0.15 | – |
| v1 original | 1 / 1 | 15 | 29 | 0.07 / 0.53 | 2,548 |
| v1 repeat (noise control) | 1 / 1 | 16 | 30 | 0.06 / 0.59 | 2,548 |
| a | 1 / 1 | 5 | 9 | 0.18 / 0.68 | 2,648 |
| **b (chosen)** | 1 / 1 | 5 | 9 | 0.10 / 0.57 | 2,687 |
| c | 1 / 1 | 5 | 9 | 0.16 / 0.77 | 2,714 |

* **Effect:** the truncation-aware request cuts correct answers blocked by about two thirds (15 → 5 on the same calls,
  29 → 9 on all 264). On truncated previews it falls from 24 to 5 of 84 correct answers.
* **Still worse than gpt-oss:** **Jev still blocks more correct answers than the gpt-oss judge (5 vs 3)** and still
  passes the ho13 r3 float-division bug at 0.5.
* **Remaining blocks:** ho10 ×3 (day-of-week counts) and ho14 ×2 (the tie-affected question).
* **Noise:** identical v1 requests flipped 5 of 264 pass/block decisions, so a, b and c are tied within Jev's own noise.
* **Why b:** it gives the lowest score to the wrong ho13 r3 (0.57) and separates best. Its best threshold (0.62)
  catches both wrong items while blocking 10 correct of 264, against 18 for a and 57 for c.
* **Threshold:** the shipped threshold stays **0.5**. 0.62 is fitted to 2 wrong items, and the threshold is mnemiq's
  shared Verifier setting, so it was not adopted.

`b` is now the patch default. `v1` stays reachable with `MNEMIQ_JEV_PROMPT=v1`, and `make bench-mnemiq-jev` pins it so
the first run stays reproducible. The patch also gains a one-line Verifier change: it renders
`max_rows=getattr(judge, "preview_rows", 5)`, so the gpt-oss judge still gets 5 rows.

**Rerun (only this system).** `mnemiq_jev_v2` uses :8094, `/mnemiqj2/`, `MNEMIQ_JEV_PROMPT=b`, and is otherwise identical
to `mnemiq_jev`. The old `mnemiq_jev` run stays on disk.

| set | system | EX exact (= relaxed) | p50 / p95 s | declined (SQL right / wrong) | timeouts | Jev calls / input tok / est. cost |
|---|---|---|---|---|---|---|
| 29 | mnemiq_verified (gpt-oss judge) | 86/87 (99%) | 4.97 / 7.43 | 1 (1 / 0) | 0 | – |
| 29 | mnemiq_jev (v1) | 78/87 (90%) | 3.41 / 5.15 | 9 (9 / 0) | 0 | 87 / 221,670 / $0.0093 |
| 29 | **mnemiq_jev_v2 (b)** | **85/87 (98%)** | 8.04 / 22.11* | **0** | 2* | 87 / 234,385 / $0.0098 |
| 29 | **mnemiq_jev_v2 rerun r2** | **86/87 (99%)** | 3.42 / 8.50 | 0 (1 `invalid_query` deferral, h11 r1, no Jev call) | 0 | 87 / 234,544 / $0.0099 |
| holdout | mnemiq_verified | 39/45 (87%) | 5.13 / 9.79 | 4 (2 / 2) | 0 | – |
| holdout | mnemiq_jev (v1) | 39/45 (87%) | 3.14 / 4.88 | 5 (5 / 0) | 0 | 45 / 114,523 / $0.0048 |
| holdout | **mnemiq_jev_v2 (b)** | 39/45 (87%) | 4.24 / 9.16* | 6 (**5 / 1**) | 0 | 45 / 119,872 / $0.0050 |
| holdout | **mnemiq_jev_v2 rerun r2** | 38/45 (84%); 39/45 with the ho14 tie rule | 2.57 / 4.35 | 6 (**5 / 1**) | 0 | 44 / 117,091 / $0.0049 |

\* **Latency is not comparable across these runs.** Over llm-meter's per-request timing, gpt-oss chat calls had
p50/p95/max 1.61/2.95/4.4 s during mnemiq_verified and 1.41/2.74/3.9 s during mnemiq_jev, but **2.37/11.21/193.5 s**
during mnemiq_jev_v2 (11:35–11:58 IST). Jev's own calls stayed at p50 ~155 ms. The 29-set's two misses are those
gpt-oss stalls: h04 r2 and h11 r3 timed out at 180 s. Neither was a decline.

* **No declines on the 29 set:** e02/e08/m01/m06, all blocked by v1, now pass.
* **Holdout declines:** 6. Five had correct SQL: ho10 ×3 (exact) and ho14 ×2 (tie-valid / exact).
* **First real catch:** ho12 r3, noul 0.40. Its `LEFT JOIN … WHERE il.track_id IS NULL` returns artists with *any*
  unsold track (241 rows, 131 extra) instead of artists with *no* sales (gold 110). That is a genuine mistake, and
  mnemiq_verified and mnemiq_failopen happened not to generate it in that attempt.
* **Wrong answers passed:** none (0 `wrong_result`).
* **Bottom line:** v2 matches or beats mnemiq_verified on accuracy (85/87 + 39/45 vs 86/87 + 39/45) at about half the
  gpt-oss prompt tokens. But on the same-SQL comparison, which is the fair one, **Jev still blocks more correct answers
  than gpt-oss (5 vs 3 of 130)**.
* **Per-attempt analysis:** `results/run-gptoss120b-mnemiq-r3/jev_v2_analysis.md`; Jev log lines in `jev2_calls.log`.

**Fresh rerun (`mnemiq_jev_v2` rerun r2).** Same configuration (variant b, threshold 0.5), with new result dirs
`results/run-gptoss120b-mnemiq-jev-v2-r2/` and `results/run-gptoss120b-holdout-jev-v2-r2/`. I reran it because the
previous v2 latency was contaminated by Ollama Cloud.

* **Upstream latency was healthy:** probes before the start gave p50 0.93 s. During the run, gpt-oss chat calls had
  p50/p95/max **1.45/4.07/11.2 s** on the 29 and **1.23/2.21/3.6 s** on the holdout. There were no timeouts.
* **Jev:** 131 calls, all HTTP 200, p50/p95 154/198 ms (29) and 168/248 ms (holdout), $0.0148 in total.
* **Holdout declines (6):** ho10 ×3 (exact) and ho14 r2/r3 (tie-valid) had correct SQL. ho12 r1 (noul 0.48) was wrong:
  the same "any unsold track" bug (241 rows vs gold 110), so it was caught again.
* **One wrong-scored answer passed:** ho14 r1 (noul 0.87) is tie-valid, so it is right under the tie rule.
* **29 set:** the only miss is h11 r1, an `invalid_query` deferral. gpt-oss's SQL was rejected 3 times, so Jev was never
  called.
* **Repeatability:** the 5-correct-blocked / 1-caught pattern matches the previous v2 run exactly.
* **Latency:** with a healthy upstream, v2 runs at p50 3.42 s (29) / 2.57 s (holdout), versus 4.97 / 5.13 s for
  mnemiq_verified (whose runs also had healthy upstream: 1.61 s p50).
* Details: `results/run-gptoss120b-mnemiq-jev-v2-r2/jev_v2_analysis.md`.

## Vanna (`vanna`): classic `generate_sql`, DDL-trained

**Version and path.** I pinned the latest PyPI release, **vanna 2.0.2** (`vanna[chromadb,openai,postgres]==2.0.2`,
chromadb 1.5.9, openai 3.35.1; `vanna/requirements.txt`).

* **Why the classic path:** 2.x's headline API is the Agent framework (`Agent` + `ToolRegistry` + `RunSqlTool`). There
  the LLM *executes* SQL as a tool call and streams UI components, and it has no DDL-training step. The 2.0.2 wheel
  still ships the classic API under **`vanna.legacy`**; the README's migration notes keep it usable via
  `LegacyVannaAdapter`. I used that path because it is Vanna's NL→SQL flow that only returns SQL:
  `ChromaDB_VectorStore` + `OpenAI_Chat` → `vn.train(ddl=…)` → `vn.generate_sql(question)`.
* **How it is served:** a ~90-line stdlib HTTP wrapper (`vanna/server.py`, :8095). It returns Vanna's SQL plus, for
  analysis only, the raw LLM text and the retrieved tables.

**Configuration.**

* **LLM:** gpt-oss:120b on Ollama Cloud via llm-meter `/vanna/v1`, temperature 0 (Vanna's default is 0.7).
* **Embeddings:** Chroma's OpenAI-compatible embedding function → meter `/vanna/v1` → local ollama **nomic-embed-text**
  (instead of Chroma's bundled all-MiniLM-L6-v2).
* **Vector store:** Vanna's default local Chroma (persistent, `vanna/state/chroma`, git-ignored).
* **Vanna defaults kept:**
  * `n_results=10` per collection, so each prompt carries the 10 of 11 DDLs nearest the question;
  * Vanna's own system prompt;
  * `allow_llm_to_see_data=False`. An `intermediate_sql` reply would come back as Vanna's refusal text, which then fails
    at execution. This never happened.
* **No retries:** there is no retry or self-correction loop. The classic `generate_sql` has none: one LLM call per
  question (measured: exactly 1 on all 132 attempts).
* **Database access:** connects as the read-only `bench` role (sets the PostgreSQL dialect). Vanna never runs the SQL;
  the harness executes it as for every system.

**Training material.** Only `vanna/training/ddl.sql`: 11 `CREATE TABLE` statements built by `vanna/build_ddl.py`
through the read-only role.

* **Contents:** columns, types and NOT NULL from information_schema, plus the 22 PK/FK constraints from `pg_constraint`
  (information_schema hides constraints from a SELECT-only role).
* **No documentation:** the database has no table or column comments, so there was no generic schema description to
  add.
* **No leakage:** no benchmark questions and no gold SQL were trained. The question-SQL collection is empty, and
  `generate_sql` does not auto-train.

**Results** (`results/run-gptoss120b-vanna-r3/` for the 29; the holdout was appended to `results/run-gptoss120b-holdout-r3/` with `--resume`; 3 runs each):

| set | EX exact | EX relaxed | p50 / p95 s | avg prompt tok | LLM calls / q |
|---|---|---|---|---|---|
| 29 | 84/87 (97%) | 84/87 (97%) | 1.57 / 2.80 | 969 | 1.0 |
| holdout | 42/45 (93%); **45/45 with the ho14 tie rule** | 42/45 (93%) | 1.45 / 2.76 | 975 | 1.0 |

Upstream was healthy throughout. Probes before the start gave p50 0.98 s. During the run, gpt-oss chat calls had
p50/p95/max 1.41/2.61/3.5 s (29) and 1.32/2.16/2.9 s (holdout), with no timeouts.

**Misses and root causes** (each re-executed against gold):

* **h02 r1, r3** (`wrong_result`): `employee LEFT JOIN customer LEFT JOIN invoice` with `COALESCE(SUM, 0)` returns all
  8 employees, 5 of them with total 0, instead of the 3 support agents. The question says "each sales support agent".
  This is a real semantic error.
* **h03 r1** (`exec_error`): **a Vanna `extract_sql` bug, not a model error.** gpt-oss returned a correct fenced query
  (re-executed: exact against gold, 22 rows). Vanna's extraction regex keeps the *last* `SELECT … ;` match, here the
  inner `SELECT AVG(...) FROM (...) sub );` fragment, so the SQL fails to parse.
* **ho14 r1–r3** (`wrong_result`): a scoring artefact. All three return weeks 25 and 16 and then week 8. Week 8 is one
  of the four weeks tied at 22.77 on the gold's `LIMIT 3` boundary, so the answer is valid under the tie rule. Vanna
  also filtered `EXTRACT(isoyear …) = 2023`, arguably closer to "ISO week numbers of 2023" than the gold's
  calendar-year filter, and that gives the same top 3 here.

**Against existing results** (already on disk, nothing rerun):

| system | 29 EX exact | holdout EX exact (tie-adjusted) | p50 s (29 / holdout) | avg prompt tok (29) | LLM calls / q |
|---|---|---|---|---|---|
| **Vanna 2.0.2** | 84/87 (97%) | 42/45 (**45/45**) | **1.57 / 1.45** | **969** | 1.0 |
| WrenAI + semantic layer, no reasoning | 86/87 (99%) | 42/45 (45/45) | 4.05 / 4.06 | 20,941 | 2.0 |
| DB-GPT 0.8.2 | 81/87 (93%) | 39/45 (42/45; ho12 ×3 wrong as recorded) | 1.95 / 2.61 | 1,684 | 1.0 |
| mnemiq_jev_v2 rerun r2 | 86/87 (99%) | 38/45 (39/45; 6 Jev declines) | 3.42 / 2.57 | 3,012 | 2.0 (+1 Jev) |

**Read-out.**

* **Accuracy and cost:** with nothing but DDL, Vanna is within 2 attempts of WrenAI's tuned semantic layer on the 29.
  It ties WrenAI on the holdout, at ~1/20 of the prompt tokens and ~⅓ of the latency.
* **Its misses:** one recurring join-semantics error (h02) and one post-processing bug (h03 r1).
* **Caveat:** the 29 were the tuning set for WrenAI's semantic layer and cube_v2, not for Vanna or DB-GPT. On the
  holdout, which none of the systems were tuned on, WrenAI and Vanna are level.

## Vanna + TypeSafe Jev answer check (`vanna_jev`, `vanna_jev_retry`)

**Setup.** Generation is the unchanged Vanna 2.0.2 service: same `generate_sql`, model, temperature, prompt, DDL
training and retrieval. Each Jev variant has its own meter prefix (`/vannaj/`, `/vannajr/`) and a byte copy of the
trained Chroma store. After generation, `vanna/server.py` (`VANNA_JEV=on|retry`) does the following:

1. **Execute:** runs the SQL as the read-only `bench` role (READ ONLY transaction, 30 s statement timeout). SQL that
   fails to execute is **returned unjudged** and scored as usual.
2. **Ask Jev:** sends **mnemiq_jev_v2's variant-b request** to Jev jev-1.14.0: question, schema, SQL, a 50-row result
   sample with row counts and the truncation note, and the reworded "does `sql` correctly answer `question`" noul.
   * The schema is the DDL statements Vanna retrieved for this question.
   * The request lives in `bench/jev_judge.py`, a stdlib copy of the patch's variant b.
     `bench/jev_judge_parity.py` checks that its preview and request body are byte-identical to the mnemiq
     `JevJudge(b)` output for 0 to 212 rows.
3. **Decide:** p ≥ 0.5 → answer returned. p < 0.5 → **declined** (fail-closed). A Jev API error or an unreadable reply
   → answer returned (fail-open) and logged. `TYPESAFE_API_KEY` is read from `.env` and never logged.
4. **Retry (`vanna_jev_retry` only):** on a decline, **one** more `generate_sql`, with retrieval still keyed on the
   original question. The retry SQL is executed and re-judged; below 0.5 again → declined. The exact question text
   sent on the retry:

   ```
   {question}

   Note: a previous attempt produced the SQL below, and an automated answer check judged that it probably does not answer the question correctly. Re-read the question and the schema and write a corrected SQL query.

   Previous SQL:
   {previous SQL}
   ```

**Results** (3 runs each; 29 in `results/run-gptoss120b-vanna-r3/`, holdout in `results/run-gptoss120b-holdout-r3/`).

* **Upstream was healthy:** probes before the start gave p50 0.99 s. During the runs, gpt-oss per-call p50/p95 was
  1.24–1.41 s / 1.99–2.61 s, max 3.9 s, with no timeouts.
* **Jev:** 264 calls, all HTTP 200, none fell open.

| set | system | EX exact | tie rule | p50 / p95 s | avg prompt tok | LLM / Jev calls per q | declined | Jev input tok / cost | Jev p50/p95 ms |
|---|---|---|---|---|---|---|---|---|---|
| 29 | vanna | 84/87 (97%) | 84/87 | 1.57 / 2.80 | 969 | 1.0 / – | – | – | – |
| 29 | vanna_jev | 86/87 (99%) | 86/87 | 1.70 / 2.97 | 969 | 1.0 / 1.0 | **0** | 118,984 / $0.0050 | 150 / 187 |
| 29 | vanna_jev_retry | 87/87 (100%) | 87/87 | 1.60 / 2.31 | 969 | 1.0 / 1.0 | **0** (0 retries) | 118,916 / $0.0050 | 149 / 211 |
| holdout | vanna | 42/45 (93%) | 45/45 | 1.45 / 2.76 | 975 | 1.0 / – | – | – | – |
| holdout | vanna_jev | 42/45 (93%) | 45/45 | 1.51 / 3.03 | 975 | 1.0 / 1.0 | **0** | 60,355 / $0.0025 | 151 / 206 |
| holdout | vanna_jev_retry | 42/45 (93%) | 45/45 | 1.64 / 2.56 | 975 | 1.0 / 1.0 | **0** (0 retries) | 60,289 / $0.0025 | 158 / 204 |

**Jev declined nothing, so the retry never fired.** Both systems returned exactly what Vanna generated.

* **The 29-set gains are not Jev's:** 86/87 and 87/87 vs plain Vanna's 84/87 come from gpt-oss run-to-run variation.
  h03's `extract_sql` truncation and h02's outer join simply didn't recur, apart from vanna_jev h02 r2.
* **Misses:**
  * **h02 r2 (vanna_jev):** genuinely wrong (the LEFT JOIN includes non-agents), and Jev passed it at 0.84.
  * **ho14 ×3 in each system:** valid under the tie rule, and Jev passed them, but only at **0.51–0.57**, just above
    the threshold.
* **Cost and latency:** the check adds ~0.1 s (Jev p50 ~150 ms plus execution) and ~1,370 Jev input tokens per
  question (about $0.00006).

**Offline same-SQL view** (`make vanna-jev-offline` → `jev_offline.jsonl`). This is Jev variant b on plain `vanna`'s
132 saved SQLs, each with its own retrieved schema: 131 judged, all HTTP 200.

| set | right passed | right blocked | wrong caught | wrong passed | not judged (exec error) |
|---|---|---|---|---|---|
| 29 | 84 | 0 | 0 | 2 | 1 |
| holdout | 45 | 0 | 0 | 0 | 0 |

Of plain Vanna's known misses, the Jev check would have caught **none**:

* **h02 r1 / r3:** genuinely wrong, but passed at 0.81 / 0.84.
* **h03 r1:** fails to execute, so it is never judged. Its defect is Vanna's SQL extraction, which only an
  execution-error retry could fix.
* **ho14 ×3:** right under the tie rule, and correctly passed (0.51–0.56).

It also blocked **0 of 129** right answers.

**Bottom line.** On Vanna's output, Jev at 0.5 is a no-op in both directions here.

* It never blocks a right answer, unlike mnemiq_jev_v2's 5 per 45 holdout attempts. Vanna's SQL is simple and its
  previews short.
* It also never catches the one recurring real error (h02), which Jev scores as plausible.
* Per-attempt details: `results/run-gptoss120b-vanna-r3/vanna_jev_analysis.md`.

## Held-out evaluation (`questions_holdout.yaml`)

The original 29 questions were the tuning set for `cube_v2` and the WrenAI semantic layer, so the first router run
fell back **0/87** times. To measure routing under distribution shift we added **15 new** Chinook questions in
`bench/questions_holdout.yaml` that are **not** paraphrases of the original set. They deliberately include:

* columns **absent from cube_v2** (`customer.fax`, `customer.phone`, `invoice.billing_address`, `invoice.billing_postal_code`);
* unusual time grains (day-of-week, ISO week, quarter + LAG);
* ranking within groups, artist-level anti-joins, and a video-revenue percentage;
* a few in-model controls (media-type count, track bytes, employee birth dates, playlists).

**Models / prompts / MDL were not edited to fit these questions** — cube_v2 model, `CUBE_V2_ROUTER_SYSTEM`, and the Wren
semantic layer stay exactly as benchmarked on the original 29. Run with `make bench-holdout REPEATS=3` (router/cube_v2/Wren noreason); DB-GPT was added to the same run dir with `--systems dbgpt --resume`.

Results (`results/run-gptoss120b-holdout-r3/`, chart `results/holdout_summary.png`, 15 × 3):

| System | EX exact | EX relaxed | p50 s | p95 s | avg prompt tok | avg LLM calls |
|---|---|---|---|---|---|---|
| Router | 39/45 (87%) | 39/45 (87%) | 3.54 | 7.77 | 11,327 | 1.9 |
| cube_v2 | 25/45 (56%) | 25/45 (56%) | 1.92 | 5.26 | 3,436 | 1.2 |
| WrenAI + semantic, no reasoning | 42/45 (93%) | 42/45 (93%) | 4.06 | 6.89 | 20,811 | 2.0 |
| DB-GPT 0.8.2 | 39/45 (87%) | 39/45 (87%) | 2.61 | 4.32 | 1,693 | 1.0 |
| mnemiq (defaults) | 5/45 (11%) | 5/45 (11%) | 3.33 | 5.40 | 4,830 | 2.2 |
| mnemiq fail-open variant | 44/45 (98%) | 44/45 (98%) | 4.10 | 7.41 | 5,237 | 3.1 |
| mnemiq judge 1200 tok (fail-closed) | 39/45 (87%) | 39/45 (87%) | 5.13 | 9.79 | 5,250 | 3.0 |
| mnemiq, TypeSafe Jev judge (fail-closed) | 39/45 (87%) | 39/45 (87%) | 3.14 | 4.88 | 2,823 (gpt-oss only) | 1.9 (+1 Jev) |
| mnemiq, Jev judge v2 (truncation-aware) | 39/45 (87%) | 39/45 (87%) | 4.24* | 9.16* | 2,929 (gpt-oss only) | 1.9 (+1 Jev) |
| mnemiq, Jev judge v2, rerun r2 | 38/45 (84%) | 38/45 (84%) | 2.57 | 4.35 | 2,804 (gpt-oss only) | 1.9 (+1 Jev) |
| Vanna 2.0.2 (DDL-trained, legacy generate_sql) | 42/45 (93%) | 42/45 (93%) | 1.45 | 2.76 | 975 | 1.0 |
| Vanna 2.0.2 + Jev answer check | 42/45 (93%) | 42/45 (93%) | 1.51 | 3.03 | 975 | 1.0 (+1 Jev) |
| Vanna 2.0.2 + Jev check + 1 retry | 42/45 (93%) | 42/45 (93%) | 1.64 | 2.56 | 975 | 1.0 (+1 Jev; 0 retries) |

Router fallback **17/45 (38%)** — triggers `cube_unsupported`×16, `cube_error`×1. Cube-answered path EX 22/28 (79%);
fallback path EX 17/17 (100%). Silent-wrong (Cube answered, no fallback): `ho12`×3, `ho14`×2, `ho04`×1. No attempt
fell back and then still failed under Wren. cube_v2's mean latency is pulled up by one 180 s timeout on `ho10`.
DB-GPT (unchanged config) matches the router's 87% EX; misses are `ho12` and `ho14` (wrong_result all 3 runs each; no errors/timeouts).
**Caveat (found later): ho14's gold has a tie at its `LIMIT 3` boundary** (see the mnemiq section). DB-GPT's and
WrenAI's ho14 `wrong_result`s re-execute to valid top-3 answers, so their ho14 misses are scoring artefacts. Scores
are left as recorded. Vanna's three misses are all ho14 and all tie-valid too (see the Vanna section); so are vanna_jev's and vanna_jev_retry's.

## Cube notes (baseline `cube`)
Not expressible as a single Cube REST query over the model (counted as failures for Cube, listed in the report):
h03 (compare with average of per-customer totals), h04 (per-country top-N/window), h05 (LAG), h07 (anti-join), h09 (set difference), h11 (share of total).
m07 can only be relaxed-correct in Cube (ordering by a measure requires the measure in the result).

## Box-specific notes
* `ollama pull` fails on this box (the CDN host resolves to a non-public 198.18.x address and Ollama refuses the redirect); `scripts/ollama_import.sh` downloads the registry blobs with curl, verifies sha256 and installs them into the container (`make up` falls back to it automatically).
* DB-GPT re-embeds all datasources at startup; calling its `/refresh` endpoint at the same time races and leaves the chroma collection empty, so `setup_connections.py` only refreshes with `--refresh`.
* No systemd: `make docker` starts `dockerd` by hand. Legacy iptables on this VM had `FORWARD DROP`, which silently blocked container↔container traffic; `make netfix` inserts `ACCEPT` for `br-+` bridges in `DOCKER-USER` (legacy table).
* WrenAI's FK auto-detection reads `information_schema.constraint_column_usage`, which hides constraints from a non-owner role, so `setup_connections.py` reads PK/FK from `pg_catalog` and sets them through Wren's own GraphQL mutations (`updateModel`, `saveRelations`).
* Telemetry: Wren `TELEMETRY_ENABLED=false`, Cube `CUBEJS_TELEMETRY=false`, Langfuse disabled.
