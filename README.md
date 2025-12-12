# Microsoft Project to Azure DevOps Converter

Sistema completo para converter arquivos .mpp (Microsoft Project) em User Stories e Tasks no Azure DevOps, com API REST documentada e interface web moderna.

## 🚀 Funcionalidades

- **Upload de arquivos .mpp**: Interface drag-and-drop para upload de arquivos
- **Visualização completa**: Exibe conteúdo do arquivo .mpp com todas as linhas e colunas
- **Classificação automática**: Identifica User Stories (sem recurso) e Tasks (com recurso)
- **Sincronização bidirecional**: Sincroniza .mpp → DevOps e DevOps → .mpp
- **Detecção de duplicatas**: Evita criar Work Items duplicados no Azure DevOps
- **Mapeamento de recursos**: Mapeia automaticamente nomes de recursos para emails
- **Hierarquia preservada**: Mantém a estrutura em cascata (User Stories → Tasks)
- **Filtros e busca**: Filtros por PMO, Responsável Técnico, Cliente e busca por termos
- **API REST completa**: Documentação Swagger/OpenAPI automática
- **Interface moderna**: UI elegante com glassmorphism e temas claro/escuro
- **Cache otimizado**: Sistema de cache para melhor performance
- **Connection pooling**: Otimização de requisições HTTP
- **Pipeline Azure DevOps**: Processamento automático agendado de arquivos .mpp do SharePoint

## 🛠️ Tecnologias Utilizadas

### Backend
- **Linguagem**: Python 3.9+
- **Framework**: FastAPI 0.115.0+
- **Servidor ASGI**: Uvicorn
- **Validação de dados**: Pydantic 2.10.0+
- **HTTP Client**: Requests 2.32.0+ (com connection pooling)
- **Parsing MPP**: MPXJ (via Java CLI)
- **SharePoint Integration**: MSAL 1.24.0+ (autenticação OAuth 2.0)
- **Ambiente**: Python Virtual Environment

### Frontend
- **Linguagem**: TypeScript
- **Framework**: React 18.2.0+
- **Build Tool**: Vite 5.0.8+
- **HTTP Client**: Axios 1.6.2+
- **Roteamento**: React Router DOM 6.20.1+

### Ferramentas de Desenvolvimento
- **Linting**: Ruff, Flake8, ESLint
- **Formatação**: Black
- **Type Checking**: MyPy
- **Testes**: Pytest
- **Segurança**: Bandit
- **Performance**: cProfile, memory-profiler

## 📋 Pré-requisitos

- **Python 3.9+**
- **Java JDK 11+** (necessário para parsing de arquivos .mpp via MPXJ)
- **Node.js 18+** (necessário para frontend)
- **Conta Azure DevOps** com PAT (Personal Access Token)

## 🛠️ Instalação

### Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
```

### Frontend

```bash
cd frontend
npm install
```

## ⚙️ Configuração

### Passo 1: Obter IDs do Azure AD

Siga o guia completo em: **`GUIA_CONFIGURACAO_SHAREPOINT.md`**

Resumo rápido:
1. Acesse https://portal.azure.com → Azure Active Directory → App registrations
2. Crie um novo registro de aplicativo
3. Anote o **Application (client) ID** e **Directory (tenant) ID**
4. Configure permissões: `Sites.Read.All` e `Files.Read.All`
5. Conceda consentimento do administrador

### Passo 2: Configurar Variáveis de Ambiente

1. **Crie o arquivo `backend/.env`** com as seguintes variáveis:

```env
# Azure DevOps
AZURE_DEVOPS_ORG=qualiit
AZURE_DEVOPS_PROJECT=Quali IT - Inovação e Tecnologia
AZURE_DEVOPS_PAT=seu_token_aqui

# Logging
LOG_LEVEL=INFO
API_TIMEOUT=30

