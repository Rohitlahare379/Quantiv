#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "== Quantive operational stack verification =="
echo "repo: ${ROOT}"

echo
echo "== Backend syntax check =="
python3 -m py_compile \
  "${ROOT}/backend/main.py" \
  "${ROOT}/backend/simulator/api/router.py" \
  "${ROOT}/backend/orchestrator/agents/regime_agent.py" \
  "${ROOT}/backend/orchestrator/agents/robustness_agent.py" \
  "${ROOT}/backend/orchestrator/agents/deployment_agent.py" \
  "${ROOT}/backend/orchestrator/runtime.py" \
  "${ROOT}/backend/orchestrator/context.py"

echo
echo "== Room 2 -> Room 3 evidence flow smoke test =="
python3 "${ROOT}/scripts/verify_evidence_flow.py"

echo
echo "== Frontend production build =="
cd "${ROOT}/frontend"
npm run build

echo
echo "== Optional live backend health check =="
if command -v curl >/dev/null 2>&1; then
  if curl -fsS "http://127.0.0.1:8000/health" >/tmp/quantive_health.json 2>/dev/null; then
    cat /tmp/quantive_health.json
    echo
  else
    echo "Backend is not currently reachable on http://127.0.0.1:8000/health"
    echo "Start it with: cd backend && uvicorn main:app --port 8000"
  fi
else
  echo "curl not available; skipping live health check"
fi

echo
echo "All local verification steps completed."
