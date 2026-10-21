#!/usr/bin/env bash
# Like scripts/ollama_import.sh, but for any registry namespace and any compose service:
#   scripts/ollama_import_ns.sh <compose-service> <namespace/model> [tag]
# e.g. scripts/ollama_import_ns.sh ollama-arctic a-kore/Arctic-Text2SQL-R1-7B latest
# Downloads the manifest + blobs from registry.ollama.ai with curl on the host (in-container `ollama pull` hangs on
# this box's resolver), verifies each sha256, copies them into the container's model store.
set -euo pipefail
SVC=$1; MODEL=$2; TAG=${3:-latest}
C=$(docker compose --profile arctic ps -q "$SVC")
W=${OLLAMA_IMPORT_TMP:-$(mktemp -d)}; mkdir -p "$W"
curl -sf -H "Accept: application/vnd.docker.distribution.manifest.v2+json" \
  "https://registry.ollama.ai/v2/$MODEL/manifests/$TAG" -o "$W/manifest"
docker exec "$C" mkdir -p /root/.ollama/models/blobs "/root/.ollama/models/manifests/registry.ollama.ai/$MODEL"
for d in $(python3 -c "import json;m=json.load(open('$W/manifest'));print(' '.join([m['config']['digest']]+[l['digest'] for l in m['layers']]))"); do
  f="$W/${d/:/-}"
  if [ ! -f "$f" ] || [ "$(sha256sum "$f" | cut -c1-64)" != "${d#sha256:}" ]; then
    curl -sfL -C - -o "$f" "https://registry.ollama.ai/v2/$MODEL/blobs/$d" || curl -sfL -o "$f" "https://registry.ollama.ai/v2/$MODEL/blobs/$d"
  fi
  [ "$(sha256sum "$f" | cut -c1-64)" = "${d#sha256:}" ] || { echo "checksum mismatch $d"; exit 1; }
  docker cp "$f" "$C:/root/.ollama/models/blobs/${d/:/-}" >/dev/null
done
docker cp "$W/manifest" "$C:/root/.ollama/models/manifests/registry.ollama.ai/$MODEL/$TAG" >/dev/null
docker exec "$C" ollama list
rm -rf "$W"
