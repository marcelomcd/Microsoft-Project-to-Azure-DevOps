#!/usr/bin/env python3
"""
Script principal para execução agendada na pipeline do Azure DevOps.

Este script:
1. Lê configuração de diretório de arquivos .mpp
2. Carrega histórico de sincronização
3. Identifica arquivos novos ou modificados
4. Processa cada arquivo através da lógica de conversão
5. Atualiza histórico após cada processamento bem-sucedido
6. Gera relatório final e logs detalhados
7. Retorna código de saída adequado (0 para sucesso, != 0 para falha)
"""
import sys
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

# Adiciona o diretório backend ao path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from app.config import settings
from app.services.sync_history import SyncHistoryService
from app.services.file_processor import FileProcessor
from app.services.devops_client import AzureDevOpsClient
from app.services.sharepoint_files import SharePointFileService

# Configuração de logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL, logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)


def find_mpp_files_sharepoint(sharepoint_service: SharePointFileService) -> List[Dict[str, Any]]:
    """
    Lista arquivos .mpp do SharePoint.
    
    Args:
        sharepoint_service: Serviço do SharePoint
        
    Returns:
        Lista de dicionários com informações dos arquivos
    """
    try:
        files = sharepoint_service.list_mpp_files()
        logger.info(f"Encontrados {len(files)} arquivo(s) .mpp no SharePoint")
        return files
    except Exception as e:
        logger.exception(f"Erro ao listar arquivos do SharePoint: {e}")
        raise


def find_mpp_files_local(directory: Path) -> List[Path]:
    """
    Encontra todos os arquivos .mpp no diretório especificado.
    
    Args:
        directory: Diretório onde buscar arquivos .mpp
        
    Returns:
        Lista de caminhos de arquivos .mpp encontrados
    """
    if not directory.exists():
        logger.warning(f"Diretório não existe: {directory}")
        return []
    
    mpp_files = list(directory.glob("*.mpp"))
    logger.info(f"Encontrados {len(mpp_files)} arquivo(s) .mpp no diretório: {directory}")
    return sorted(mpp_files)


def validate_environment() -> bool:
    """
    Valida variáveis de ambiente e configurações necessárias.
    
    Returns:
        True se validação passou, False caso contrário
    """
    errors = []
    
    # Valida PAT
    if not settings.AZURE_DEVOPS_PAT:
        errors.append("AZURE_DEVOPS_PAT não configurado")
    
    # Valida fonte de arquivos
    if settings.USE_SHAREPOINT:
        if not settings.SHAREPOINT_CLIENT_ID:
            errors.append("SHAREPOINT_CLIENT_ID não configurado")
        if not settings.SHAREPOINT_CLIENT_SECRET:
            errors.append("SHAREPOINT_CLIENT_SECRET não configurado")
        if not settings.SHAREPOINT_TENANT_ID:
            errors.append("SHAREPOINT_TENANT_ID não configurado")
        if not settings.SHAREPOINT_SITE_URL:
            errors.append("SHAREPOINT_SITE_URL não configurado")
    else:
        if not settings.MPP_FILES_DIR:
            errors.append("MPP_FILES_DIR não configurado (ou configure USE_SHAREPOINT=True)")
    
    if errors:
        logger.error("Erros de validação:")
        for error in errors:
            logger.error(f"  - {error}")
        return False
    
    return True


