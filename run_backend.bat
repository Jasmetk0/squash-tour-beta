@echo off
setlocal

cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Creating Python virtual environment in .venv...
    py -3.12 -m venv .venv
    if errorlevel 1 (
        echo Python 3.12 launcher was not available. Trying default python...
        python -m venv .venv
    )
    if errorlevel 1 goto error
)

call ".venv\Scripts\activate.bat"
if errorlevel 1 goto error

echo Installing/updating backend dependencies...
python -m pip install --upgrade pip
if errorlevel 1 goto error

python -m pip install -e ".[dev]"
if errorlevel 1 goto error

set "PYTHONPATH=%CD%\src"

echo.
echo Starting Squash Tour Beta backend at http://127.0.0.1:8000
echo Press Ctrl+C to stop the backend.
echo.
python -m uvicorn beta_engine.main:app --host 127.0.0.1 --port 8000
if errorlevel 1 goto error

goto end

:error
echo.
echo Backend startup failed. Please copy the error text above and send it for debugging.
pause
exit /b 1

:end
echo.
echo Backend process stopped.
pause
