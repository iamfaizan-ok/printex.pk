#!/usr/bin/env bash
# ==============================================================================
# PrintX (printex.pk) - Local Development Launcher
# Starts the Django backend (port 8000) and Vite frontend (port 3000)
# ==============================================================================

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$PROJECT_ROOT/backend_all"
FRONTEND_DIR="$PROJECT_ROOT/user_frontend"

# Colors for terminal output
BOLD="\033[1m"
GREEN="\033[0;32m"
CYAN="\033[0;36m"
YELLOW="\033[0;33m"
RED="\033[0;31m"
RESET="\033[0m"

echo -e "${BOLD}${CYAN}"
echo "  ========================================================"
echo "           🖨️  PrintX (printex.pk) Local Runner           "
echo "  ========================================================"
echo -e "${RESET}"

MODE="${1:-all}"

# Locate Python & Pip binaries (supports both Windows and Unix virtualenvs)
if [ -f "$BACKEND_DIR/venv/Scripts/python.exe" ]; then
    PYTHON_BIN="$BACKEND_DIR/venv/Scripts/python.exe"
    PIP_BIN="$BACKEND_DIR/venv/Scripts/pip.exe"
elif [ -f "$BACKEND_DIR/venv/bin/python" ]; then
    PYTHON_BIN="$BACKEND_DIR/venv/bin/python"
    PIP_BIN="$BACKEND_DIR/venv/bin/pip"
else
    PYTHON_BIN="python3"
    PIP_BIN="pip3"
fi

# Ensure python venv exists
if [ ! -d "$BACKEND_DIR/venv" ]; then
    echo -e "${YELLOW}Backend virtualenv not found. Creating one now...${RESET}"
    python3 -m venv "$BACKEND_DIR/venv"
    if [ -f "$BACKEND_DIR/venv/Scripts/pip.exe" ]; then
        PIP_BIN="$BACKEND_DIR/venv/Scripts/pip.exe"
        PYTHON_BIN="$BACKEND_DIR/venv/Scripts/python.exe"
    else
        PIP_BIN="$BACKEND_DIR/venv/bin/pip"
        PYTHON_BIN="$BACKEND_DIR/venv/bin/python"
    fi
    "$PIP_BIN" install --upgrade pip
    "$PIP_BIN" install -r "$BACKEND_DIR/requirements.txt"
fi

# Ensure frontend node_modules exists
if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
    echo -e "${YELLOW}Frontend node_modules not found. Installing now...${RESET}"
    (cd "$FRONTEND_DIR" && npm install)
fi

cleanup() {
    echo -e "\n${YELLOW}Shutting down services...${RESET}"
    if [ -n "$BACKEND_PID" ]; then
        kill "$BACKEND_PID" 2>/dev/null || true
    fi
    if [ -n "$FRONTEND_PID" ]; then
        kill "$FRONTEND_PID" 2>/dev/null || true
    fi
    wait 2>/dev/null || true
    echo -e "${GREEN}All services stopped cleanly.${RESET}"
    exit 0
}

trap cleanup SIGINT SIGTERM EXIT

start_backend() {
    echo -e "${GREEN}Applying Database Migrations (PostgreSQL printx_db)...${RESET}"
    (cd "$BACKEND_DIR" && "$PYTHON_BIN" manage.py migrate --noinput)
    echo -e "${GREEN}Starting Django Backend on http://127.0.0.1:8000 ...${RESET}"
    (cd "$BACKEND_DIR" && "$PYTHON_BIN" manage.py runserver 0.0.0.0:8000) &
    BACKEND_PID=$!
}

start_frontend() {
    echo -e "${GREEN}Starting Vite Frontend on http://localhost:3000 ...${RESET}"
    (cd "$FRONTEND_DIR" && npm run dev) &
    FRONTEND_PID=$!
}

case "$MODE" in
    backend)
        start_backend
        echo -e "\n${BOLD}${GREEN}Backend is running!${RESET}"
        echo -e "  • API Base:   ${CYAN}http://localhost:8000/api/v1/${RESET}"
        echo -e "  • Swagger UI: ${CYAN}http://localhost:8000/api/docs/${RESET}"
        echo -e "  • Admin UI:   ${CYAN}http://localhost:8000/admin-panel/login.html${RESET}"
        echo -e "  • Django:     ${CYAN}http://localhost:8000/admin/${RESET}\n"
        wait "$BACKEND_PID"
        ;;
    frontend)
        start_frontend
        echo -e "\n${BOLD}${GREEN}Frontend is running!${RESET}"
        echo -e "  • User Portal: ${CYAN}http://localhost:3000${RESET}\n"
        wait "$FRONTEND_PID"
        ;;
    all|*)
        start_backend
        start_frontend
        
        echo -e "\n${BOLD}${GREEN}========================================================${RESET}"
        echo -e "${BOLD}${GREEN} PrintX Local Development Services Ready:${RESET}"
        echo -e "   Customer Frontend:    ${CYAN}http://localhost:3000${RESET}"
        echo -e "   Admin Operations:     ${CYAN}http://localhost:8000/admin-panel/login.html${RESET}"
        echo -e "   REST API Base:        ${CYAN}http://localhost:8000/api/v1/${RESET}"
        echo -e "   Swagger / OpenAPI:    ${CYAN}http://localhost:8000/api/docs/${RESET}"
        echo -e "   Django Admin:         ${CYAN}http://localhost:8000/admin/${RESET}"
        echo -e "   Shop Registration:    ${CYAN}http://localhost:8000/admin-panel/register-shop.html${RESET}"
        echo -e "${BOLD}${GREEN}========================================================${RESET}\n"
        echo -e "Press ${BOLD}Ctrl+C${RESET} anytime to stop all services.\n"
        
        wait
        ;;
esac