def process_files_sharepoint(
    files: List[Dict[str, Any]],
    history_service: SyncHistoryService,
    file_processor: FileProcessor,
    sharepoint_service: SharePointFileService
) -> Dict[str, Any]:
    """
    Processa lista de arquivos .mpp do SharePoint.
    
    Args:
        files: Lista de dicionários com informações dos arquivos do SharePoint
        history_service: Serviço de histórico
        file_processor: Processador de arquivos
        sharepoint_service: Serviço do SharePoint
        
    Returns:
        Dicionário com resultados do processamento
    """
    results = {
        "processed": [],
        "skipped": [],
        "failed": [],
        "total_files": len(files),
        "total_processed": 0,
        "total_skipped": 0,
        "total_failed": 0
    }
    
    import tempfile
    from datetime import datetime
    
    for file_info in files:
        filename = file_info["name"]
        file_id = file_info["id"]
        last_modified_str = file_info.get("last_modified")
        
        # Verifica se deve processar baseado no histórico
        file_entry = history_service.get_file_info(filename)
        should_process = True
        
        if file_entry and last_modified_str:
            # Compara timestamps
            try:
                last_modified = datetime.fromisoformat(last_modified_str.replace('Z', '+00:00'))
                last_sync_str = file_entry.get("last_modified")
                
                if last_sync_str:
                    last_sync = datetime.fromisoformat(last_sync_str.replace('Z', '+00:00'))
                    if last_modified <= last_sync:
                        should_process = False
            except (ValueError, TypeError):
                pass  # Se erro ao comparar, processa de qualquer forma
        
        if not should_process:
            logger.info(f"Arquivo ignorado (não modificado): {filename}")
            results["skipped"].append({
                "filename": filename,
                "reason": "Arquivo não modificado desde última sincronização"
            })
            results["total_skipped"] += 1
            continue
        
        # Baixa arquivo temporariamente
        temp_file = None
        try:
            logger.info(f"Baixando arquivo do SharePoint: {filename}")
            temp_file = sharepoint_service.download_file(file_id)
            
            # Processa arquivo
            logger.info(f"Processando arquivo: {filename}")
            process_result = file_processor.process_mpp_file(
                file_path=temp_file,
                update_existing=True,
                skip_duplicates=True
            )
            
            if process_result["success"]:
                # Atualiza histórico (usando timestamp do SharePoint)
                history_service.update_file_history(
                    filename=filename,
                    work_item_id=process_result["work_item_id"],
                    file_path=None,
                    last_modified=last_modified_str
                )
                
                # Extrai estatísticas
                conv_result = process_result.get("conversion_result")
                stats = {
                    "filename": filename,
                    "work_item_id": process_result["work_item_id"],
                    "created_user_stories": conv_result.created_user_stories if conv_result else 0,
                    "created_tasks": conv_result.created_tasks if conv_result else 0,
                    "updated_user_stories": conv_result.updated_user_stories if conv_result else 0,
                    "updated_tasks": conv_result.updated_tasks if conv_result else 0,
                    "skipped_user_stories": conv_result.skipped_user_stories if conv_result else 0,
                    "skipped_tasks": conv_result.skipped_tasks if conv_result else 0,
                    "errors": conv_result.errors if conv_result else []
                }
                
                results["processed"].append(stats)
                results["total_processed"] += 1
                
                logger.info(
                    f"Arquivo processado com sucesso: {filename} - "
                    f"Criadas: {stats['created_user_stories']} US, {stats['created_tasks']} Tasks - "
                    f"Atualizadas: {stats['updated_user_stories']} US, {stats['updated_tasks']} Tasks"
                )
            else:
                # Falha no processamento
                error_info = {
                    "filename": filename,
                    "error": process_result.get("error", "Erro desconhecido"),
                    "work_item_id": process_result.get("work_item_id")
                }
                results["failed"].append(error_info)
                results["total_failed"] += 1
                
                logger.error(f"Falha ao processar arquivo: {filename} - {error_info['error']}")
        
        except Exception as e:
            error_info = {
                "filename": filename,
                "error": f"Erro ao baixar/processar: {str(e)}",
                "work_item_id": None
            }
            results["failed"].append(error_info)
            results["total_failed"] += 1
            logger.exception(f"Erro ao processar arquivo {filename}: {e}")
        
        finally:
            # Remove arquivo temporário
            if temp_file and temp_file.exists():
                try:
                    temp_file.unlink()
                    logger.debug(f"Arquivo temporário removido: {temp_file}")
                except Exception as e:
                    logger.warning(f"Erro ao remover arquivo temporário {temp_file}: {e}")
    
    # Salva histórico após processar todos os arquivos
    try:
        history_service.save_history()
        logger.info("Histórico de sincronização salvo")
    except Exception as e:
        logger.error(f"Erro ao salvar histórico: {e}")
    
    return results


