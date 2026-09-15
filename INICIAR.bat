@echo off
setlocal EnableExtensions
cd /d "%~dp0backend"

if not exist "venv\Scripts\python.exe" (
  echo [ERRO] Ambiente virtual nao encontrado.
  echo Execute CONFIGURAR.bat primeiro.
  pause
  exit /b 1
)

if not exist ".env" (
  copy /Y ".env.example" ".env" >nul
  echo [ERRO] backend\.env foi criado agora.
  echo Coloque sua GEMINI_API_KEY no arquivo e execute novamente.
  pause
  exit /b 1
)

findstr /B /C:"GEMINI_API_KEY=COLE_SUA_CHAVE_AQUI" ".env" >nul
if not errorlevel 1 (
  echo [ERRO] Configure sua GEMINI_API_KEY em backend\.env antes de iniciar.
  pause
  exit /b 1
)

findstr /R /C:"^GEMINI_API_KEY=$" ".env" >nul
if not errorlevel 1 (
  echo [ERRO] GEMINI_API_KEY esta vazia em backend\.env.
  pause
  exit /b 1
)

set "APP_HOST=127.0.0.1"
set "APP_PORT=8000"
for /f "usebackq tokens=1,* delims==" %%A in (".env") do (
  if /I "%%A"=="APP_HOST" set "APP_HOST=%%B"
  if /I "%%A"=="APP_PORT" set "APP_PORT=%%B"
)
set "APP_URL=http://%APP_HOST%:%APP_PORT%"

echo ========================================
echo  Iniciando Xampoula Chat
echo ========================================
echo [INFO] Abra no navegador: %APP_URL%
echo [INFO] Pressione CTRL+C para encerrar.
echo.

rem Abre o navegador depois de uma pequena espera sem atrapalhar o servidor.
start "" powershell -NoProfile -WindowStyle Hidden -Command "Start-Sleep -Seconds 2; Start-Process '%APP_URL%'"

"venv\Scripts\python.exe" main.py

pause
