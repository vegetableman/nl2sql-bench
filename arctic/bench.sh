#!/usr/bin/env bash
# One-shot Arctic benchmark on the HF Inference Endpoint (system `arctic`), always pausing the endpoint at the end.
#   ARCTIC_GPU=nvidia-a10g ARCTIC_OUT=run-arctic-hf-a10g-r3 arctic/bench.sh
# resume endpoint -> wait running -> warm-up (2 throwaway calls, not timed) -> 29 x3 into results/$ARCTIC_OUT
# -> 15 holdout x3 appended to results/run-gptoss120b-holdout-r3 (--resume) ; EXIT trap: pause + verify paused via API.
# The endpoint's instance type is set on the endpoint itself (HF UI / update); ARCTIC_GPU only labels the reports.
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"; cd "$HERE/.."
EP="arctic/.venv/bin/python arctic/endpoint.py"
export ARCTIC_GPU=${ARCTIC_GPU:-nvidia-a10g}
OUT=${ARCTIC_OUT:-run-arctic-hf-a10g-r3}
REPEATS=${REPEATS:-3}
cleanup() {
  rc=$?
  echo "[$(date '+%F %T %Z')] cleanup (rc=$rc): pausing endpoint"
  for i in 1 2 3; do
    $EP pause && $EP status | grep -q '"status": "paused"' && { echo "endpoint paused (verified)"; exit $rc; }
    sleep 20
  done
  echo "!!! endpoint NOT verified paused"; exit 99
}
trap cleanup EXIT
trap 'exit 130' INT TERM HUP
set -e
echo "[$(date '+%F %T %Z')] start ($ARCTIC_GPU, out=$OUT, repeats=$REPEATS)"
$EP status
$EP status | grep -q '"status": "running"' || $EP resume
$EP wait
arctic/.venv/bin/python arctic/warmup.py
echo "[$(date '+%F %T %Z')] original 29"
.venv/bin/python bench/harness.py --repeats "$REPEATS" --systems arctic --out "$OUT" --resume
echo "[$(date '+%F %T %Z')] holdout 15"
.venv/bin/python bench/harness.py --repeats "$REPEATS" --systems arctic --questions bench/questions_holdout.yaml --out run-gptoss120b-holdout-r3 --resume
echo "[$(date '+%F %T %Z')] done"