def process_files_local(
    files: List[Path],
    history_service: SyncHistoryService,
    file_processor: FileProcessor
) -> Dict[str, Any]:
    """
    Processa lista de arquivos .mpp do diretório local.
    
    Args:
        files: Lista de Paths dos arquivos
        history_service: Serviço de histórico
        file_processor: Processador de arquivos
        
    Returns:
        Dicionário com resultados do processamento
    """
    results = {
        "processed": [],
        "skipped": [],
        "failed": [],
        "total_files": len(files),
        "total_processed": 0,
        "total_skipped": 0,
        "total_failed": 0
    }
    
    for file_path in files:
        filename = file_path.name
        
        # Verifica se deve processar
        if not history_service.should_process_file(file_path):
            logger.info(f"Arquivo ignorado (não modificado): {filename}")
            results["skipped"].append({
                "filename": filename,
                "reason": "Arquivo não modificado desde última sincronização"
            })
            results["total_skipped"] += 1
            continue
        
        # Processa arquivo
        logger.info(f"Processando arquivo: {filename}")
        process_result = file_processor.process_mpp_file(
            file_path=file_path,
            update_existing=True,
            skip_duplicates=True
        )
        
        if process_result["success"]:
            # Atualiza histórico
            history_service.update_file_history(
                filename=filename,
                work_item_id=process_result["work_item_id"],
                file_path=file_path
            )
            
            # Extrai estatísticas
            conv_result = process_result.get("conversion_result")
            stats = {
                "filename": filename,
                "work_item_id": process_result["work_item_id"],
                "created_user_stories": conv_result.created_user_stories if conv_result else 0,
                "created_tasks": conv_result.created_tasks if conv_result else 0,
                "updated_user_stories": conv_result.updated_user_stories if conv_result else 0,
                "updated_tasks": conv_result.updated_tasks if conv_result else 0,
                "skipped_user_stories": conv_result.skipped_user_stories if conv_result else 0,
                "skipped_tasks": conv_result.skipped_tasks if conv_result else 0,
                "errors": conv_result.errors if conv_result else []
            }
            
            results["processed"].append(stats)
            results["total_processed"] += 1
            
            logger.info(
                f"Arquivo processado com sucesso: {filename} - "
                f"Criadas: {stats['created_user_stories']} US, {stats['created_tasks']} Tasks - "
                f"Atualizadas: {stats['updated_user_stories']} US, {stats['updated_tasks']} Tasks"
            )
        else:
            # Falha no processamento
            error_info = {
                "filename": filename,
                "error": process_result.get("error", "Erro desconhecido"),
                "work_item_id": process_result.get("work_item_id")
            }
            results["failed"].append(error_info)
            results["total_failed"] += 1
            
            logger.error(f"Falha ao processar arquivo: {filename} - {error_info['error']}")
    
    # Salva histórico após processar todos os arquivos
    try:
        history_service.save_history()
        logger.info("Histórico de sincronização salvo")
    except Exception as e:
        logger.error(f"Erro ao salvar histórico: {e}")
    
    return results


