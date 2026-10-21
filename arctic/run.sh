#!/usr/bin/env bash
# Arctic-Text2SQL-R1-7B on the CPU-only `ollama-arctic` container (system `arctic`).
#   arctic/run.sh up        start the container (compose profile `arctic`) + recreate llm-meter only if it lacks /arctic/ routing
#   arctic/run.sh import    a-kore/Arctic-Text2SQL-R1-7B:latest (Q8_0) from registry.ollama.ai (curl import; in-container pull hangs here)
#   arctic/run.sh import-gguf [QUANT]  mradermacher/Arctic-Text2SQL-R1-7B-GGUF <QUANT>.gguf from Hugging Face (default Q4_K_M)
#   arctic/run.sh create    derived model `arctic-text2sql-bench` (arctic/Modelfile.tmpl) FROM $ARCTIC_FROM
#   arctic/run.sh info      versions / digests for VERSIONS.md
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"; cd "$HERE/.."
DC="docker compose --profile arctic"
FROM=${ARCTIC_FROM:-a-kore/Arctic-Text2SQL-R1-7B:latest}
THREADS=${ARCTIC_THREADS:-$(nproc)}
C() { $DC ps -q ollama-arctic; }
case "${1:-}" in
  up)
    $DC up -d ollama-arctic
    curl -sf http://localhost:${METER_PORT:-8089}/health | grep -q '"arctic"' || $DC up -d --no-deps --build llm-meter ;;
  import)
    scripts/ollama_import_ns.sh ollama-arctic a-kore/Arctic-Text2SQL-R1-7B latest ;;
  import-gguf)
    Q=${2:-Q4_K_M}; W=${ARCTIC_DL:-/tmp/arctic-dl}; mkdir -p "$W"; f="$W/Arctic-Text2SQL-R1-7B.$Q.gguf"
    curl -sfL -C - -o "$f" "https://huggingface.co/mradermacher/Arctic-Text2SQL-R1-7B-GGUF/resolve/main/Arctic-Text2SQL-R1-7B.$Q.gguf"
    docker exec "$(C)" mkdir -p /import; docker cp "$f" "$(C):/import/" >/dev/null
    printf 'FROM /import/Arctic-Text2SQL-R1-7B.%s.gguf\n' "$Q" | docker exec -i "$(C)" sh -c "cat > /import/Modelfile && ollama create arctic-r1-7b-$(echo $Q | tr A-Z a-z) -f /import/Modelfile"
    docker exec "$(C)" rm -f "/import/Arctic-Text2SQL-R1-7B.$Q.gguf" ;;
  create)
    sed -e "s#__FROM__#$FROM#" -e "s#__THREADS__#$THREADS#" arctic/Modelfile.tmpl | docker exec -i "$(C)" sh -c 'cat > /tmp/Modelfile && ollama create arctic-text2sql-bench -f /tmp/Modelfile'
    docker exec "$(C)" ollama show arctic-text2sql-bench --modelfile | grep -E '^(FROM|PARAMETER)' ;;
  info)
    docker exec "$(C)" ollama --version; docker exec "$(C)" ollama list
    docker exec "$(C)" ollama show arctic-text2sql-bench ;;
  *) sed -n 2,7p "$0"; exit 2 ;;
esac
