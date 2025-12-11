"""Modelos de dados para arquivos .mpp"""
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel

class MPPTask(BaseModel):
    """Representa uma tarefa do arquivo .mpp"""
    id: Optional[str] = None
    name: str
    resource_name: Optional[str] = None
    start_date: Optional[datetime] = None
    finish_date: Optional[datetime] = None
    duration: Optional[str] = None
    percent_complete: Optional[float] = None
    priority: Optional[int] = None
    notes: Optional[str] = None
    is_user_story: bool = False
    parent_id: Optional[str] = None
    level: int = 0
    summary: bool = False
    work: Optional[str] = None
    work_hours: Optional[float] = None
    predecessors: Optional[str] = None
    type: Optional[str] = None
    task_mode: Optional[str] = None

class MPPProject(BaseModel):
    """Representa um projeto do arquivo .mpp"""
    name: str
    file_name: str
    work_item_id: Optional[str] = None
    tasks: List[MPPTask] = []
    created_at: datetime = datetime.now()

class ParsedMPPData(BaseModel):
    """Dados parseados de um arquivo .mpp"""
    project: MPPProject
    user_stories: List[MPPTask] = []
    tasks: List[MPPTask] = []

