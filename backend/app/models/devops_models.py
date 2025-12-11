"""Modelos de dados para Azure DevOps"""
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel

class WorkItemField(BaseModel):
    """Campo de um Work Item"""
    op: str = "add"
    path: str
    value: Any

class WorkItemCreate(BaseModel):
    """Modelo para criação de Work Item"""
    title: str
    work_item_type: str  # "User Story" ou "Task"
    assigned_to: Optional[str] = None
    area_path: Optional[str] = None
    iteration_path: Optional[str] = None
    start_date: Optional[datetime] = None
    target_date: Optional[datetime] = None
    description: Optional[str] = None
    parent_id: Optional[int] = None
    custom_fields: Optional[Dict[str, Any]] = None

class WorkItemResponse(BaseModel):
    """Resposta de um Work Item do Azure DevOps"""
    id: int
    rev: int
    fields: Dict[str, Any]
    relations: Optional[List[Dict[str, Any]]] = None
    url: str

class ProjectInfo(BaseModel):
    """Informações de um projeto/Feature"""
    id: str
    name: str
    description: Optional[str] = None
    url: str
    area_path: Optional[str] = None
    iteration_path: Optional[str] = None
    numero_proposta: Optional[str] = None
    responsavel_tecnico: Optional[Any] = None
    horas_projeto: Optional[Any] = None
    target_date: Optional[str] = None
    created_by: Optional[Any] = None
    criticidade: Optional[str] = None
    situacao_pendente: Optional[str] = None
    data_liberada_homologacao: Optional[str] = None
    parent: Optional[str] = None
    user_stories_count: int = 0
    tasks_count: int = 0

class ConversionResult(BaseModel):
    """Resultado de uma conversão"""
    project_name: str
    created_user_stories: int = 0
    created_tasks: int = 0
    updated_user_stories: int = 0
    updated_tasks: int = 0
    skipped_user_stories: int = 0
    skipped_tasks: int = 0
    errors: List[str] = []
    work_items: List[WorkItemResponse] = []
    sync_log: Optional[Dict[str, Any]] = None  # Registro detalhado da sincronização

