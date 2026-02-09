"""Configurações do sistema usando Pydantic Settings para validação e segurança."""
import os
from typing import List
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configurações da aplicação com validação automática."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
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
