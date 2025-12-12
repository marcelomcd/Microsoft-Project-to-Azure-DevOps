# Configuração do SharePoint para Pipeline

Este guia explica como configurar o SharePoint como fonte de arquivos .mpp na pipeline.

## 📋 Informações do SharePoint

Com base nos links fornecidos, as informações do SharePoint são:

- **Site URL**: `https://qualiitcombr.sharepoint.com/sites/projetosqualiit`
- **Pasta**: `Documentos Compartilhados/Cronogramas - Project`

## ⚙️ Configuração na Pipeline

### Passo 1: Configurar Variáveis na Pipeline

1. Vá em **Pipelines** → **Pipelines** → [Sua Pipeline] → **Edit** → **Variables**

2. Configure as seguintes variáveis:

#### Variável 1: USE_SHAREPOINT
- **Name**: `USE_SHAREPOINT`
- **Value**: `True`
- **Keep this value secret**: ❌ Não
- Clique em **OK**

#### Variável 2: SHAREPOINT_SITE_URL
- **Name**: `SHAREPOINT_SITE_URL`
- **Value**: `https://qualiitcombr.sharepoint.com/sites/projetosqualiit`
- **Keep this value secret**: ❌ Não
- Clique em **OK**

#### Variável 3: SHAREPOINT_FOLDER_PATH
- **Name**: `SHAREPOINT_FOLDER_PATH`
- **Value**: `Documentos Compartilhados/Cronogramas - Project`
- **Keep this value secret**: ❌ Não
- Clique em **OK**

#### Variável 4: SHAREPOINT_CLIENT_ID
- **Name**: `SHAREPOINT_CLIENT_ID`
- **Value**: Seu Client ID do Microsoft Entra ID (Application ID)
- **Keep this value secret**: ❌ Não
- Clique em **OK**

#### Variável 5: SHAREPOINT_CLIENT_SECRET
- **Name**: `SHAREPOINT_CLIENT_SECRET`
- **Value**: Seu Client Secret do Microsoft Entra ID
- **Keep this value secret**: ✅ **SIM** (marcar como secreto!)
- Clique em **OK**

#### Variável 6: SHAREPOINT_TENANT_ID
- **Name**: `SHAREPOINT_TENANT_ID`
- **Value**: Seu Tenant ID (Directory ID) do Microsoft Entra ID
- **Keep this value secret**: ❌ Não
- Clique em **OK**

### Passo 2: Remover ou Deixar Vazio MPP_FILES_DIR

Se você configurou `USE_SHAREPOINT=True`, não precisa configurar `MPP_FILES_DIR`. Você pode:
- Deixar a variável vazia, ou
- Remover a variável da pipeline

### Passo 3: Salvar e Testar

1. Clique em **Save** (canto superior direito)
2. Execute a pipeline manualmente para testar
3. Verifique os logs para confirmar que está acessando o SharePoint corretamente

## 🔐 Como Obter as Credenciais do SharePoint

### Client ID, Client Secret e Tenant ID

Essas informações vêm de um **App Registration** no Microsoft Entra ID (Azure AD):

1. Acesse: https://portal.azure.com
2. Vá em **Microsoft Entra ID** → **App registrations**
3. Selecione seu app (ou crie um novo)
4. **Client ID (Application ID)**: Encontrado na página **Overview**
5. **Tenant ID (Directory ID)**: Encontrado na página **Overview**
6. **Client Secret**: Vá em **Certificates & secrets** → **New client secret**

### Permissões Necessárias

O app precisa ter as seguintes permissões no Microsoft Graph API:
- `Sites.Read.All` (Application permission)
- `Files.Read.All` (Application permission)

Para configurar:
1. Vá em **API permissions**
2. Clique em **Add a permission**
3. Selecione **Microsoft Graph**
4. Selecione **Application permissions**
5. Adicione `Sites.Read.All` e `Files.Read.All`
6. Clique em **Grant admin consent**

## ✅ Checklist de Configuração

- [ ] `USE_SHAREPOINT` configurado como `True`
- [ ] `SHAREPOINT_SITE_URL` configurado corretamente
- [ ] `SHAREPOINT_FOLDER_PATH` configurado corretamente
- [ ] `SHAREPOINT_CLIENT_ID` configurado
- [ ] `SHAREPOINT_CLIENT_SECRET` configurado (como secreto)
- [ ] `SHAREPOINT_TENANT_ID` configurado
- [ ] Permissões do app configuradas no Microsoft Entra ID
- [ ] Pipeline testada e funcionando

## 🐛 Troubleshooting

### Erro: "SHAREPOINT_SITE_URL não está configurado"

**Solução**: Verifique se a variável `SHAREPOINT_SITE_URL` está configurada na pipeline.

### Erro: "Erro de autenticação"

**Solução**: 
- Verifique se `SHAREPOINT_CLIENT_ID`, `SHAREPOINT_CLIENT_SECRET` e `SHAREPOINT_TENANT_ID` estão corretos
- Verifique se o Client Secret não expirou
- Verifique se as permissões foram concedidas no Microsoft Entra ID

### Erro: "Pasta não encontrada"

**Solução**: 
- Verifique se `SHAREPOINT_FOLDER_PATH` está correto
- O caminho deve ser relativo ao site, ex: `Documentos Compartilhados/Cronogramas - Project`
- Não inclua o nome do site no caminho

### Erro: "Acesso negado"

**Solução**: 
- Verifique se o app tem as permissões necessárias
- Verifique se o admin consent foi concedido
- Verifique se o app tem acesso ao site SharePoint

## 📚 Referências

- [Microsoft Graph API - Sites](https://learn.microsoft.com/en-us/graph/api/resources/site)
- [Microsoft Graph API - Files](https://learn.microsoft.com/en-us/graph/api/resources/driveitem)
- [Azure AD App Registration](https://learn.microsoft.com/en-us/azure/active-directory/develop/quickstart-register-app)

