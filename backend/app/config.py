"""Configurações do sistema usando Pydantic Settings para validação e segurança."""
import os
from typing import List
from pydantic import Field
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


# Instância global de configurações
# Nota: O PAT será validado quando necessário (não na inicialização)
settings = Settings()
