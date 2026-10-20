# nl2sql-bench — WrenAI vs DB-GPT vs Cube(+LLM adapter) on the same Postgres + same LLM
SHELL := /bin/bash
PY    := .venv/bin/python
WREN  := docker compose --project-directory wrenai --env-file wrenai/.env -f wrenai/docker-compose.yaml -f wrenai/docker-compose.override.yaml
WRENMDL := docker compose -p wrenai-mdl --project-directory wrenai_mdl --env-file wrenai_mdl/.env -f wrenai_mdl/docker-compose.yaml -f wrenai_mdl/docker-compose.override.yaml
REPEATS ?= 1
SYSTEMS ?= wrenai,dbgpt,cube
QUESTIONS ?= bench/questions.yaml

.PHONY: wren-mdl wren-mdl-noreason wren-mdl-restore wren-mdl-up report up down clean setup bench mock verify probe status logs venv render docker netfix wait bench-router bench-holdout mnemiq-install mnemiq-up bench-mnemiq mnemiq-failopen-up bench-mnemiq-failopen mnemiq-verified-up bench-mnemiq-verified mnemiq-jev-up bench-mnemiq-jev mnemiq-jev2-up bench-mnemiq-jev2

up: docker netfix venv render          ## start everything and connect all tools to Postgres
	docker compose up -d --build
	@if grep -q '^EMBEDDING_UPSTREAM_BASE=http://ollama' .env; then \
	  m=$$(grep '^EMBEDDING_MODEL=' .env | cut -d= -f2); echo "pulling local embedding model $$m"; \
	  docker compose exec -T ollama ollama list | grep -q "^$$m" \
	  || docker compose exec -T ollama ollama pull $$m >/dev/null 2>&1 \
	  || scripts/ollama_import.sh $$m; fi
	$(WREN) up -d --force-recreate wren-ai-service
	$(WREN) up -d
	$(MAKE) --no-print-directory wait setup

wren-mdl-up: docker netfix venv render ## start the 2nd WrenAI stack (UI :3001, AI :5556) used by system wrenai_mdl
	$(WRENMDL) up -d --force-recreate wren-ai-service
	$(WRENMDL) up -d
	@for u in "http://localhost:5556/health" "http://localhost:3001"; do printf "waiting for %s " $$u; \
	  for i in $$(seq 1 90); do curl -sf -o /dev/null $$u && break; printf .; sleep 2; done; echo " ok"; done

wren-mdl: wren-mdl-up                  ## build + deploy the semantic layer (wrenai_mdl/mdl/semantic_layer.yaml) on the 2nd stack
	cd bench && ../$(PY) wren_mdl.py

# The 2nd stack serves two systems by switching ONE wren-ai-service setting (same project/MDL/instructions):
#   wrenai_mdl          = variant "semantic" (upstream defaults)            -> make wren-mdl-restore
#   wrenai_mdl_noreason = variant "noreason" (allow_sql_generation_reasoning: false) -> make wren-mdl-noreason
wren-mdl-noreason:                     ## switch the 2nd stack to the no-reasoning variant (system wrenai_mdl_noreason)
	$(PY) bench/render_config.py --mdl-variant noreason
	$(MAKE) --no-print-directory _wren-mdl-reload

wren-mdl-restore:                      ## switch the 2nd stack back to the default semantic-layer variant (system wrenai_mdl)
	$(PY) bench/render_config.py --mdl-variant semantic
	$(MAKE) --no-print-directory _wren-mdl-reload

_wren-mdl-reload:
	$(WRENMDL) up -d --force-recreate wren-ai-service
	@printf "waiting for wren-ai-service "; for i in $$(seq 1 90); do curl -sf -o /dev/null http://localhost:5556/health && break; printf .; sleep 2; done; echo " ok"
	cd bench && ../$(PY) wren_mdl.py --redeploy

