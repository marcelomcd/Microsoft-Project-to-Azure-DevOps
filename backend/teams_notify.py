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


def _escape_html(s: str) -> str:
    """Escapa texto para uso seguro em HTML."""
    if not s:
        return ""
    return (
        str(s)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _build_teams_message_html(
    features_data: list,
    work_item_link_fn,
    intro_title: str = "Tasks mantidas como fechadas (não alteradas)",
) -> str:
    """
    Monta o corpo da mensagem no Teams em HTML: título com links (Feature | Microsoft Project),
    tasks com link, motivo (status DevOps vs .mpp) e responsável com mailto.
    Tasks duplicadas (mesmo task_id) são mostradas uma vez.
    """
    parts = [
        "<p>Olá,</p>",
        "<p>A sincronização MPP → Azure DevOps identificou Tasks que já estão <strong>fechadas</strong> no Azure DevOps, "
        "mas que não estavam como concluídas no arquivo .mpp.</p>",
        f"<p><strong>{_escape_html(intro_title)}</strong></p>",
        "<p></p>",
    ]
    for feat in features_data:
        fid = feat.get("feature_id")
        feature_url = work_item_link_fn(fid)
        file_links = feat.get("file_links") or []
        mpp_url = (file_links[0].get("web_url") or "").strip() if file_links else ""
        mpp_label = "Microsoft Project"
        if mpp_url:
            parts.append(
                f'<p><strong><a href="{_escape_html(feature_url)}">Feature</a> | '
                f'<a href="{_escape_html(mpp_url)}">{_escape_html(mpp_label)}</a> {_escape_html(str(fid))}</strong></p>'
            )
        else:
            parts.append(
                f'<p><strong><a href="{_escape_html(feature_url)}">Feature</a> {_escape_html(str(fid))}</strong></p>'
            )
        parts.append("<ul>")
        seen_task_ids = set()
        for t in feat.get("closed_tasks") or []:
            tid = t.get("task_id")
            if tid is not None and tid in seen_task_ids:
                continue
            if tid is not None:
                seen_task_ids.add(tid)
            title = _escape_html((t.get("title") or "")[:80])
            task_url = work_item_link_fn(tid) if tid is not None else ""
            devops_state = _escape_html((t.get("devops_state") or "—").strip())
            mpp_status = _escape_html((t.get("mpp_status") or "—").strip())
            motivo = f"Fechada no Azure DevOps ({devops_state}), ainda {mpp_status} no Microsoft Project."
            assignee_name = _escape_html(
                (t.get("task_assigned_to_display_name") or t.get("task_assigned_to_email") or "").strip()
            )
            assignee_email = (t.get("task_assigned_to_email") or "").strip()
            if task_url:
                task_part = f'<strong><a href="{_escape_html(task_url)}">Task {tid}</a>: {title}</strong>'
            else:
                task_part = f"<strong>Task {tid}: {title}</strong>"
            parts.append(f"<li>{task_part} — {_escape_html(motivo)}")
            if assignee_name:
                if assignee_email:
                    parts.append(f' Responsável: <a href="mailto:{_escape_html(assignee_email)}">{_escape_html(assignee_name)}</a>')
                else:
                    parts.append(f" Responsável: {_escape_html(assignee_name)}")
            parts.append("</li>")
        parts.append("</ul>")
        if len(file_links) > 1:
            parts.append("<p><strong>Outros arquivos .mpp desta Feature:</strong></p><ul>")
            for link in file_links[1:]:
                name = _escape_html(link.get("file_name") or "(arquivo)")
                url = (link.get("web_url") or "").strip()
                if url:
                    parts.append(f'<li><a href="{_escape_html(url)}">{name}</a></li>')
                else:
                    parts.append(f"<li>{name}</li>")
            parts.append("</ul>")
        parts.append("<p></p>")
    return "".join(parts)


def _build_html_log(
    email: str,
    display_name: str,
    features: list,
    work_item_link_fn,
) -> str:
    """
    Gera o HTML do corpo da mensagem enviada ao PMO (mesmo formato da mensagem Teams).
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
        "    .task-motivo { color: #605e5c; font-size: 0.9em; }",
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
        feature_url = work_item_link_fn(fid)
        file_links = feat.get("file_links") or []
        mpp_url = (file_links[0].get("web_url") or "").strip() if file_links else ""
        parts.append("  <div class=\"feature-block\">")
        if mpp_url:
            parts.append(f"    <h3><a href=\"{escaped(feature_url)}\" target=\"_blank\" rel=\"noopener\">Feature</a> | <a href=\"{escaped(mpp_url)}\" target=\"_blank\" rel=\"noopener\">Microsoft Project</a> {escaped(str(fid))}</h3>")
        else:
            parts.append(f"    <h3><a href=\"{escaped(feature_url)}\" target=\"_blank\" rel=\"noopener\">Feature</a> {escaped(str(fid))}</h3>")
        parts.append("    <ul>")
        seen_task_ids = set()
        for t in feat.get("closed_tasks") or []:
            tid = t.get("task_id")
            if tid is not None and tid in seen_task_ids:
                continue
            if tid is not None:
                seen_task_ids.add(tid)
            title = (t.get("title") or "")[:80]
            task_url = work_item_link_fn(tid) if tid is not None else ""
            devops_state = (t.get("devops_state") or "—").strip()
            mpp_status = (t.get("mpp_status") or "—").strip()
            motivo = f"Fechada no Azure DevOps ({devops_state}), ainda {mpp_status} no Microsoft Project."
            assignee_name = (t.get("task_assigned_to_display_name") or t.get("task_assigned_to_email") or "").strip()
            assignee_email = (t.get("task_assigned_to_email") or "").strip()
            if task_url:
                parts.append(f"      <li><strong><a href=\"{escaped(task_url)}\" target=\"_blank\" rel=\"noopener\">Task {escaped(str(tid))}</a>: {escaped(title)}</strong>")
            else:
                parts.append(f"      <li><strong>Task {escaped(str(tid))}: {escaped(title)}</strong>")
            parts.append(f" <span class=\"task-motivo\">— {escaped(motivo)}</span>")
            if assignee_name:
                if assignee_email:
                    parts.append(f' <span class=\"task-assignee\">Responsável: <a href=\"mailto:{escaped(assignee_email)}\">{escaped(assignee_name)}</a></span>')
                else:
                    parts.append(f" <span class=\"task-assignee\">Responsável: {escaped(assignee_name)}</span>")
            parts.append("</li>")
        parts.append("    </ul>")
        if file_links:
            parts.append("    <div class=\"file-links\">")
            parts.append("      <p><strong>Arquivos .mpp no SharePoint:</strong></p>")
            for link in file_links:
                name = link.get("file_name") or "(arquivo)"
                url = (link.get("web_url") or "").strip()
                if url:
                    parts.append(f"      <p class=\"file-name\"><a href=\"{escaped(url)}\" target=\"_blank\" rel=\"noopener\">{escaped(name)}</a></p>")
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


# Escopos usados na autenticação delegada (devem bater com get_teams_refresh_token.py)
_DELEGATED_SCOPES = ["User.Read", "Chat.Create", "ChatMessage.Send", "offline_access"]


def _get_graph_token_delegated() -> str:
    """Obtém token ao Graph usando refresh token do usuário (auth delegada)."""
    import msal
    
    # Remove espaços e quebras de linha (evita token truncado ao colar no .env)
    refresh_token = (getattr(settings, "TEAMS_REFRESH_TOKEN", "") or "").strip().replace("\r", "").replace("\n", "").replace(" ", "")
    if not refresh_token:
        raise ValueError("TEAMS_REFRESH_TOKEN está vazio; execute get_teams_refresh_token.py para obter um.")
    if len(refresh_token) < 200:
        logger.warning("TEAMS_REFRESH_TOKEN parece truncado (muito curto). Obtenha um novo com: python scripts/get_teams_refresh_token.py")
    client_id = settings.GRAPH_CLIENT_ID or settings.SHAREPOINT_CLIENT_ID
    client_secret = settings.GRAPH_CLIENT_SECRET or settings.SHAREPOINT_CLIENT_SECRET
    tenant_id = settings.GRAPH_TENANT_ID or settings.SHAREPOINT_TENANT_ID
    if not all([client_id, client_secret, tenant_id]):
        raise ValueError(
            "Configure GRAPH_CLIENT_ID, GRAPH_CLIENT_SECRET e GRAPH_TENANT_ID "
            "(ou SHAREPOINT_*) para usar o refresh token."
        )
    authority = f"https://login.microsoftonline.com/{tenant_id}"
    app = msal.ConfidentialClientApplication(
        client_id,
        authority=authority,
        client_credential=client_secret,
    )
    # Escopos do Graph para criar chat e enviar mensagem (não incluir reservados: openid, profile, offline_access)
    scopes = [
        "https://graph.microsoft.com/User.Read",
        "https://graph.microsoft.com/Chat.Create",
        "https://graph.microsoft.com/ChatMessage.Send",
    ]
    result = app.acquire_token_by_refresh_token(refresh_token, scopes=scopes)
    if "access_token" not in result:
        raise RuntimeError(
            f"Falha ao renovar token (refresh token expirado ou inválido): {result.get('error_description', result)}"
        )
    return result["access_token"]


def _get_me_id(token: str, requests_module) -> str | None:
    """Retorna o object ID do usuário atual (token delegado)."""
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    try:
        resp = requests_module.get(f"{GRAPH_BASE}/me?$select=id", headers=headers, timeout=15)
        if resp.status_code != 200:
            return None
        return (resp.json() or {}).get("id")
    except Exception:
        return None


def _create_chat_and_send_message(
    token: str,
    user_email: str,
    body_text: str,
    requests_module,
    initiator_user_id: str | None = None,
) -> bool:
    """
    Cria chat 1:1 com o usuário (por email/UPN) e envia a mensagem.
    Com auth delegada (initiator_user_id preenchido), inclui os 2 membros exigidos pela API.
    Retorna True se enviou com sucesso.
    """
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    if initiator_user_id:
        # Auth delegada: chat entre o usuário logado e o destinatário (2 membros)
        members = [
            {
                "@odata.type": "#microsoft.graph.aadUserConversationMember",
                "roles": ["owner"],
                "user@odata.bind": f"https://graph.microsoft.com/v1.0/users('{initiator_user_id}')",
            },
            {
                "@odata.type": "#microsoft.graph.aadUserConversationMember",
                "roles": ["owner"],
                "user@odata.bind": f"https://graph.microsoft.com/v1.0/users('{user_email}')",
            },
        ]
    else:
        members = [
            {
                "@odata.type": "#microsoft.graph.aadUserConversationMember",
                "roles": ["owner"],
                "user@odata.bind": f"https://graph.microsoft.com/v1.0/users('{user_email}')",
            }
        ]
    create_body = {
        "chatType": "oneOnOne",
        "members": members,
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
        # Enviar mensagem no chat (HTML para quebras de linha, negrito e links clicáveis)
        msg_body = {
            "body": {
                "contentType": "html",
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
    responsável (Assigned To da Feature no Azure DevOps).

    Cada destinatário é o assigned_to_email da Feature; um PMO pode receber
    uma única mensagem com todas as Features (e tasks fechadas) das quais ele
    é responsável. O relatório é gerado pela sync (pipeline_sync) com o
    Assigned To real de cada Feature.
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
    # Agrupa por responsável (Assigned To da Feature): cada PMO recebe uma mensagem com suas Features
    by_email: dict = {}
    for feat in features:
        email = (feat.get("assigned_to_email") or "").strip()
        display = (feat.get("assigned_to_display_name") or "").strip() or email
        if not email:
            logger.warning(
                f"Feature {feat.get('feature_id')} sem email do responsável (Assigned To); ignorando."
            )
            continue
        by_email.setdefault(email, {"display": display, "features": []})
        by_email[email]["features"].append(feat)
    if not by_email:
        logger.warning("Nenhum responsável com email no relatório.")
        return 0
    refresh_token = (getattr(settings, "TEAMS_REFRESH_TOKEN", "") or "").strip()
    use_delegated = bool(refresh_token)
    if use_delegated:
        logger.info("TEAMS_REFRESH_TOKEN definido: usando autenticação delegada (envio como seu usuário).")
    else:
        logger.info("TEAMS_REFRESH_TOKEN não definido: usando credenciais de aplicativo (pode gerar erro 'requires 2 members').")
    try:
        if use_delegated:
            token = _get_graph_token_delegated()
        else:
            token = _get_graph_token()
    except Exception as e:
        logger.error(f"Não foi possível obter token Graph: {e}")
        return 1
    initiator_user_id = _get_me_id(token, requests) if use_delegated else None
    if use_delegated and not initiator_user_id:
        logger.warning("Token delegado ativo mas não foi possível obter o ID do usuário (/me); o envio pode falhar com 'requires 2 members'.")
    sent = 0
    # Link para work items (Feature ou Task): evita duplicar ?workitem= na URL
    feature_board_base = (getattr(settings, "AZURE_DEVOPS_FEATURE_BOARD_BASE_URL", "") or "").strip().rstrip("/")
    if feature_board_base:
        base_clean = feature_board_base.split("?")[0].rstrip("/")
        def work_item_link(wi_id):
            return f"{base_clean}?workitem={wi_id}"
    else:
        org = getattr(settings, "AZURE_DEVOPS_ORG", "qualiit")
        base_url = f"https://dev.azure.com/{org}"
        def work_item_link(wi_id):
            return f"{base_url}/_workitems/edit/{wi_id}"
    for email, data in by_email.items():
        body_content = _build_teams_message_html(data["features"], work_item_link)
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
                work_item_link,
            )
            html_path.write_text(html_content, encoding="utf-8")
            logger.info(f"Log HTML gravado: {html_path}")
        except Exception as e:
            logger.warning(f"Não foi possível gravar log HTML para {email}: {e}")
        if _create_chat_and_send_message(token, email, body_content, requests, initiator_user_id):
            sent += 1
    # E-mail de verificação: envia uma mensagem consolidada com tudo que foi enviado aos PMOs
    verification_email = (getattr(settings, "TEAMS_VERIFICATION_EMAIL", "") or "").strip()
    if verification_email and verification_email not in by_email:
        # Monta HTML de verificação: lista por PMO com links
        verification_parts = [
            "<p><strong>Relatório de verificação – Conteúdo enviado aos PMOs</strong></p>",
            "<p>Resumo do que foi enviado a cada responsável (Features/Tasks fechadas no DevOps que não estavam no .mpp):</p>",
            "<p></p>",
        ]
        for email, data in by_email.items():
            verification_parts.append(
                f"<p><strong>— Enviado para: {_escape_html(data['display'])} ({_escape_html(email)})</strong></p>"
            )
            for feat in data["features"]:
                fid = feat.get("feature_id")
                link_url = work_item_link(fid)
                verification_parts.append(f'<p>Feature {fid} – <a href="{_escape_html(link_url)}">Abrir no Azure DevOps</a></p>')
                verification_parts.append("<ul>")
                for t in feat.get("closed_tasks") or []:
                    tid = t.get("task_id")
                    title = _escape_html((t.get("title") or "")[:80])
                    assignee = _escape_html(
                        (t.get("task_assigned_to_display_name") or t.get("task_assigned_to_email") or "").strip()
                    )
                    if assignee:
                        verification_parts.append(f"<li>Task {tid}: {title} (Responsável: {assignee})</li>")
                    else:
                        verification_parts.append(f"<li>Task {tid}: {title}</li>")
                verification_parts.append("</ul>")
                for link in feat.get("file_links") or []:
                    name = _escape_html(link.get("file_name") or "(arquivo)")
                    url = (link.get("web_url") or "").strip()
                    if url:
                        verification_parts.append(f'<p>Arquivo .mpp: <a href="{_escape_html(url)}">{name}</a></p>')
                    else:
                        verification_parts.append(f"<p>Arquivo .mpp: {name}</p>")
            verification_parts.append("<p></p>")
        verification_body = "".join(verification_parts)
        if _create_chat_and_send_message(token, verification_email, verification_body, requests, initiator_user_id):
            logger.info(f"Mensagem de verificação enviada para {verification_email}")
    elif verification_email and verification_email in by_email:
        # Já recebeu a mensagem como PMO; opcionalmente enviar resumo dos outros
        others = {e: d for e, d in by_email.items() if e != verification_email}
        if others:
            verification_parts = [
                "<p><strong>Relatório de verificação – Conteúdo enviado aos outros PMOs</strong></p>",
                "<p></p>",
            ]
            for email, data in others.items():
                verification_parts.append(
                    f"<p><strong>— Enviado para: {_escape_html(data['display'])} ({_escape_html(email)})</strong></p>"
                )
                for feat in data["features"]:
                    fid = feat.get("feature_id")
                    n = len(feat.get("closed_tasks") or [])
                    verification_parts.append(f"<p>Feature {fid}: {n} task(s)</p>")
                verification_parts.append("<p></p>")
            verification_body = "".join(verification_parts)
            if _create_chat_and_send_message(token, verification_email, verification_body, requests, initiator_user_id):
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
