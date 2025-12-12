#!/bin/bash
# Script para testar conexão com SharePoint e descobrir caminho correto
# 
# Antes de executar, configure as variáveis de ambiente no arquivo .env
# ou exporte-as no terminal

echo "================================================================================"
echo "  TESTE DE CONEXÃO COM SHAREPOINT"
echo "  Descobrindo caminho correto da pasta"
echo "================================================================================"
echo ""

# Verifica se Python está instalado
if ! command -v python3 &> /dev/null; then
    echo "ERRO: Python não encontrado!"
    echo "Instale Python 3.9+ e tente novamente."
    exit 1
fi

# Ativa ambiente virtual se existir
if [ -f "venv/bin/activate" ]; then
    echo "Ativando ambiente virtual..."
    source venv/bin/activate
fi

# Executa o script
echo "Executando script de teste..."
echo ""
cd backend
python3 test_sharepoint_path.py

echo ""
echo "================================================================================"
echo "  TESTE CONCLUIDO"
echo "================================================================================"

