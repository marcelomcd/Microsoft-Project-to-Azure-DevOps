"""Router para Work Items do Azure DevOps"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List, Dict, Any

from app.services.devops_client import AzureDevOpsClient
from app.services.workitem_analyzer import WorkItemAnalyzer
from app.models.devops_models import WorkItemResponse

router = APIRouter(prefix="/workitems", tags=["workitems"])

def get_devops_client():
    """Obtém instância do cliente DevOps (lazy initialization)"""
    try:
        return AzureDevOpsClient()
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))

def get_analyzer():
    """Obtém instância do analyzer (lazy initialization)"""
    return WorkItemAnalyzer(get_devops_client())


@router.get(
    "/{work_item_id}",
    response_model=WorkItemResponse,
    summary="Obtém um Work Item por ID",
    description="""
    Obtém detalhes completos de um Work Item do Azure DevOps.
    
    **Retorno:**
    - Todos os campos do Work Item
    - Relações (parent, children, etc.)
    - URL do Work Item no Azure DevOps
    """
)
async def get_work_item(work_item_id: int) -> WorkItemResponse:
    """
    Obtém um Work Item por ID.
    
    Args:
        work_item_id: ID do Work Item no Azure DevOps
        
    Returns:
        Work Item encontrado com todos os campos e relações
        
    Raises:
        HTTPException 404: Se o Work Item não for encontrado
        HTTPException 500: Se houver erro na busca
    """
    try:
        client = get_devops_client()
        work_item = client.get_work_item_by_id(work_item_id)
        if not work_item:
            raise HTTPException(status_code=404, detail=f"Work Item {work_item_id} não encontrado")
        return work_item
    except ValueError as e:
        # Erro de configuração (PAT não configurado)
        raise HTTPException(status_code=500, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        # Melhora mensagem de erro para o usuário
        if "autenticação" in error_msg.lower() or "AZURE_DEVOPS_PAT" in error_msg:
            raise HTTPException(
                status_code=500, 
                detail=f"Erro de autenticação: {error_msg}. Verifique o arquivo .env no backend."
            )
        raise HTTPException(status_code=500, detail=f"Erro ao buscar Work Item: {error_msg}")


@router.get(
    "/",
    response_model=List[WorkItemResponse],
    summary="Busca Work Items por filtros",
    description="""
    Busca Work Items no Azure DevOps usando filtros.
    
    **Filtros disponíveis:**
    - title: Busca por título (case-insensitive)
    - work_item_type: Tipo do Work Item (User Story, Task, Feature, etc.)
    - area_path: Area Path para filtrar
    
    **Nota:** O parâmetro `title` é obrigatório.
    """
)
async def search_work_items(
    title: Optional[str] = Query(None, description="Título do Work Item (obrigatório)"),
    work_item_type: Optional[str] = Query(None, description="Tipo do Work Item (User Story, Task, Feature, etc.)"),
    area_path: Optional[str] = Query(None, description="Area Path para filtrar")
) -> List[WorkItemResponse]:
    """
    Busca Work Items por título e outros filtros.
    
    Args:
        title: Título para buscar (obrigatório)
        work_item_type: Tipo do Work Item (opcional)
        area_path: Area Path para filtrar (opcional)
        
    Returns:
        Lista de Work Items encontrados
        
    Raises:
        HTTPException 400: Se o título não for fornecido
        HTTPException 500: Se houver erro na busca
    """
    if not title:
        raise HTTPException(status_code=400, detail="Parâmetro 'title' é obrigatório")
    
    client = get_devops_client()
    work_items = client.search_work_items_by_title(
        title=title,
        work_item_type=work_item_type,
        area_path=area_path
    )
    
    return work_items


@router.get(
    "/{work_item_id}/analyze",
    summary="Analisa um Work Item e retorna informações estruturadas",
    description="""
    Analisa uma Feature do Azure DevOps e retorna informações estruturadas.
    
    **Retorno inclui:**
    - Informações básicas da Feature (ID, título, estado, etc.)
    - User Stories filhas (com suas Tasks aninhadas)
    - Tasks diretamente vinculadas à Feature
    - Campos customizados
    - Informações do parent (se houver)
    
    **Estrutura hierárquica:**
    - Feature
      - User Stories
        - Tasks (aninhadas dentro de cada User Story)
      - Tasks (diretamente na Feature)
    """
)
async def analyze_work_item(work_item_id: int) -> Dict[str, Any]:
    """
    Analisa um Work Item e retorna informações estruturadas incluindo filhos.
    
    Este endpoint é usado principalmente para exibir detalhes de uma Feature
    na aba "Azure DevOps User Stories and Task's".
    
    Args:
        work_item_id: ID da Feature no Azure DevOps
        
    Returns:
        Dicionário com:
        - Informações básicas da Feature
        - Lista de User Stories (com Tasks aninhadas)
        - Lista de Tasks diretamente na Feature
        - Campos customizados
        - Informações do parent
        
    Raises:
        HTTPException 404: Se a Feature não for encontrada
        HTTPException 500: Se houver erro na análise
    """
    try:
        analyzer = get_analyzer()
        analysis = analyzer.analyze_work_item(work_item_id)
        if not analysis:
            raise HTTPException(status_code=404, detail="Work Item não encontrado")
        return analysis
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
        raise HTTPException(status_code=500, detail=f"Erro ao analisar Work Item: {error_msg}")
