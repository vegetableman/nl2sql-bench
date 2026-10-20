#!/usr/bin/env bash
# mnemiq (agenticfabriq/mnemiq @ MNEMIQ_COMMIT) as benchmarked system `mnemiq`.
# Usage: mnemiq/run.sh {install|install-verified|install-jev|enrich|build|serve|ask "q"}  (MNEMIQ_VARIANT=default|failopen|verified|jev)
# Out-of-the-box engine settings; only connection/identity/endpoint variables are set here.
# Secrets are read from ../.env and exported, never echoed.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"; ROOT="$(dirname "$HERE")"
MNEMIQ_COMMIT=a453b05129f365c56a66f303b7e1911311d246fd
ENGINE="$HERE/engine"
VERIFIED_ENGINE="$HERE/engine-verified"   # separate worktree, same commit + patches/verifier-tokens.patch
if [ "${1:-}" = install ]; then
  [ -d "$ENGINE/.git" ] || git clone -q https://github.com/agenticfabriq/mnemiq.git "$ENGINE"
  git -C "$ENGINE" fetch -q origin && git -C "$ENGINE" checkout -q "$MNEMIQ_COMMIT"
  (cd "$ENGINE" && uv sync -q --extra server)
  echo "mnemiq installed at $(git -C "$ENGINE" rev-parse HEAD)"; exit 0
fi
JEV_ENGINE="$HERE/engine-jev"   # separate worktree, same commit + patches/jev-judge.patch
if [ "${1:-}" = install-jev ]; then        # mnemiq_jev only; the main and verified engines are not touched
  [ -d "$JEV_ENGINE" ] || git -C "$ENGINE" worktree add -q --detach "$JEV_ENGINE" "$MNEMIQ_COMMIT"
  git -C "$JEV_ENGINE" checkout -q -- . && git -C "$JEV_ENGINE" apply "$HERE/patches/jev-judge.patch"
  (cd "$JEV_ENGINE" && uv sync -q --extra server)
  echo "mnemiq-jev installed at $(git -C "$JEV_ENGINE" rev-parse HEAD) + jev-judge.patch"; exit 0
fi
if [ "${1:-}" = install-verified ]; then   # the ONLY code change of any variant; the main engine stays unpatched
  [ -d "$VERIFIED_ENGINE" ] || git -C "$ENGINE" worktree add -q --detach "$VERIFIED_ENGINE" "$MNEMIQ_COMMIT"
  git -C "$VERIFIED_ENGINE" checkout -q -- . && git -C "$VERIFIED_ENGINE" apply "$HERE/patches/verifier-tokens.patch"
  (cd "$VERIFIED_ENGINE" && uv sync -q --extra server)
  echo "mnemiq-verified installed at $(git -C "$VERIFIED_ENGINE" rev-parse HEAD) + verifier-tokens.patch"; exit 0
fi
set -a; . "$ROOT/.env"; set +a
# MNEMIQ_VARIANT=failopen: identical except MNEMIQ_VERIFY_FAIL_CLOSED=0 (documented knob: an unreachable/unreadable
# judge returns the answer unchecked instead of withholding it). Own store copy, port 8091, meter prefix /mnemiqfo/.
VARIANT="${MNEMIQ_VARIANT:-default}"
if [ "$VARIANT" = failopen ]; then PREFIX=mnemiqfo; PORT=8091; STORE=chinook-failopen.duckdb; export MNEMIQ_VERIFY_FAIL_CLOSED=0
# MNEMIQ_VARIANT=verified: identical to the defaults (fail-closed ON) except the judge call's output budget,
# MNEMIQ_VERIFY_MAX_TOKENS (added by patches/verifier-tokens.patch; unpatched value 200). Port 8092, /mnemiqv/.
elif [ "$VARIANT" = verified ]; then PREFIX=mnemiqv; PORT=8092; STORE=chinook-verified.duckdb; ENGINE="$VERIFIED_ENGINE"
  export MNEMIQ_VERIFY_MAX_TOKENS="${MNEMIQ_VERIFY_MAX_TOKENS:-1200}"
# MNEMIQ_VARIANT=jev: as `verified` (fail-closed ON, thinking, same policy/window/store copy) but the judge is
# TypeSafe Jev (patches/jev-judge.patch, MNEMIQ_VERIFY_BACKEND=jev); judge calls go direct to TypeSafe with
# TYPESAFE_API_KEY from .env (never echoed). SQL generation stays on gpt-oss via the meter. Port 8093, /mnemiqj/.
elif [ "$VARIANT" = jev ]; then PREFIX=mnemiqj; PORT=8093; STORE=chinook-jev.duckdb; ENGINE="$JEV_ENGINE"
  export MNEMIQ_VERIFY_BACKEND=jev MNEMIQ_JEV_MODEL="${MNEMIQ_JEV_MODEL:-jev-1.14.0}" TYPESAFE_API_KEY
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
  py)     shift; exec .venv/bin/python "$@" ;;   # a script in this variant's engine + env (judge comparison)
  *) echo "usage: $0 {install|install-verified|install-jev|enrich|build|serve|ask q|py script}"; exit 2 ;;
esac
