# 📋 Configuração do SharePoint na Pipeline

## ✅ Caminho Correto da Pasta

Com base nas informações fornecidas, o caminho correto da pasta no SharePoint é:

```
Documentos Compartilhados/Cronogramas - Project
```

## 🔧 Variáveis a Configurar na Pipeline

Configure as seguintes variáveis na pipeline do Azure DevOps:

### Variáveis Obrigatórias:

1. **`USE_SHAREPOINT`**
   - Valor: `true`
   - Tipo: String (será convertido para boolean automaticamente)

2. **`SHAREPOINT_SITE_URL`**
   - Valor: `https://qualiitcombr.sharepoint.com/sites/projetosqualiit`
   - Tipo: String
   - Nota: Use `qualiitcombr.sharepoint.com` (não `qualiitcombr-my.sharepoint.com`)

3. **`SHAREPOINT_FOLDER_PATH`**
   - Valor: `Documentos Compartilhados/Cronogramas - Project`
   - Tipo: String
   - Nota: Este é o caminho completo dentro da biblioteca de documentos

4. **`SHAREPOINT_CLIENT_ID`**
   - Valor: (seu Client ID do App Registration)
   - Tipo: Secret (marque como secreto)

5. **`SHAREPOINT_CLIENT_SECRET`**
   - Valor: (seu Client Secret do App Registration)
   - Tipo: Secret (marque como secreto)

6. **`SHAREPOINT_TENANT_ID`**
   - Valor: (seu Tenant ID do Microsoft Entra ID)
   - Tipo: Secret (marque como secreto)

## 📝 Como Configurar na Pipeline

1. Acesse a pipeline no Azure DevOps
2. Vá em **Edit** → **Variables**
3. Adicione cada variável acima
4. Para variáveis secretas (Client ID, Client Secret, Tenant ID):
   - Marque a opção **"Keep this value secret"**
   - Clique em **Save**

## 🔍 Verificação

Após configurar, execute a pipeline e verifique os logs:

- ✅ Se encontrar a pasta, verá: `✅ Pasta encontrada com caminho: Documentos Compartilhados/Cronogramas - Project`
- ✅ Se encontrar arquivos .mpp, verá: `📄 Encontrados X arquivo(s) .mpp`

## ⚠️ Troubleshooting

Se a pasta não for encontrada, o código tentará automaticamente estas variações:

1. `Documentos Compartilhados/Cronogramas - Project` (caminho original)
2. `Cronogramas - Project` (sem "Documentos Compartilhados/")
3. `Cronogramas-Project` (sem espaços)
4. `CronogramasProject` (sem espaços e hífen)

Os logs mostrarão qual variação funcionou.

## 📌 Notas Importantes

- O código busca automaticamente a biblioteca "Documentos Compartilhados" primeiro
- Se não encontrar, usa a primeira biblioteca disponível
- O caminho é case-sensitive, então use exatamente: `Cronogramas - Project` (com espaço e hífen)
