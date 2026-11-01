#!/usr/bin/env bash
# =============================================================================
# deploy.sh — Script de Despliegue GEM OS en VPS Linux (Hostinger/Ubuntu)
# =============================================================================
# Uso:
#   chmod +x deploy.sh
#   GEM_OS_DATA_DIR=/var/www/gem_os/data ./deploy.sh
#
# Variables de entorno requeridas (en .env o exportadas):
#   OPENROUTER_API_KEY  — Clave API de OpenRouter (fallback cloud)
#   FREELLM_API_KEY     — Clave FreeLLMAPI proxy (prioridad $0)
#   FREELLM_BASE_URL    — URL del proxy FreeLLMAPI
#
# Variables opcionales:
#   GEM_OS_DATA_DIR     — Ruta de datos persistentes (default: ./data)
#   DASHBOARD_PORT      — Puerto del servidor web (default: 8050)
#   WORKERS             — Número de workers uvicorn (default: 2)
# =============================================================================
set -euo pipefail

# ── Configuración ─────────────────────────────────────────────────────────────
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="${PROJECT_DIR}/.venv"
DATA_DIR="${GEM_OS_DATA_DIR:-${PROJECT_DIR}/data}"
PORT="${DASHBOARD_PORT:-8050}"
WORKERS="${WORKERS:-2}"
PYTHON="${VENV_DIR}/bin/python"
UVICORN="${VENV_DIR}/bin/uvicorn"

# ── Colores ───────────────────────────────────────────────────────────────────
GREEN='\033[0;32m'; CYAN='\033[0;36m'; YELLOW='\033[1;33m'; NC='\033[0m'
info()  { echo -e "${CYAN}[GEM OS]${NC} $*"; }
ok()    { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }

info "Iniciando despliegue de GEM OS en ${PROJECT_DIR}"

# ── 1. Entorno virtual ────────────────────────────────────────────────────────
if [ ! -d "${VENV_DIR}" ]; then
  info "Creando entorno virtual Python..."
  python3 -m venv "${VENV_DIR}"
fi
source "${VENV_DIR}/bin/activate"
ok "Entorno virtual activado."

# ── 2. Dependencias ───────────────────────────────────────────────────────────
info "Instalando dependencias desde requirements.txt..."
pip install --quiet --upgrade pip
pip install --quiet -r "${PROJECT_DIR}/requirements.txt"
ok "Dependencias instaladas."

# ── 3. Directorios de datos ───────────────────────────────────────────────────
info "Creando directorios de persistencia en ${DATA_DIR}..."
mkdir -p "${DATA_DIR}"
mkdir -p "${PROJECT_DIR}/logs"
mkdir -p "${PROJECT_DIR}/backups"
mkdir -p "${PROJECT_DIR}/ai_workspace"
ok "Directorios creados."

# ── 4. Variables de entorno ───────────────────────────────────────────────────
if [ -f "${PROJECT_DIR}/.env" ]; then
  info "Cargando .env..."
  set -a
  source "${PROJECT_DIR}/.env"
  set +a
elif [ -f "${PROJECT_DIR}/.env.example" ]; then
  warn ".env no encontrado. Copia .env.example a .env y configura tus claves API."
fi

export GEM_OS_DATA_DIR="${DATA_DIR}"
export DISABLE_OLLAMA="${DISABLE_OLLAMA:-true}"
export DASHBOARD_PORT="${PORT}"

# ── 5. Inicialización de BD (idempotente) ─────────────────────────────────────
info "Inicializando base de datos SQLite (schema + migrations)..."
cd "${PROJECT_DIR}"
"${PYTHON}" init_database.py
ok "Base de datos lista."

# ── 6. Lanzar servidor ────────────────────────────────────────────────────────
info "Iniciando GEM OS en http://0.0.0.0:${PORT} (${WORKERS} workers)..."
info "Presiona Ctrl+C para detener."
exec "${UVICORN}" app.services.dashboard_server:app \
  --host 0.0.0.0 \
  --port "${PORT}" \
  --workers "${WORKERS}" \
  --log-level info \
  --access-log
