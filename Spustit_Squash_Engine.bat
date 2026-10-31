@echo off
setlocal
cd /d "%~dp0"
if not exist "%~dp0SquashEnginePreview.exe" (
  echo Stahni pripraveny Windows ZIP z GitHub Actions, ne Code / Download ZIP.
  echo Download the prepared Windows ZIP from GitHub Actions, not the source ZIP.
  echo Navod / Guide: docs\WINDOWS_PREVIEW.md
  pause
  exit /b 1
)
"%~dp0SquashEnginePreview.exe" %*
if errorlevel 1 (
  echo.
  echo Zkopiruj chybu vyse. Ulozena data nemaz. / Copy the error above. Keep saved data.
  pause
  exit /b 1
)