# SharePoint (para pipeline automática)
SHAREPOINT_SITE_URL=https://qualiitcombr.sharepoint.com/sites/projetosqualiit
SHAREPOINT_FOLDER_PATH=Documentos Compartilhados/Cronogramas - Project
SHAREPOINT_CLIENT_ID=seu_client_id_aqui
SHAREPOINT_CLIENT_SECRET=seu_client_secret_aqui
SHAREPOINT_TENANT_ID=seu_tenant_id_aqui
```

2. **Configure o PAT do Azure DevOps**:
   - Acesse: https://dev.azure.com/{org}/_usersSettings/tokens
   - Crie um token com permissões de "Work Items (Read & Write)"

3. **Configure o App Registration no Azure AD (para monitoramento SharePoint)**:
   - Acesse: https://portal.azure.com → Azure Active Directory → App registrations
   - Crie um novo registro de aplicativo
   - Anote o **Application (client) ID** e **Directory (tenant) ID**
   - Em "Authentication", adicione uma plataforma "Mobile and desktop applications"
   - Em "API permissions", adicione as permissões:
     - `Microsoft Graph` → `Sites.Read.All` (Application)
     - `Microsoft Graph` → `Files.Read.All` (Application)
   - Configure as variáveis `SHAREPOINT_CLIENT_ID` e `SHAREPOINT_TENANT_ID` no `.env`

## 🚀 Execução

### Método Rápido (Recomendado)

Execute o arquivo `INICIAR_SISTEMA.bat` na raiz do projeto:

```bash
INICIAR_SISTEMA.bat
```

Este script irá:
- ✅ Verificar se Node.js, Python e Java estão instalados
- ✅ Criar ambiente virtual se necessário
- ✅ Instalar dependências automaticamente
- ✅ Criar diretórios necessários (uploads, logs)
- ✅ Iniciar Backend e Frontend em janelas separadas

**Acesse:**
- **Frontend:** http://localhost:3000
- **Backend API:** http://127.0.0.1:8000
- **Documentação Swagger:** http://127.0.0.1:8000/docs

### Método Manual

#### Backend

```bash
cd backend
venv\Scripts\activate
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

#### Frontend

```bash
cd frontend
npm run dev
```

## 📖 Uso

### Via Interface Web

1. Acesse: http://localhost:3000
2. Faça upload de um arquivo .mpp
3. Visualize os dados na aba "Microsoft Project Verify"
4. Verifique o projeto no Azure DevOps na aba "Azure DevOps User Stories and Task's"
5. Sincronize os dados na aba "Sync .MPP → DevOps"

### Processamento Automático via Pipeline do Azure DevOps

O sistema processa automaticamente arquivos .mpp do SharePoint através de uma pipeline agendada no Azure DevOps.

#### Como Funciona

1. **Pipeline agendada**: Executa diariamente (ou conforme agendamento configurado)
2. **Detecção inteligente**: Processa apenas arquivos modificados desde a última execução
3. **Processamento automático**: Download, parse e conversão para Azure DevOps
4. **Estado persistente**: Salva timestamp da execução para próxima verificação

#### Configuração da Pipeline

**Guia completo**: Veja `PIPELINE_SETUP.md` para instruções detalhadas.

**Resumo:**
1. Crie a pipeline no Azure DevOps usando `azure-pipelines.yml`
2. Configure variáveis de ambiente (públicas e secretas)
3. Configure agendamento (padrão: diariamente às 02:00 UTC)
4. Pipeline executa automaticamente

#### Variáveis Necessárias na Pipeline

**Públicas:**
- `SHAREPOINT_SITE_URL`
- `SHAREPOINT_FOLDER_PATH` (pode ser vazio para raiz)
- `SHAREPOINT_CLIENT_ID`
- `SHAREPOINT_TENANT_ID`
- `AZURE_DEVOPS_ORG`
- `AZURE_DEVOPS_PROJECT`

**Secretas (Keep this value secret):**
- `SHAREPOINT_CLIENT_SECRET`
- `AZURE_DEVOPS_PAT`

#### Execução Manual (para testes)

```bash
cd backend
venv\Scripts\activate
python pipeline_main.py
```

O script:
- Valida todas as configurações
- Conecta ao SharePoint
- Processa arquivos modificados desde última execução
- Retorna exit code: 0 (sucesso) ou 1 (erro)

#### Pontos Críticos

1. **Java**: Pipeline precisa ter Java 11+ instalado (para parsing MPP)
2. **Variáveis Secretas**: Configure como "Keep this value secret" no Azure DevOps
3. **Timestamp**: Estado é salvo em `pipeline_state.json` (publicado como artefato)
4. **Exit Codes**: Script retorna 0 (sucesso) ou 1 (erro) para pipeline detectar falhas
5. **Logging**: Logs são capturados automaticamente pelo Azure DevOps

#### Controle via API (Opcional)

Endpoints disponíveis para monitoramento via API:

- **`GET /api/v1/monitor/status`** - Status do monitoramento
- **`POST /api/v1/monitor/check-now`** - Forçar verificação imediata
- **`GET /api/v1/monitor/history`** - Histórico de processamentos
- **`POST /api/v1/monitor/reset-state`** - Resetar estado
- **`GET /api/v1/monitor/test-connection`** - Testar conexão com SharePoint

### Via API REST

Acesse a documentação interativa: http://127.0.0.1:8000/docs

**Principais endpoints:**

**Upload e Conversão:**
- `POST /api/v1/upload/` - Upload de arquivo .mpp
- `POST /api/v1/convert/` - Converter arquivo para Azure DevOps
- `GET /api/v1/workitems/{id}/analyze` - Analise Work Item completo
- `GET /api/v1/projects/` - Listar projetos (Features)

