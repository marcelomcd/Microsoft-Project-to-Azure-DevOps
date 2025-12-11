"""
Script para sincronizar todos os arquivos .mpp do workspace com o Azure DevOps.

Este script:
1. Encontra todos os arquivos .mpp no workspace
2. Para cada arquivo, extrai o Work Item ID do nome
3. Faz upload e parse do arquivo
4. Sincroniza User Stories e Tasks com o Azure DevOps
5. Garante que Tasks estejam vinculadas corretamente aos User Stories
6. Sincroniza datas corretamente
"""
import os
import sys
from pathlib import Path
from typing import List, Dict, Any

# Adiciona o diretório backend ao path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from app.services.mpp_parser import MPPParser
from app.services.mapper_service import MapperService
from app.services.devops_client import AzureDevOpsClient
from app.utils.validators import validate_mpp_filename


def find_mpp_files(workspace_root: Path) -> List[Path]:
    """Encontra todos os arquivos .mpp no workspace"""
    mpp_files = []
    
    # Busca na raiz do workspace
    for file in workspace_root.glob("*.mpp"):
        mpp_files.append(file)
    
    # Busca no diretório backend/uploads
    uploads_dir = workspace_root / "backend" / "uploads"
    if uploads_dir.exists():
        for file in uploads_dir.glob("*.mpp"):
            mpp_files.append(file)
    
    return mpp_files


def extract_work_item_id(filename: str) -> int:
    """Extrai Work Item ID do nome do arquivo"""
    work_item_id, _ = validate_mpp_filename(filename)
    if work_item_id:
        try:
            return int(work_item_id)
        except (ValueError, TypeError):
            pass
    return None


def sync_mpp_file(file_path: Path, mapper_service: MapperService, parser: MPPParser) -> Dict[str, Any]:
    """Sincroniza um arquivo .mpp com o Azure DevOps"""
    filename = file_path.name
    work_item_id = extract_work_item_id(filename)
    
    if not work_item_id:
        return {
            "file": filename,
            "success": False,
            "error": f"Nao foi possivel extrair Work Item ID do nome do arquivo: {filename}"
        }
    
    print(f"\n{'='*80}")
    print(f"Processando arquivo: {filename}")
    print(f"Work Item ID: {work_item_id}")
    print(f"{'='*80}")
    
    try:
        # Parse do arquivo
        print(f"Parseando arquivo {filename}...")
        parsed_data = parser.parse_file(str(file_path), original_filename=filename)
        
        print(f"  - Projeto: {parsed_data.project.name}")
        print(f"  - User Stories: {len(parsed_data.user_stories)}")
        print(f"  - Tasks: {len(parsed_data.tasks)}")
        
        # Sincroniza com Azure DevOps
        print(f"Sincronizando com Azure DevOps (Feature ID: {work_item_id})...")
        result = mapper_service.convert_to_devops(
            parsed_data=parsed_data,
            skip_duplicates=True,
            parent_feature_id=work_item_id,
            update_existing=True  # Atualiza itens existentes
        )
        
        print(f"\nResultado da sincronizacao:")
        print(f"  + User Stories criadas: {result.created_user_stories}")
        print(f"  + User Stories atualizadas: {result.updated_user_stories or 0}")
        print(f"  - User Stories puladas: {result.skipped_user_stories}")
        print(f"  + Tasks criadas: {result.created_tasks}")
        print(f"  + Tasks atualizadas: {result.updated_tasks or 0}")
        print(f"  - Tasks puladas: {result.skipped_tasks}")
        
        if result.errors:
            print(f"\nErros encontrados ({len(result.errors)}):")
            for error in result.errors:
                print(f"  - {error}")
        
        return {
            "file": filename,
            "work_item_id": work_item_id,
            "success": True,
            "result": {
                "created_user_stories": result.created_user_stories,
                "updated_user_stories": result.updated_user_stories or 0,
                "skipped_user_stories": result.skipped_user_stories,
                "created_tasks": result.created_tasks,
                "updated_tasks": result.updated_tasks or 0,
                "skipped_tasks": result.skipped_tasks,
                "errors": result.errors
            }
        }
        
    except Exception as e:
        error_msg = f"Erro ao processar arquivo {filename}: {str(e)}"
        print(f"❌ {error_msg}")
        import traceback
        traceback.print_exc()
        return {
            "file": filename,
            "work_item_id": work_item_id,
            "success": False,
            "error": error_msg
        }


def main():
    """Função principal"""
    # Determina o diretório raiz do workspace
    # Assume que o script está em backend/, então sobe um nível
    script_dir = Path(__file__).parent
    workspace_root = script_dir.parent
    
    print(f"Workspace root: {workspace_root}")
    print(f"Buscando arquivos .mpp...")
    
    # Encontra todos os arquivos .mpp
    mpp_files = find_mpp_files(workspace_root)
    
    if not mpp_files:
        print("Nenhum arquivo .mpp encontrado no workspace.")
        return
    
    print(f"Encontrados {len(mpp_files)} arquivo(s) .mpp:")
    for file in mpp_files:
        print(f"  - {file.name}")
    
    # Inicializa serviços
    print("\nInicializando serviços...")
    parser = MPPParser()
    devops_client = AzureDevOpsClient()
    mapper_service = MapperService(devops_client)
    
    # Processa cada arquivo
    results = []
    for mpp_file in mpp_files:
        result = sync_mpp_file(mpp_file, mapper_service, parser)
        results.append(result)
    
    # Resumo final
    print(f"\n{'='*80}")
    print("RESUMO FINAL")
    print(f"{'='*80}")
    
    successful = sum(1 for r in results if r.get("success"))
    failed = len(results) - successful
    
    print(f"Total de arquivos processados: {len(results)}")
    print(f"  + Sucesso: {successful}")
    print(f"  - Falhas: {failed}")
    
    if successful > 0:
        total_created_us = sum(r["result"]["created_user_stories"] for r in results if r.get("success"))
        total_updated_us = sum(r["result"]["updated_user_stories"] for r in results if r.get("success"))
        total_created_tasks = sum(r["result"]["created_tasks"] for r in results if r.get("success"))
        total_updated_tasks = sum(r["result"]["updated_tasks"] for r in results if r.get("success"))
        
        print(f"\nEstatísticas totais:")
        print(f"  - User Stories criadas: {total_created_us}")
        print(f"  - User Stories atualizadas: {total_updated_us}")
        print(f"  - Tasks criadas: {total_created_tasks}")
        print(f"  - Tasks atualizadas: {total_updated_tasks}")
    
    if failed > 0:
        print(f"\nArquivos com falha:")
        for r in results:
            if not r.get("success"):
                print(f"  - {r['file']}: {r.get('error', 'Erro desconhecido')}")


if __name__ == "__main__":
    main()

