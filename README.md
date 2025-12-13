# Microsoft Project to Azure DevOps Converter

Sistema automatizado para sincronizar arquivos `.mpp` (Microsoft Project) do SharePoint com Work Items no Azure DevOps, criando e atualizando User Stories e Tasks automaticamente via pipeline agendada.

## 🚀 Funcionalidades

- ✅ **Sincronização Automatizada**: Pipeline agendada executa de segunda a sexta-feira às 6:30h BRT
- ✅ **Integração SharePoint**: Busca e processa arquivos `.mpp` automaticamente do SharePoint
- ✅ **Identificação Automática**: Extrai Feature ID dos primeiros 5 dígitos do nome do arquivo
- ✅ **Busca Inteligente**: Busca User Stories e Tasks pelo nome exato antes de criar
- ✅ **Atualização Condicional**: Atualiza apenas se o arquivo foi modificado recentemente
- ✅ **Hierarquia Preservada**: Mantém Tasks vinculadas às User Stories corretas
- ✅ **Detecção de Duplicatas**: Evita criar itens duplicados no Azure DevOps
- ✅ **Histórico de Sincronização**: Mantém registro completo de todas as operações
- ✅ **Cache Otimizado**: Sistema de cache para melhor performance
- ✅ **Connection Pooling**: Otimização de requisições HTTP

## 🛠️ Tecnologias Utilizadas

### Backend
- **Linguagem**: Python 3.9+
- **Framework**: FastAPI 0.115.0+
- **Servidor ASGI**: Uvicorn
- **Validação de dados**: Pydantic 2.10.0+
- **HTTP Client**: Requests 2.32.0+ (com connection pooling)
- **Parsing MPP**: MPXJ (via Java CLI)
- **Ambiente**: Python Virtual Environment

### Integração
- **Azure DevOps**: REST API v7.1
- **SharePoint**: Microsoft Graph API
- **Autenticação**: OAuth2 (Microsoft Entra ID), PAT (Azure DevOps)

## 📋 Pré-requisitos

- **Python 3.9+**
- **Java JDK 11+** (necessário para parsing de arquivos .mpp via MPXJ)
- **Conta Azure DevOps** com PAT (Personal Access Token)
- **App Registration** no Microsoft Entra ID (para acesso ao SharePoint)

## 🛠️ Instalação

### Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
```

## ⚙️ Configuração

### Configuração Local (para testes)

1. **Crie o arquivo `backend/.env`** com as seguintes variáveis:

```env
# Azure DevOps
AZURE_DEVOPS_ORG=qualiit
AZURE_DEVOPS_PROJECT=Quali IT - Inovação e Tecnologia
AZURE_DEVOPS_PAT=seu_token_aqui

# SharePoint (opcional para testes locais)
USE_SHAREPOINT=True
SHAREPOINT_SITE_URL=https://qualiitcombr.sharepoint.com/sites/projetosqualiit
SHAREPOINT_FOLDER_PATH=Cronogramas - Project
SHAREPOINT_CLIENT_ID=seu_client_id
SHAREPOINT_CLIENT_SECRET=seu_client_secret
SHAREPOINT_TENANT_ID=seu_tenant_id

