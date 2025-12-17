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

- ✅ **Sincronização Automatizada**: Pipeline agendada executa de segunda a sexta-feira às 6:00h, 12:00h e 18:00h BRT
- ✅ **Verificação de Alterações**: Processa apenas arquivos modificados desde a última sincronização
- ✅ **Integração SharePoint**: Busca e processa arquivos `.mpp` automaticamente do SharePoint
- ✅ **Identificação Automática**: Extrai Feature ID dos primeiros 5 dígitos do nome do arquivo
- ✅ **Busca Inteligente**: Busca User Stories e Tasks pelo nome exato antes de criar
- ✅ **Atualização Condicional**: Atualiza apenas se o arquivo foi modificado recentemente
- ✅ **Hierarquia Preservada**: Mantém Tasks vinculadas às User Stories corretas
- ✅ **Detecção de Duplicatas**: Evita criar itens duplicados no Azure DevOps
- ✅ **Horas de Trabalho**: Converte automaticamente horas do campo "Trabalho" do MPP para "Original Estimate" nas Tasks
- ✅ **Histórico de Sincronização**: Mantém registro completo de todas as operações
- ✅ **Cache Otimizado**: Sistema de cache para melhor performance

### Tecnologias Utilizadas

- **Backend**: Python 3.9+, FastAPI, Pydantic
- **Parsing MPP**: MPXJ (Java) via CLI
- **Integração**: Azure DevOps REST API, Microsoft Graph API (SharePoint)
- **Pipeline**: Azure DevOps Pipelines (YAML)
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

### Componentes Principais

1. **`pipeline_sync.py`**: Script principal executado pela pipeline
2. **`MPPParser`**: Faz parse dos arquivos .mpp usando MPXJ (Java)
3. **`FileProcessor`**: Orquestra o processamento completo
4. **`MapperService`**: Converte dados MPP para Work Items do Azure DevOps
5. **`AzureDevOpsClient`**: Cliente REST para Azure DevOps API
6. **`SharePointFileService`**: Gerencia download de arquivos do SharePoint
7. **`SyncHistoryService`**: Mantém histórico de sincronizações

---

<a id="pre-requisitos"></a>
## 📋 Pré-requisitos

- **Python 3.9+**
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
- **Agendamento**: Segunda a sexta-feira às 6:00h, 12:00h e 18:00h BRT
  - 6:00h BRT = 9:00h UTC
  - 12:00h BRT = 15:00h UTC
  - 18:00h BRT = 21:00h UTC
- **Verificação de Alterações**: Processa apenas arquivos modificados desde a última sincronização
- **Ambiente**: Ubuntu Latest
- **Python**: 3.9
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
   - **Valor**: Nome da pasta dentro da biblioteca de documentos
   - **Tipo**: String
   - **Secreto**: ❌ Não
   - **Importante**: Não inclua o nome da biblioteca no caminho, pois o código já seleciona a biblioteca automaticamente

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
- ✅ Se encontrar arquivos .mpp, verá: `📄 Encontrados X arquivo(s) .mpp`
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

1. **Agendamento**: Pipeline executa automaticamente de segunda a sexta às 6:00h, 12:00h e 18:00h BRT
   - Verifica se houve alterações nos arquivos antes de processar
   - Processa apenas arquivos modificados desde a última sincronização

2. **Busca de Arquivos**:
   - Se `USE_SHAREPOINT=true`: Busca arquivos `.mpp` no SharePoint
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

10. **Registro de Histórico**:
    - Salva timestamp da sincronização
    - Gera relatório JSON com estatísticas

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
│   ├── logs/                     # Logs do sistema e histórico de sincronização
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
- ✅ **Logs Detalhados**: Gera logs completos de todas as operações
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

# Verificar logs
cat backend/logs/sync_history.json
```

### Formato de Nome de Arquivo

```
[5 dígitos] [resto do nome].mpp
```

**Exemplo válido**: `14320 025447-02 - Projeto - Descrição.mpp`

### Variáveis Críticas

- `AZURE_DEVOPS_PAT`: Token de autenticação (obrigatório, secreto)
- `USE_SHAREPOINT`: Habilita/desabilita SharePoint (true/false)
- `SHAREPOINT_FOLDER_PATH`: Caminho da pasta no SharePoint
- `SHAREPOINT_CLIENT_SECRET`: Client Secret do App Registration (obrigatório, secreto)

### Horário de Execução

- **Agendamento**: Segunda a sexta-feira
- **Horário**: 6:30h BRT (9:30h UTC)
- **Frequência**: Diária (apenas dias úteis)

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
1. Verifique os logs em `backend/logs/sync_history.json`
2. Execute `test_sharepoint_path.py` para testar conexão SharePoint
3. Verifique as variáveis da pipeline no Azure DevOps
4. Consulte a seção [Troubleshooting](#troubleshooting)

---

**Última atualização**: 13/12/2025  
**Versão**: 1.0.2  
**Desenvolvido por**: Marcelo Macedo  
**E-mail**: [marcelo.macedo@qualiit.com.br](mailto:marcelo.macedo@qualiit.com.br)