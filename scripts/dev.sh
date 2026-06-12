#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_PID=""

cleanup() {
  if [[ -n "${BACKEND_PID}" ]]; then
    kill "${BACKEND_PID}" >/dev/null 2>&1 || true
  fi
}

trap cleanup EXIT INT TERM

if curl -fsS "http://127.0.0.1:8000/health" >/dev/null 2>&1; then
  echo "Backend déjà lancé sur http://127.0.0.1:8000"
else
  if [[ ! -x "${ROOT_DIR}/venv/bin/python" ]]; then
    echo "Backend indisponible : venv/bin/python introuvable."
    echo "Créez le venv puis installez requirements.txt avant de relancer npm run dev."
    exit 1
  fi

  echo "Démarrage du backend sur http://127.0.0.1:8000"
  "${ROOT_DIR}/venv/bin/python" -m uvicorn app.main:app --app-dir "${ROOT_DIR}" --host 127.0.0.1 --port 8000 --reload &
  BACKEND_PID="$!"

  for _ in {1..40}; do
    if curl -fsS "http://127.0.0.1:8000/health" >/dev/null 2>&1; then
      break
    fi
    sleep 0.25
  done

  if ! curl -fsS "http://127.0.0.1:8000/health" >/dev/null 2>&1; then
    echo "Le backend n'a pas répondu sur http://127.0.0.1:8000/health."
    exit 1
  fi
fi

if command -v lsof >/dev/null 2>&1 && lsof -i :5173 -sTCP:LISTEN >/dev/null 2>&1; then
  echo "Frontend déjà lancé sur http://localhost:5173"
  if [[ -n "${BACKEND_PID}" ]]; then
    echo "Backend lancé pour cette session. Ctrl+C pour l'arrêter."
    wait "${BACKEND_PID}"
  else
    echo "Environnement prêt : http://localhost:5173"
    while true; do sleep 3600; done
  fi
else
  npm --prefix "${ROOT_DIR}/frontend" run dev:vite
fi
