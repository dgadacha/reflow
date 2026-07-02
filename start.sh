#!/usr/bin/env bash
# Lance backend (FastAPI) + frontend (Astro) ensemble.
# Premier lancement : crée le venv, installe les dépendances, prépare le .env.
# Ctrl+C arrête les deux.
set -e

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND="$ROOT/backend"
FRONTEND="$ROOT/frontend"

# Mode dev : ./start.sh --dev  → quota illimité + cache des vidéos testées.
# La variable exportée l'emporte sur le .env (dotenv n'écrase pas l'env existant).
if [ "$1" = "--dev" ]; then
  export REFLOW_DEV_MODE=true
  echo "→ Mode dev activé (quota illimité + cache des générations)"
fi

# --- Backend : venv + dépendances + .env ---
cd "$BACKEND"
if [ ! -d ".venv" ]; then
  echo "→ Création du venv Python…"
  python3 -m venv .venv
fi
source .venv/bin/activate
if ! python -c "import fastapi" 2>/dev/null; then
  echo "→ Installation des dépendances Python…"
  pip install -q -r requirements.txt
fi
if [ ! -f ".env" ]; then
  cp .env.example .env
  echo "⚠  backend/.env créé — pense à y mettre ta clé ANTHROPIC_API_KEY."
fi

# --- Frontend : node_modules ---
cd "$FRONTEND"
if [ ! -d "node_modules" ]; then
  echo "→ Installation des dépendances npm…"
  npm install
fi

# --- Lancement des deux processus ---
cleanup() {
  echo ""
  echo "→ Arrêt…"
  kill "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

cd "$BACKEND"
source .venv/bin/activate
uvicorn main:app --reload --port 8787 &
BACKEND_PID=$!

cd "$FRONTEND"
npm run dev &
FRONTEND_PID=$!

echo ""
echo "✦ Reflow lancé"
echo "  backend  → http://localhost:8787"
echo "  frontend → http://localhost:4321"
echo "  (Ctrl+C pour tout arrêter)"

wait
