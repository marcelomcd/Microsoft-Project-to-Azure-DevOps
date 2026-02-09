"""Serviço para processar arquivos .mpp (parse + conversão)"""
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List

from app.services.mpp_parser import MPPParser
from app.services.mapper_service import MapperService
from app.services.devops_client import AzureDevOpsClient
from app.models.mpp_models import ParsedMPPData
from app.models.devops_models import ConversionResult
from app.utils.validators import validate_mpp_filename

logger = logging.getLogger(__name__)


class FileProcessor:
    """Processa arquivos .mpp: faz parse e conversão para Azure DevOps"""
    
    def __init__(
        self,
        devops_client: Optional[AzureDevOpsClient] = None,
        mapper_service: Optional[MapperService] = None
    ):
        """
        Inicializa o processador de arquivos.
        
        Args:
            devops_client: Cliente Azure DevOps (opcional, cria novo se não fornecido)
            mapper_service: Serviço de mapeamento (opcional, cria novo se não fornecido)
        """
        self.parser = MPPParser()
        self.devops_client = devops_client or AzureDevOpsClient()
        self.mapper_service = mapper_service or MapperService(self.devops_client)
    
    def process_mpp_file(
        self,
        file_path: Path,
        parent_feature_id: Optional[int] = None,
        original_filename: Optional[str] = None,
        update_existing: bool = True,
        skip_duplicates: bool = True,
        closed_tasks_collector: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Processa um arquivo .mpp completo: parse + conversão para Azure DevOps.
        
        Args:
            file_path: Caminho do arquivo .mpp
            parent_feature_id: ID da Feature pai (opcional, será extraído do nome se não fornecido)
            original_filename: Nome original do arquivo (usado quando file_path é temporário, ex: arquivos do SharePoint)
            update_existing: Se True, atualiza itens existentes
            skip_duplicates: Se True, pula itens duplicados
            
        Returns:
            Dicionário com resultado do processamento contendo:
            - success: bool - Se processamento foi bem-sucedido
            - filename: str - Nome do arquivo
            - work_item_id: int|None - ID do Work Item (Feature)
            - parsed_data: ParsedMPPData|None - Dados parseados
            - conversion_result: ConversionResult|None - Resultado da conversão
            - error: str|None - Mensagem de erro se houver falha
        """
        # Usa original_filename se fornecido, senão usa o nome do arquivo no caminho
        filename = original_filename or file_path.name
        logger.info(f"Iniciando processamento do arquivo: {filename}")
        
        result = {
            "success": False,
            "filename": filename,
            "work_item_id": None,
            "parsed_data": None,
            "conversion_result": None,
            "error": None
        }
        
        try:
            # Passo 1: Parse do arquivo (usa original_filename para o parser também)
            logger.debug(f"Fazendo parse do arquivo: {file_path}")
            parsed_data = self.parser.parse_file(str(file_path), original_filename=filename)
            
            if not parsed_data:
                error_msg = f"Falha ao fazer parse do arquivo: {filename}"
                logger.error(error_msg)
                result["error"] = error_msg
                return result
            
            result["parsed_data"] = parsed_data
            
            # Passo 2: Extrai Work Item ID do nome do arquivo ou usa fornecido
            # IMPORTANTE: Usa filename (que pode ser original_filename) para extrair o Work Item ID
            work_item_id = parent_feature_id
            if not work_item_id:
                work_item_id_from_filename, _ = validate_mpp_filename(filename)
                if work_item_id_from_filename:
                    try:
                        work_item_id = int(work_item_id_from_filename)
                    except (ValueError, TypeError):
                        pass
            
            # Se não tem work_item_id nem do nome nem fornecido, tenta do parsed_data
            if not work_item_id and parsed_data.project.work_item_id:
                try:
                    work_item_id = int(parsed_data.project.work_item_id)
                except (ValueError, TypeError):
                    pass
            
            if not work_item_id:
                error_msg = f"Não foi possível determinar Work Item ID (Feature ID) para o arquivo: {filename}"
                logger.error(error_msg)
                result["error"] = error_msg
                return result
            
            result["work_item_id"] = work_item_id
            logger.info(f"Work Item ID identificado: {work_item_id}")
            
            # Passo 3: Conversão para Azure DevOps
            logger.debug(f"Convertendo para Azure DevOps (Feature ID: {work_item_id})")
            conversion_result = self.mapper_service.convert_to_devops(
                parsed_data=parsed_data,
                skip_duplicates=skip_duplicates,
                parent_feature_id=work_item_id,
                update_existing=update_existing,
                closed_tasks_collector=closed_tasks_collector,
            )
            
            result["conversion_result"] = conversion_result
            result["success"] = True
            
            logger.info(
                f"Processamento concluído: {filename} - "
                f"Criadas: {conversion_result.created_user_stories} US, {conversion_result.created_tasks} Tasks - "
                f"Atualizadas: {conversion_result.updated_user_stories or 0} US, {conversion_result.updated_tasks or 0} Tasks - "
                f"Puladas: {conversion_result.skipped_user_stories} US, {conversion_result.skipped_tasks} Tasks"
            )
            
            if conversion_result.errors:
                logger.warning(f"Erros durante conversão de {filename}: {conversion_result.errors}")
            
            return result
            
        except Exception as e:
            error_msg = f"Erro ao processar arquivo {filename}: {str(e)}"
            logger.exception(error_msg)
            result["error"] = error_msg
            return result
    
    def parse_file_only(self, file_path: Path) -> Optional[ParsedMPPData]:
        """
        Apenas faz parse do arquivo sem converter para Azure DevOps.
        
        Args:
            file_path: Caminho do arquivo .mpp
            
        Returns:
            ParsedMPPData ou None se houver erro
        """
        filename = file_path.name
        logger.info(f"Fazendo parse do arquivo: {filename}")
        
        try:
            parsed_data = self.parser.parse_file(str(file_path), original_filename=filename)
            return parsed_data
        except Exception as e:
            logger.exception(f"Erro ao fazer parse do arquivo {filename}: {e}")
            return None

