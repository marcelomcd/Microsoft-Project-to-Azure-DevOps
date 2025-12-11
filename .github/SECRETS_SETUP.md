# Configuração de Secrets e Tokens

## ⚠️ IMPORTANTE: Segurança

**NUNCA** commite tokens ou senhas diretamente no código ou em arquivos versionados!

## Token do GitHub (Cursor/Repo Workflow)

O token fornecido deve ser configurado nas seguintes formas:

### 1. Para Cursor IDE

1. Abra as configurações do Cursor
2. Vá para **Settings** → **GitHub** ou **Extensions** → **GitHub**
3. Cole o token na seção apropriada
4. O token será armazenado localmente e não será commitado

### 2. Para GitHub Actions (se necessário)

Se você precisar usar este token em workflows do GitHub Actions:

1. Vá para o repositório no GitHub
2. Clique em **Settings** → **Secrets and variables** → **Actions**
3. Clique em **New repository secret**
4. Nome: `GITHUB_TOKEN` (ou outro nome apropriado)
5. Valor: Cole o token
6. Clique em **Add secret**

### 3. Para uso local (variáveis de ambiente)

Se precisar usar o token em scripts locais:

**Windows (PowerShell):**
```powershell
$env:GITHUB_TOKEN = "seu_token_aqui"
```

**Windows (CMD):**
```cmd
set GITHUB_TOKEN=seu_token_aqui
```

**Linux/Mac:**
```bash
export GITHUB_TOKEN="seu_token_aqui"
```

### 4. Arquivo .env (NÃO versionado)

Se precisar usar em scripts, adicione ao `.env` (que já está no `.gitignore`):

```env
                GITHUB_TOKEN=seu_token_aqui
```

## Token do Azure DevOps

O token do Azure DevOps já está configurado em `backend/.env` (não versionado).

## Verificação

Para verificar se o token está funcionando:

```bash
# Teste de autenticação GitHub
curl -H "Authorization: token seu_token_aqui" https://api.github.com/user
```

## Permissões do Token

O token criado deve ter as seguintes permissões (scopes):
- `repo` - Acesso completo aos repositórios
- `workflow` - Atualizar workflows do GitHub Actions (se necessário)

## Rotação de Tokens

- Tokens devem ser rotacionados periodicamente
- Se um token for comprometido, revogue-o imediatamente no GitHub
- Gere um novo token e atualize todas as configurações

## Suporte

Para mais informações sobre tokens do GitHub:
- [GitHub Docs - Personal Access Tokens](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/creating-a-personal-access-token)

