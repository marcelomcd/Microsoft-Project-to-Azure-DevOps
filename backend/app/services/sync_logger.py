"""Serviço para registro de alterações na sincronização"""
import json
import uuid
from typing import Optional, Dict, Any
from datetime import datetime
from pathlib import Path

from app.models.sync_log import SyncLog, SyncItem


class SyncLogger:
    """Gerencia o registro de alterações durante a sincronização"""
    
    def __init__(self, log_dir: Optional[Path] = None):
        """
        Inicializa o logger de sincronização.
        
        Args:
            log_dir: Diretório para salvar logs (padrão: logs/ no diretório do projeto)
        """
        if log_dir is None:
            # Diretório padrão: backend/logs/
            backend_dir = Path(__file__).parent.parent.parent
            log_dir = backend_dir / "logs"
        
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        self.current_log: Optional[SyncLog] = None
    
    def start_sync(
        self,
        feature_id: Optional[int],
        project_name: str,
        file_name: str,
        total_user_stories: int,
        total_tasks: int
    ) -> str:
        """
        Inicia um novo registro de sincronização.
        
        Args:
            feature_id: ID da Feature no Azure DevOps
            project_name: Nome do projeto
            file_name: Nome do arquivo .mpp
            total_user_stories: Total de User Stories no arquivo
            total_tasks: Total de Tasks no arquivo
            
        Returns:
            ID único da sincronização
        """
        sync_id = str(uuid.uuid4())
        
        self.current_log = SyncLog(
            sync_id=sync_id,
            feature_id=feature_id,
            project_name=project_name,
            file_name=file_name,
            total_user_stories=total_user_stories,
            total_tasks=total_tasks
        )
        
        return sync_id
    
    def log_created_user_story(
        self,
        title: str,
        work_item_id: int,
        parent_id: Optional[int],
        mpp_task_id: Optional[str] = None
    ):
        """Registra uma User Story criada"""
        if not self.current_log:
            return
        
        item = SyncItem(
            title=title,
            work_item_type="User Story",
            work_item_id=work_item_id,
            parent_id=parent_id,
            action="created",
            mpp_task_id=mpp_task_id
        )
        self.current_log.created_user_stories.append(item)
    
    def log_created_task(
        self,
        title: str,
        work_item_id: int,
        parent_id: Optional[int],
        mpp_task_id: Optional[str] = None
    ):
        """Registra uma Task criada"""
        if not self.current_log:
            return
        
        item = SyncItem(
            title=title,
            work_item_type="Task",
            work_item_id=work_item_id,
            parent_id=parent_id,
            action="created",
            mpp_task_id=mpp_task_id
        )
        self.current_log.created_tasks.append(item)
    
    def log_updated_user_story(
        self,
        title: str,
        work_item_id: int,
        parent_id: Optional[int],
        mpp_task_id: Optional[str] = None
    ):
        """Registra uma User Story atualizada"""
        if not self.current_log:
            return
        
        item = SyncItem(
            title=title,
            work_item_type="User Story",
            work_item_id=work_item_id,
            parent_id=parent_id,
            action="updated",
            mpp_task_id=mpp_task_id
        )
        self.current_log.updated_user_stories.append(item)
    
    def log_updated_task(
        self,
        title: str,
        work_item_id: int,
        parent_id: Optional[int],
        mpp_task_id: Optional[str] = None
    ):
        """Registra uma Task atualizada"""
        if not self.current_log:
            return
        
        item = SyncItem(
            title=title,
            work_item_type="Task",
            work_item_id=work_item_id,
            parent_id=parent_id,
            action="updated",
            mpp_task_id=mpp_task_id
        )
        self.current_log.updated_tasks.append(item)
    
    def log_skipped_user_story(
        self,
        title: str,
        work_item_id: Optional[int],
        parent_id: Optional[int],
        mpp_task_id: Optional[str] = None
    ):
        """Registra uma User Story pulada (duplicada)"""
        if not self.current_log:
            return
        
        item = SyncItem(
            title=title,
            work_item_type="User Story",
            work_item_id=work_item_id,
            parent_id=parent_id,
            action="skipped",
            mpp_task_id=mpp_task_id
        )
        self.current_log.skipped_user_stories.append(item)
    
    def log_skipped_task(
        self,
        title: str,
        work_item_id: Optional[int],
        parent_id: Optional[int],
        mpp_task_id: Optional[str] = None
    ):
        """Registra uma Task pulada (duplicada)"""
        if not self.current_log:
            return
        
        item = SyncItem(
            title=title,
            work_item_type="Task",
            work_item_id=work_item_id,
            parent_id=parent_id,
            action="skipped",
            mpp_task_id=mpp_task_id
        )
        self.current_log.skipped_tasks.append(item)
    
    def log_failed_user_story(
        self,
        title: str,
        error: str,
        parent_id: Optional[int],
        mpp_task_id: Optional[str] = None
    ):
        """Registra uma User Story que falhou"""
        if not self.current_log:
            return
        
        item = SyncItem(
            title=title,
            work_item_type="User Story",
            parent_id=parent_id,
            action="failed",
            error=error,
            mpp_task_id=mpp_task_id
        )
        self.current_log.failed_user_stories.append(item)
    
    def log_failed_task(
        self,
        title: str,
        error: str,
        parent_id: Optional[int],
        mpp_task_id: Optional[str] = None
    ):
        """Registra uma Task que falhou"""
        if not self.current_log:
            return
        
        item = SyncItem(
            title=title,
            work_item_type="Task",
            parent_id=parent_id,
            action="failed",
            error=error,
            mpp_task_id=mpp_task_id
        )
        self.current_log.failed_tasks.append(item)
    
    def finish_sync(self) -> Dict[str, Any]:
        """
        Finaliza o registro de sincronização e salva o log.
        
        Returns:
            Resumo da sincronização
        """
        if not self.current_log:
            return {}
        
        # Gera resumo
        summary = self.current_log.get_summary()
        self.current_log.summary = summary
        
        # Salva log em JSON
        log_file = self.log_dir / f"sync_{self.current_log.sync_id}.json"
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(self.current_log.model_dump(), f, indent=2, ensure_ascii=False, default=str)
        
        # Salva resumo em texto legível
        summary_file = self.log_dir / f"sync_{self.current_log.sync_id}_summary.txt"
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write(self._format_summary_text())
        
        log_data = summary.copy()
        log_data['log_file'] = str(log_file)
        log_data['summary_file'] = str(summary_file)
        
        return log_data
    
    def _format_summary_text(self) -> str:
        """Formata resumo em texto legível"""
        if not self.current_log:
            return ""
        
        log = self.current_log
        lines = [
            "=" * 80,
            "REGISTRO DE SINCRONIZACAO",
            "=" * 80,
            f"ID: {log.sync_id}",
            f"Data/Hora: {log.timestamp.strftime('%Y-%m-%d %H:%M:%S')}",
            f"Feature ID: {log.feature_id}",
            f"Projeto: {log.project_name}",
            f"Arquivo: {log.file_name}",
            "",
            "ESTATISTICAS:",
            f"  User Stories no arquivo: {log.total_user_stories}",
            f"  Tasks no arquivo: {log.total_tasks}",
            "",
            "CRIADOS:",
            f"  User Stories: {len(log.created_user_stories)}",
            f"  Tasks: {len(log.created_tasks)}",
            "",
            "ATUALIZADOS:",
            f"  User Stories: {len(log.updated_user_stories)}",
            f"  Tasks: {len(log.updated_tasks)}",
            "",
            "PULADOS (duplicados):",
            f"  User Stories: {len(log.skipped_user_stories)}",
            f"  Tasks: {len(log.skipped_tasks)}",
            "",
            "FALHAS:",
            f"  User Stories: {len(log.failed_user_stories)}",
            f"  Tasks: {len(log.failed_tasks)}",
            "",
        ]
        
        # Detalhes de itens criados
        if log.created_user_stories:
            lines.extend([
                "USER STORIES CRIADAS:",
                *[f"  - {item.title} (ID: {item.work_item_id}, Parent: {item.parent_id})" 
                  for item in log.created_user_stories],
                ""
            ])
        
        if log.created_tasks:
            lines.extend([
                "TASKS CRIADAS:",
                *[f"  - {item.title} (ID: {item.work_item_id}, Parent: {item.parent_id})" 
                  for item in log.created_tasks[:20]],  # Limita a 20 para não ficar muito longo
                "" if len(log.created_tasks) <= 20 else f"  ... e mais {len(log.created_tasks) - 20} Tasks",
                ""
            ])
        
        # Detalhes de falhas
        if log.failed_user_stories:
            lines.extend([
                "USER STORIES COM FALHA:",
                *[f"  - {item.title}: {item.error}" for item in log.failed_user_stories],
                ""
            ])
        
        if log.failed_tasks:
            lines.extend([
                "TASKS COM FALHA:",
                *[f"  - {item.title}: {item.error}" for item in log.failed_tasks[:10]],  # Limita a 10
                "" if len(log.failed_tasks) <= 10 else f"  ... e mais {len(log.failed_tasks) - 10} Tasks com falha",
                ""
            ])
        
        lines.append("=" * 80)
        
        return "\n".join(lines)

