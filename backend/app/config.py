"""Configurações do sistema usando Pydantic Settings para validação e segurança."""
import os
from pathlib import Path
from typing import List
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# .env na pasta backend (app/config.py -> app -> backend)
_BACKEND_DIR = Path(__file__).resolve().parent.parent
_ENV_FILE = _BACKEND_DIR / ".env"


class Settings(BaseSettings):
    """Configurações da aplicação com validação automática."""
    
    model_config = SettingsConfigDict(
        env_file=_ENV_FILE if _ENV_FILE.exists() else ".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )
    
    # Azure DevOps
    AZURE_DEVOPS_ORG: str = Field(
        default="qualiit",
        description="Organização do Azure DevOps"
    )
    AZURE_DEVOPS_PROJECT: str = Field(
        default="Quali IT - Inovação e Tecnologia",
        description="Nome do projeto no Azure DevOps"
    )
    
    @field_validator('AZURE_DEVOPS_ORG', mode='before')
    @classmethod
    def parse_azure_devops_org(cls, v):
        """Trata variáveis não definidas do Azure DevOps Pipeline"""
        if isinstance(v, str):
            # Se for a string literal da variável não definida no Azure DevOps, usa default
            if v.startswith('$(') and v.endswith(')'):
                return "qualiit"  # Default
        return v
    
    @field_validator('AZURE_DEVOPS_ORG', mode='before')
    @classmethod
    def parse_azure_devops_org(cls, v):
        """Trata variáveis não definidas do Azure DevOps Pipeline"""
        if isinstance(v, str):
            # Se for a string literal da variável não definida no Azure DevOps, usa default
            if v.startswith('$(') and v.endswith(')'):
                return "qualiit"  # Default
        return v
    AZURE_DEVOPS_PAT: str = Field(
        default="",
        description="Personal Access Token do Azure DevOps (obrigatório via env var)"
    )
    # Link do board de Features (notificação Teams). O link da Feature é: este base + ?workitem=ID.
    AZURE_DEVOPS_FEATURE_BOARD_BASE_URL: str = Field(
        default="https://dev.azure.com/qualiit/Quali%20IT%20-%20Inova%C3%A7%C3%A3o%20e%20Tecnologia/_boards/board/t/Quali%20IT%20!%20Gestao%20de%20Projeto/Features",
        description="URL base do board de Features (sem ?workitem=). Usado nos links da notificação Teams."
    )

    @property
    def azure_devops_base_url(self) -> str:
        """URL base do Azure DevOps."""
        return f"https://dev.azure.com/{self.AZURE_DEVOPS_ORG}"
    
    def validate_pat(self) -> None:
        """Valida que o PAT foi fornecido. Chame antes de usar."""
        if not self.AZURE_DEVOPS_PAT:
            raise ValueError(
                "AZURE_DEVOPS_PAT deve ser configurado via variável de ambiente"
            )
    
    # API
    API_V1_PREFIX: str = Field(
        default="/api/v1",
        description="Prefixo da API v1"
    )
    
    # Upload
    UPLOAD_DIR: str = Field(
        default="uploads",
        description="Diretório para uploads de arquivos"
    )
    MAX_UPLOAD_SIZE: int = Field(
        default=50 * 1024 * 1024,  # 50MB
        description="Tamanho máximo de upload em bytes"
    )
    
    # CORS
    CORS_ORIGINS: List[str] = Field(
        default=[
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:5173"
        ],
        description="Origens permitidas para CORS"
    )
    
    # Logging
    LOG_LEVEL: str = Field(
        default="INFO",
        description="Nível de log (DEBUG, INFO, WARNING, ERROR, CRITICAL)"
    )
    
    # Performance
    API_TIMEOUT: int = Field(
        default=30,
        description="Timeout padrão para requisições à API (segundos)"
    )
    
    # Pipeline/Scheduled Execution
    MPP_FILES_DIR: str = Field(
        default="",
        description="Diretório onde os arquivos .mpp estão localizados (obrigatório se usar diretório local)"
    )
    SYNC_HISTORY_FILE: str = Field(
        default="logs/sync_history.json",
        description="Caminho relativo do arquivo de histórico de sincronização"
    )
    TIMEZONE: str = Field(
        default="America/Sao_Paulo",
        description="Timezone para processamento (padrão: America/Sao_Paulo - Horário de Brasília)"
    )
    
    # SharePoint Integration (OAuth2)
    SHAREPOINT_CLIENT_ID: str = Field(
        default="",
        description="Client ID (Application ID) do Microsoft Entra ID para SharePoint"
    )
    SHAREPOINT_CLIENT_SECRET: str = Field(
        default="",
        description="Client Secret do Microsoft Entra ID para SharePoint (obrigatório se usar SharePoint)"
    )
    SHAREPOINT_TENANT_ID: str = Field(
        default="",
        description="Tenant ID (Directory ID) do Microsoft Entra ID (obrigatório se usar SharePoint)"
    )
    SHAREPOINT_SITE_URL: str = Field(
        default="",
        description="URL do site SharePoint (ex: https://qualiitcombr-my.sharepoint.com/sites/projetosqualiit)"
    )
    SHAREPOINT_FOLDER_PATH: str = Field(
        default="Cronogramas - Project",
        description="Caminho da pasta no SharePoint onde os arquivos .mpp estão localizados (dentro da biblioteca 'Documentações de Projetos')"
    )
    USE_SHAREPOINT: bool = Field(
        default=False,
        description="Se True, usa SharePoint como fonte de arquivos. Se False, usa MPP_FILES_DIR"
    )
    # Microsoft Graph / Teams (notificação PMO – tasks fechadas no DevOps)
    TEAMS_NOTIFICATION_ENABLED: bool = Field(
        default=False,
        description="Se True, habilita envio de mensagem no Teams para PMO (tasks fechadas no DevOps, run 8:30)"
    )
    GRAPH_CLIENT_ID: str = Field(
        default="",
        description="Client ID do app no Entra ID para Microsoft Graph (pode ser o mesmo do SharePoint)"
    )
    GRAPH_CLIENT_SECRET: str = Field(
        default="",
        description="Client Secret do app para Graph (Chat.Create, ChatMessage.Send)"
    )
    GRAPH_TENANT_ID: str = Field(
        default="",
        description="Tenant ID do Entra ID (pode ser o mesmo do SharePoint)"
    )
    # E-mail que recebe uma cópia consolidada de tudo que foi enviado aos PMOs (para verificação)
    TEAMS_VERIFICATION_EMAIL: str = Field(
        default="",
        description="Se preenchido, recebe uma mensagem no Teams com o resumo de tudo enviado aos PMOs (ex: marcelo.macedo@qualiit.com.br)"
    )
    # Refresh token do usuário para envio no Teams em nome do usuário (auth delegada).
    # Quando preenchido, as mensagens são enviadas a partir da sua conta; evita o erro "requires 2 members".
    # Obtenha com: python scripts/get_teams_refresh_token.py
    TEAMS_REFRESH_TOKEN: str = Field(
        default="",
        description="Refresh token (delegado) para enviar mensagens no Teams como usuário; obter com get_teams_refresh_token.py"
    )

    @field_validator('TEAMS_NOTIFICATION_ENABLED', mode='before')
    @classmethod
    def parse_teams_notification_enabled(cls, v):
        if isinstance(v, bool):
            return v
        if isinstance(v, str):
            if v.startswith('$(') and v.endswith(')'):
                return False
            return v.strip().lower() in ('true', '1', 'yes', 'on')
        return False
    
    @field_validator('USE_SHAREPOINT', mode='before')
    @classmethod
    def parse_use_sharepoint(cls, v):
        """Converte string para boolean, tratando valores inválidos como False"""
        if isinstance(v, bool):
            return v
        if isinstance(v, str):
            # Se for a string literal da variável não definida no Azure DevOps, retorna False
            if v.startswith('$(') and v.endswith(')'):
                return False
            # Converte strings comuns para boolean
            v_lower = v.strip().lower()
            if v_lower in ('true', '1', 'yes', 'on'):
                return True
            if v_lower in ('false', '0', 'no', 'off', ''):
                return False
        # Se não conseguir converter, retorna False (padrão)
        return False


# Instância global de configurações
# Nota: O PAT será validado quando necessário (não na inicialização)
settings = Settings()
