"""Validações utilitárias"""
import re
from typing import Optional

from typing import Tuple

def validate_mpp_filename(filename: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Valida e extrai informações do nome do arquivo .mpp.
    
    IMPORTANTE: Os 5 primeiros dígitos do nome do arquivo são o Work Item ID (Feature ID).
    
    Args:
        filename: Nome do arquivo
        
    Returns:
        Tupla (work_item_id, project_name) onde:
        - work_item_id: Os 5 primeiros dígitos do nome do arquivo
        - project_name: Resto do nome do arquivo (sem extensão e sem os 5 primeiros dígitos)
    """
    if not filename.endswith('.mpp'):
        return None, None
    
    # Remove extensão
    name_without_ext = filename[:-4]
    
    # Extrai os 5 primeiros dígitos como Work Item ID
    match = re.match(r'^(\d{5})', name_without_ext)
    if match:
        work_item_id = match.group(1)
        # O nome do projeto é tudo após os 5 primeiros dígitos (removendo espaços iniciais)
        project_name = name_without_ext[5:].strip()
        # Remove espaços, hífens ou underscores iniciais do nome do projeto
        project_name = re.sub(r'^[\s\-_]+', '', project_name)
        return work_item_id, project_name if project_name else name_without_ext
    
    # Se não encontrou 5 dígitos no início, retorna None
    return None, name_without_ext

def sanitize_title(title: str) -> str:
    """Remove caracteres inválidos do título"""
    # Remove caracteres de controle e normaliza espaços
    title = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', title)
    title = re.sub(r'\s+', ' ', title)
    return title.strip()

def extract_client_from_path(path: str) -> Optional[str]:
    """
    Extrai o nome do cliente do Area Path ou Iteration Path.
    Cliente normalmente está após a última barra '/'
    
    Args:
        path: Area Path ou Iteration Path
        
    Returns:
        Nome do cliente ou None
    """
    if not path:
        return None
    
    parts = path.split('/')
    if len(parts) > 1:
        return parts[-1]
    return None

