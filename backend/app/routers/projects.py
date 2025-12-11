"""Router para projetos do Azure DevOps"""
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional

from app.services.devops_client import AzureDevOpsClient
from app.models.devops_models import ProjectInfo, WorkItemResponse
from app.utils.cache import project_cache

router = APIRouter(prefix="/projects", tags=["projects"])

def get_devops_client():
    """Obtém instância do cliente DevOps (lazy initialization)"""
    try:
        return AzureDevOpsClient()
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/",
    response_model=List[ProjectInfo],
    summary="Lista todos os projetos/Features do Azure DevOps",
    description="""
    Lista todas as Features do Azure DevOps com informações detalhadas.
    
    **Informações retornadas:**
    - ID, nome e descrição da Feature
    - Area Path e Iteration Path
    - Campos customizados (Número de Proposta, Responsável Técnico, etc.)
    - Contagem de User Stories e Tasks
    - URL da Feature no Azure DevOps
    
    **Cache:**
    - Por padrão, usa cache para melhor performance
    - Cache expira após 5 minutos
    - Desative cache para obter dados sempre atualizados
    """
)
async def list_projects(
    limit: Optional[int] = Query(None, description="Limite de resultados (opcional, None = todos)"),
    use_cache: bool = Query(True, description="Usar cache quando disponível (padrão: True)")
) -> List[ProjectInfo]:
    """
    Lista todos os projetos/Features do Azure DevOps.
    
    Este endpoint é usado na aba "Projects in Azure DevOps" para exibir
    todas as Features disponíveis.
    
    Args:
        limit: Limite de resultados (opcional, None = todos os projetos)
        use_cache: Se True, usa cache quando disponível (padrão: True)
    
    Returns:
        Lista de Features com informações detalhadas
        
    Raises:
        HTTPException 500: Se houver erro ao buscar Features
    """
    try:
        # Se limit não for especificado, busca todos os projetos (None = todos)
        client = get_devops_client()
        projects = client.list_projects(limit=limit, use_cache=use_cache)
        return projects
    except ValueError as e:
        # Erro de configuração (PAT não configurado)
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        error_msg = str(e)
        # Melhora mensagem de erro para o usuário
        if "autenticação" in error_msg.lower() or "AZURE_DEVOPS_PAT" in error_msg:
            raise HTTPException(
                status_code=500, 
                detail=f"Erro de autenticação: {error_msg}. Verifique o arquivo .env no backend."
            )
        raise HTTPException(status_code=500, detail=f"Erro ao listar projetos: {error_msg}")


@router.get("/{project_id}/workitems", response_model=List[WorkItemResponse])
async def get_project_work_items(project_id: str) -> List[WorkItemResponse]:
    """
    Lista todos os Work Items de um projeto.
    
    Args:
        project_id: ID do projeto
        
    Returns:
        Lista de Work Items do projeto
    """
    client = get_devops_client()
    work_items = client.get_project_work_items(project_id)
    return work_items


@router.post("/cache/clear")
async def clear_cache():
    """Limpa o cache de projetos"""
    try:
        project_cache.clear()
        return {"message": "Cache limpo com sucesso"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao limpar cache: {str(e)}")


@router.get("/cache/stats")
async def get_cache_stats():
    """Retorna estatísticas do cache"""
    try:
        return project_cache.get_stats()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao obter estatísticas: {str(e)}")

