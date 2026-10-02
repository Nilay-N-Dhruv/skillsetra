@echo off
setlocal
cd /d "%~dp0"
if not exist "backend\.env" copy /Y "backend\.env.example" "backend\.env" >nul
echo.
echo Skillsetra AI configuration
echo Primary: Puter AI (browser, no API key required)
echo Secondary: Ollama (local, install Ollama and pull a model such as llama3.2:3b)
echo.
start "" notepad.exe "%~dp0backend\.env"
pause
