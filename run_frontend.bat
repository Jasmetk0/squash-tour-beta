@echo off
setlocal

cd /d "%~dp0\web"
if errorlevel 1 goto error

if not exist "node_modules\" (
    echo Installing frontend dependencies...
    npm install
    if errorlevel 1 goto error
)

echo.
echo Starting Squash Tour Beta frontend at http://127.0.0.1:5173
echo Press Ctrl+C to stop the frontend.
echo.
npm run dev -- --host 127.0.0.1
if errorlevel 1 goto error

goto end

:error
echo.
echo Frontend startup failed. Please copy the error text above and send it for debugging.
pause
exit /b 1

:end
echo.
echo Frontend process stopped.
pause
