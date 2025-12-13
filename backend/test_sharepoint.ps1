# Script PowerShell para testar SharePoint localmente
# Configura variáveis de ambiente e executa o script Python

Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host "  TESTE DE CONEXAO COM SHAREPOINT" -ForegroundColor Cyan
Write-Host "  Descobrindo caminho correto da pasta" -ForegroundColor Cyan
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host ""

# Verifica se Python está instalado
try {
    $pythonVersion = python --version 2>&1
    Write-Host "Python encontrado: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "ERRO: Python nao encontrado!" -ForegroundColor Red
    Write-Host "Instale Python 3.9+ e tente novamente." -ForegroundColor Yellow
    exit 1
}

# Configura variáveis de ambiente
Write-Host "Configurando variáveis de ambiente..." -ForegroundColor Yellow

$env:USE_SHAREPOINT = "True"
$env:SHAREPOINT_SITE_URL = "https://qualiitcombr.sharepoint.com/sites/projetosqualiit"
$env:SHAREPOINT_CLIENT_ID = "2a41ace8-8b14-42db-808e-8681331138f5"
$env:SHAREPOINT_TENANT_ID = "6eb6a2fd-839d-460d-9bb0-7ed15211a782"

# Client Secret (hardcoded para testes - REMOVER EM PRODUÇÃO)
# ATENÇÃO: Este secret está hardcoded apenas para facilitar testes locais
# NUNCA commite este arquivo com o secret no repositório!
$env:SHAREPOINT_CLIENT_SECRET = "4K88Q~u8vqfCeG5-OXUQ9QE6jDdI2GlS.jDRvcG2"

# Alternativa: Se preferir inserir manualmente, descomente as linhas abaixo e comente a linha acima
# Write-Host ""
# Write-Host "Por favor, informe o SHAREPOINT_CLIENT_SECRET:" -ForegroundColor Yellow
# Write-Host "(O valor será ocultado por segurança)" -ForegroundColor Gray
# $secureSecret = Read-Host -AsSecureString
# $bstr = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureSecret)
# $env:SHAREPOINT_CLIENT_SECRET = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($bstr)

Write-Host ""
Write-Host "Variáveis configuradas:" -ForegroundColor Green
Write-Host "  USE_SHAREPOINT = $env:USE_SHAREPOINT"
Write-Host "  SHAREPOINT_SITE_URL = $env:SHAREPOINT_SITE_URL"
Write-Host "  SHAREPOINT_CLIENT_ID = $env:SHAREPOINT_CLIENT_ID"
Write-Host "  SHAREPOINT_TENANT_ID = $env:SHAREPOINT_TENANT_ID"
Write-Host "  SHAREPOINT_CLIENT_SECRET = [OCULTO]"
Write-Host ""

# Executa o script Python
Write-Host "Executando script de teste..." -ForegroundColor Yellow
Write-Host ""

python test_sharepoint_path.py

Write-Host ""
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host "  TESTE CONCLUIDO" -ForegroundColor Cyan
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Pressione qualquer tecla para continuar..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")

