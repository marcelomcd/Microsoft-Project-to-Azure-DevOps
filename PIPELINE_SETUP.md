# Configuração da Pipeline de Sincronização Agendada

Este documento descreve como configurar e executar a pipeline de sincronização agendada no Azure DevOps para processar arquivos .mpp automaticamente.

## Visão Geral

A pipeline executa diariamente às **6:00h (horário de Brasília)** e processa arquivos .mpp de um diretório configurado, sincronizando User Stories e Tasks com o Azure DevOps.

### Funcionalidades

- **Processamento Inteligente**: Processa apenas arquivos novos ou modificados desde a última sincronização
- **Histórico Persistente**: Mantém histórico de sincronização para evitar reprocessamento desnecessário
- **Logs Detalhados**: Gera logs completos de todas as operações
- **Tratamento de Erros**: Continua processamento mesmo se alguns arquivos falharem
- **Relatórios**: Gera relatórios detalhados de cada execução

## Pré-requisitos

1. **Azure DevOps Organization** configurada
2. **Repositório** no Azure Repos com o código deste projeto
3. **Personal Access Token (PAT)** com permissões para:
   - Leitura e escrita de Work Items
   - Leitura de projetos
4. **Diretório de arquivos .mpp** acessível pela pipeline
5. **Agente de pipeline** com:
   - Python 3.9+
   - Java JDK 11+
   - Acesso ao diretório de arquivos .mpp (se em network share)

## Configuração da Pipeline

### 1. Criar Pipeline no Azure DevOps

1. No Azure DevOps, vá para **Pipelines** > **New Pipeline**
2. Selecione seu repositório (Azure Repos)
3. Escolha **Existing Azure Pipelines YAML file**
4. Selecione o branch e o arquivo `azure-pipelines.yml`
5. Salve a pipeline

### 2. Configurar Variáveis de Ambiente

Configure as seguintes variáveis na pipeline (Pipeline Variables ou Variable Groups):

#### Variáveis Obrigatórias

**Para Azure DevOps:**
| Variável | Descrição | Exemplo | Secreto? |
|----------|-----------|---------|----------|
| `AZURE_DEVOPS_PAT` | Personal Access Token do Azure DevOps | `your-pat-token` | ✅ Sim |

**Para SharePoint (se `USE_SHAREPOINT=True`):**
| Variável | Descrição | Exemplo | Secreto? |
|----------|-----------|---------|----------|
| `SHAREPOINT_CLIENT_ID` | Client ID (Application ID) do Microsoft Entra ID | `2a41ace8-8b14-42db-808e-8681331138f5` | ❌ Não |
| `SHAREPOINT_CLIENT_SECRET` | Client Secret do Microsoft Entra ID | `4K88Q~u8vqfCeG5-OXUQ9QE6jDdI2GlS.jDRvcG2` | ✅ Sim |
| `SHAREPOINT_TENANT_ID` | Tenant ID (Directory ID) do Microsoft Entra ID | `6eb6a2fd-839d-460d-9bb0-7ed15211a782` | ❌ Não |
| `SHAREPOINT_SITE_URL` | URL do site SharePoint | `https://qualiitcombr-my.sharepoint.com/sites/projetosqualiit` | ❌ Não |

**Para diretório local (se `USE_SHAREPOINT=False`):**
| Variável | Descrição | Exemplo | Secreto? |
|----------|-----------|---------|----------|
| `MPP_FILES_DIR` | Caminho do diretório onde os arquivos .mpp estão localizados | `/mnt/shared/mpp_files` ou `C:\mpp_files` | ❌ Não |

#### Variáveis Opcionais

| Variável | Descrição | Padrão | Secreto? |
|----------|-----------|--------|----------|
| `USE_SHAREPOINT` | Se True, usa SharePoint. Se False, usa diretório local | `False` | ❌ Não |
| `SHAREPOINT_FOLDER_PATH` | Caminho da pasta no SharePoint | `Documentos Compartilhados/Cronogramas - Project` | ❌ Não |
| `AZURE_DEVOPS_ORG` | Nome da organização Azure DevOps | `qualiit` | ❌ Não |
| `AZURE_DEVOPS_PROJECT` | Nome do projeto Azure DevOps | `Quali IT - Inovação e Tecnologia` | ❌ Não |
| `LOG_LEVEL` | Nível de log (DEBUG, INFO, WARNING, ERROR) | `INFO` | ❌ Não |

#### Como Configurar Variáveis

