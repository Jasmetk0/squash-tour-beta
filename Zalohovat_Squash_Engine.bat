@echo off
setlocal
cd /d "%~dp0"
if not exist "%~dp0SquashEnginePreview.exe" (
  echo Nejprve rozbal cely Windows preview ZIP. / Extract the complete preview ZIP.
  echo Navod / Guide: docs\WINDOWS_PREVIEW.md
  pause
  exit /b 1
)
echo.
echo ZALOHA / BACKUP: ukonci nejdrive bezici Squash Engine.
echo Close the running engine before backing up.
echo.
"%~dp0SquashEnginePreview.exe" --backup %*
if errorlevel 1 (
  echo.
  echo Chyba zalohy. Originalni data zustala zachovana.
  echo Backup failed. Original data was preserved.
  pause
  exit /b 1
)
echo.
echo Uschovej ZIP soukrome. Obsahuje vsechny ulozene Runy a jejich data.
echo Keep the ZIP private. It contains saved Runs and data.
pause
