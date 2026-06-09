#!/usr/bin/env bash
# ────────────────────────────────────────────────────────────────
#  InspectAI — Dev start (PostgreSQL + FastAPI + Vite)
# ────────────────────────────────────────────────────────────────
set -e

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
BACKEND="$PROJECT_ROOT/backend"
FRONTEND="$PROJECT_ROOT/frontend"

echo ""
echo "  InspectAI — Dev Start"
echo "  ─────────────────────"
echo ""

# ── 0. Check PostgreSQL ──────────────────────────────────────────
if ! command -v psql &>/dev/null && ! command -v pg_isready &>/dev/null; then
    echo "  ⚠  PostgreSQL client not found."
    echo "     Убедитесь, что PostgreSQL запущен (или используйте docker-compose)."
    echo ""
fi

# ── 1. Backend deps ──────────────────────────────────────────────
echo "→ Устанавливаем Python-зависимости..."
cd "$BACKEND"
pip install -q -r requirements.txt

# ── 2. .env ──────────────────────────────────────────────────────
if [ ! -f .env ]; then
    echo "→ Копируем .env.example → .env"
    cp .env.example .env
    echo "  ⚠  Откройте backend/.env и задайте DATABASE_URL и YANDEX_MAPS_KEY"
    echo ""
fi

# ── 3. Media dirs ────────────────────────────────────────────────
mkdir -p media/uploads media/annotated media/reports

# ── 4. Alembic migrations ────────────────────────────────────────
echo "→ Применяем миграции Alembic..."
alembic upgrade head

# ── 5. Seed ──────────────────────────────────────────────────────
echo "→ Заполняем начальные данные..."
python ../scripts/seed.py 2>/dev/null || echo "  (пользователи уже созданы)"

# ── 6. Frontend deps ─────────────────────────────────────────────
echo "→ Устанавливаем npm-зависимости..."
cd "$FRONTEND"
npm install --silent

echo ""
echo "  ✓ Готово! Запускаем:"
echo "    Backend  → http://localhost:8000"
echo "    Frontend → http://localhost:5173"
echo "    API docs → http://localhost:8000/api/docs"
echo "    Логин: admin / admin123"
echo ""

# ── 7. Start both ────────────────────────────────────────────────
cd "$BACKEND"
uvicorn main:app --host 0.0.0.0 --port 8000 --reload &
BPID=$!

cd "$FRONTEND"
npm run dev &
FPID=$!

trap "kill $BPID $FPID 2>/dev/null; exit 0" INT TERM
wait
