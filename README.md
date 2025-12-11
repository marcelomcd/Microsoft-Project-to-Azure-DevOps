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

## 🛠️ Tecnologias Utilizadas

### Backend
- **Linguagem**: Python 3.9+
- **Framework**: FastAPI 0.115.0+
- **Servidor ASGI**: Uvicorn
- **Validação de dados**: Pydantic 2.10.0+
- **HTTP Client**: Requests 2.32.0+ (com connection pooling)
- **Parsing MPP**: MPXJ (via Java CLI)
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

1. **Crie o arquivo `backend/.env`** com as seguintes variáveis:

```env
AZURE_DEVOPS_ORG=qualiit
AZURE_DEVOPS_PROJECT=Quali IT - Inovação e Tecnologia
AZURE_DEVOPS_PAT=seu_token_aqui
LOG_LEVEL=INFO
API_TIMEOUT=30
```

2. **Configure o PAT do Azure DevOps**:
   - Acesse: https://dev.azure.com/{org}/_usersSettings/tokens
   - Crie um token com permissões de "Work Items (Read & Write)"

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

### Via API REST

Acesse a documentação interativa: http://127.0.0.1:8000/docs

**Principais endpoints:**
- `POST /api/v1/upload/` - Upload de arquivo .mpp
- `GET /api/v1/workitems/{id}/analyze` - Analise Work Item completo
- `POST /api/v1/convert/` - Converter arquivo para Azure DevOps
- `GET /api/v1/projects/` - Listar projetos (Features)

## 📁 Estrutura do Projeto

```
.
├── backend/
│   ├── app/
│   │   ├── main.py              # Aplicação FastAPI
│   │   ├── config.py            # Configurações (Pydantic Settings)
│   │   ├── models/              # Modelos de dados (Pydantic)
│   │   ├── services/            # Serviços (Parser, Mapper, DevOps Client)
│   │   ├── routers/             # Endpoints da API
│   │   └── utils/               # Utilitários (Cache, Validators)
│   ├── lib/                     # Bibliotecas Java (MPXJ)
│   ├── uploads/                 # Arquivos .mpp temporários
│   ├── logs/                    # Logs do sistema
│   ├── requirements.txt         # Dependências Python
│   └── requirements-dev.txt     # Dependências de desenvolvimento
├── frontend/
│   ├── src/
│   │   ├── components/          # Componentes React
│   │   ├── services/            # Cliente API
│   │   └── App.tsx             # Aplicação principal
│   └── package.json            # Dependências Node.js
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

- **Frontend não funciona**: Instale Node.js de https://nodejs.org/
- **Backend não inicia**: Verifique se porta 8000 está livre e se o PAT está configurado
- **Erro ao processar .mpp**: Verifique se Java está instalado e no PATH
- **Projetos não aparecem**: Verifique se o nome do projeto no .env está correto (com acentos)

## 📄 Licença

Este projeto é de uso interno.

Desenvolvido para Quali IT - Inovação e Tecnologia

## 👥 Contribuidores

- Marcelo Macedo