**Método 1: Pipeline Variables (Recomendado para PAT)**

1. Vá para a pipeline
2. Clique em **Edit** > **Variables**
3. Adicione cada variável:
   - **Name**: Nome da variável (ex: `AZURE_DEVOPS_PAT`)
   - **Value**: Valor da variável
   - **Keep this value secret**: ✅ Marcar para PAT

**Método 2: Variable Groups**

1. Vá para **Pipelines** > **Library**
2. Crie um novo **Variable Group** (ex: `MPP_SYNC_VARIABLES`)
3. Adicione todas as variáveis
4. No `azure-pipelines.yml`, descomente a linha `- group: MPP_SYNC_VARIABLES`

### 3. Configurar Agendamento

O agendamento já está configurado no `azure-pipelines.yml` para executar às **6:00h (horário de Brasília)** todos os dias.

Para alterar o horário, edite a linha `cron: "0 9 * * *"` no arquivo:
- Formato: `minuto hora dia mês dia_da_semana`
- Exemplo: `0 9 * * *` = 9:00h UTC (6:00h BRT)
- **Nota**: Azure DevOps usa UTC. Para 6:00h BRT, use 9:00h UTC

Conversão de horários:
- 6:00h BRT = 9:00h UTC
- 8:00h BRT = 11:00h UTC
- 12:00h BRT = 15:00h UTC

### 4. Configurar Fonte de Arquivos

Escolha entre SharePoint ou diretório local configurando `USE_SHAREPOINT`.

#### Opção 1: SharePoint (Recomendado)

1. Configure `USE_SHAREPOINT=True`
2. Configure todas as variáveis do SharePoint (veja tabela acima)
3. Configure `SHAREPOINT_SITE_URL` com a URL do site SharePoint
4. Configure `SHAREPOINT_FOLDER_PATH` com o caminho da pasta (padrão: `Documentos Compartilhados/Cronogramas - Project`)

**Exemplo de configuração:**
```
USE_SHAREPOINT=True
SHAREPOINT_CLIENT_ID=2a41ace8-8b14-42db-808e-8681331138f5
SHAREPOINT_CLIENT_SECRET=4K88Q~u8vqfCeG5-OXUQ9QE6jDdI2GlS.jDRvcG2
SHAREPOINT_TENANT_ID=6eb6a2fd-839d-460d-9bb0-7ed15211a782
SHAREPOINT_SITE_URL=https://qualiitcombr-my.sharepoint.com/sites/projetosqualiit
SHAREPOINT_FOLDER_PATH=Documentos Compartilhados/Cronogramas - Project
```

**Permissões necessárias no Microsoft Entra ID:**
- O aplicativo deve ter permissões de leitura no SharePoint
- Configure em "API permissions" do app registration:
  - `Sites.Read.All` (Microsoft Graph)
  - `Files.Read.All` (Microsoft Graph)

#### Opção 2: Diretório Local

1. Configure `USE_SHAREPOINT=False`
2. Configure `MPP_FILES_DIR` com o caminho do diretório

**Se o diretório está em um network share:**
- Configure mapeamento de rede no agente (se self-hosted)
- Ou monte o share no pipeline antes de executar o script
- Use caminho absoluto: `/mnt/shared/mpp_files` (Linux) ou `\\server\share\mpp_files` (Windows)

**Se o diretório está no próprio repositório:**
- Configure `MPP_FILES_DIR` para o caminho relativo: `backend/uploads`

## Estrutura do Histórico de Sincronização

O histórico é armazenado em `backend/logs/sync_history.json`:

```json
{
  "version": "1.0",
  "last_updated": "2024-01-15T09:00:00-03:00",
  "files": {
    "15404 Projeto Exemplo.mpp": {
      "sync_count": 5,
      "first_sync": "2024-01-10T09:00:00-03:00",
      "last_sync": "2024-01-15T09:00:00-03:00",
      "last_modified": "2024-01-15T08:30:00-03:00",
      "work_item_id": 15404
    }
  }
}
```

### Quando um arquivo é processado?

Um arquivo é processado se:
1. **Não está no histórico** (arquivo novo)
2. **Foi modificado** desde a última sincronização (compara timestamp de modificação)

## Logs e Relatórios

### Logs de Execução

Os logs são salvos em `backend/logs/`:
- `sync_history.json` - Histórico de sincronização
- `sync_{sync_id}.json` - Log detalhado de cada sincronização
- `sync_{sync_id}_summary.txt` - Resumo legível de cada sincronização

