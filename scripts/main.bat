@echo off
setlocal

:: --- Admin check (robust) ---
:: fltmc requires admin; returns nonzero if not admin
fltmc >nul 2>&1
if errorlevel 1 (
  echo Requesting administrative privileges...
  :: Relaunch this .bat elevated under cmd.exe so .bat handling is consistent
  %SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe -NoProfile -ExecutionPolicy Bypass -Command ^
    "Start-Process -FilePath '%ComSpec%' -ArgumentList '/c, ""%~f0""' -Verb RunAs"

  :: If UAC was cancelled, show a message instead of silently closing
  if errorlevel 1 (
    echo Elevation was cancelled or failed.
    pause
  )
  exit /b
)

:: --- Already elevated below this line ---
cd /d "%~dp0"

:: Prefer the Python launcher (works across per-user/system installs)
:: Fallback to python if py isn't present.
where py >nul 2>&1
if %errorlevel%==0 (
  py -3 AutoFarmers.py
) else (
  :: If you know the exact path, you can hardcode it instead of relying on PATH:
  :: "C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python310\python.exe" AutoFarmers.py
  python AutoFarmers.py
)

echo.
pause
