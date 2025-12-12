"""
Script para sincronizar todos os arquivos .mpp do workspace com o Azure DevOps.

Este script:
1. Encontra todos os arquivos .mpp no diretório configurado
2. Usa histórico de sincronização para processar apenas arquivos novos ou modificados
3. Para cada arquivo, extrai o Work Item ID do nome
4. Faz parse e conversão para Azure DevOps
5. Atualiza histórico após processamento bem-sucedido
6. Gera relatório final

NOTA: Para execução agendada na pipeline, use pipeline_sync.py
"""
import os
import sys
from pathlib import Path
from typing import List, Dict, Any

# Adiciona o diretório backend ao path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from app.config import settings
from app.services.file_processor import FileProcessor
from app.services.sync_history import SyncHistoryService
from app.services.devops_client import AzureDevOpsClient


def find_mpp_files(directory: Path) -> List[Path]:
    """
    Encontra todos os arquivos .mpp no diretório especificado.
    
    Args:
        directory: Diretório onde buscar arquivos .mpp
        
    Returns:
        Lista de caminhos de arquivos .mpp encontrados
    """
    if not directory.exists():
        print(f"Aviso: Diretório não existe: {directory}")
        return []
    
    mpp_files = list(directory.glob("*.mpp"))
    return sorted(mpp_files)


def main():
    """Função principal"""
    print("=" * 80)
    print("Sincronização de Arquivos .mpp com Azure DevOps")
    print("=" * 80)
    
    # Determina diretório de arquivos
    if settings.MPP_FILES_DIR:
        mpp_files_dir = Path(settings.MPP_FILES_DIR)
    else:
        # Fallback: usa diretório backend/uploads
        script_dir = Path(__file__).parent
        mpp_files_dir = script_dir / "uploads"
        print(f"Aviso: MPP_FILES_DIR não configurado. Usando diretório padrão: {mpp_files_dir}")
    
    print(f"Diretório de arquivos: {mpp_files_dir}")
    
    if not mpp_files_dir.exists():
        print(f"Erro: Diretório não existe: {mpp_files_dir}")
        return
    
    # Inicializa serviços
    print("\nInicializando serviços...")
    history_service = SyncHistoryService()
    devops_client = AzureDevOpsClient()
    file_processor = FileProcessor(devops_client=devops_client)
    
    # Encontra arquivos .mpp
    print(f"\nBuscando arquivos .mpp...")
    mpp_files = find_mpp_files(mpp_files_dir)
    
    if not mpp_files:
        print("Nenhum arquivo .mpp encontrado.")
        return
    
    print(f"Encontrados {len(mpp_files)} arquivo(s) .mpp:")
    for file in mpp_files:
        # Verifica se deve processar
        should_process = history_service.should_process_file(file)
        status = "[NOVO/MODIFICADO]" if should_process else "[NÃO MODIFICADO]"
        print(f"  {status} {file.name}")
    
    # Filtra apenas arquivos que devem ser processados
    files_to_process = [f for f in mpp_files if history_service.should_process_file(f)]
    
    if not files_to_process:
        print("\nNenhum arquivo precisa ser processado (todos estão atualizados).")
        return
    
    print(f"\nProcessando {len(files_to_process)} arquivo(s)...")
    
    # Processa cada arquivo
    results = []
    for mpp_file in files_to_process:
        filename = mpp_file.name
        print(f"\n{'='*80}")
        print(f"Processando: {filename}")
        print(f"{'='*80}")
        
        result = file_processor.process_mpp_file(
            file_path=mpp_file,
            update_existing=True,
            skip_duplicates=True
        )
        
        if result["success"]:
            # Atualiza histórico
            history_service.update_file_history(
                filename=filename,
                work_item_id=result["work_item_id"],
                file_path=mpp_file
            )
            
            conv_result = result.get("conversion_result")
            file_result = {
                "file": filename,
                "work_item_id": result["work_item_id"],
                "success": True,
                "result": {
                    "created_user_stories": conv_result.created_user_stories if conv_result else 0,
                    "updated_user_stories": conv_result.updated_user_stories if conv_result else 0,
                    "skipped_user_stories": conv_result.skipped_user_stories if conv_result else 0,
                    "created_tasks": conv_result.created_tasks if conv_result else 0,
                    "updated_tasks": conv_result.updated_tasks if conv_result else 0,
                    "skipped_tasks": conv_result.skipped_tasks if conv_result else 0,
                    "errors": conv_result.errors if conv_result else []
                }
            }
        else:
            file_result = {
                "file": filename,
                "success": False,
                "error": result.get("error", "Erro desconhecido")
            }
        
        results.append(file_result)
    
    # Salva histórico
    try:
        history_service.save_history()
        print("\nHistórico de sincronização salvo")
    except Exception as e:
        print(f"\nErro ao salvar histórico: {e}")
    
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

