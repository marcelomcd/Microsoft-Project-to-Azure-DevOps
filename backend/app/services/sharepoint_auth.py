"""Serviço de autenticação SharePoint usando OAuth 2.0 com Microsoft Graph API"""
import os
import json
from typing import Optional, Dict, Any
from pathlib import Path
import msal

from app.config import settings


class SharePointAuth:
    """Gerencia autenticação OAuth 2.0 para Microsoft Graph API"""
    
    # Escopos necessários para acessar SharePoint
    SCOPES = [
        "https://graph.microsoft.com/Sites.Read.All",
        "https://graph.microsoft.com/Files.Read.All",
        "offline_access"  # Para obter refresh token
    ]
    
    def __init__(self):
        """Inicializa o serviço de autenticação"""
        self.client_id = settings.SHAREPOINT_CLIENT_ID
        self.client_secret = settings.SHAREPOINT_CLIENT_SECRET
        self.tenant_id = settings.SHAREPOINT_TENANT_ID
        
        # Valida configurações obrigatórias
        if not self.client_id:
            raise ValueError("SHAREPOINT_CLIENT_ID não configurado no arquivo .env")
        if not self.tenant_id:
            raise ValueError("SHAREPOINT_TENANT_ID não configurado no arquivo .env")
        
        # Constrói authority sempre com tenant (obrigatório para MSAL)
        self.authority = f"{settings.SHAREPOINT_AUTHORITY}/{self.tenant_id}"
        
        # Caminho para armazenar tokens
        self.token_cache_path = Path(__file__).parent.parent.parent / ".token_cache.json"
        
        # Detecta se usa Application permissions (com Client Secret) ou Delegated (login interativo)
        self.use_application_permissions = bool(self.client_secret and self.client_secret.strip())
        
        # Valida Client Secret se usar Application permissions
        if self.use_application_permissions and not self.client_secret.strip():
            raise ValueError("SHAREPOINT_CLIENT_SECRET não configurado no arquivo .env (necessário para Application permissions)")
        
        # Inicializa aplicação MSAL baseado no tipo
        try:
            if self.use_application_permissions:
                # Application permissions - usa ConfidentialClientApplication
                self.app = msal.ConfidentialClientApplication(
                    client_id=self.client_id,
                    client_credential=self.client_secret,
                    authority=self.authority,
                    token_cache=msal.SerializableTokenCache()
                )
            else:
                # Delegated permissions - usa PublicClientApplication (login interativo)
                self.app = msal.PublicClientApplication(
                    client_id=self.client_id,
                    authority=self.authority,
                    token_cache=msal.SerializableTokenCache()
                )
        except Exception as e:
            raise ValueError(f"Erro ao inicializar MSAL. Verifique as configurações no .env: {str(e)}")
        
        # Carrega cache de tokens se existir
        self._load_token_cache()
    
    def _load_token_cache(self) -> None:
        """Carrega cache de tokens do arquivo"""
        if self.token_cache_path.exists():
            try:
                with open(self.token_cache_path, 'r') as f:
                    cache_data = json.load(f)
                    self.app.token_cache.deserialize(json.dumps(cache_data))
            except Exception as e:
                print(f"Aviso: Não foi possível carregar cache de tokens: {e}")
    
    def _save_token_cache(self) -> None:
        """Salva cache de tokens no arquivo"""
        try:
            if self.app.token_cache.has_state_changed:
                cache_data = json.loads(self.app.token_cache.serialize())
                with open(self.token_cache_path, 'w') as f:
                    json.dump(cache_data, f, indent=2)
        except Exception as e:
            print(f"Aviso: Não foi possível salvar cache de tokens: {e}")
    
    def get_access_token(self) -> Optional[str]:
        """
        Obtém token de acesso válido.
        
        Para Application permissions: usa Client Credentials flow (sem usuário)
        Para Delegated permissions: usa login interativo
        
        Returns:
            Token de acesso ou None se falhar
        """
        if self.use_application_permissions:
            # Application permissions - Client Credentials flow
            return self._get_application_token()
        else:
            # Delegated permissions - login interativo
            return self._get_delegated_token()
    
    def _get_application_token(self) -> Optional[str]:
        """Obtém token usando Application permissions (Client Credentials)"""
        try:
            # Para Application permissions, não precisa de scopes específicos
            # Usa apenas o endpoint padrão
            result = self.app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
            
            if result and "access_token" in result:
                self._save_token_cache()
                return result["access_token"]
            else:
                error = result.get("error_description", result.get("error", "Erro desconhecido"))
                print(f"Erro ao obter token de aplicação: {error}")
                return None
        except Exception as e:
            print(f"Erro ao obter token de aplicação: {e}")
            return None
    
    def _get_delegated_token(self) -> Optional[str]:
        """Obtém token usando Delegated permissions (login interativo)"""
        # Tenta obter token do cache
        accounts = self.app.get_accounts()
        if accounts:
            # Tenta obter token silenciosamente
            result = self.app.acquire_token_silent(
                scopes=self.SCOPES,
                account=accounts[0]
            )
            
            if result and "access_token" in result:
                self._save_token_cache()
                return result["access_token"]
        
        # Se não conseguiu token silenciosamente, tenta login interativo
        print("Token não encontrado ou expirado. Iniciando login interativo...")
        result = self._interactive_login()
        
        if result and "access_token" in result:
            self._save_token_cache()
            return result["access_token"]
        
        return None
    
    def _interactive_login(self) -> Optional[Dict[str, Any]]:
        """
        Realiza login interativo via navegador.
        
        Returns:
            Resultado da autenticação com access_token ou None
        """
        try:
            # Fluxo de autorização interativa
            result = self.app.acquire_token_interactive(
                scopes=self.SCOPES,
                prompt="select_account"  # Permite selecionar conta
            )
            
            if "access_token" in result:
                print("✓ Autenticação bem-sucedida!")
                return result
            else:
                error = result.get("error_description", result.get("error", "Erro desconhecido"))
                print(f"✗ Erro na autenticação: {error}")
                return None
                
        except Exception as e:
            print(f"✗ Erro durante login interativo: {e}")
            return None
    
    def refresh_token(self) -> Optional[str]:
        """
        Renova token usando refresh token.
        
        Returns:
            Novo token de acesso ou None se falhar
        """
        accounts = self.app.get_accounts()
        if not accounts:
            return None
        
        try:
            result = self.app.acquire_token_silent(
                scopes=self.SCOPES,
                account=accounts[0],
                force_refresh=True
            )
            
            if result and "access_token" in result:
                self._save_token_cache()
                return result["access_token"]
        except Exception as e:
            print(f"Erro ao renovar token: {e}")
        
        return None
    
    def is_authenticated(self) -> bool:
        """
        Verifica se há autenticação válida.
        
        Returns:
            True se há token válido, False caso contrário
        """
        token = self.get_access_token()
        return token is not None
    
    def logout(self) -> None:
        """Remove tokens e limpa cache"""
        accounts = self.app.get_accounts()
        for account in accounts:
            self.app.remove_account(account)
        
        # Remove arquivo de cache
        if self.token_cache_path.exists():
            try:
                os.remove(self.token_cache_path)
            except Exception as e:
                print(f"Erro ao remover cache: {e}")
        
        print("Logout realizado com sucesso")
