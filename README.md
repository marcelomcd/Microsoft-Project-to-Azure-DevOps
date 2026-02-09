# Microsoft Project to Azure DevOps Converter

Sistema automatizado para sincronizar arquivos `.mpp` (Microsoft Project) do SharePoint com Work Items no Azure DevOps, criando e atualizando User Stories e Tasks automaticamente via pipeline agendada.

## 📋 Índice

1. [Visão Geral](#visao-geral)
2. [Arquitetura do Sistema](#arquitetura-do-sistema)
3. [Pré-requisitos](#pre-requisitos)
4. [Instalação](#instalacao)
5. [Configuração](#configuracao)
6. [Funcionamento](#funcionamento)
7. [Estrutura do Projeto](#estrutura-do-projeto)
8. [Troubleshooting](#troubleshooting)
9. [Referência Rápida](#referencia-rapida)

---

<a id="visao-geral"></a>
## 🎯 Visão Geral

### Funcionalidades Principais

- ✅ **Sincronização Automatizada**: Pipeline agendada executa diariamente às 6:30h BRT
- ✅ **Verificação de Alterações**: Processa apenas arquivos modificados desde a última sincronização
- ✅ **Integração SharePoint**: Busca e processa arquivos `.mpp` automaticamente do SharePoint (pasta principal e subpastas de clientes)
- ✅ **Identificação Automática**: Extrai Feature ID dos primeiros 5 dígitos do nome do arquivo
- ✅ **Busca Inteligente**: Busca User Stories e Tasks pelo nome exato antes de criar
- ✅ **Atualização Condicional**: Atualiza apenas se o arquivo foi modificado recentemente
- ✅ **Hierarquia Preservada**: Mantém Tasks vinculadas às User Stories corretas
- ✅ **Detecção de Duplicatas**: Evita criar itens duplicados no Azure DevOps
- ✅ **Horas de Trabalho**: Converte automaticamente horas do campo "Trabalho" do MPP para "Original Estimate" nas Tasks
- ✅ **Histórico de Sincronização**: Mantém registro completo de todas as operações
- ✅ **Relatórios em HTML**: Logs de sincronização apenas em HTML, nomeados pelo ID da Feature (ex: `16073.html`), para análise futura
- ✅ **Cache Otimizado**: Sistema de cache para melhor performance
- ✅ **Notificação Teams**: Mensagem no Teams (chat 1:1) para cada PMO às 8h BRT com tasks fechadas no DevOps que não estavam no .mpp e **links dos arquivos .mpp no SharePoint** para edição (pipeline opcional separada)

### Tecnologias Utilizadas

- **Backend**: Python 3.10+, FastAPI, Pydantic
- **Parsing MPP**: MPXJ (Java) via CLI
- **Integração**: Azure DevOps REST API, Microsoft Graph API (SharePoint, Teams)
- **Pipeline**: Azure DevOps Pipelines (YAML) — sync 6:30 BRT, notificação Teams 8h BRT (opcional)
- **Autenticação**: OAuth2 (Microsoft Entra ID), PAT (Azure DevOps)

---

<a id="arquitetura-do-sistema"></a>
## 🏗️ Arquitetura do Sistema

### Fluxo de Execução

```
SharePoint (arquivos .mpp)
    ↓
Pipeline Azure DevOps (agendada)
    ↓
pipeline_sync.py (orquestrador)
    ↓
SharePointFileService (download)
    ↓
MPPParser (parse via Java MPXJ)
    ↓
FileProcessor (processamento)
    ↓
MapperService (conversão)
    ↓
AzureDevOpsClient (API)
    ↓
Azure DevOps (Work Items)
```

**Notificação Teams (opcional):** Uma segunda pipeline agendada às **8h BRT** baixa o relatório `closed_tasks_report.json` da sync e envia mensagem no **Teams** (chat 1:1) para cada PMO com a lista de tasks fechadas e links dos .mpp no SharePoint. Ver [Configuração – Notificação Teams](#variáveis-para-notificação-teams-opcional-pipeline-8h).

### Componentes Principais

1. **`pipeline_sync.py`**: Script principal executado pela pipeline
2. **`MPPParser`**: Faz parse dos arquivos .mpp usando MPXJ (Java)
3. **`FileProcessor`**: Orquestra o processamento completo
4. **`MapperService`**: Converte dados MPP para Work Items do Azure DevOps
5. **`AzureDevOpsClient`**: Cliente REST para Azure DevOps API
6. **`SharePointFileService`**: Gerencia download de arquivos do SharePoint
7. **`SyncHistoryService`**: Mantém histórico de sincronizações
8. **`SyncLogger`**: Gera relatórios HTML de sincronização (nomeados pelo ID da Feature)
9. **`teams_notify.py`**: Envia notificação no Teams para PMOs (tasks fechadas + links .mpp no SharePoint), executado pela pipeline das 8h

---

<a id="pre-requisitos"></a>
## 📋 Pré-requisitos

- **Python 3.10+**
- **Java JDK 11+** (necessário para parsing de arquivos .mpp via MPXJ)
- **Conta Azure DevOps** com PAT (Personal Access Token) com permissões de Work Items (Read & Write)
- **App Registration** no Microsoft Entra ID (para acesso ao SharePoint)

---

<a id="instalacao"></a>
## 🛠️ Instalação

### Instalação Local (para testes)

```bash
# 1. Criar ambiente virtual
cd backend
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows

# 2. Instalar dependências
pip install -r requirements.txt

# 3. Configurar variáveis de ambiente
cp env.example.txt .env
# Editar .env com suas credenciais
```

---

<a id="configuracao"></a>
## ⚙️ Configuração

### Configuração Local (para testes)

Crie o arquivo `backend/.env` com as seguintes variáveis:

```env
# Azure DevOps
AZURE_DEVOPS_ORG=sua_organizacao
AZURE_DEVOPS_PROJECT=seu_projeto
AZURE_DEVOPS_PAT=seu_pat_token_aqui

# SharePoint (opcional para testes locais)
USE_SHAREPOINT=True
SHAREPOINT_SITE_URL=https://seu-tenant.sharepoint.com/sites/seu-site
SHAREPOINT_FOLDER_PATH=nome_da_pasta
SHAREPOINT_CLIENT_ID=seu_client_id
SHAREPOINT_CLIENT_SECRET=seu_client_secret
SHAREPOINT_TENANT_ID=seu_tenant_id

# Outras
LOG_LEVEL=INFO
API_TIMEOUT=30
```

### Configuração da Pipeline Azure DevOps

A pipeline está configurada para executar:
- **Agendamento**: Diariamente às 6:30h BRT
  - 6:30h BRT = 9:30h UTC
- **Verificação de Alterações**: Processa apenas arquivos modificados desde a última sincronização
- **Ambiente**: Ubuntu Latest
- **Python**: 3.10 (pré-instalado no agente; evita download e token GitHub)
- **Java**: JDK 11

#### Variáveis Obrigatórias para SharePoint

Configure as seguintes variáveis em **Edit** → **Variables**:

1. **`USE_SHAREPOINT`**
   - **Valor**: `true`
   - **Tipo**: String (será convertido para boolean automaticamente)
   - **Secreto**: ❌ Não

2. **`SHAREPOINT_SITE_URL`**
   - **Valor**: URL completa do site SharePoint
   - **Tipo**: String
   - **Secreto**: ❌ Não
   - **Nota**: Use o formato `https://tenant.sharepoint.com/sites/site-name` (não `tenant-my.sharepoint.com`)

3. **`SHAREPOINT_FOLDER_PATH`**
   - **Valor**: Nome da pasta principal dentro da biblioteca de documentos (ex.: `Cronogramas - Project`)
   - **Tipo**: String
   - **Secreto**: ❌ Não
   - **Importante**: Não inclua o nome da biblioteca no caminho; o código já seleciona a biblioteca. Os arquivos `.mpp` são buscados **na pasta principal e em todas as subpastas** (ex.: pastas com nome do cliente).

4. **`SHAREPOINT_CLIENT_ID`**
   - **Valor**: Client ID do App Registration
   - **Tipo**: String
   - **Secreto**: ❌ Não (mas pode ser marcado como secreto por segurança)

5. **`SHAREPOINT_CLIENT_SECRET`**
   - **Valor**: Client Secret do App Registration
   - **Tipo**: String
   - **Secreto**: ✅ **SIM** (marque como secreto)
   - **Importante**: Use o **VALOR** do secret, não o ID. O valor é mostrado apenas uma vez ao criar no Azure Portal.

6. **`SHAREPOINT_TENANT_ID`**
   - **Valor**: Tenant ID do Microsoft Entra ID
   - **Tipo**: String
   - **Secreto**: ❌ Não (mas pode ser marcado como secreto por segurança)

#### Variáveis Obrigatórias para Azure DevOps

7. **`AZURE_DEVOPS_PAT`**
   - **Valor**: Personal Access Token do Azure DevOps
   - **Tipo**: String
   - **Secreto**: ✅ **SIM** (marque como secreto)
   - **Permissões necessárias**: Work Items (Read & Write)

#### Variáveis Opcionais (com valores padrão)

8. **`AZURE_DEVOPS_ORG`**
   - **Valor**: Nome da organização (padrão configurado no código)
   - **Tipo**: String
   - **Secreto**: ❌ Não
   - **Nota**: Configure apenas se diferente do padrão

9. **`AZURE_DEVOPS_PROJECT`**
   - **Valor**: Nome do projeto (padrão configurado no código)
   - **Tipo**: String
   - **Secreto**: ❌ Não
   - **Nota**: Configure apenas se diferente do padrão

10. **`LOG_LEVEL`**
    - **Valor**: `INFO` (padrão)
    - **Tipo**: String
    - **Secreto**: ❌ Não
    - **Opções**: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`

#### Variáveis para Notificação Teams (opcional, pipeline 8h)

Para **replicar o seu `.env` local** nas pipelines do Azure DevOps (sem commitar segredos), use a lista completa em **[docs/PIPELINE_VARIABLES_AZURE_DEVOPS.md](docs/PIPELINE_VARIABLES_AZURE_DEVOPS.md)** — sync (6:30) e notificação Teams (8h).

11. **`TEAMS_NOTIFICATION_ENABLED`**
    - **Valor**: `true` para ativar envio de mensagem no Teams para PMOs (tasks fechadas no DevOps)

11.1. **`TEAMS_VERIFICATION_EMAIL`** (opcional)
    - **Valor**: E-mail que recebe uma **cópia consolidada** de tudo que foi enviado aos PMOs (ex: `marcelo.macedo@qualiit.com.br`), para verificar se o script/pipeline funcionou. Se o e-mail for também PMO, recebe um resumo do que foi enviado aos outros.
    - **Tipo**: String (convertido para boolean)
    - **Secreto**: ❌ Não

11.2. **`TEAMS_REFRESH_TOKEN`** (opcional, recomendado para envio no Teams)
    - **Valor**: Refresh token do **seu usuário** para enviar mensagens no Teams em seu nome (auth delegada). Evita o erro *"Creation of 'OneOnOne' chat requires 2 members"* que ocorre com credenciais só de aplicativo.
    - **Como obter**: No app no **Microsoft Entra ID** → Autenticação → adicione um redirect URI **Web**: `http://localhost:8400`. Depois execute **uma vez** `python scripts/get_teams_refresh_token.py` na pasta `backend` (com GRAPH_* ou SHAREPOINT_* no .env). O navegador abrirá para login; copie o valor exibido para o .env e, na pipeline, para uma variável secreta.
    - **App no Entra ID**: permissões delegadas **User.Read**, **Chat.Create** (e consentimento).
    - **Secreto**: ✅ Sim (não versionar; use variável secreta na pipeline).

12. **`GRAPH_CLIENT_ID`** / **`GRAPH_CLIENT_SECRET`** / **`GRAPH_TENANT_ID`**
    - **Valor**: Mesmo app do SharePoint ou um app com permissões **Microsoft Graph** (Application): `Chat.Create`, `ChatMessage.Send`. Admin consent obrigatório.
    - Se não preencher, o script usa `SHAREPOINT_CLIENT_ID`, `SHAREPOINT_CLIENT_SECRET`, `SHAREPOINT_TENANT_ID` (mesmo app deve ter as permissões Graph acima).

13. **`AZURE_DEVOPS_FEATURE_BOARD_BASE_URL`** (opcional)
    - **Valor**: URL base do board de **Features** usada nos links da mensagem do Teams (formato: `.../Features` sem `?workitem=`). Ex.: `https://dev.azure.com/qualiit/Quali%20IT%20-%20Inova%C3%A7%C3%A3o%20e%20Tecnologia/_boards/board/t/Quali%20IT%20!%20Gestao%20de%20Projeto/Features` → o link da Feature fica `{base}?workitem=10461`.
    - Se não definir, usa o link padrão `_workitems/edit/{id}`.
    - Os **links dos arquivos .mpp** na mensagem são as mesmas URLs de onde a sincronização lê os arquivos no SharePoint (mesmo local já usado pelo script).

14. **Pipeline de notificação (8h)**  
    - Crie uma **nova Pipeline** no Azure DevOps que use o arquivo **`azure-pipelines-teams-notify.yml`**.
    - Em **Resources** (ou no YAML), defina a variável **`SYNC_PIPELINE_NAME`** com o **nome exato** da pipeline de sincronização (6:30).
    - Agendamento: 8h BRT (11:00 UTC). A pipeline baixa o artefato `sync_logs` da última execução da pipeline de sync e executa `teams_notify.py`.

#### Teste local da notificação Teams
- **No uso real (pipeline 8h):** cada mensagem é enviada ao **responsável (Assigned To) de cada Feature** no Azure DevOps — um PMO por mensagem, com apenas as Features e tasks fechadas dele. O relatório `closed_tasks_report.json` é gerado pela sync com esses dados.
- **Teste local:** o script `test_teams_notify_local.py` gera um relatório de **exemplo** (Feature fictícia) e envia para um e-mail que você informar, **apenas para validar** se o envio no Teams está funcionando. Por padrão usa `jessica.barbosa@qualiit.com.br`; para outro destinatário: `python scripts/test_teams_notify_local.py --email outro@qualiit.com.br`.
- **Recomendado (envio como seu usuário):** Na pasta **`backend`**, execute **uma vez** `python scripts/get_teams_refresh_token.py`, faça login no navegador e copie o **TEAMS_REFRESH_TOKEN** para o `.env`. Depois defina **TEAMS_NOTIFICATION_ENABLED=true** e rode `python scripts/test_teams_notify_local.py`. As mensagens serão enviadas no Teams a partir da sua conta.
- Sem refresh token: com só client_id/secret, alguns tenants retornam *"Creation of 'OneOnOne' chat requires 2 members"*; use o refresh token (acima) para evitar isso.
- O script de teste grava o relatório de exemplo em `backend/logs/teams_notify_test/closed_tasks_report.json` e chama `teams_notify.py`; assim você confere no Teams se o envio está funcionando.

#### Passo a Passo para Configurar Variáveis

1. Acesse o Azure DevOps → **Pipelines** → Selecione sua pipeline
2. Clique em **Edit** (ou **⋮** → **Edit**)
3. Clique em **Variables** (no topo da página)
4. Para cada variável:
   - Clique em **+ New variable**
   - Digite o **nome** da variável
   - Digite o **valor**
   - Para variáveis secretas, marque **☑ Keep this value secret**
   - Clique em **OK**
5. Clique em **Save** para salvar a pipeline

### Configuração do SharePoint

#### App Registration no Microsoft Entra ID

Para configurar o acesso ao SharePoint, você precisa criar um App Registration:

1. Acesse o Azure Portal: https://portal.azure.com
2. Vá em **Microsoft Entra ID** → **App registrations**
3. Clique em **+ New registration**
4. Configure:
   - **Name**: Nome do app (ex: "MPP Sync SharePoint")
   - **Supported account types**: Accounts in this organizational directory only
   - **Redirect URI**: Deixe vazio (não necessário para app-only)
5. Após criar, anote o **Application (client) ID** → use em `SHAREPOINT_CLIENT_ID`
6. Anote o **Directory (tenant) ID** → use em `SHAREPOINT_TENANT_ID`
7. Vá em **Certificates & secrets** → **+ New client secret**
8. **Copie o VALOR do secret imediatamente** (não o ID) → use em `SHAREPOINT_CLIENT_SECRET`
9. Vá em **API permissions** → **+ Add a permission** → **Microsoft Graph** → **Application permissions**
10. Adicione as permissões:
    - `Sites.Read.All`
    - `Files.Read.All`
11. Clique em **Grant admin consent** para conceder as permissões

#### Verificação da Configuração

Após configurar, execute a pipeline manualmente e verifique os logs:

- ✅ Se encontrar a pasta, verá: `✅ Pasta encontrada: [nome da pasta]`
- ✅ Se encontrar arquivos .mpp (pasta principal + subpastas), verá: `📄 Encontrados X arquivo(s) .mpp (pasta principal + subpastas)`
- ✅ Se processar com sucesso, verá: `✅ Sincronização concluída`

### Segurança

- **NUNCA** commite secrets no código
- Use sempre variáveis secretas na pipeline
- Rotacione os secrets periodicamente
- Mantenha arquivos com secrets no `.gitignore`

---

<a id="funcionamento"></a>
## 🔄 Funcionamento

### Processo de Sincronização

1. **Agendamento**: Pipeline executa automaticamente diariamente às 6:30h BRT
   - Verifica se houve alterações nos arquivos antes de processar
   - Processa apenas arquivos modificados desde a última sincronização

2. **Busca de Arquivos**:
   - Se `USE_SHAREPOINT=true`: Busca arquivos `.mpp` no SharePoint na **pasta principal** configurada em `SHAREPOINT_FOLDER_PATH` e em **todas as subpastas** (ex.: pastas por cliente). Arquivos na raiz da pasta e dentro de cada subpasta são considerados.
   - Caso contrário: Busca em diretório local configurado

3. **Verificação de Histórico**:
   - Compara timestamp do arquivo com última sincronização
   - Ignora arquivos não modificados desde última execução
   - Evita processamento desnecessário

4. **Download e Parse**:
   - Baixa arquivo do SharePoint (se aplicável)
   - Faz parse usando MPXJ (Java) para extrair:
     - User Stories (tarefas sem recurso)
     - Tasks (tarefas com recurso)
     - Horas de trabalho (campo "Trabalho" em segundos)
     - Hierarquia (parent-child)

5. **Conversão de Horas**:
   - Converte horas do campo "Trabalho" (em segundos) para horas decimais
   - Exemplos: 1800 segundos = 0.5 hrs, 3600 segundos = 1.0 hrs, 28800 segundos = 8.0 hrs
   - Preenche campo "Original Estimate" nas Tasks do Azure DevOps
   - Apenas Tasks recebem horas (User Stories não)

6. **Extração de Feature ID**:
   - Extrai os primeiros 5 dígitos do nome do arquivo
   - Exemplo: `14320 025447-02 - Projeto...` → Feature ID: `14320`

7. **Busca de Duplicatas**:
   - Busca User Stories e Tasks existentes pelo nome exato
   - Usa WIQL query: `[System.Title] = 'nome exato' AND [System.Parent] = feature_id`

8. **Criação/Atualização**:
   - **Se não existe**: Cria novo Work Item
   - **Se existe e arquivo foi modificado**: Atualiza Work Item existente
   - **Se existe e arquivo não foi modificado**: Pula (não processa)

9. **Vinculação de Hierarquia**:
   - Tasks são vinculadas às User Stories corretas
   - Mantém estrutura: Feature → User Story → Task

10. **Registro de Histórico e Relatório**:
    - Salva timestamp da sincronização
    - Gera relatório em **HTML** (não mais .json ou .txt), nomeado pelo **ID da Feature** (ex: `16073.html`), em `backend/logs/`
    - O relatório inclui: referência no arquivo (User Stories/Tasks), já existiam na Feature, criados, atualizados, ignorados, erros (com motivo quando houver)

11. **Notificação Teams (opcional, 8h BRT)**:
    - Se houver Tasks que estão **Closed** no Azure DevOps mas não estavam no .mpp, a sync grava `backend/logs/closed_tasks_report.json` com o **Assigned To (PMO) de cada Feature**.
    - Uma **segunda pipeline** (azure-pipelines-teams-notify.yml) agendada às **8h BRT** baixa esse relatório e envia **mensagem no Teams** (chat 1:1) **para o responsável de cada Feature** (Assigned To no Azure DevOps): cada PMO recebe uma mensagem apenas com as Features e tasks fechadas das quais ele é responsável, mais os **links dos arquivos .mpp no SharePoint** para abrir e alterar (editar o .mpp no SharePoint é a boa prática).
    - Para cada PMO é gerado também um **log em HTML** com o corpo completo da mensagem enviada, em `logs/teams_notify/<email>.html` (ex: `jessica.barbosa_qualiit.com.br.html`), de forma estruturada e fácil de ler.

### Formato do Nome do Arquivo

O nome do arquivo `.mpp` deve seguir o padrão:

```
[5 dígitos] [resto do nome].mpp
```

**Exemplo**: `14320 025447-02 - Projeto - Descrição.mpp`
- Feature ID: `14320` (extraído dos primeiros 5 dígitos)
- Nome do projeto: `025447-02 - Projeto - Descrição`

### Lógica de Atualização

- **Arquivo modificado recentemente** → `update_existing=True` → Atualiza itens existentes
- **Arquivo não modificado** → Arquivo é ignorado (não processado)
- **Item não existe** → Sempre cria novo, independente de timestamp

### Estrutura do Arquivo .mpp

- **User Stories**: Tarefas sem recurso atribuído (coluna "Nomes dos recursos" vazia)
- **Tasks**: Tarefas com recurso atribuído (coluna "Nomes dos recursos" preenchida)
- **Horas de Trabalho**: Campo "Trabalho" do MPP (em segundos) é convertido automaticamente para horas
  - Conversão: segundos ÷ 3600 = horas (formato decimal)
  - Exemplos: 0.5 hrs (meia hora), 1.0 hrs, 8.0 hrs (oito horas)
  - Preenchido no campo "Original Estimate" das Tasks no Azure DevOps
- **Hierarquia**: Tasks são vinculadas às User Stories baseado na estrutura hierárquica do arquivo

### Notas Importantes

1. **Features nunca são criadas**: O sistema apenas busca Features existentes pelo ID extraído do nome do arquivo
2. **Busca por nome exato**: User Stories e Tasks são buscadas pelo título exato antes de criar
3. **Hierarquia preservada**: Tasks sempre são vinculadas às User Stories corretas
4. **Atualização condicional**: Itens são atualizados apenas se o arquivo foi modificado recentemente
5. **Cache**: Sistema usa cache para otimizar requisições à API do Azure DevOps

---

<a id="estrutura-do-projeto"></a>
## 📁 Estrutura do Projeto

```
.
├── backend/
│   ├── app/
│   │   ├── main.py              # Aplicação FastAPI
│   │   ├── config.py            # Configurações (Pydantic Settings)
│   │   ├── models/              # Modelos de dados (Pydantic)
│   │   │   ├── mpp_models.py    # Modelos de dados MPP
│   │   │   ├── devops_models.py # Modelos de dados Azure DevOps
│   │   │   └── sync_log.py      # Modelo de log de sincronização
│   │   ├── templates/           # Templates para relatórios
│   │   │   └── sync_report.html # Template HTML do relatório de sincronização
│   │   ├── services/            # Serviços principais
│   │   │   ├── devops_client.py     # Cliente Azure DevOps API
│   │   │   ├── file_processor.py    # Processador de arquivos
│   │   │   ├── mapper_service.py    # Conversão MPP → DevOps
│   │   │   ├── mpp_parser.py        # Parser de arquivos .mpp
│   │   │   ├── sharepoint_auth.py   # Autenticação SharePoint
│   │   │   ├── sharepoint_files.py  # Download de arquivos SharePoint
│   │   │   ├── sync_history.py      # Histórico de sincronizações
│   │   │   ├── sync_logger.py       # Logger de sincronização
│   │   │   └── workitem_analyzer.py # Analisador de Work Items
│   │   ├── routers/             # Endpoints da API
│   │   │   ├── convert.py       # Endpoint de conversão
│   │   │   ├── projects.py      # Endpoint de projetos
│   │   │   ├── upload.py        # Endpoint de upload
│   │   │   └── workitems.py     # Endpoint de work items
│   │   └── utils/                # Utilitários
│   │       ├── cache.py          # Sistema de cache
│   │       ├── resource_mapper.py # Mapeamento de recursos
│   │       └── validators.py     # Validações (nome de arquivo, etc.)
│   ├── lib/                      # Bibliotecas Java (MPXJ e dependências)
│   │   ├── mpxj.jar              # MPXJ (parsing MPP)
│   │   ├── MppToJson.java       # Script Java para conversão
│   │   ├── MppToJson.class      # Classe compilada Java
│   │   ├── poi.jar               # Apache POI (dependência MPXJ)
│   │   ├── poi-ooxml.jar        # Apache POI OOXML
│   │   ├── poi-scratchpad.jar   # Apache POI Scratchpad
│   │   ├── jackson-*.jar         # Jackson JSON (dependências)
│   │   ├── commons-*.jar        # Apache Commons (dependências)
│   │   └── log4j-*.jar          # Log4j (dependências)
│   ├── logs/                     # Relatórios HTML de sincronização (ex: 16073.html) e sync_history.json
│   ├── pipeline_sync.py          # Script principal para execução agendada
│   ├── test_sharepoint_path.py   # Script para descobrir caminho SharePoint
│   ├── requirements.txt          # Dependências Python
│   └── env.example.txt           # Exemplo de variáveis de ambiente
├── .gitignore                    # Arquivos ou pastas ignorados
├── azure-pipelines.yml           # Definição da pipeline Azure DevOps
└── README.md                     # Este arquivo
```

---

<a id="execucao"></a>
## 🚀 Execução

### Execução Local (para testes)

Para testar a sincronização localmente:

```bash
cd backend
python pipeline_sync.py
```

Ou para testar apenas a conexão com SharePoint:

```bash
cd backend
python test_sharepoint_path.py
```

### Execução Automatizada (Pipeline Azure DevOps)

O sistema suporta execução agendada via pipeline do Azure DevOps para processar arquivos .mpp automaticamente.

#### Características

- ✅ **Processamento Automático**: Executa de segunda a sexta-feira às 6:30h BRT (9:30h UTC)
- ✅ **Processamento Inteligente**: Processa apenas arquivos novos ou modificados
- ✅ **Histórico Persistente**: Mantém histórico de sincronização para evitar reprocessamento
- ✅ **Logs Detalhados**: Gera relatórios HTML por Feature (ex: `16073.html`) com estatísticas e detalhes de erros
- ✅ **Tratamento de Erros**: Continua processamento mesmo se alguns arquivos falharem

---

<a id="troubleshooting"></a>
## 🔍 Troubleshooting

### Erro: "404 Client Error: Not Found"

**Causa**: URL incorreta ou projeto não encontrado

**Solução**:
1. Verifique se `AZURE_DEVOPS_ORG` está configurado corretamente
2. Verifique se `AZURE_DEVOPS_PROJECT` está correto
3. Verifique se o PAT tem permissões adequadas

### Erro: "Feature [ID] não existe"

**Causa**: Feature não encontrada no Azure DevOps

**Solução**:
1. Verifique se a Feature existe no projeto correto
2. Verifique se o Feature ID extraído do nome do arquivo está correto (primeiros 5 dígitos)
3. Verifique permissões do PAT

### Erro: "Pasta não encontrada no SharePoint"

**Causa**: Caminho da pasta incorreto

**Solução**:
1. Execute `test_sharepoint_path.py` localmente para descobrir o caminho correto
2. Configure `SHAREPOINT_FOLDER_PATH` com o caminho exato
3. Verifique se o App Registration tem permissões no SharePoint
4. O código tenta automaticamente variações do caminho se necessário

### Erro: "Invalid client secret provided"

**Causa**: Client Secret incorreto

**Solução**:
1. Use o **VALOR** do secret, não o ID
2. O valor é mostrado apenas uma vez ao criar no Azure Portal
3. Se necessário, crie um novo secret e atualize a variável

### Erro: "Java não está disponível"

**Causa**: Java não instalado ou não no PATH

**Solução**:
1. Instale Java JDK 11+
2. Verifique se `java -version` funciona
3. Na pipeline, o Java é instalado automaticamente

### Arquivos não estão sendo processados

**Causa**: Arquivos não modificados desde última sincronização

**Solução**:
- Este é o comportamento esperado
- Arquivos são processados apenas se foram modificados
- Para forçar processamento, delete o histórico em `backend/logs/sync_history.json`

---

<a id="referencia-rapida"></a>
## 📖 Referência Rápida

### Comandos Úteis

```bash
# Testar conexão SharePoint localmente
cd backend
python test_sharepoint_path.py

# Executar pipeline localmente (simulação)
python pipeline_sync.py

# Verificar histórico de sincronização
cat backend/logs/sync_history.json

# Relatórios de sincronização (um HTML por Feature, ex: 16073.html)
ls backend/logs/*.html
```

### Formato de Nome de Arquivo

```
[5 dígitos] [resto do nome].mpp
```

**Exemplo válido**: `14320 025447-02 - Projeto - Descrição.mpp`

### Variáveis Críticas

- `AZURE_DEVOPS_PAT`: Token de autenticação (obrigatório, secreto)
- `USE_SHAREPOINT`: Habilita/desabilita SharePoint (true/false)
- `SHAREPOINT_FOLDER_PATH`: Pasta principal no SharePoint (arquivos também são buscados nas subpastas)
- `SHAREPOINT_CLIENT_SECRET`: Client Secret do App Registration (obrigatório, secreto)

### Horário de Execução

- **Agendamento**: Diariamente
- **Horário**: 6:30h BRT (9:30h UTC)
- **Frequência**: Uma vez por dia
- **Verificação de Alterações**: Processa apenas arquivos modificados

### Funcionalidades Técnicas

- **Cache**: Cache de projetos (TTL: 60 minutos), work items (TTL: 30 minutos), parsing MPP (TTL: 120 minutos)
- **Connection Pooling**: Reutilização de conexões HTTP com retry automático
- **Qualidade de Código**: Clean Code, SOLID, type hints, testes unitários, análise estática

---

## 📄 Licença

Este projeto é de uso interno.

---

## 🆘 Suporte

Para problemas ou dúvidas:
1. Verifique o histórico em `backend/logs/sync_history.json` e os relatórios HTML em `backend/logs/` (ex: `16073.html` por Feature)
2. Execute `test_sharepoint_path.py` para testar conexão SharePoint
3. Verifique as variáveis da pipeline no Azure DevOps
4. Consulte a seção [Troubleshooting](#troubleshooting)

---

**Última atualização**: 09/02/2026  
**Versão**: 1.1.0  

### Histórico de versões

| Versão | Data | Alterações |
|--------|------|------------|
| **1.1.0** | 09/02/2026 | Notificação Teams: mensagem no Teams (chat 1:1) para cada PMO às 8h BRT com tasks fechadas no DevOps que não estavam no .mpp; links dos arquivos .mpp no SharePoint na mensagem; link da Feature no board do Azure DevOps (formato `.../Features?workitem=ID`). Pipeline opcional 8h (azure-pipelines-teams-notify.yml). |
| **1.0.6** | 09/02/2026 | Sync considera pasta principal e subpastas no SharePoint (um nível, por cliente). Chave de histórico por pasta. README com nova lógica e variável SHAREPOINT_FOLDER_PATH. Regra de commit/push para Azure DevOps. Pasta .cursor no .gitignore. |
| **1.0.5** | 06/02/2026 | Relatório de sync: Task em amarelo, User Story em azul; recurso "Cliente" apenas no template. Ajustes no resource mapper (Vladimir Davelli). |
| **1.0.4** | 06/02/2026 | Logs HTML: dados de Task (recurso, datas, horas), cores PT-BR e formatação. Atualizações SharePoint e guia MPP. Requirements e documentação. |
| **1.0.3** | 06/02/2026 | Logs apenas em HTML nomeados pelo ID da Feature (ex: `16073.html`). GITHUB_ACCESS_TOKEN para Python na pipeline. Pipeline ajustada para Python 3.10 (pré-instalado no agente). Remoção de sync_report_v2.html. |
| **1.0.2** | 15/01–19/01/2026 | Mapeamento de Status do MPP para State do Azure DevOps. Proteção de Tasks Closed/Resolved/Removed (não reabertar). Tarefas com recurso "Cliente" sem responsável atribuído. Resource mapper (Tiago Oliveira e outros). Pipeline diária às 6:30 BRT. |
| **1.0.1** | 17/12/2025 | Conversão de horas do campo "Trabalho" do MPP para "Original Estimate" nas Tasks (segundos → horas). Pipeline agendada diariamente às 6:30 BRT. Documentação de horários e versão. |
| **1.0.0** | 12/2025 | Versão inicial: sincronização de arquivos .mpp (SharePoint ou local) com Azure DevOps; parsing via MPXJ (Java); criação/atualização de User Stories e Tasks; extração de Feature ID do nome do arquivo; busca por nome exato; histórico de sincronização; atualização condicional por timestamp; integração SharePoint (OAuth2) e pipeline Azure DevOps. |

**Desenvolvido por**: Marcelo Macedo  
**E-mail**: [marcelo.macedo@qualiit.com.br](mailto:marcelo.macedo@qualiit.com.br)