**Monitoramento SharePoint:**
- `GET /api/v1/monitor/status` - Status do monitoramento
- `POST /api/v1/monitor/check-now` - Forçar verificação imediata
- `GET /api/v1/monitor/history` - Histórico de processamento
- `POST /api/v1/monitor/reset-state` - Resetar estado
- `GET /api/v1/monitor/test-connection` - Testar conexão com SharePoint

## 📁 Estrutura do Projeto

```
.
├── backend/
│   ├── app/
│   │   ├── main.py              # Aplicação FastAPI
│   │   ├── config.py            # Configurações (Pydantic Settings)
│   │   ├── models/              # Modelos de dados (Pydantic)
│   │   ├── services/            # Serviços (Parser, Mapper, DevOps Client, SharePoint)
│   │   ├── routers/             # Endpoints da API
│   │   └── utils/               # Utilitários (Cache, Validators)
│   ├── pipeline_main.py         # Script principal para execução na pipeline
│   ├── sharepoint_monitor.py    # Script de monitoramento (para uso via API)
│   ├── lib/                     # Bibliotecas Java (MPXJ)
│   ├── uploads/                 # Arquivos .mpp temporários
│   ├── logs/                    # Logs do sistema
│   ├── pipeline_state.json      # Estado da pipeline (timestamp última execução)
│   ├── sharepoint_state.json    # Estado de arquivos processados (para uso via API)
│   ├── requirements.txt         # Dependências Python
│   └── requirements-dev.txt     # Dependências de desenvolvimento
├── frontend/
│   ├── src/
│   │   ├── components/          # Componentes React
│   │   ├── services/            # Cliente API
│   │   └── App.tsx             # Aplicação principal
│   └── package.json            # Dependências Node.js
├── azure-pipelines.yml          # Definição da pipeline do Azure DevOps
├── PIPELINE_SETUP.md            # Guia completo de configuração da pipeline
├── INICIAR_SISTEMA.bat         # Script de inicialização
└── README.md                    # Este arquivo
```

## 📝 Formato do Arquivo .mpp

- **Nome do arquivo**: `{work_item_id} {project_name}.mpp`
  - Exemplo: `15507 - Teste MPP.mpp`
- **User Stories**: Linhas sem valor na coluna "Nomes dos recursos"
- **Tasks**: Linhas com valor na coluna "Nomes dos recursos"
- **Hierarquia**: Tasks seguem a User Story anterior baseado na estrutura do arquivo

## 🔧 Funcionalidades Técnicas

### Pipeline Azure DevOps
- Execução agendada (configurável via cron)
- Processamento baseado em timestamp (apenas arquivos modificados)
- Estado persistente entre execuções
- Exit codes apropriados para detecção de falhas
- Logging estruturado para Azure DevOps
- Publicação de artefatos (logs e estado)

### Cache
- Cache de projetos (TTL: 60 minutos)
- Cache de work items (TTL: 30 minutos)
- Cache de parsing MPP (TTL: 120 minutos)

### Connection Pooling
- Reutilização de conexões HTTP
- Retry automático em caso de falhas
- Timeout configurável

### Qualidade de Código
- Clean Code principles
- SOLID principles
- Type hints completos
- Testes unitários (Pytest)
- Análise estática (Ruff, Flake8, MyPy)
- Formatação automática (Black)

## 🐛 Troubleshooting

### Problemas Gerais
- **Frontend não funciona**: Instale Node.js de https://nodejs.org/
- **Backend não inicia**: Verifique se porta 8000 está livre e se o PAT está configurado
- **Erro ao processar .mpp**: Verifique se Java está instalado e no PATH
- **Projetos não aparecem**: Verifique se o nome do projeto no .env está correto (com acentos)

### Problemas na Pipeline
- **Pipeline falha na autenticação**: Verifique se `SHAREPOINT_CLIENT_SECRET` está configurado como Secret Variable
- **Java not found**: Pipeline precisa ter Java instalado (configurado no azure-pipelines.yml)
- **Nenhum arquivo processado**: Verifique se há arquivos modificados desde última execução (veja pipeline_state.json)
- **Erro 404 ao acessar pasta**: Verifique se `SHAREPOINT_FOLDER_PATH` está correto ou deixe vazio para raiz
- **Timeout na pipeline**: Aumente `timeoutInMinutes` no azure-pipelines.yml

Para mais detalhes, consulte `PIPELINE_SETUP.md`

## 📄 Licença

Este projeto é de uso interno.

Desenvolvido para Quali IT - Inovação e Tecnologia

## 👥 Contribuidores

- Marcelo Macedo
