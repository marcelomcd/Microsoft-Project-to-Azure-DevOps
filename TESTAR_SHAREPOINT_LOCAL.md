# Como Testar o SharePoint Localmente

Este guia explica como usar o script local para descobrir o caminho correto da pasta no SharePoint.

## 🎯 Objetivo

O script `test_sharepoint_path.py` vai:
1. ✅ Conectar ao SharePoint usando suas credenciais
2. 📁 Listar todas as pastas disponíveis
3. 🔍 Buscar arquivos .mpp em todas as pastas
4. 💡 Recomendar o caminho correto para usar na pipeline

## 📋 Pré-requisitos

1. **Python 3.9+** instalado
2. **Dependências Python** instaladas (execute: `pip install -r requirements.txt`)
3. **Credenciais do SharePoint** (Client ID, Client Secret, Tenant ID)

## ⚙️ Configuração

### Opção 1: Usar arquivo .env (Recomendado)

1. Crie um arquivo `.env` na pasta `backend/`:

```env
# SharePoint Configuration
USE_SHAREPOINT=True
SHAREPOINT_SITE_URL=https://qualiitcombr.sharepoint.com/sites/projetosqualiit
SHAREPOINT_FOLDER_PATH=Documentos Compartilhados/Cronogramas - Project
SHAREPOINT_CLIENT_ID=2a41ace8-8b14-42db-808e-8681331138f5
SHAREPOINT_CLIENT_SECRET=seu_client_secret_aqui
SHAREPOINT_TENANT_ID=6eb6a2fd-839d-460d-9bb0-7ed15211a782

# Azure DevOps (opcional para este teste)
AZURE_DEVOPS_ORG=qualiit
AZURE_DEVOPS_PROJECT=Quali IT - Inovação e Tecnologia
AZURE_DEVOPS_PAT=seu_pat_aqui
```

2. Substitua `seu_client_secret_aqui` pelo Client Secret real

### Opção 2: Variáveis de Ambiente

No Windows (PowerShell):
```powershell
$env:USE_SHAREPOINT="True"
$env:SHAREPOINT_SITE_URL="https://qualiitcombr.sharepoint.com/sites/projetosqualiit"
$env:SHAREPOINT_CLIENT_ID="2a41ace8-8b14-42db-808e-8681331138f5"
$env:SHAREPOINT_CLIENT_SECRET="seu_client_secret_aqui"
$env:SHAREPOINT_TENANT_ID="6eb6a2fd-839d-460d-9bb0-7ed15211a782"
```

No Linux/Mac:
```bash
export USE_SHAREPOINT=True
export SHAREPOINT_SITE_URL="https://qualiitcombr.sharepoint.com/sites/projetosqualiit"
export SHAREPOINT_CLIENT_ID="2a41ace8-8b14-42db-808e-8681331138f5"
export SHAREPOINT_CLIENT_SECRET="seu_client_secret_aqui"
export SHAREPOINT_TENANT_ID="6eb6a2fd-839d-460d-9bb0-7ed15211a782"
```

## 🚀 Execução

### Windows

**Método 1: Script Batch (Mais Fácil)**
```cmd
cd backend
test_sharepoint_local.bat
```

**Método 2: Manual**
```cmd
cd backend
python test_sharepoint_path.py
```

### Linux/Mac

**Método 1: Script Shell (Mais Fácil)**
```bash
chmod +x backend/test_sharepoint_local.sh
./backend/test_sharepoint_local.sh
```

**Método 2: Manual**
```bash
cd backend
python3 test_sharepoint_path.py
```

## 📊 O que o Script Faz

1. **Valida configuração** - Verifica se todas as variáveis estão configuradas
2. **Conecta ao SharePoint** - Testa autenticação
3. **Lista conteúdo da raiz** - Mostra pastas e arquivos na raiz
4. **Busca recursiva** - Procura arquivos .mpp em todas as pastas (até 3 níveis)
5. **Recomenda caminho** - Sugere o caminho correto para usar na pipeline

