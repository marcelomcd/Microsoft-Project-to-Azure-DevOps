#!/usr/bin/env python3
"""
Envia notificação no Teams para cada PMO (responsável pela Feature) com a lista de
Tasks que estão Closed no Azure DevOps mas não estavam no arquivo .mpp.

Uso: python teams_notify.py [--report PATH]
Requer: closed_tasks_report.json (gerado pela sync às 6:30) e variáveis Graph/Teams.
Deve ser executado pela pipeline às 8:30 (após download do artefato da run 6:30).
"""
import argparse
import json
import logging
import sys
from pathlib import Path

# Adiciona o diretório backend ao path
backend_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(backend_dir))

from app.config import settings

logging.basicConfig(
    level=getattr(logging, getattr(settings, "LOG_LEVEL", "INFO"), logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

GRAPH_BASE = "https://graph.microsoft.com/v1.0"


def _get_graph_token() -> str:
    """Obtém token de acesso ao Microsoft Graph (client credentials)."""
    import msal
    
    client_id = settings.GRAPH_CLIENT_ID or settings.SHAREPOINT_CLIENT_ID
    client_secret = settings.GRAPH_CLIENT_SECRET or settings.SHAREPOINT_CLIENT_SECRET
    tenant_id = settings.GRAPH_TENANT_ID or settings.SHAREPOINT_TENANT_ID
    if not all([client_id, client_secret, tenant_id]):
        raise ValueError(
            "Configure GRAPH_CLIENT_ID, GRAPH_CLIENT_SECRET e GRAPH_TENANT_ID "
            "(ou use as variáveis SHAREPOINT_* do mesmo app)"
        )
    authority = f"https://login.microsoftonline.com/{tenant_id}"
    app = msal.ConfidentialClientApplication(
        client_id,
        authority=authority,
        client_credential=client_secret,
    )
    result = app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
    if "access_token" not in result:
        raise RuntimeError(f"Falha ao obter token Graph: {result.get('error_description', result)}")
    return result["access_token"]


def _create_chat_and_send_message(
    token: str,
    user_email: str,
    body_text: str,
    requests_module,
) -> bool:
    """
    Cria chat 1:1 com o usuário (por email/UPN) e envia a mensagem.
    Retorna True se enviou com sucesso.
    """
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    # Criar chat 1:1 (app + usuário)
    create_body = {
        "chatType": "oneOnOne",
        "members": [
            {
                "@odata.type": "#microsoft.graph.aadUserConversationMember",
                "roles": ["owner"],
                "user@odata.bind": f"https://graph.microsoft.com/v1.0/users('{user_email}')",
            }
        ],
    }
    try:
        resp = requests_module.post(
            f"{GRAPH_BASE}/chats",
            headers=headers,
            json=create_body,
            timeout=30,
        )
        if resp.status_code not in (200, 201):
            logger.warning(
                f"Criação de chat para {user_email} falhou: {resp.status_code} - {resp.text[:200]}"
            )
            return False
        chat_id = resp.json().get("id")
        if not chat_id:
            return False
        # Enviar mensagem no chat
        msg_body = {
            "body": {
                "contentType": "text",
                "content": body_text,
            },
        }
        msg_resp = requests_module.post(
            f"{GRAPH_BASE}/chats/{chat_id}/messages",
            headers=headers,
            json=msg_body,
            timeout=30,
        )
        if msg_resp.status_code not in (200, 201):
            logger.warning(
                f"Envio de mensagem para {user_email} falhou: {msg_resp.status_code} - {msg_resp.text[:200]}"
            )
            return False
        logger.info(f"Mensagem enviada no Teams para {user_email}")
        return True
    except Exception as e:
        logger.exception(f"Erro ao enviar para {user_email}: {e}")
        return False


def run(report_path: Path) -> int:
    """
    Lê closed_tasks_report.json e envia uma mensagem no Teams para cada PMO
    (assigned_to_email) com a lista de tasks fechadas da(s) Feature(s) dele.
    """
    import requests
    
    if not report_path.exists():
        logger.warning(f"Arquivo de relatório não encontrado: {report_path}")
        return 0
    with open(report_path, "r", encoding="utf-8") as f:
        report = json.load(f)
    features = report.get("features") or []
    if not features:
        logger.info("Nenhuma task fechada para notificar.")
        return 0
    # Agrupa por email (um PMO pode ter mais de uma Feature)
    by_email: dict = {}
    for feat in features:
        email = (feat.get("assigned_to_email") or "").strip()
        display = (feat.get("assigned_to_display_name") or "").strip() or email
        if not email:
            logger.warning(
                f"Feature {feat.get('feature_id')} sem email do responsável (assigned_to); ignorando."
            )
            continue
        by_email.setdefault(email, {"display": display, "features": []})
        by_email[email]["features"].append(feat)
    if not by_email:
        logger.warning("Nenhum responsável com email no relatório.")
        return 0
    try:
        token = _get_graph_token()
    except Exception as e:
        logger.error(f"Não foi possível obter token Graph: {e}")
        return 1
    sent = 0
    org = getattr(settings, "AZURE_DEVOPS_ORG", "qualiit")
    base_url = f"https://dev.azure.com/{org}"
    for email, data in by_email.items():
        lines = [
            "Olá,",
            "",
            "A sincronização MPP → Azure DevOps identificou Tasks que já estão **fechadas** no Azure DevOps, "
            "mas que não estavam como concluídas no arquivo .mpp.",
            "",
            "**Tasks mantidas como fechadas (não alteradas):**",
            "",
        ]
        for feat in data["features"]:
            fid = feat.get("feature_id")
            lines.append(f"**Feature {fid}**")
            for t in feat.get("closed_tasks") or []:
                tid = t.get("task_id")
                title = (t.get("title") or "")[:80]
                lines.append(f"  • Task {tid}: {title}")
            lines.append(f"  Link Azure DevOps: {base_url}/_workitems/edit/{fid}")
            # Links dos arquivos .mpp no SharePoint (para alterar diretamente)
            file_links = feat.get("file_links") or []
            if file_links:
                lines.append("")
                lines.append("**Arquivos .mpp no SharePoint (para alterar e refletir as conclusões):**")
                for link in file_links:
                    name = link.get("file_name") or "(arquivo)"
                    url = (link.get("web_url") or "").strip()
                    if url:
                        lines.append(f"  • {name}")
                        lines.append(f"    {url}")
                    else:
                        lines.append(f"  • {name}")
            lines.append("")
        body_text = "\n".join(lines).strip()
        if _create_chat_and_send_message(token, email, body_text, requests):
            sent += 1
    logger.info(f"Notificações enviadas: {sent}/{len(by_email)}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Notificação Teams: tasks fechadas no DevOps por PMO")
    parser.add_argument(
        "--report",
        type=Path,
        default=backend_dir / "logs" / "closed_tasks_report.json",
        help="Caminho do closed_tasks_report.json",
    )
    args = parser.parse_args()
    if not getattr(settings, "TEAMS_NOTIFICATION_ENABLED", False):
        logger.info("TEAMS_NOTIFICATION_ENABLED não está ativo; encerrando sem enviar.")
        return 0
    return run(args.report)


if __name__ == "__main__":
    sys.exit(main())