def print_summary(results: Dict[str, Any]) -> None:
    """Imprime resumo do processamento"""
    print("\n" + "=" * 80)
    print("RESUMO DA SINCRONIZAÇÃO")
    print("=" * 80)
    print(f"Total de arquivos encontrados: {results['total_files']}")
    print(f"  + Processados: {results['total_processed']}")
    print(f"  - Ignorados (não modificados): {results['total_skipped']}")
    print(f"  ❌ Falhas: {results['total_failed']}")
    
    if results["processed"]:
        print("\n" + "-" * 80)
        print("ARQUIVOS PROCESSADOS:")
        print("-" * 80)
        
        total_created_us = sum(r["created_user_stories"] for r in results["processed"])
        total_created_tasks = sum(r["created_tasks"] for r in results["processed"])
        total_updated_us = sum(r["updated_user_stories"] for r in results["processed"])
        total_updated_tasks = sum(r["updated_tasks"] for r in results["processed"])
        
        print(f"\nEstatísticas Gerais:")
        print(f"  - User Stories criadas: {total_created_us}")
        print(f"  - User Stories atualizadas: {total_updated_us}")
        print(f"  - Tasks criadas: {total_created_tasks}")
        print(f"  - Tasks atualizadas: {total_updated_tasks}")
        
        print(f"\nDetalhes por arquivo:")
        for r in results["processed"]:
            print(f"  • {r['filename']} (Feature ID: {r['work_item_id']})")
            print(f"    - Criadas: {r['created_user_stories']} US, {r['created_tasks']} Tasks")
            print(f"    - Atualizadas: {r['updated_user_stories']} US, {r['updated_tasks']} Tasks")
            print(f"    - Puladas: {r['skipped_user_stories']} US, {r['skipped_tasks']} Tasks")
            if r.get("errors"):
                print(f"    - Erros: {len(r['errors'])}")
    
    if results["failed"]:
        print("\n" + "-" * 80)
        print("ARQUIVOS COM FALHA:")
        print("-" * 80)
        for r in results["failed"]:
            print(f"  ❌ {r['filename']}: {r['error']}")
    
    print("\n" + "=" * 80)


def main() -> int:
    """
    Função principal do script.
    
    Returns:
        Código de saída (0 para sucesso, != 0 para falha)
    """
    start_time = datetime.now()
    logger.info("=" * 80)
    logger.info("Iniciando sincronização agendada de arquivos .mpp")
    logger.info(f"Horário de início: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 80)
    
    # Valida ambiente
    if not validate_environment():
        logger.error("Validação de ambiente falhou. Encerrando.")
        return 1
    
    # Valida diretório de arquivos
    mpp_files_dir = Path(settings.MPP_FILES_DIR)
    if not mpp_files_dir.exists():
        logger.error(f"Diretório de arquivos não existe: {mpp_files_dir}")
        logger.error("Configure MPP_FILES_DIR corretamente na pipeline ou variáveis de ambiente")
        return 1
    
    if not mpp_files_dir.is_dir():
        logger.error(f"MPP_FILES_DIR não é um diretório: {mpp_files_dir}")
        return 1
    
    # Inicializa serviços
    logger.info("Inicializando serviços...")
    try:
        history_service = SyncHistoryService()
        devops_client = AzureDevOpsClient()
        file_processor = FileProcessor(devops_client=devops_client)
        logger.info("Serviços inicializados com sucesso")
    except Exception as e:
        logger.exception(f"Erro ao inicializar serviços: {e}")
        return 1
    
    # Encontra arquivos .mpp
    logger.info(f"Buscando arquivos .mpp no diretório: {mpp_files_dir}")
    mpp_files = find_mpp_files(mpp_files_dir)
    
    if not mpp_files:
        logger.warning("Nenhum arquivo .mpp encontrado no diretório especificado")
        return 0  # Não é erro se não há arquivos
    
    # Processa arquivos
    logger.info(f"Iniciando processamento de {len(mpp_files)} arquivo(s)")
    results = process_files(mpp_files, history_service, file_processor)
    
    # Imprime resumo
    print_summary(results)
    
    # Calcula tempo de execução
    end_time = datetime.now()
    duration = end_time - start_time
    logger.info(f"Sincronização concluída em {duration.total_seconds():.2f} segundos")
    logger.info(f"Horário de término: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Retorna código de saída
    # 0 = sucesso (mesmo com alguns arquivos falhando, se pelo menos um foi processado)
    # 1 = falha completa (nenhum arquivo processado ou erro crítico)
    if results["total_processed"] > 0 or results["total_skipped"] > 0:
        # Houve processamento bem-sucedido ou arquivos ignorados (que é esperado)
        if results["total_failed"] > 0:
            logger.warning(f"Atenção: {results['total_failed']} arquivo(s) falharam, mas processamento continuou")
        return 0
    else:
        # Nenhum arquivo processado e todos falharam
        logger.error("Falha completa: nenhum arquivo foi processado com sucesso")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)

