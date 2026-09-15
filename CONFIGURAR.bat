@echo off
setlocal EnableExtensions
cd /d "%~dp0backend"

echo ========================================
echo  Configurando Xampoula Chat
echo ========================================
echo.

if not exist ".env" (
  copy /Y ".env.example" ".env" >nul
  echo [OK] backend\.env criado a partir do .env.example.
)

set "PYTHON_EXE="
set "USE_PY_LAUNCHER="

rem Tenta encontrar um python.exe real no PATH (ignora o alias quebrado da Store).
for /f "delims=" %%P in ('where python 2^>nul') do (
  if not defined PYTHON_EXE (
    "%%P" -c "import sys" >nul 2>&1
    if not errorlevel 1 set "PYTHON_EXE=%%P"
  )
)

rem Instalacoes oficiais via winget/python.org normalmente ficam aqui.
if not defined PYTHON_EXE (
  for /d %%D in ("%LOCALAPPDATA%\Programs\Python\Python3*") do (
    if exist "%%~fD\python.exe" set "PYTHON_EXE=%%~fD\python.exe"
  )
)

rem Tenta o Python Launcher como alternativa.
if not defined PYTHON_EXE (
  where py >nul 2>&1
  if not errorlevel 1 (
    py -3 -c "import sys" >nul 2>&1
    if not errorlevel 1 set "USE_PY_LAUNCHER=1"
  )
)

if not defined PYTHON_EXE if not defined USE_PY_LAUNCHER (
  echo [ERRO] Python nao foi encontrado.
  echo.
  echo Instale o Python 3.10 ou superior e tente novamente.
  echo Pelo PowerShell voce pode usar:
  echo   winget install Python.Python.3.13
  echo.
  echo Depois feche e abra o terminal novamente.
  echo Se o Windows insistir em abrir a Microsoft Store, desative os aliases
  echo python.exe e python3.exe em "Aliases de execucao do aplicativo".
  echo.
  pause
  exit /b 1
)

if not exist "venv\Scripts\python.exe" (
  echo [1/3] Criando ambiente virtual...
  if defined PYTHON_EXE (
    "%PYTHON_EXE%" -m venv venv
  ) else (
    py -3 -m venv venv
  )
  if errorlevel 1 goto :erro
) else (
  echo [1/3] Ambiente virtual ja existe.
)

echo [2/3] Atualizando pip...
"venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 goto :erro

echo [3/3] Instalando dependencias...
"venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto :erro

echo.
echo [OK] Configuracao concluida.
echo Abra backend\.env e coloque sua GEMINI_API_KEY antes de iniciar.
pause
exit /b 0

:erro
echo.
echo [ERRO] A configuracao falhou. Veja a mensagem acima.
pause
exit /b 1
