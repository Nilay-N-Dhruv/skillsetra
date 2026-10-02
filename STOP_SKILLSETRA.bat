@echo off
setlocal
for %%P in (3000 8000) do (
  for /f "tokens=5" %%A in ('netstat -ano ^| findstr :%%P ^| findstr LISTENING') do taskkill /PID %%A /F >nul 2>nul
)
echo SKILLSETRA local web/API processes on ports 3000 and 8000 were stopped.
timeout /t 2 /nobreak >nul