### Artefatos da Pipeline

A pipeline publica os logs como artefatos:
- Nome: `sync_logs`
- Conteúdo: Diretório `backend/logs/` completo

Para acessar:
1. Execute a pipeline
2. Na execução, vá para **Artifacts**
3. Baixe `sync_logs`

## Execução Manual

Para executar a pipeline manualmente:

1. Vá para a pipeline no Azure DevOps
2. Clique em **Run pipeline**
3. Selecione o branch (geralmente `main` ou `master`)
4. Clique em **Run**

## Troubleshooting

### Pipeline falha ao iniciar

**Problema**: Erro "AZURE_DEVOPS_PAT não está configurado"

**Solução**:
- Verifique se a variável `AZURE_DEVOPS_PAT` está configurada
- Verifique se está marcada como "Keep this value secret" se necessário
- Teste o PAT manualmente usando a API do Azure DevOps

### Pipeline não encontra arquivos

**Problema**: "Nenhum arquivo .mpp encontrado no diretório especificado"

**Solução**:
- Verifique se `MPP_FILES_DIR` está configurado corretamente
- Verifique se o diretório existe e é acessível
- Teste o caminho manualmente no agente

### Arquivos não são processados

**Problema**: Arquivos existem mas não são processados

**Solução**:
- Verifique o histórico em `sync_history.json`
- Um arquivo só é processado se for novo ou modificado
- Para forçar reprocessamento, remova a entrada do histórico

### Erro de autenticação

**Problema**: Erro ao acessar Azure DevOps API

**Solução**:
- Verifique se o PAT está válido e não expirou
- Verifique se o PAT tem permissões necessárias:
  - Work Items (Read & Write)
  - Projects and Teams (Read)
- Regenerate o PAT se necessário

### Erro de Java

**Problema**: "Java não encontrado" ou erro ao usar MPXJ

**Solução**:
- Verifique se Java JDK 11+ está instalado no agente
- Se usar self-hosted agent, instale Java
- Se usar Microsoft-hosted agent, o Java é instalado automaticamente pelo step `JavaToolInstaller@0`

### Erro de timezone

**Problema**: Comparação de timestamps incorreta

**Solução**:
- Verifique se `TIMEZONE` está configurado corretamente (padrão: `America/Sao_Paulo`)
- Para outros timezones, use formato IANA: `America/New_York`, `Europe/London`, etc.

### Histórico corrompido

**Problema**: Erro ao carregar histórico

**Solução**:
- O sistema automaticamente cria um novo histórico se o arquivo estiver corrompido
- Para resetar completamente, delete `backend/logs/sync_history.json`
- Todos os arquivos serão processados na próxima execução

## Execução Local (Desenvolvimento/Testes)

Para testar localmente antes de configurar a pipeline:

```bash
# Configurar variáveis de ambiente
export AZURE_DEVOPS_PAT="seu-pat-aqui"
export MPP_FILES_DIR="/caminho/para/arquivos"
export AZURE_DEVOPS_ORG="sua-org"
export AZURE_DEVOPS_PROJECT="seu-projeto"

# Executar script
cd backend
python pipeline_sync.py
```

Ou use o script refatorado:

```bash
cd backend
python sync_all_mpp_files.py
```

## Monitoramento

### Verificar Última Execução

1. Vá para a pipeline no Azure DevOps
2. Veja a última execução e seu status
3. Clique para ver logs detalhados

### Verificar Histórico

1. Baixe os artefatos da última execução
2. Abra `sync_logs/sync_history.json`
3. Verifique quais arquivos foram processados

### Alertas (Opcional)

Configure alertas no Azure DevOps para:
- Pipeline falhada
- Pipeline não executada por X dias

## Boas Práticas

1. **Teste Localmente Primeiro**: Sempre teste mudanças localmente antes de fazer commit
2. **Backup do Histórico**: Faça backup periódico de `sync_history.json`
3. **Monitoramento**: Verifique logs regularmente para identificar problemas
4. **Validação de Arquivos**: Garanta que arquivos .mpp seguem o formato esperado (Work Item ID nos primeiros 5 dígitos)
5. **PAT Seguro**: Nunca commite o PAT no código. Sempre use variáveis secretas
6. **Logs**: Mantenha logs por período razoável (pode configurar retenção no Azure DevOps)

## Suporte

Para problemas ou dúvidas:
1. Verifique os logs da pipeline
2. Verifique o histórico de sincronização
3. Execute o script localmente para debug
4. Consulte a documentação do código