# Outras
LOG_LEVEL=INFO
API_TIMEOUT=30
```

2. **Configure o PAT do Azure DevOps**:
   - Acesse: https://dev.azure.com/{org}/_usersSettings/tokens
   - Crie um token com permissões de "Work Items (Read & Write)"

3. **Configure App Registration no Microsoft Entra ID** (para SharePoint):
   - Crie um App Registration
   - Configure permissões: `Sites.Read.All`, `Files.Read.All`
   - Gere Client Secret e copie o valor imediatamente

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

#### Configuração da Pipeline

1. **Configure variáveis na pipeline** (veja [CONFIGURAR_PIPELINE_VARIABLES.md](CONFIGURAR_PIPELINE_VARIABLES.md) para detalhes):
   - `AZURE_DEVOPS_PAT` (obrigatório, secreto)
   - `USE_SHAREPOINT=true` (obrigatório)
   - `SHAREPOINT_SITE_URL` (obrigatório)
   - `SHAREPOINT_FOLDER_PATH` (obrigatório)
   - `SHAREPOINT_CLIENT_ID` (obrigatório)
   - `SHAREPOINT_CLIENT_SECRET` (obrigatório, secreto)
   - `SHAREPOINT_TENANT_ID` (obrigatório)
   - `AZURE_DEVOPS_ORG` (opcional, default: qualiit)
   - `AZURE_DEVOPS_PROJECT` (opcional, default: Quali IT - Inovação e Tecnologia)

2. **A pipeline executa automaticamente** de segunda a sexta-feira às 6:30h BRT

**Documentação completa:** 
- 📚 [DOCUMENTACAO_COMPLETA.md](DOCUMENTACAO_COMPLETA.md) - Documentação completa do sistema
- ⚡ [GUIA_RAPIDO.md](GUIA_RAPIDO.md) - Referência rápida de configuração
- 🔧 [CONFIGURAR_PIPELINE_VARIABLES.md](CONFIGURAR_PIPELINE_VARIABLES.md) - Guia de configuração de variáveis

## 📖 Uso

### Formato do Nome do Arquivo

O nome do arquivo `.mpp` deve seguir o padrão:

```
[5 dígitos] [resto do nome].mpp
```

**Exemplo**: `14320 025447-02 - Combio - Integração Liber.mpp`
- Feature ID: `14320` (extraído dos primeiros 5 dígitos)
- Nome do projeto: `025447-02 - Combio - Integração Liber`

### Processo de Sincronização

1. **Pipeline executa automaticamente** de segunda a sexta às 6:30h BRT
2. **Busca arquivos `.mpp`** no SharePoint (pasta configurada)
3. **Verifica histórico**: Compara timestamp com última sincronização
4. **Faz parse do arquivo**: Extrai User Stories e Tasks usando MPXJ (Java)
5. **Extrai Feature ID**: Dos primeiros 5 dígitos do nome do arquivo
6. **Busca duplicatas**: Verifica se User Stories/Tasks já existem pelo nome exato
7. **Cria ou atualiza**: Cria novos itens ou atualiza existentes (se arquivo foi modificado)
8. **Mantém hierarquia**: Vincula Tasks às User Stories corretas
9. **Registra histórico**: Salva timestamp e gera relatório JSON

## 📁 Estrutura do Projeto

```
.
├── backend/
│   ├── app/
│   │   ├── main.py              # Aplicação FastAPI
│   │   ├── config.py            # Configurações (Pydantic Settings)
│   │   ├── models/              # Modelos de dados (Pydantic)
│   │   ├── services/            # Serviços (Parser, Mapper, DevOps Client, etc.)
│   │   ├── routers/             # Endpoints da API
│   │   └── utils/               # Utilitários (Cache, Validators)
│   ├── lib/                     # Bibliotecas Java (MPXJ)
│   ├── uploads/                 # Arquivos .mpp temporários
│   ├── logs/                    # Logs do sistema e histórico de sincronização
│   ├── pipeline_sync.py         # Script principal para execução agendada
│   ├── sync_all_mpp_files.py   # Script de sincronização (refatorado)
│   ├── requirements.txt         # Dependências Python
│   └── requirements-dev.txt     # Dependências de desenvolvimento
├── azure-pipelines.yml         # Definição da pipeline Azure DevOps
├── DOCUMENTACAO_COMPLETA.md   # Documentação completa do sistema
├── GUIA_RAPIDO.md             # Referência rápida de configuração
├── CONFIGURAR_PIPELINE_VARIABLES.md  # Guia de configuração
├── CONFIGURAR_SHAREPOINT.md   # Configuração do SharePoint
└── README.md                   # Este arquivo
```

## 📝 Estrutura do Arquivo .mpp

- **User Stories**: Tarefas sem recurso atribuído (coluna "Nomes dos recursos" vazia)
- **Tasks**: Tarefas com recurso atribuído (coluna "Nomes dos recursos" preenchida)
- **Hierarquia**: Tasks são vinculadas às User Stories baseado na estrutura hierárquica do arquivo

## 🔧 Funcionalidades Técnicas

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

Consulte a seção de troubleshooting em [DOCUMENTACAO_COMPLETA.md](DOCUMENTACAO_COMPLETA.md) para problemas comuns e soluções.

**Problemas mais comuns:**
- **404 Not Found**: Verifique `AZURE_DEVOPS_ORG` e `AZURE_DEVOPS_PROJECT`
- **Feature não existe**: Verifique se Feature ID está correto no nome do arquivo
- **Pasta não encontrada**: Execute `test_sharepoint_path.py` para descobrir caminho correto
- **Invalid client secret**: Use o VALOR do secret, não o ID
- **Java não disponível**: Instale Java JDK 11+ e verifique PATH

## 📄 Licença

Este projeto é de uso interno.

Desenvolvido para Quali IT - Inovação e Tecnologia

## 👥 Contribuidores

- Marcelo Macedo
