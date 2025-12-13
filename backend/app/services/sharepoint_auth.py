"""Serviço de autenticação SharePoint usando OAuth2 (Microsoft Entra ID)"""
import logging
from typing import Optional
from msal import ConfidentialClientApplication
from datetime import datetime, timedelta

from app.config import settings

logger = logging.getLogger(__name__)


class SharePointAuthService:
    """Gerencia autenticação OAuth2 para SharePoint"""
    
    def __init__(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        tenant_id: Optional[str] = None
    ):
        """
        Inicializa o serviço de autenticação.
        
        Args:
            client_id: Client ID (Application ID) do Microsoft Entra ID
            client_secret: Client Secret
            tenant_id: Tenant ID (Directory ID)
        """
        self.client_id = client_id or settings.SHAREPOINT_CLIENT_ID
        self.client_secret = client_secret or settings.SHAREPOINT_CLIENT_SECRET
        self.tenant_id = tenant_id or settings.SHAREPOINT_TENANT_ID
        
        if not self.client_id or not self.client_secret or not self.tenant_id:
            raise ValueError(
                "Configurações do SharePoint não estão completas. "
                "Configure SHAREPOINT_CLIENT_ID, SHAREPOINT_CLIENT_SECRET e SHAREPOINT_TENANT_ID."
            )
        
        # Authority URL para Microsoft Entra ID
        self.authority = f"https://login.microsoftonline.com/{self.tenant_id}"
        
        # Scope necessário para SharePoint
        self.scope = ["https://graph.microsoft.com/.default"]
        
        # Inicializa aplicação MSAL
        self.app = ConfidentialClientApplication(
            client_id=self.client_id,
            client_credential=self.client_secret,
            authority=self.authority
        )
        
        # Cache de token
        self._access_token: Optional[str] = None
        self._token_expires_at: Optional[datetime] = None
    
    def get_access_token(self, force_refresh: bool = False) -> str:
        """
        Obtém access token válido (usa cache se disponível).
        
        Args:
            force_refresh: Se True, força renovação do token
            
        Returns:
            Access token JWT
            
        Raises:
            ValueError: Se não conseguir obter token
        """
        # Verifica se token em cache ainda é válido
        if not force_refresh and self._access_token and self._token_expires_at:
            # Renova com 5 minutos de antecedência
            if datetime.now() < (self._token_expires_at - timedelta(minutes=5)):
                logger.debug("Usando token em cache")
                return self._access_token
        
        logger.info("Obtendo novo access token do Microsoft Entra ID")
        
        # Obtém token usando client credentials flow
        result = self.app.acquire_token_for_client(scopes=self.scope)
        
        if "access_token" in result:
            self._access_token = result["access_token"]
            
            # Calcula tempo de expiração (default 3600 segundos)
            expires_in = result.get("expires_in", 3600)
            self._token_expires_at = datetime.now() + timedelta(seconds=expires_in - 300)  # -5 min para segurança
            
            logger.info(f"Token obtido com sucesso. Expira em: {self._token_expires_at}")
            return self._access_token
        else:
            error_msg = result.get("error_description", result.get("error", "Erro desconhecido"))
            error_code = result.get("error", "")
            
            # Melhora mensagem de erro para casos comuns
            if "AADSTS7000215" in error_msg or "Invalid client secret" in error_msg:
                detailed_msg = (
                    f"❌ Client Secret inválido!\n\n"
                    f"   O erro indica que o SHAREPOINT_CLIENT_SECRET está incorreto.\n"
                    f"   Certifique-se de usar o VALOR do secret, não o ID do secret.\n\n"
                    f"   Como obter o valor correto:\n"
                    f"   1. Acesse o Azure Portal (portal.azure.com)\n"
                    f"   2. Vá em 'Microsoft Entra ID' > 'App registrations'\n"
                    f"   3. Encontre o app com Client ID: {self.client_id}\n"
                    f"   4. Vá em 'Certificates & secrets'\n"
                    f"   5. Se o secret expirou, crie um novo\n"
                    f"   6. Copie o VALOR do secret (não o ID)\n"
                    f"   7. IMPORTANTE: Copie o valor ANTES de fechar a página (não será possível ver novamente)\n\n"
                    f"   Erro original: {error_msg}"
                )
                logger.error(detailed_msg)
                raise ValueError(detailed_msg)
            elif "AADSTS700016" in error_msg or "Application" in error_msg:
                detailed_msg = (
                    f"❌ Application não encontrada no diretório!\n\n"
                    f"   O Client ID '{self.client_id}' não foi encontrado no Tenant '{self.tenant_id}'.\n"
                    f"   Verifique se:\n"
                    f"   1. O SHAREPOINT_CLIENT_ID está correto\n"
                    f"   2. O SHAREPOINT_TENANT_ID está correto\n"
                    f"   3. O app está registrado no tenant correto\n\n"
                    f"   Erro original: {error_msg}"
                )
                logger.error(detailed_msg)
                raise ValueError(detailed_msg)
            else:
                logger.error(f"Falha ao obter access token: {error_msg}")
                raise ValueError(f"Falha na autenticação: {error_msg}")
    
    def clear_token_cache(self) -> None:
        """Limpa cache de token (força renovação na próxima chamada)"""
        self._access_token = None
        self._token_expires_at = None
        logger.debug("Cache de token limpo")

