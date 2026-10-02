@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"
set "ROOT=%~dp0"
set "DEMO_MODE=true"
set "ENVIRONMENT=demo"
set "AI_PROVIDER=puter"
set "PUTER_MODEL=openai/gpt-oss-20b"
set "OLLAMA_MODEL=llama3.2:3b"
set "CORS_ORIGINS=http://localhost:3000"
set "NEXT_PUBLIC_DEMO_MODE=true"
set "NEXT_PUBLIC_API_BASE_URL="
set "BACKEND_INTERNAL_URL=http://127.0.0.1:8000"

echo ============================================================
echo        SKILLSETRA - NO SIGN-IN DEMO TEST
echo ============================================================
echo.
where node >nul 2>nul || (echo ERROR: Node.js 20+ is required.&pause&exit /b 1)
where npm >nul 2>nul || (echo ERROR: npm is required.&pause&exit /b 1)
where python >nul 2>nul || (echo ERROR: Python 3.11+ is required.&pause&exit /b 1)
for /f "tokens=1 delims=." %%v in ('node -p "process.versions.node.split('.')[0]"') do set "NODE_MAJOR=%%v"
if !NODE_MAJOR! LSS 20 (echo ERROR: Node.js 20+ is required.&pause&exit /b 1)
if not exist "%ROOT%backend\.venv\Scripts\python.exe" (python -m venv "%ROOT%backend\.venv" || (echo ERROR: Python venv failed.&pause&exit /b 1))
if not exist "%ROOT%backend\.venv\Scripts\uvicorn.exe" ("%ROOT%backend\.venv\Scripts\python.exe" -m pip install -r "%ROOT%backend\requirements.txt" || (echo ERROR: Backend install failed.&pause&exit /b 1))
if not exist "%ROOT%frontend\node_modules\next\package.json" (pushd "%ROOT%frontend" & call npm.cmd install --no-audit --no-fund & set "NPM_RESULT=!ERRORLEVEL!" & popd & if not "!NPM_RESULT!"=="0" (echo ERROR: Frontend install failed.&pause&exit /b 1))
if exist "%ROOT%frontend\.next" rmdir /s /q "%ROOT%frontend\.next" >nul 2>&1
>"%ROOT%backend\.env" echo DEMO_MODE=true
>>"%ROOT%backend\.env" echo ENVIRONMENT=demo
>>"%ROOT%backend\.env" echo AI_PROVIDER=puter
>>"%ROOT%backend\.env" echo PUTER_MODEL=openai/gpt-oss-20b
>>"%ROOT%backend\.env" echo OLLAMA_MODEL=llama3.2:3b
>>"%ROOT%backend\.env" echo OLLAMA_BASE_URL=http://localhost:11434
>>"%ROOT%backend\.env" echo CORS_ORIGINS=http://localhost:3000
>"%ROOT%frontend\.env.local" echo NEXT_PUBLIC_DEMO_MODE=true
>>"%ROOT%frontend\.env.local" echo NEXT_PUBLIC_API_BASE_URL=
>>"%ROOT%frontend\.env.local" echo BACKEND_INTERNAL_URL=http://127.0.0.1:8000
for /f "tokens=5" %%P in ('netstat -ano ^| findstr LISTENING ^| findstr ":8000"') do taskkill /PID %%P /F >nul 2>&1
for /f "tokens=5" %%P in ('netstat -ano ^| findstr LISTENING ^| findstr ":3000"') do taskkill /PID %%P /F >nul 2>&1
echo Starting backend...
start "SKILLSETRA API - DEMO" "%ComSpec%" /k "cd /d %ROOT%backend && set DEMO_MODE=true&& set ENVIRONMENT=demo&& set AI_PROVIDER=puter&& set PUTER_MODEL=openai/gpt-oss-20b&& set OLLAMA_MODEL=llama3.2:3b&& set CORS_ORIGINS=http://localhost:3000&& .venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000"
echo Starting frontend...
start "SKILLSETRA WEB - DEMO" "%ComSpec%" /k "cd /d %ROOT%frontend && set NEXT_PUBLIC_DEMO_MODE=true&& set NEXT_PUBLIC_API_BASE_URL=&& set BACKEND_INTERNAL_URL=http://127.0.0.1:8000&& npm.cmd run dev"
echo Waiting for SKILLSETRA API...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ok=$false; for($i=0;$i-lt60;$i++){try{Invoke-WebRequest -UseBasicParsing -TimeoutSec 2 'http://localhost:8000/api/v1/health'|Out-Null;$ok=$true;break}catch{Start-Sleep -Seconds 1}};if(-not $ok){exit 1}"
if errorlevel 1 echo WARNING: API is still starting...
echo Waiting for SKILLSETRA web app...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ok=$false; for($i=0;$i-lt90;$i++){try{Invoke-WebRequest -UseBasicParsing -TimeoutSec 2 'http://localhost:3000/'|Out-Null;$ok=$true;break}catch{Start-Sleep -Seconds 1}};if(-not $ok){exit 1}"
if errorlevel 1 (echo ERROR: Web app did not become ready. Check the SKILLSETRA WEB terminal.&pause&exit /b 1)
start "" "http://localhost:3000/dashboard"
echo.
echo READY - browser opened automatically.
echo Demo Mode: ENABLED
 echo Puter AI: PRIMARY browser provider
 echo Ollama: SECONDARY local provider (optional)
echo Web: http://localhost:3000/dashboard
echo API via Next proxy: http://localhost:3000/api/v1/health
echo API docs direct: http://localhost:8000/docs
exit /b 0
