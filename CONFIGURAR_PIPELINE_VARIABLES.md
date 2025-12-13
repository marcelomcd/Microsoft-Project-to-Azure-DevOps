# 📋 Configuração de Variáveis na Pipeline do Azure DevOps

## ✅ Caminho Correto Confirmado

Após testes locais, confirmamos que:
- **Biblioteca**: `Documentações de Projetos` (selecionada automaticamente pelo código)
- **Pasta**: `Cronogramas - Project`
- **Arquivos encontrados**: 17 arquivos .mpp, incluindo o arquivo F703 mencionado

## 🔧 Variáveis a Configurar na Pipeline

Acesse a pipeline no Azure DevOps e configure as seguintes variáveis em **Edit** → **Variables**:

### Variáveis Obrigatórias para SharePoint:

1. **`USE_SHAREPOINT`**
   - **Valor**: `true`
   - **Tipo**: String (será convertido para boolean automaticamente)
   - **Secreto**: ❌ Não

2. **`SHAREPOINT_SITE_URL`**
   - **Valor**: `https://qualiitcombr.sharepoint.com/sites/projetosqualiit`
   - **Tipo**: String
   - **Secreto**: ❌ Não
   - **Nota**: Use `qualiitcombr.sharepoint.com` (não `qualiitcombr-my.sharepoint.com`)

3. **`SHAREPOINT_FOLDER_PATH`**
   - **Valor**: `Cronogramas - Project`
   - **Tipo**: String
   - **Secreto**: ❌ Não
   - **Importante**: Não inclua "Documentações de Projetos" no caminho, pois o código já seleciona essa biblioteca automaticamente

4. **`SHAREPOINT_CLIENT_ID`**
   - **Valor**: `2a41ace8-8b14-42db-808e-8681331138f5`
   - **Tipo**: String
   - **Secreto**: ✅ **SIM** (marque como secreto)

5. **`SHAREPOINT_CLIENT_SECRET`**
   - **Valor**: `4K88Q~u8vqfCeG5-OXUQ9QE6jDdI2GlS.jDRvcG2`
   - **Tipo**: String
   - **Secreto**: ✅ **SIM** (marque como secreto)
   - **Importante**: Use o **VALOR** do secret, não o ID do secret

6. **`SHAREPOINT_TENANT_ID`**
   - **Valor**: `6eb6a2fd-839d-460d-9bb0-7ed15211a782`
   - **Tipo**: String
   - **Secreto**: ✅ **SIM** (marque como secreto)

### Variáveis Obrigatórias para Azure DevOps:

7. **`AZURE_DEVOPS_PAT`**
   - **Valor**: (seu Personal Access Token do Azure DevOps)
   - **Tipo**: String
   - **Secreto**: ✅ **SIM** (marque como secreto)

### Variáveis Opcionais (com valores padrão):

8. **`AZURE_DEVOPS_ORG`**
   - **Valor**: `qualiit` (padrão)
   - **Tipo**: String
   - **Secreto**: ❌ Não
   - **Nota**: Configure apenas se diferente do padrão

9. **`AZURE_DEVOPS_PROJECT`**
   - **Valor**: `Quali IT - Inovação e Tecnologia` (padrão)
   - **Tipo**: String
   - **Secreto**: ❌ Não
   - **Nota**: Configure apenas se diferente do padrão

10. **`LOG_LEVEL`**
    - **Valor**: `INFO` (padrão)
    - **Tipo**: String
    - **Secreto**: ❌ Não
    - **Opções**: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`

## 📝 Passo a Passo para Configurar

1. Acesse o Azure DevOps: https://dev.azure.com/qualiit/ALM
2. Vá em **Pipelines** → Selecione sua pipeline
3. Clique em **Edit** (ou **⋮** → **Edit**)
4. Clique em **Variables** (no topo da página)
5. Para cada variável acima:
   - Clique em **+ New variable**
   - Digite o **nome** da variável
   - Digite o **valor**
   - Para variáveis secretas, marque **☑ Keep this value secret**
   - Clique em **OK**
6. Clique em **Save** para salvar a pipeline

## ✅ Verificação

Após configurar, execute a pipeline manualmente e verifique os logs:

- ✅ Se encontrar a pasta, verá: `✅ Pasta encontrada: Cronogramas - Project`
- ✅ Se encontrar arquivos .mpp, verá: `📄 Encontrados X arquivo(s) .mpp`
- ✅ Se processar com sucesso, verá: `✅ Sincronização concluída`

## ⚠️ Troubleshooting

### Erro: "Pasta não encontrada"
- Verifique se `SHAREPOINT_FOLDER_PATH` está exatamente como: `Cronogramas - Project`
- Verifique se `SHAREPOINT_SITE_URL` está correto
- Verifique se as permissões do App Registration estão corretas

### Erro: "Invalid client secret"
- Certifique-se de usar o **VALOR** do secret, não o ID
- Verifique se o secret não expirou no Azure Portal
- Se expirou, crie um novo secret e atualize a variável

### Erro: "Nenhum arquivo .mpp encontrado"
- Verifique se há arquivos .mpp na pasta `Cronogramas - Project`
- Verifique se as permissões do App Registration permitem ver os arquivos

## 📌 Notas Importantes

- O código busca automaticamente a biblioteca "Documentações de Projetos"
- O caminho `Cronogramas - Project` é relativo à raiz dessa biblioteca
- Não inclua "Documentações de Projetos" ou "Documentos Compartilhados" no `SHAREPOINT_FOLDER_PATH`
- O código tenta múltiplas codificações de caminho automaticamente se necessário

## 🔒 Segurança

- **NUNCA** commite secrets no código
- Use sempre variáveis secretas na pipeline
- Rotacione os secrets periodicamente
- O arquivo `backend/test_sharepoint.ps1` contém secrets e está no `.gitignore` - não commite!

