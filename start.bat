@echo off
setlocal EnableExtensions
title Offline Shop POS
cd /d "%~dp0"

rem --- Locate Python (prefer the project virtual environment) ---
set "PY=python"
if exist "%~dp0.venv\Scripts\python.exe" set "PY=%~dp0.venv\Scripts\python.exe"
if exist "%~dp0main\.venv\Scripts\python.exe" set "PY=%~dp0main\.venv\Scripts\python.exe"

rem --- Locate the Django project folder (the one containing manage.py) ---
set "PROJECT_DIR=%~dp0main"
if not exist "%PROJECT_DIR%\manage.py" set "PROJECT_DIR=%~dp0"

if not exist "%PROJECT_DIR%\manage.py" (
    echo.
    echo   ERROR: manage.py was not found.
    echo   Put start.bat in the project folder that contains the "main" folder.
    echo.
    pause
    exit /b 1
)

"%PY%" --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo   ERROR: Python was not found.
    echo   Install Python 3.12 or newer, or recreate the .venv folder.
    echo.
    pause
    exit /b 1
)

echo.
echo   ============================================
echo     Offline Shop POS
echo   ============================================
echo.
echo   Starting the local server. Keep this window
echo   open while you are billing.
echo.
echo   Address: http://127.0.0.1:8000
echo   To stop: close this window or press Ctrl+C.
echo.

cd /d "%PROJECT_DIR%"

rem Apply any pending database migrations, then open the browser
"%PY%" manage.py migrate --noinput

rem Open the browser a few seconds after the server should be ready
start "" /min cmd /c "ping -n 6 127.0.0.1 >nul & start http://127.0.0.1:8000"

"%PY%" manage.py runserver 127.0.0.1:8000

echo.
echo   The server has stopped.
pause
