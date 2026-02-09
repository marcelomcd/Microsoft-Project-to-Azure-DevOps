#!/usr/bin/env python3
"""
Envia notificação no Teams para cada PMO (responsável pela Feature) com a lista de
Tasks que estão Closed no Azure DevOps mas não estavam no arquivo .mpp.

Para cada PMO também gera um log em HTML com o corpo completo da mensagem enviada,
em <diretório_do_report>/teams_notify/<email_sanitizado>.html (ex: jessica.barbosa_qualiit.com.br.html).

Uso: python teams_notify.py [--report PATH]
Requer: closed_tasks_report.json (gerado pela sync às 6:30) e variáveis Graph/Teams.
Deve ser executado pela pipeline às 8h (após download do artefato da run 6:30).
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

# Nome do subdiretório onde são gravados os logs HTML por PMO (relativo ao diretório do report)
TEAMS_NOTIFY_LOG_SUBDIR = "teams_notify"


def _sanitize_email_for_filename(email: str) -> str:
    """Gera nome de arquivo seguro a partir do e-mail (ex: user@domain.com -> user_domain.com)."""
    if not email:
        return "sem_email"
    return email.strip().replace("@", "_").replace(" ", "_")


def _build_html_log(
    email: str,
    display_name: str,
    features: list,
    feature_link_fn,
) -> str:
    """
    Gera o HTML do corpo da mensagem enviada ao PMO, de forma estruturada e fácil de ler.
    """
    from datetime import datetime
    escaped = lambda s: (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
    now = datetime.now().strftime("%d/%m/%Y %H:%M")
    parts = [
        "<!DOCTYPE html>",
        "<html lang=\"pt-BR\">",
        "<head>",
        "  <meta charset=\"utf-8\">",
        "  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">",
        f"  <title>Notificação Teams – {escaped(display_name or email)}</title>",
        "  <style>",
        "    body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 24px; max-width: 720px; color: #242424; line-height: 1.5; }",
        "    h1 { font-size: 1.25rem; color: #106ebe; margin-bottom: 8px; }",
        "    h2 { font-size: 1.1rem; color: #323130; margin-top: 20px; margin-bottom: 8px; }",
        "    .meta { color: #605e5c; font-size: 0.9rem; margin-bottom: 20px; }",
        "    .intro { margin-bottom: 16px; }",
        "    ul { margin: 8px 0; padding-left: 24px; }",
        "    li { margin: 4px 0; }",
        "    a { color: #106ebe; text-decoration: none; }",
        "    a:hover { text-decoration: underline; }",
        "    .feature-block { background: #faf9f8; border-left: 4px solid #106ebe; padding: 12px 16px; margin: 16px 0; border-radius: 0 4px 4px 0; }",
        "    .feature-block h3 { margin: 0 0 8px 0; font-size: 1rem; color: #106ebe; }",
        "    .file-links { margin-top: 12px; }",
        "    .file-links .file-name { font-weight: 600; }",
        "    .file-links a { display: block; margin: 4px 0; word-break: break-all; }",
        "    .task-assignee { color: #605e5c; font-size: 0.95em; }",
        "  </style>",
        "</head>",
        "<body>",
        f"  <h1>Notificação Teams – Tasks fechadas no Azure DevOps</h1>",
        f"  <p class=\"meta\">Destinatário: <strong>{escaped(display_name or email)}</strong> &lt;{escaped(email)}&gt; · Gerado em {now}</p>",
        "  <p class=\"intro\">A sincronização MPP → Azure DevOps identificou Tasks que já estão <strong>fechadas</strong> no Azure DevOps, mas que não estavam como concluídas no arquivo .mpp.</p>",
        "  <h2>Tasks mantidas como fechadas (não alteradas)</h2>",
    ]
    for feat in features:
        fid = feat.get("feature_id")
        link_url = feature_link_fn(fid)
        parts.append("  <div class=\"feature-block\">")
        parts.append(f"    <h3>Feature {escaped(str(fid))}</h3>")
        parts.append("    <ul>")
        for t in feat.get("closed_tasks") or []:
            tid = t.get("task_id")
            title = (t.get("title") or "")[:80]
            assignee = (t.get("task_assigned_to_display_name") or t.get("task_assigned_to_email") or "").strip()
            if assignee:
                parts.append(f"      <li>Task {escaped(str(tid))}: {escaped(title)} <span class=\"task-assignee\">(Responsável: {escaped(assignee)})</span></li>")
            else:
                parts.append(f"      <li>Task {escaped(str(tid))}: {escaped(title)}</li>")
        parts.append("    </ul>")
        parts.append(f"    <p><a href=\"{escaped(link_url)}\" target=\"_blank\" rel=\"noopener\">Abrir Feature no Azure DevOps</a></p>")
        file_links = feat.get("file_links") or []
        if file_links:
            parts.append("    <div class=\"file-links\">")
            parts.append("      <p><strong>Arquivos .mpp no SharePoint (para alterar e refletir as conclusões):</strong></p>")
            for link in file_links:
                name = link.get("file_name") or "(arquivo)"
                url = (link.get("web_url") or "").strip()
                if url:
                    parts.append(f"      <p class=\"file-name\">{escaped(name)}</p>")
                    parts.append(f"      <a href=\"{escaped(url)}\" target=\"_blank\" rel=\"noopener\">{escaped(url)}</a>")
                else:
                    parts.append(f"      <p class=\"file-name\">{escaped(name)}</p>")
            parts.append("    </div>")
        parts.append("  </div>")
    parts.append("</body>")
    parts.append("</html>")
    return "\n".join(parts)


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
    Nota: com permissão de aplicativo (app-only), alguns tenants retornam
    "Creation of 'OneOnOne' chat requires 2 members". Nesse caso use
    autenticação delegada (usuário) ou considere webhook/connector do Teams.
    Retorna True se enviou com sucesso.
    """
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    # Criar chat 1:1 (doc: um membro; em app-only o tenant pode exigir 2)
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
    # Link da Feature: board de Features se configurado, senão _workitems/edit
    feature_board_base = (getattr(settings, "AZURE_DEVOPS_FEATURE_BOARD_BASE_URL", "") or "").strip().rstrip("/")
    if feature_board_base:
        def feature_link(fid):
            return f"{feature_board_base}?workitem={fid}"
    else:
        org = getattr(settings, "AZURE_DEVOPS_ORG", "qualiit")
        base_url = f"https://dev.azure.com/{org}"
        def feature_link(fid):
            return f"{base_url}/_workitems/edit/{fid}"
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
                assignee = (t.get("task_assigned_to_display_name") or t.get("task_assigned_to_email") or "").strip()
                if assignee:
                    lines.append(f"  • Task {tid}: {title} (Responsável: {assignee})")
                else:
                    lines.append(f"  • Task {tid}: {title}")
            lines.append(f"  Link Azure DevOps: {feature_link(fid)}")
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
        # Log HTML com o corpo completo da mensagem enviada ao PMO (nome do arquivo = email sanitizado)
        log_dir = report_path.parent / TEAMS_NOTIFY_LOG_SUBDIR
        log_dir.mkdir(parents=True, exist_ok=True)
        safe_name = _sanitize_email_for_filename(email)
        html_path = log_dir / f"{safe_name}.html"
        try:
            html_content = _build_html_log(
                email,
                data["display"],
                data["features"],
                feature_link,
            )
            html_path.write_text(html_content, encoding="utf-8")
            logger.info(f"Log HTML gravado: {html_path}")
        except Exception as e:
            logger.warning(f"Não foi possível gravar log HTML para {email}: {e}")
        if _create_chat_and_send_message(token, email, body_text, requests):
            sent += 1
    # E-mail de verificação: envia uma mensagem consolidada com tudo que foi enviado aos PMOs
    verification_email = (getattr(settings, "TEAMS_VERIFICATION_EMAIL", "") or "").strip()
    if verification_email and verification_email not in by_email:
        verification_lines = [
            "**Relatório de verificação – Conteúdo enviado aos PMOs**",
            "",
            "Resumo do que foi enviado a cada responsável (Features/Tasks fechadas no DevOps que não estavam no .mpp):",
            "",
        ]
        for email, data in by_email.items():
            verification_lines.append(f"--- Enviado para: {data['display']} ({email}) ---")
            for feat in data["features"]:
                fid = feat.get("feature_id")
                verification_lines.append(f"Feature {fid}")
                for t in feat.get("closed_tasks") or []:
                    tid = t.get("task_id")
                    title = (t.get("title") or "")[:80]
                    assignee = (t.get("task_assigned_to_display_name") or t.get("task_assigned_to_email") or "").strip()
                    if assignee:
                        verification_lines.append(f"  • Task {tid}: {title} (Responsável: {assignee})")
                    else:
                        verification_lines.append(f"  • Task {tid}: {title}")
                verification_lines.append(f"  Link: {feature_link(fid)}")
                for link in feat.get("file_links") or []:
                    verification_lines.append(f"  .mpp: {link.get('file_name') or '(arquivo)'}")
            verification_lines.append("")
        verification_body = "\n".join(verification_lines).strip()
        if _create_chat_and_send_message(token, verification_email, verification_body, requests):
            logger.info(f"Mensagem de verificação enviada para {verification_email}")
    elif verification_email and verification_email in by_email:
        # Já recebeu a mensagem como PMO; opcionalmente enviar resumo dos outros
        others = {e: d for e, d in by_email.items() if e != verification_email}
        if others:
            verification_lines = [
                "**Relatório de verificação – Conteúdo enviado aos outros PMOs**",
                "",
            ]
            for email, data in others.items():
                verification_lines.append(f"--- Enviado para: {data['display']} ({email}) ---")
                for feat in data["features"]:
                    fid = feat.get("feature_id")
                    verification_lines.append(f"Feature {fid}: {len(feat.get('closed_tasks') or [])} task(s)")
                verification_lines.append("")
            verification_body = "\n".join(verification_lines).strip()
            if _create_chat_and_send_message(token, verification_email, verification_body, requests):
                logger.info(f"Resumo de verificação (outros PMOs) enviado para {verification_email}")
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