mnemiq-install:                        ## clone agenticfabriq/mnemiq at the pinned commit (mnemiq/run.sh) + uv sync --extra server
	mnemiq/run.sh install
	@test -n "$$(ls $$HOME/.duckdb/extensions/v*/linux_amd64/postgres_scanner.duckdb_extension 2>/dev/null)" || \
	  (cd mnemiq/engine && .venv/bin/mnemiq extensions fetch --platform linux_amd64 --out /tmp/duckdb-ext && mkdir -p $$HOME/.duckdb/extensions && cp -r /tmp/duckdb-ext/* $$HOME/.duckdb/extensions/)

mnemiq-up:                             ## enrich + build Chinook (once), then serve the HTTP API on :8090 (background)
	@test -f mnemiq/state/chinook.duckdb || { mnemiq/run.sh enrich && mnemiq/run.sh build; }
	@curl -sf -o /dev/null http://localhost:8090/healthz || (setsid nohup mnemiq/run.sh serve > mnemiq/serve.log 2>&1 &)
	@printf "waiting for mnemiq "; for i in $$(seq 1 60); do curl -sf -o /dev/null http://localhost:8090/healthz && break; printf .; sleep 2; done; echo " ok"

bench-mnemiq: mnemiq-up                ## mnemiq x3 on the 29 (results/run-gptoss120b-mnemiq-r3) and the 15 holdout (added to run-gptoss120b-holdout-r3)
	$(PY) bench/harness.py --repeats $(REPEATS) --systems mnemiq --out run-gptoss120b-mnemiq-r3 --resume
	$(PY) bench/harness.py --repeats $(REPEATS) --systems mnemiq --questions bench/questions_holdout.yaml --out run-gptoss120b-holdout-r3 --resume

mnemiq-failopen-up: mnemiq-up          ## variant: same store (copied), MNEMIQ_VERIFY_FAIL_CLOSED=0, :8091, meter /mnemiqfo/
	@test -f mnemiq/state/chinook-failopen.duckdb || cp mnemiq/state/chinook.duckdb mnemiq/state/chinook-failopen.duckdb
	@curl -sf -o /dev/null http://localhost:8091/healthz || (MNEMIQ_VARIANT=failopen setsid nohup mnemiq/run.sh serve > mnemiq/serve-failopen.log 2>&1 &)
	@printf "waiting for mnemiq (failopen) "; for i in $$(seq 1 60); do curl -sf -o /dev/null http://localhost:8091/healthz && break; printf .; sleep 2; done; echo " ok"

bench-mnemiq-failopen: mnemiq-failopen-up  ## variant x3 on the 29 and the 15 holdout (same run dirs, system mnemiq_failopen)
	$(PY) bench/harness.py --repeats $(REPEATS) --systems mnemiq_failopen --out run-gptoss120b-mnemiq-r3 --resume
	$(PY) bench/harness.py --repeats $(REPEATS) --systems mnemiq_failopen --questions bench/questions_holdout.yaml --out run-gptoss120b-holdout-r3 --resume

mnemiq-verified-up: mnemiq-up          ## variant: patched worktree (patches/verifier-tokens.patch), judge max_tokens 1200, fail-closed ON, :8092, /mnemiqv/
	@test -d mnemiq/engine-verified/.venv || mnemiq/run.sh install-verified
	@test -f mnemiq/state/chinook-verified.duckdb || cp mnemiq/state/chinook.duckdb mnemiq/state/chinook-verified.duckdb
	@curl -sf -o /dev/null http://localhost:8092/healthz || (MNEMIQ_VARIANT=verified setsid nohup mnemiq/run.sh serve > mnemiq/serve-verified.log 2>&1 &)
	@printf "waiting for mnemiq (verified) "; for i in $$(seq 1 60); do curl -sf -o /dev/null http://localhost:8092/healthz && break; printf .; sleep 2; done; echo " ok"

bench-mnemiq-verified: mnemiq-verified-up  ## variant x3 on the 29 and the 15 holdout (same run dirs, system mnemiq_verified)
	$(PY) bench/harness.py --repeats $(REPEATS) --systems mnemiq_verified --out run-gptoss120b-mnemiq-r3 --resume
	$(PY) bench/harness.py --repeats $(REPEATS) --systems mnemiq_verified --questions bench/questions_holdout.yaml --out run-gptoss120b-holdout-r3 --resume

report:                                ## combined report (all systems) -> results/combined_summary.md + results/summary.png
	$(PY) bench/combine.py

venv: .venv/.ok
.venv/.ok: requirements.txt
	uv venv -q .venv --python 3.12 && uv pip install -q --python $(PY) -r requirements.txt && touch $@

render: .env                           ## write wrenai/.env + wrenai/config.yaml from .env
	$(PY) bench/render_config.py
.env:
	cp .env.example .env

docker:                                ## start dockerd if not running (box has no systemd)
	@docker info >/dev/null 2>&1 || { sudo sh -c 'nohup dockerd >/var/log/dockerd.log 2>&1 &'; sleep 5; sudo chmod 666 /var/run/docker.sock; }

netfix:                                ## this box has legacy iptables FORWARD=DROP that breaks container<->container traffic
	@if command -v iptables-legacy >/dev/null && sudo iptables-legacy -S FORWARD 2>/dev/null | grep -q -- '-P FORWARD DROP'; then \
	  sudo iptables-legacy -C DOCKER-USER -i br-+ -j ACCEPT 2>/dev/null || sudo iptables-legacy -I DOCKER-USER -i br-+ -j ACCEPT; \
	  sudo iptables-legacy -C DOCKER-USER -o br-+ -j ACCEPT 2>/dev/null || sudo iptables-legacy -I DOCKER-USER -o br-+ -j ACCEPT; \
	  echo "netfix: legacy FORWARD rules ensured"; fi

wait:                                  ## wait until services answer
	@for u in "http://localhost:8089/health" "http://localhost:5555/health" "http://localhost:3000" "http://localhost:5670/api/v2/serve/datasources" "http://localhost:4000/readyz" "http://localhost:4001/readyz"; do \
	  printf "waiting for %s " $$u; for i in $$(seq 1 90); do curl -sf -o /dev/null $$u && break; printf .; sleep 2; done; echo " ok"; done

setup:                                 ## (re)connect WrenAI + DB-GPT to Postgres, redeploy/re-embed schema
	cd bench && ../$(PY) setup_connections.py

verify:                                ## gold SQL runs + Cube reference queries (baseline REST + cube_v2 SQL API) reproduce gold + API probe
	cd bench && ../$(PY) verify_gold.py && ../$(PY) verify_cube_v2.py && ../$(PY) probe.py

probe:
	cd bench && ../$(PY) probe.py

mock:                                  ## dry-run of the harness without an LLM key
	$(PY) bench/harness.py --mock --repeats $(REPEATS) --systems $(SYSTEMS) --questions $(QUESTIONS)

bench:                                 ## real benchmark (needs LLM_API_KEY)
	$(PY) bench/harness.py --repeats $(REPEATS) --systems $(SYSTEMS) --questions $(QUESTIONS)

bench-router: wren-mdl-noreason        ## router = cube_v2 (router prompt) → WrenAI semantic no-reasoning; 3 runs → results/run-gptoss120b-router-r3/
	$(PY) bench/harness.py --repeats $(REPEATS) --systems router --out run-gptoss120b-router-r3

bench-holdout: wren-mdl-noreason       ## held-out 15q: router + cube_v2 + wrenai_mdl_noreason x3 → results/run-gptoss120b-holdout-r3/
	$(PY) bench/harness.py --repeats $(REPEATS) --systems router,cube_v2,wrenai_mdl_noreason --questions bench/questions_holdout.yaml --out run-gptoss120b-holdout-r3

status:
	docker compose ps; $(WREN) ps; -$(WRENMDL) ps

logs:
	docker compose logs --tail 50; $(WREN) logs --tail 50

down:
	-$(WRENMDL) down
	-$(WREN) down
	-docker compose down

clean:                                 ## stop and delete all volumes (DB, both Wren projects, DB-GPT metadata)
	-$(WRENMDL) down -v
	-$(WREN) down -v
	-docker compose down -v

mnemiq-jev-up: mnemiq-up               ## variant: patched worktree (patches/jev-judge.patch), judge = TypeSafe Jev, fail-closed ON, :8093, /mnemiqj/
	@test -d mnemiq/engine-jev/.venv || mnemiq/run.sh install-jev
	@test -f mnemiq/state/chinook-jev.duckdb || cp mnemiq/state/chinook.duckdb mnemiq/state/chinook-jev.duckdb
	@curl -sf -o /dev/null http://localhost:8093/healthz || (MNEMIQ_VARIANT=jev setsid nohup mnemiq/run.sh serve > mnemiq/serve-jev.log 2>&1 &)
	@printf "waiting for mnemiq (jev) "; for i in $$(seq 1 60); do curl -sf -o /dev/null http://localhost:8093/healthz && break; printf .; sleep 2; done; echo " ok"

bench-mnemiq-jev: mnemiq-jev-up        ## variant x3 on the 29 and the 15 holdout (same run dirs, system mnemiq_jev)
	$(PY) bench/harness.py --repeats $(REPEATS) --systems mnemiq_jev --out run-gptoss120b-mnemiq-r3 --resume
	$(PY) bench/harness.py --repeats $(REPEATS) --systems mnemiq_jev --questions bench/questions_holdout.yaml --out run-gptoss120b-holdout-r3 --resume

mnemiq-jev2-up:                        ## variant: as mnemiq-jev but truncation-aware Jev request (MNEMIQ_JEV_PROMPT=b), :8094, /mnemiqj2/
	@test -d mnemiq/engine-jev/.venv || mnemiq/run.sh install-jev
	@test -f mnemiq/state/chinook-jev2.duckdb || cp mnemiq/state/chinook.duckdb mnemiq/state/chinook-jev2.duckdb
	@curl -sf -o /dev/null http://localhost:8094/healthz || (MNEMIQ_VARIANT=jev2 setsid nohup mnemiq/run.sh serve > mnemiq/serve-jev2.log 2>&1 &)
	@printf "waiting for mnemiq (jev2) "; for i in $$(seq 1 60); do curl -sf -o /dev/null http://localhost:8094/healthz && break; printf .; sleep 2; done; echo " ok"

bench-mnemiq-jev2: mnemiq-jev2-up      ## variant x3 on the 29 and the 15 holdout (same run dirs, system mnemiq_jev_v2)
	$(PY) bench/harness.py --repeats $(REPEATS) --systems mnemiq_jev_v2 --out run-gptoss120b-mnemiq-r3 --resume
	$(PY) bench/harness.py --repeats $(REPEATS) --systems mnemiq_jev_v2 --questions bench/questions_holdout.yaml --out run-gptoss120b-holdout-r3 --resume
