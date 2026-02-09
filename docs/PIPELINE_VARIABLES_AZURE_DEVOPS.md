# Variáveis das pipelines no Azure DevOps

Use os **mesmos valores** do seu `backend/.env` local. No Azure DevOps, defina em **Pipeline** → **Edit** → **Variables** (nunca commite o `.env`).

---

## Pipeline de sincronização (6:30) – `azure-pipelines.yml`

| Variável no Azure DevOps | Valor (origem) | Secreto? |
|--------------------------|----------------|----------|
| `AZURE_DEVOPS_PAT` | Do `.env`: `AZURE_DEVOPS_PAT` | Sim |
| `USE_SHAREPOINT` | Do `.env`: `USE_SHAREPOINT` (ex.: `True`) | Não |
| `SHAREPOINT_CLIENT_ID` | Do `.env`: `SHAREPOINT_CLIENT_ID` | Não |
| `SHAREPOINT_CLIENT_SECRET` | Do `.env`: `SHAREPOINT_CLIENT_SECRET` | Sim |
| `SHAREPOINT_TENANT_ID` | Do `.env`: `SHAREPOINT_TENANT_ID` | Não |
| `SHAREPOINT_SITE_URL` | Do `.env`: `SHAREPOINT_SITE_URL` | Não |
| `SHAREPOINT_FOLDER_PATH` | Do `.env`: `SHAREPOINT_FOLDER_PATH` | Não |
| `AZURE_DEVOPS_ORG` | Do `.env`: `AZURE_DEVOPS_ORG` (ex.: `qualiit`) | Não |
| `AZURE_DEVOPS_PROJECT` | Do `.env`: `AZURE_DEVOPS_PROJECT` (ex.: `Quali IT - Inovação e Tecnologia`) | Não |

Opcionais: `MPP_FILES_DIR` (se não usar SharePoint), `LOG_LEVEL`.

---

## Pipeline de notificação Teams (8h) – `azure-pipelines-teams-notify.yml`

Use os mesmos valores do `.env` onde indicado. Para Graph (envio de mensagem), normalmente usa-se o **mesmo app** do SharePoint; nesse caso, use os mesmos `CLIENT_ID`, `CLIENT_SECRET` e `TENANT_ID`.

| Variável no Azure DevOps | Valor (origem) | Secreto? |
|--------------------------|----------------|----------|
| `TEAMS_NOTIFICATION_ENABLED` | `true` | Não |
| `GRAPH_CLIENT_ID` | Do `.env`: mesmo que `SHAREPOINT_CLIENT_ID` | Não |
| `GRAPH_CLIENT_SECRET` | Do `.env`: mesmo que `SHAREPOINT_CLIENT_SECRET` | Sim |
| `GRAPH_TENANT_ID` | Do `.env`: mesmo que `SHAREPOINT_TENANT_ID` | Não |
| `SHAREPOINT_CLIENT_ID` | Do `.env`: `SHAREPOINT_CLIENT_ID` | Não |
| `SHAREPOINT_CLIENT_SECRET` | Do `.env`: `SHAREPOINT_CLIENT_SECRET` | Sim |
| `SHAREPOINT_TENANT_ID` | Do `.env`: `SHAREPOINT_TENANT_ID` | Não |
| `AZURE_DEVOPS_ORG` | Do `.env`: `AZURE_DEVOPS_ORG` | Não |
| `TEAMS_VERIFICATION_EMAIL` | E-mail que recebe cópia (ex.: `marcelo.macedo@qualiit.com.br`) | Não |
| `TEAMS_REFRESH_TOKEN` | Do `.env`: `TEAMS_REFRESH_TOKEN` | Sim |
| `AZURE_DEVOPS_FEATURE_BOARD_BASE_URL` | Opcional; URL base do board de Features para links na mensagem | Não |

---

## Como configurar no Azure DevOps

1. Abra **Pipelines** → selecione a pipeline (sync ou notificação Teams).
2. **Edit** → no topo, clique em **Variables**.
3. **+ New variable** para cada linha da tabela acima.
4. **Nome** = exatamente como na tabela (ex.: `TEAMS_NOTIFICATION_ENABLED`).
5. **Valor** = o mesmo que está no seu `backend/.env` (ou `true` / e-mail onde indicado).
6. Para variáveis marcadas como **Secreto? = Sim**, marque **Keep this value secret**.
7. **Save** na pipeline.

Assim as pipelines passam a usar a mesma configuração do seu ambiente local, sem expor o `.env` no repositório.
