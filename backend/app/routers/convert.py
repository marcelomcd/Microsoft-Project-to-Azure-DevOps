"""
Router para conversão de arquivos .mpp para Azure DevOps

Este router fornece endpoints para:
- Converter arquivos .mpp parseados em Work Items (User Stories e Tasks) no Azure DevOps
- Sincronizar dados do Azure DevOps para formato compatível com .mpp
"""
from fastapi import APIRouter, HTTPException, Body
from typing import Optional, Dict

from app.services.mapper_service import MapperService
from app.services.devops_client import AzureDevOpsClient
from app.services.workitem_analyzer import WorkItemAnalyzer
from app.models.devops_models import ConversionResult
from app.routers.upload import parsed_files

router = APIRouter(prefix="/convert", tags=["convert"])

def get_devops_client():
    """Obtém instância do cliente DevOps (lazy initialization)"""
    try:
        return AzureDevOpsClient()
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))

def get_mapper_service():
    """Obtém instância do mapper service (lazy initialization)"""
    return MapperService(get_devops_client())

def get_analyzer():
    """Obtém instância do analyzer (lazy initialization)"""
    return WorkItemAnalyzer(get_devops_client())


@router.post(
    "/",
    response_model=ConversionResult,
    summary="Converte arquivo .mpp em Work Items no Azure DevOps",
    description="""
    Converte um arquivo .mpp parseado em User Stories e Tasks no Azure DevOps.
    
    **Funcionalidades:**
    - Cria User Stories e Tasks baseadas no arquivo .mpp
    - Verifica duplicatas antes de criar (evita duplicação)
    - Vincula Tasks às User Stories corretas baseado na hierarquia
    - Atualiza itens existentes se `update_existing=True`
    - Valida que todos os parents existem antes de criar
    - Gera registro detalhado de todas as operações
    
    **Validações:**
    - Verifica se a Feature pai existe antes de criar User Stories
    - Verifica se User Stories existem antes de vincular Tasks
    - Valida títulos não vazios
    - Double check de duplicatas antes de criar
    
    **Registro de Alterações:**
    O resultado inclui `sync_log` com:
    - Itens criados (User Stories e Tasks)
    - Itens atualizados
    - Itens pulados (duplicados)
    - Itens com falha (com mensagens de erro)
    - Estatísticas completas
    
    **Exemplo de uso:**
    ```json
    {
        "file_id": "uuid-do-arquivo",
        "parent_feature_id": 15404,
        "update_existing": true,
        "skip_duplicates": true
    }
    ```
    """
)
async def convert_mpp_to_devops(
    file_id: str = Body(..., description="ID do arquivo parseado (obtido no upload)"),
    area_path: Optional[str] = Body(None, description="Area Path do projeto (opcional, será determinado automaticamente)"),
    iteration_path: Optional[str] = Body(None, description="Iteration Path do projeto (opcional, será determinado automaticamente)"),
    skip_duplicates: bool = Body(True, description="Se True, verifica e pula itens duplicados"),
    parent_feature_id: Optional[int] = Body(None, description="ID da Feature pai para vincular User Stories (opcional, será obtido do nome do arquivo se não fornecido)"),
    update_existing: bool = Body(False, description="Se True, atualiza itens existentes ao invés de apenas pular")
) -> ConversionResult:
    """
    Converte arquivo .mpp parseado em Work Items no Azure DevOps.
    
    Este endpoint processa o arquivo .mpp e cria/atualiza User Stories e Tasks
    no Azure DevOps, garantindo que:
    - Não há duplicatas
    - Tasks estão vinculadas às User Stories corretas
    - Todos os parents existem antes de criar filhos
    
    Returns:
        ConversionResult com estatísticas e registro detalhado (sync_log)
        
    Raises:
        HTTPException 404: Se o arquivo não for encontrado
        HTTPException 500: Se houver erro na conversão
    """
    if file_id not in parsed_files:
        raise HTTPException(status_code=404, detail="Arquivo não encontrado. Faça upload do arquivo primeiro.")
    
    try:
        from app.models.mpp_models import ParsedMPPData
        
        # Recupera dados parseados
        file_data = parsed_files[file_id]
        parsed_data = ParsedMPPData(**file_data["parsed_data"])
        
        # Converte
        mapper = get_mapper_service()
        result = mapper.convert_to_devops(
            parsed_data=parsed_data,
            area_path=area_path,
            iteration_path=iteration_path,
            skip_duplicates=skip_duplicates,
            parent_feature_id=parent_feature_id,
            update_existing=update_existing
        )
        
        return result
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
        raise HTTPException(status_code=500, detail=f"Erro ao converter: {error_msg}")


@router.post(
    "/sync-from-devops",
    summary="Sincroniza dados do Azure DevOps para formato compatível com .mpp",
    description="""
    Sincroniza dados de uma Feature do Azure DevOps para formato compatível com .mpp.
    
    **Funcionalidades:**
    - Busca Feature e todos os seus filhos (User Stories e Tasks)
    - Retorna dados estruturados que podem ser usados para gerar arquivo .mpp
    - Permite filtrar itens fechados
    
    **Exemplo de uso:**
    ```json
    {
        "work_item_id": 15404,
        "include_closed": true
    }
    ```
    """
)
async def sync_devops_to_mpp(
    work_item_id: int = Body(..., description="ID da Feature no Azure DevOps"),
    include_closed: bool = Body(True, description="Se True, inclui User Stories e Tasks com status 'Closed'")
) -> Dict:
    """
    Sincroniza dados do Azure DevOps para formato compatível com .mpp.
    
    Retorna dados estruturados que podem ser usados para gerar arquivo .mpp.
    Inclui a Feature, suas User Stories e Tasks (hierarquicamente organizadas).
    
    Args:
        work_item_id: ID da Feature no Azure DevOps
        include_closed: Se True, inclui User Stories e Tasks com status 'Closed'
        
    Returns:
        Dicionário com:
        - success: True se bem-sucedido
        - work_item_id: ID da Feature
        - data: Dados estruturados (Feature, User Stories, Tasks)
        - message: Mensagem de sucesso
        
    Raises:
        HTTPException 404: Se a Feature não for encontrada
        HTTPException 500: Se houver erro na sincronização
    """
    try:
        # Analisa Work Item e filhos
        analyzer = get_analyzer()
        analysis = analyzer.analyze_work_item(work_item_id)
        if not analysis:
            raise HTTPException(status_code=404, detail=f"Work Item {work_item_id} não encontrado")
        
        # Filtra por status se necessário
        if not include_closed:
            analysis['user_stories'] = [
                us for us in analysis.get('user_stories', [])
                if us.get('state', '').lower() not in ['closed', 'concluído', 'resolvido']
            ]
            analysis['tasks'] = [
                task for task in analysis.get('tasks', [])
                if task.get('state', '').lower() not in ['closed', 'concluído', 'resolvido']
            ]
        
        return {
            "success": True,
            "work_item_id": work_item_id,
            "data": analysis,
            "message": f"Dados sincronizados do Work Item {work_item_id}"
        }
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
        raise HTTPException(status_code=500, detail=f"Erro ao sincronizar: {error_msg}")

