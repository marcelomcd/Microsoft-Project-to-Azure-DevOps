#!/usr/bin/env python3
"""
Script de teste local para notificação Teams.

Gera um closed_tasks_report.json de exemplo e executa teams_notify.py para
enviar uma mensagem de teste ao e-mail informado (por padrão marcelo.macedo@qualiit.com.br).
Use para verificar se a mensagem chega no Teams antes de confiar na pipeline.

Requisitos:
  - TEAMS_NOTIFICATION_ENABLED=true no .env (ou variável de ambiente)
  - GRAPH_* ou SHAREPOINT_* configurados no .env (app com Chat.Create + Chat.ReadWrite.All e consentimento)

Uso (a partir da raiz do repo ou de backend/):
  python scripts/test_teams_notify_local.py
  python scripts/test_teams_notify_local.py --email daniel.bragion@qualiit.com.br
"""
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

# backend/scripts -> backend
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

# Relatório de teste será gravado em backend/logs/teams_notify_test/
TEST_REPORT_DIR = backend_dir / "logs" / "teams_notify_test"
DEFAULT_TEST_EMAIL = "marcelo.macedo@qualiit.com.br"


def build_test_report(recipient_email: str, recipient_display_name: str) -> Path:
    """Monta um closed_tasks_report.json de teste e retorna o caminho do arquivo."""
    TEST_REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report_path = TEST_REPORT_DIR / "closed_tasks_report.json"
    report = {
        "generated_at": datetime.now().isoformat(),
        "features": [
            {
                "feature_id": 99999,
                "assigned_to_email": recipient_email,
                "assigned_to_display_name": recipient_display_name or recipient_email,
                "closed_tasks": [
                    {
                        "task_id": 100001,
                        "title": "[TESTE] Task fechada no DevOps – verificação de envio no Teams",
                        "mpp_status": "Em andamento",
                        "devops_state": "Closed",
                        "task_assigned_to_email": "marcelo.macedo@qualiit.com.br",
                        "task_assigned_to_display_name": "Marcelo Macedo",
                    },
                    {
                        "task_id": 100002,
                        "title": "[TESTE] Segunda task – script de teste local",
                        "mpp_status": "Não iniciada",
                        "devops_state": "Resolved",
                        "task_assigned_to_email": "",
                        "task_assigned_to_display_name": "Daniel Bragion",
                    },
                ],
                "file_links": [
                    {"file_name": "Exemplo_Projeto.mpp", "web_url": "https://qualiitcombr.sharepoint.com/"},
                ],
            },
        ],
    }
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Relatório de teste gravado: {report_path}")
    return report_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Teste local: envia mensagem de teste no Teams")
    parser.add_argument(
        "--email",
        default=DEFAULT_TEST_EMAIL,
        help=f"E-mail que receberá a mensagem de teste (default: {DEFAULT_TEST_EMAIL})",
    )
    parser.add_argument(
        "--name",
        default="",
        help="Nome de exibição do destinatário (opcional)",
    )
    args = parser.parse_args()
    email = (args.email or "").strip() or DEFAULT_TEST_EMAIL
    name = (args.name or "").strip() or email

    print("Gerando relatório de teste...")
    report_path = build_test_report(email, name)
    print(f"Destinatário da mensagem de teste: {name} <{email}>")
    print("Executando teams_notify.py (requer TEAMS_NOTIFICATION_ENABLED=true e credenciais Graph no .env)...")
    print()

    from teams_notify import run
    return run(report_path)


if __name__ == "__main__":
    sys.exit(main())
