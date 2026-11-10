@echo off
rem Download new Discord messages, then build the bug audit.
rem Without ANTHROPIC_API_KEY in .env it only writes out\discord-messages.md.
cd /d "%~dp0"
python fetch.py || goto :fail
findstr /r /c:"^ANTHROPIC_API_KEY=..*" .env >nul 2>&1
if errorlevel 1 (
  python audit.py --export-only || goto :fail
  echo.
  echo Upload out\discord-messages.md to Claude and ask for the bug audit.
) else (
  python audit.py || goto :fail
  echo.
  echo The audit is in out\bug-audit.md
)
pause
exit /b 0
:fail
echo Something went wrong, see the message above.
pause
exit /b 1
