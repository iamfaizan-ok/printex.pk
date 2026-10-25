@echo off
setlocal enabledelayedexpansion

echo ========================================================
echo          PrintX (printex.pk) Windows Local Runner
echo ========================================================
echo.

set "SCRIPT_DIR=%~dp0"
set "BACKEND_DIR=%SCRIPT_DIR%backend_all"
set "FRONTEND_DIR=%SCRIPT_DIR%user_frontend"

set "PYTHON_EXE=%BACKEND_DIR%\venv\Scripts\python.exe"
set "PIP_EXE=%BACKEND_DIR%\venv\Scripts\pip.exe"

if not exist "%PYTHON_EXE%" (
    echo [INFO] Creating Python virtual environment...
    python -m venv "%BACKEND_DIR%\venv"
    "%PIP_EXE%" install --upgrade pip
    "%PIP_EXE%" install -r "%BACKEND_DIR%\requirements.txt"
)

set "MODE=%~1"
if "%MODE%"=="" set "MODE=all"

if /i "%MODE%"=="backend" goto :start_backend_only
if /i "%MODE%"=="frontend" goto :start_frontend_only
goto :start_all

:start_backend_only
echo [INFO] Applying Database Migrations (PostgreSQL printx_db)...
cd /d "%BACKEND_DIR%"
"%PYTHON_EXE%" manage.py migrate --noinput
echo [INFO] Starting Backend on http://127.0.0.1:8000 ...
"%PYTHON_EXE%" manage.py runserver 0.0.0.0:8000
goto :end

:start_frontend_only
echo [INFO] Starting Frontend on http://localhost:3000 ...
cd /d "%FRONTEND_DIR%"
call npm run dev
goto :end

:start_all
echo [INFO] Applying Database Migrations (PostgreSQL printx_db)...
cd /d "%BACKEND_DIR%"
"%PYTHON_EXE%" manage.py migrate --noinput
echo [INFO] Starting Django Backend in a new window...
start "PrintX Backend (Port 8000)" cmd /k "cd /d "%BACKEND_DIR%" && "%PYTHON_EXE%" manage.py runserver 0.0.0.0:8000"

echo [INFO] Starting Frontend in current window...
echo.
echo ========================================================
echo  Customer Frontend:    http://localhost:3000
echo  Admin Operations:     http://localhost:8000/admin-panel/login.html
echo  Shop Onboarding:      http://localhost:8000/admin-panel/register-shop.html
echo ========================================================
echo.
cd /d "%FRONTEND_DIR%"
call npm run dev

:end
