"""Modelos para registro de alterações na sincronização"""
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class SyncItem(BaseModel):
    """Item individual sincronizado"""
    title: str = Field(..., description="Título do item")
    work_item_type: str = Field(..., description="Tipo do Work Item (User Story ou Task)")
    work_item_id: Optional[int] = Field(None, description="ID do Work Item no Azure DevOps")
    parent_id: Optional[int] = Field(None, description="ID do parent (Feature ou User Story)")
    action: str = Field(..., description="Ação realizada: created, updated, skipped, failed")
    error: Optional[str] = Field(None, description="Mensagem de erro se action=failed")
    mpp_task_id: Optional[str] = Field(None, description="ID da tarefa no arquivo .mpp")


class SyncLog(BaseModel):
    """Registro completo de uma sincronização"""
    sync_id: str = Field(..., description="ID único da sincronização")
    timestamp: datetime = Field(default_factory=datetime.now, description="Data/hora da sincronização")
    feature_id: Optional[int] = Field(None, description="ID da Feature no Azure DevOps")
    project_name: str = Field(..., description="Nome do projeto")
    file_name: str = Field(..., description="Nome do arquivo .mpp")
    
    # Estatísticas
    total_user_stories: int = Field(0, description="Total de User Stories no arquivo")
    total_tasks: int = Field(0, description="Total de Tasks no arquivo")
    
    # Itens criados
    created_user_stories: List[SyncItem] = Field(default_factory=list, description="User Stories criadas")
    created_tasks: List[SyncItem] = Field(default_factory=list, description="Tasks criadas")
    
    # Itens atualizados
    updated_user_stories: List[SyncItem] = Field(default_factory=list, description="User Stories atualizadas")
    updated_tasks: List[SyncItem] = Field(default_factory=list, description="Tasks atualizadas")
    
    # Itens pulados (duplicados)
    skipped_user_stories: List[SyncItem] = Field(default_factory=list, description="User Stories puladas")
    skipped_tasks: List[SyncItem] = Field(default_factory=list, description="Tasks puladas")
    
    # Itens com falha
    failed_user_stories: List[SyncItem] = Field(default_factory=list, description="User Stories que falharam")
    failed_tasks: List[SyncItem] = Field(default_factory=list, description="Tasks que falharam")
    
    # Resumo
    summary: Dict[str, Any] = Field(default_factory=dict, description="Resumo da sincronização")
    
    def get_summary(self) -> Dict[str, Any]:
        """Gera resumo da sincronização"""
        return {
            "sync_id": self.sync_id,
            "timestamp": self.timestamp.isoformat(),
            "feature_id": self.feature_id,
            "project_name": self.project_name,
            "file_name": self.file_name,
            "statistics": {
                "total_user_stories": self.total_user_stories,
                "total_tasks": self.total_tasks,
                "created": {
                    "user_stories": len(self.created_user_stories),
                    "tasks": len(self.created_tasks)
                },
                "updated": {
                    "user_stories": len(self.updated_user_stories),
                    "tasks": len(self.updated_tasks)
                },
                "skipped": {
                    "user_stories": len(self.skipped_user_stories),
                    "tasks": len(self.skipped_tasks)
                },
                "failed": {
                    "user_stories": len(self.failed_user_stories),
                    "tasks": len(self.failed_tasks)
                }
            },
            "total_processed": (
                len(self.created_user_stories) + 
                len(self.created_tasks) + 
                len(self.updated_user_stories) + 
                len(self.updated_tasks) + 
                len(self.skipped_user_stories) + 
                len(self.skipped_tasks) + 
                len(self.failed_user_stories) + 
                len(self.failed_tasks)
            )
        }

