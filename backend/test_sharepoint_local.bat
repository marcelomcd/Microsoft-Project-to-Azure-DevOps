@echo off
REM Script para testar conexão com SharePoint e descobrir caminho correto
REM 
REM Antes de executar, configure as variáveis de ambiente no arquivo .env
REM ou exporte-as no terminal

echo ================================================================================
echo   TESTE DE CONEXAO COM SHAREPOINT
echo   Descobrindo caminho correto da pasta
echo ================================================================================
echo.

REM Verifica se Python está instalado
python --version >nul 2>&1
if errorlevel 1 (
    echo ERRO: Python nao encontrado!
    echo Instale Python 3.9+ e tente novamente.
    pause
    exit /b 1
)

REM Ativa ambiente virtual se existir
if exist "venv\Scripts\activate.bat" (
    echo Ativando ambiente virtual...
    call venv\Scripts\activate.bat
)

REM Executa o script
echo Executando script de teste...
echo.
cd backend
python test_sharepoint_path.py

echo.
echo ================================================================================
echo   TESTE CONCLUIDO
echo ================================================================================
pause

