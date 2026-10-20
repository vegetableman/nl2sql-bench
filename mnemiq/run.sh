#!/usr/bin/env bash
# mnemiq (agenticfabriq/mnemiq @ MNEMIQ_COMMIT) as benchmarked system `mnemiq`.
# Usage: mnemiq/run.sh {install|enrich|build|serve|ask "q"}
# Out-of-the-box engine settings; only connection/identity/endpoint variables are set here.
# Secrets are read from ../.env and exported, never echoed.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"; ROOT="$(dirname "$HERE")"
MNEMIQ_COMMIT=a453b05129f365c56a66f303b7e1911311d246fd
ENGINE="$HERE/engine"
if [ "${1:-}" = install ]; then
  [ -d "$ENGINE/.git" ] || git clone -q https://github.com/agenticfabriq/mnemiq.git "$ENGINE"
  git -C "$ENGINE" fetch -q origin && git -C "$ENGINE" checkout -q "$MNEMIQ_COMMIT"
  (cd "$ENGINE" && uv sync -q --extra server)
  echo "mnemiq installed at $(git -C "$ENGINE" rev-parse HEAD)"; exit 0
fi
set -a; . "$ROOT/.env"; set +a
# MNEMIQ_VARIANT=failopen: identical except MNEMIQ_VERIFY_FAIL_CLOSED=0 (documented knob: an unreachable/unreadable
# judge returns the answer unchecked instead of withholding it). Own store copy, port 8091, meter prefix /mnemiqfo/.
VARIANT="${MNEMIQ_VARIANT:-default}"
if [ "$VARIANT" = failopen ]; then PREFIX=mnemiqfo; PORT=8091; STORE=chinook-failopen.duckdb; export MNEMIQ_VERIFY_FAIL_CLOSED=0
else PREFIX=mnemiq; PORT=8090; STORE=chinook.duckdb; fi
METER="http://localhost:${METER_PORT:-8089}/$PREFIX/v1"
mkdir -p "$HERE/state"
# source manifest: same Postgres, read-only role `bench` (DSN from .env, file is git-ignored)
python3 - "$HERE/state/sources.json" <<PY
import json, sys
json.dump([{"id": "chinook", "kind": "postgres", "target": "${BENCH_DB_URL}",
            "catalog": "src", "schema": "public"}], open(sys.argv[1], "w"), indent=2)
PY
chmod 600 "$HERE/state/sources.json"
export MNEMIQ_SOURCES_PATH="$HERE/state/sources.json" MNEMIQ_SOURCE_ID=chinook
export MNEMIQ_AUTHZ_PATH="$HERE/authz.json" MNEMIQ_STORE_PATH="$HERE/state/$STORE"
export MNEMIQ_ROLES=bench MNEMIQ_PRINCIPAL=nl2sql-bench
export MNEMIQ_LLM_BASE_URL="$METER" MNEMIQ_LLM_MODEL="${LLM_MODEL:-gpt-oss:120b}"
export MNEMIQ_LLM_API_KEY="${OLLAMA_API_KEY:-${LLM_API_KEY}}"
export MNEMIQ_EMBED_BASE_URL="$METER" MNEMIQ_EMBED_API_KEY=ollama MNEMIQ_EMBED_MODEL="${EMBEDDING_MODEL:-nomic-embed-text}"
export MNEMIQ_LLM_CONTEXT_WINDOW="${LLM_CONTEXT_WINDOW:-128000}"   # Ollama Cloud doesn't report its window
cd "$ENGINE"
case "${1:-}" in
  enrich) exec .venv/bin/mnemiq enrich ;;
  build)  exec .venv/bin/mnemiq build ;;
  serve)  exec .venv/bin/mnemiq serve --http --host 127.0.0.1 --port "$PORT" ;;
  ask)    shift; exec .venv/bin/mnemiq ask "$@" --json ;;
  *) echo "usage: $0 {install|enrich|build|serve|ask q}"; exit 2 ;;
esac