## 📝 Exemplo de Saída

```
================================================================================
  🔍 DESCOBRINDO CAMINHO CORRETO DO SHAREPOINT
================================================================================

📋 Validando configuração...
✅ Configuração validada
   Site URL: https://qualiitcombr.sharepoint.com/sites/projetosqualiit
   Folder Path: Documentos Compartilhados/Cronogramas - Project

🔌 Conectando ao SharePoint...
✅ Conectado com sucesso!

================================================================================
  📁 CONTEÚDO DA RAIZ
================================================================================

📁 Listando conteúdo da raiz:

📁 Pastas encontradas (3):
   - Documentos Compartilhados
   - Imagens
   - Outros

⚠️  Nenhum arquivo .mpp encontrado neste nível

================================================================================
  🔍 BUSCANDO ARQUIVOS .MPP RECURSIVAMENTE
================================================================================

🔍 Buscando em: Documentos Compartilhados
✅ Pasta encontrada: Documentos Compartilhados

📁 Pastas encontradas (2):
   - Cronogramas - Project
   - Outros Documentos

⚠️  Nenhum arquivo .mpp encontrado neste nível

🔍 Buscando em: Documentos Compartilhados/Cronogramas - Project
✅ Pasta encontrada: Documentos Compartilhados/Cronogramas - Project

📄 Arquivos .mpp encontrados (5):
   - 15404 - Projeto Exemplo.mpp (2.5 MB) - Modificado: 2025-12-10T10:30:00Z
   - 15405 - Outro Projeto.mpp (1.8 MB) - Modificado: 2025-12-11T14:20:00Z
   ...

================================================================================
  📊 RESULTADOS DA BUSCA
================================================================================

✅ Encontrados 5 arquivo(s) .mpp em 1 pasta(s):

📁 Pasta: Documentos Compartilhados/Cronogramas - Project
   Arquivos .mpp: 5
      - 15404 - Projeto Exemplo.mpp (2.5 MB)
      - 15405 - Outro Projeto.mpp (1.8 MB)
      ...

================================================================================
  💡 RECOMENDAÇÃO
================================================================================

✅ Todos os arquivos estão na pasta: Documentos Compartilhados/Cronogramas - Project

📝 Configure a variável SHAREPOINT_FOLDER_PATH como:
   Documentos Compartilhados/Cronogramas - Project
```

## ✅ Após Executar o Script

1. **Copie o caminho recomendado** mostrado no final
2. **Configure na pipeline**:
   - Vá em Pipelines → Pipelines → [Sua Pipeline] → Edit → Variables
   - Encontre `SHAREPOINT_FOLDER_PATH`
   - Cole o caminho recomendado
   - Salve

3. **Execute a pipeline novamente** - Agora deve encontrar os arquivos!

## 🐛 Troubleshooting

### Erro: "USE_SHAREPOINT não está configurado"

**Solução**: Configure as variáveis de ambiente ou crie o arquivo `.env`

### Erro: "Erro de autenticação"

**Solução**: 
- Verifique se o Client Secret está correto
- Verifique se não expirou
- Verifique se as permissões do App Registration estão corretas

### Erro: "Site não encontrado"

**Solução**: 
- Verifique se `SHAREPOINT_SITE_URL` está correto
- Formato esperado: `https://qualiitcombr.sharepoint.com/sites/projetosqualiit`

### Nenhum arquivo .mpp encontrado

**Solução**: 
- Verifique se há arquivos .mpp no SharePoint
- Verifique se as permissões do App Registration incluem acesso aos arquivos
- Verifique se o caminho do site está correto

## 📚 Próximos Passos

Após descobrir o caminho correto:
1. Configure `SHAREPOINT_FOLDER_PATH` na pipeline
2. Execute a pipeline
3. Verifique se os arquivos são processados corretamente

