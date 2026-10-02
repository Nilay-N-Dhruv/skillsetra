@echo off
setlocal EnableExtensions
cd /d "%~dp0"

set "ROOT=%~dp0"
set "FRONTEND=%ROOT%frontend"
set "BACKEND=%ROOT%backend"

cls
echo ============================================================
echo                 SKILLSETRA - ONE CLICK START
echo ============================================================
echo.

echo Checking required software...
where node >nul 2>nul
if errorlevel 1 goto :node_missing
where npm >nul 2>nul
if errorlevel 1 goto :node_missing
where python >nul 2>nul
if errorlevel 1 goto :python_missing

for /f "tokens=1 delims=." %%v in ('node -p "process.versions.node.split('.')[0]"') do set "NODE_MAJOR=%%v"
if %NODE_MAJOR% LSS 20 goto :node_old

if not exist "%FRONTEND%\package.json" goto :bad_project
if not exist "%BACKEND%\requirements.txt" goto :bad_project

echo.
echo [1/4] Preparing Python environment...
if not exist "%BACKEND%\.venv\Scripts\python.exe" (
  python -m venv "%BACKEND%\.venv"
  if errorlevel 1 goto :python_env_failed
)
if not exist "%BACKEND%\.env" copy /Y "%BACKEND%\.env.example" "%BACKEND%\.env" >nul

if not exist "%BACKEND%\.venv\Scripts\uvicorn.exe" (
  echo Installing backend packages...
  "%BACKEND%\.venv\Scripts\python.exe" -m pip install -r "%BACKEND%\requirements.txt"
  if errorlevel 1 goto :backend_install_failed
)

echo.
echo [2/4] Preparing frontend environment...
if not exist "%FRONTEND%\.env.local" copy /Y "%FRONTEND%\.env.example" "%FRONTEND%\.env.local" >nul
if not exist "%FRONTEND%\node_modules\next\package.json" (
  echo Installing frontend packages. This can take a few minutes the first time...
  pushd "%FRONTEND%"
  call npm.cmd install --no-audit --no-fund
  set "NPM_RESULT=%ERRORLEVEL%"
  popd
  if not "%NPM_RESULT%"=="0" goto :frontend_install_failed
)

echo.
echo Clearing stale Next.js development cache...
if exist "%FRONTEND%\.next" rmdir /s /q "%FRONTEND%\.next" >nul 2>&1

echo.
echo [3/4] Starting FastAPI...
start "SKILLSETRA API" "%ComSpec%" /k call "%ROOT%_RUN_BACKEND.bat"

timeout /t 2 /nobreak >nul

echo.
echo [4/4] Starting Next.js...
start "SKILLSETRA WEB" "%ComSpec%" /k call "%ROOT%_RUN_FRONTEND.bat"

echo.
echo Waiting for the web server...
timeout /t 6 /nobreak >nul
start "" "http://localhost:3000"
echo.
echo ============================================================
echo SKILLSETRA is starting.
echo Web:  http://localhost:3000
echo API:  http://localhost:8000/docs
echo Demo mode: no login required
 echo.
echo Keep the two SKILLSETRA terminal windows open while using it.
echo To stop everything, double-click STOP_SKILLSETRA.bat
 echo ============================================================
exit /b 0

:node_missing
echo ERROR: Node.js is not installed or is not available on PATH.
echo Install Node.js 20+ and run START_SKILLSETRA.bat again.
pause
exit /b 1

:node_old
echo ERROR: Node.js 20+ is required. Your Node.js version is too old.
pause
exit /b 1

:python_missing
echo ERROR: Python is not installed or is not available on PATH.
echo Install Python 3.11+ and run START_SKILLSETRA.bat again.
pause
exit /b 1

:bad_project
echo ERROR: The project is incomplete. START_SKILLSETRA.bat must stay beside frontend and backend folders.
pause
exit /b 1

:python_env_failed
echo ERROR: Could not create the Python virtual environment.
pause
exit /b 1

:backend_install_failed
echo ERROR: Backend dependency installation failed.
echo Check the SKILLSETRA setup output above, then run START_SKILLSETRA.bat again.
pause
exit /b 1

:frontend_install_failed
echo ERROR: Frontend dependency installation failed.
echo Check the npm output above, then run START_SKILLSETRA.bat again.
pause
exit /b 1
