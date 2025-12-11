@echo off
setlocal enabledelayedexpansion
title MPP to Azure DevOps Converter

REM Forca a janela a permanecer aberta
if "%1"=="" (
    cmd /k "%~f0" keep
    exit /b
)

REM Muda para o diretorio do script
cd /d "%~dp0"
if errorlevel 1 (
    echo [ERRO] Falha ao acessar diretorio do script!
    pause
    exit /b 1
)

echo ========================================
echo   MPP to Azure DevOps Converter
echo   Iniciando Backend e Frontend...
echo ========================================
echo.

REM Configura PATH para Node.js
set "PATH=C:\Program Files\nodejs;%PATH%"

REM Verifica Node.js
where node >nul 2>&1
if errorlevel 1 (
    echo [ERRO] Node.js nao encontrado!
    echo Instale Node.js de https://nodejs.org/
    pause
    exit /b 1
)
echo [OK] Node.js encontrado
node --version

REM Verifica Python
where python >nul 2>&1
if errorlevel 1 (
    echo [ERRO] Python nao encontrado!
    echo Instale Python e adicione ao PATH.
    pause
    exit /b 1
)
echo [OK] Python encontrado
python --version

REM Verifica Java
where java >nul 2>&1
if errorlevel 1 (
    echo [AVISO] Java nao encontrado - funcionalidade limitada
) else (
    echo [OK] Java encontrado
)
echo.

REM Backend
cd /d "%~dp0backend"
if errorlevel 1 (
    echo [ERRO] Diretorio backend nao encontrado!
    pause
    exit /b 1
)

REM Cria .env se nao existir
if not exist ".env" (
    echo [AVISO] Criando arquivo .env...
    echo # Azure DevOps Configuration > .env
    echo AZURE_DEVOPS_ORG=qualiit >> .env
    echo AZURE_DEVOPS_PROJECT=Quali IT - Inovacao e Tecnologia >> .env
    echo AZURE_DEVOPS_PAT=SEU_PAT_AQUI >> .env
    echo [OK] Arquivo .env criado - Configure o PAT!
    timeout /t 2 /nobreak >nul
)

REM Cria diretorios
if not exist "uploads" mkdir uploads >nul 2>&1
if not exist "logs" mkdir logs >nul 2>&1

REM Ambiente virtual
if not exist "venv\Scripts\activate.bat" (
    echo [AVISO] Criando ambiente virtual...
    python -m venv venv
    if errorlevel 1 (
        echo [ERRO] Falha ao criar venv!
        pause
        exit /b 1
    )
    echo [OK] Ambiente virtual criado
    echo Instalando dependencias...
    call venv\Scripts\activate.bat
    pip install --upgrade pip >nul 2>&1
    pip install -r requirements.txt
    if errorlevel 1 (
        echo [ERRO] Falha ao instalar dependencias!
        pause
        exit /b 1
    )
    echo [OK] Dependencias instaladas
) else (
    echo [OK] Ambiente virtual encontrado
    call venv\Scripts\activate.bat
    pip install -r requirements.txt --quiet >nul 2>&1
)

echo.
echo [INFO] Iniciando Backend...
start "MPP Backend" cmd /k "cd /d %~dp0backend && venv\Scripts\activate.bat && uvicorn app.main:app --reload --host 127.0.0.1 --port 8000"

timeout /t 3 /nobreak >nul

REM Frontend
cd /d "%~dp0frontend"
if errorlevel 1 (
    echo [ERRO] Diretorio frontend nao encontrado!
    pause
    exit /b 1
)

if not exist "node_modules" (
    echo [AVISO] Instalando dependencias do frontend...
    call npm install
    if errorlevel 1 (
        echo [ERRO] Falha ao instalar dependencias!
        pause
        exit /b 1
    )
)

echo [INFO] Iniciando Frontend...
start "MPP Frontend" cmd /k "cd /d %~dp0frontend && npm run dev"

echo.
echo ========================================
echo   Sistema iniciado!
echo ========================================
echo.
echo Backend:  http://127.0.0.1:8000
echo Docs:     http://127.0.0.1:8000/docs
echo Frontend: http://localhost:3000
echo.
echo Configure o AZURE_DEVOPS_PAT no arquivo .env
echo.
pause
