#!/usr/bin/env python3
"""
Obtém um refresh token do usuário para envio de mensagens no Teams em nome dele (auth delegada).

Execute uma vez: o navegador abre para você fazer login; o script exibirá o
TEAMS_REFRESH_TOKEN para colocar no .env e (opcionalmente) na pipeline.

Requisitos:
  - No app no Microsoft Entra ID: adicione um redirect URI "Web": http://localhost:8400
  - Permissões delegadas: User.Read, Chat.Create (e consentimento do usuário).
  - GRAPH_CLIENT_ID, GRAPH_CLIENT_SECRET e GRAPH_TENANT_ID no .env (ou SHAREPOINT_*).

Uso (a partir da pasta backend):
  python scripts/get_teams_refresh_token.py
"""
import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from app.config import settings

REDIRECT_URI = "http://localhost:8400"


def main() -> int:
    import msal
    import urllib.parse
    from http.server import HTTPServer, BaseHTTPRequestHandler

    client_id = (settings.GRAPH_CLIENT_ID or settings.SHAREPOINT_CLIENT_ID or "").strip()
    client_secret = (settings.GRAPH_CLIENT_SECRET or settings.SHAREPOINT_CLIENT_SECRET or "").strip()
    tenant_id = (settings.GRAPH_TENANT_ID or settings.SHAREPOINT_TENANT_ID or "").strip()
    if not client_id or not client_secret or not tenant_id:
        print("Configure GRAPH_CLIENT_ID, GRAPH_CLIENT_SECRET e GRAPH_TENANT_ID (ou SHAREPOINT_*) no .env e tente novamente.")
        return 1

    authority = f"https://login.microsoftonline.com/{tenant_id}"
    scopes = [
        "https://graph.microsoft.com/User.Read",
        "https://graph.microsoft.com/Chat.Create",
        "https://graph.microsoft.com/ChatMessage.Send",
    ]
    app = msal.ConfidentialClientApplication(
        client_id,
        authority=authority,
        client_credential=client_secret,
    )

    flow = app.initiate_auth_code_flow(scopes=scopes, redirect_uri=REDIRECT_URI)
    if not flow:
        print("Falha ao iniciar fluxo de autorização:", app.get_authorization_request_url(scopes))
        return 1

    auth_uri = flow["auth_uri"]
    result_holder = {"flow": flow}

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            parsed = urllib.parse.urlparse(self.path)
            if parsed.path in ("/", ""):
                # parse_qs retorna listas; auth_response deve ser dict com valores únicos (como request.args)
                params = urllib.parse.parse_qs(parsed.query)
                auth_response = {k: (v[0] if isinstance(v, list) and v else v) for k, v in params.items()}
                if auth_response.get("code"):
                    result_holder["auth_response"] = auth_response
                self.send_response(200)
                self.send_header("Content-type", "text/html; charset=utf-8")
                self.end_headers()
                if result_holder.get("auth_response"):
                    self.wfile.write(
                        b"<html><body><p>Login concluido. Volte ao terminal.</p></body></html>"
                    )
                else:
                    self.wfile.write(
                        b"<html><body><p>Nenhum codigo recebido. Feche e tente novamente.</p></body></html>"
                    )
            else:
                self.send_response(404)
                self.end_headers()

        def log_message(self, format, *args):
            pass

    server = HTTPServer(("localhost", 8400), Handler)
    print("Abrindo o navegador para login. Use a conta que enviara as mensagens no Teams.")
    print("Se nao abrir, acesse manualmente:\n", auth_uri)
    try:
        import webbrowser
        webbrowser.open(auth_uri)
    except Exception:
        pass

    server.handle_request()
    server.server_close()

    auth_response = result_holder.get("auth_response")
    if not auth_response or not auth_response.get("code"):
        print("Nenhum codigo de autorizacao recebido. No app no Entra ID, em Autenticacao, adicione redirect URI Web: ", REDIRECT_URI)
        return 1

    # flow (com code_verifier do PKCE) + auth_response para trocar o código por token
    result = app.acquire_token_by_auth_code_flow(
        result_holder["flow"], auth_response, scopes=scopes
    )

    if "access_token" not in result:
        print("Falha ao trocar codigo por token:", result.get("error_description", result))
        return 1

    refresh = result.get("refresh_token")
    if not refresh:
        print("Nao foi retornado refresh_token. No app no Entra ID, em Autenticacao, habilite 'Tokens de atualizacao' (Allow refresh tokens).")
        return 1

    print("\n" + "=" * 60)
    print("TEAMS_REFRESH_TOKEN (copie e coloque no .env):")
    print("=" * 60)
    print(refresh)
    print("=" * 60)
    print("\nNo .env adicione (em uma linha, sem quebras):")
    print("TEAMS_REFRESH_TOKEN=<o valor acima>")
    print("\nPara a pipeline no Azure DevOps, crie uma variavel secreta TEAMS_REFRESH_TOKEN com o mesmo valor.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
