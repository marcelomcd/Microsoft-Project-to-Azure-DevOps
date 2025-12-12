"""Serviço para gerenciar histórico de sincronização de arquivos"""
import json
import logging
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime
from typing import Dict, Optional

try:
    from zoneinfo import ZoneInfo
except ImportError:
    # Python < 3.9 ou sistema sem zoneinfo
    try:
        from backports.zoneinfo import ZoneInfo
    except ImportError:
        # Fallback: usar pytz se disponível, senão usar timezone local
        try:
            import pytz
            ZoneInfo = lambda tz: pytz.timezone(tz)
        except ImportError:
            # Último fallback: usar timezone local
            import time
            ZoneInfo = lambda tz: None  # Retorna None, será tratado no código

from app.config import settings

logger = logging.getLogger(__name__)


class SyncHistoryService:
    """Gerencia histórico de arquivos processados para sincronização agendada"""
    
    def __init__(self, history_file: Optional[Path] = None):
        """
        Inicializa o serviço de histórico.
        
        Args:
            history_file: Caminho do arquivo de histórico (padrão: logs/sync_history.json)
        """
        if history_file is None:
            # Diretório padrão: backend/logs/
            backend_dir = Path(__file__).parent.parent.parent
            history_file = backend_dir / "logs" / "sync_history.json"
        
        self.history_file = Path(history_file)
        self.history_file.parent.mkdir(parents=True, exist_ok=True)
        self._history: Dict = {}
        
        # Configura timezone
        try:
            self._timezone = ZoneInfo(settings.TIMEZONE) if ZoneInfo else None
        except Exception:
            # Se falhar, usa timezone local (None)
            self._timezone = None
        
        self._load_history()
    
    def _load_history(self) -> None:
        """Carrega histórico do arquivo JSON"""
        if not self.history_file.exists():
            logger.info(f"Arquivo de histórico não existe. Criando novo: {self.history_file}")
            self._history = {
                "version": "1.0",
                "last_updated": None,
                "files": {}
            }
            return
        
        try:
            with open(self.history_file, 'r', encoding='utf-8') as f:
                self._history = json.load(f)
            
            # Valida estrutura
            if "files" not in self._history:
                logger.warning("Arquivo de histórico com estrutura inválida. Reinicializando.")
                self._history = {
                    "version": "1.0",
                    "last_updated": None,
                    "files": {}
                }
            
            logger.info(f"Histórico carregado: {len(self._history.get('files', {}))} arquivos registrados")
        except json.JSONDecodeError as e:
            logger.error(f"Erro ao decodificar histórico: {e}. Criando novo histórico.")
            self._history = {
                "version": "1.0",
                "last_updated": None,
                "files": {}
            }
        except Exception as e:
            logger.error(f"Erro ao carregar histórico: {e}. Criando novo histórico.")
            self._history = {
                "version": "1.0",
                "last_updated": None,
                "files": {}
            }
    
    def save_history(self) -> None:
        """Salva histórico atualizado no arquivo JSON"""
        try:
            if self._timezone:
                self._history["last_updated"] = datetime.now(self._timezone).isoformat()
            else:
                self._history["last_updated"] = datetime.now().isoformat()
            
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(self._history, f, indent=2, ensure_ascii=False)
            
            logger.debug(f"Histórico salvo: {self.history_file}")
        except Exception as e:
            logger.error(f"Erro ao salvar histórico: {e}")
            raise
    
    def should_process_file(self, file_path: Path) -> bool:
        """
        Verifica se um arquivo deve ser processado.
        
        Um arquivo deve ser processado se:
        - Não está no histórico (novo arquivo)
        - Foi modificado desde a última sincronização
        
        Args:
            file_path: Caminho do arquivo .mpp
            
        Returns:
            True se arquivo deve ser processado, False caso contrário
        """
        if not file_path.exists():
            logger.warning(f"Arquivo não existe: {file_path}")
            return False
        
        filename = file_path.name
        file_stat = file_path.stat()
        
        # Obtém timestamp de modificação do arquivo
        if self._timezone:
            file_modified = datetime.fromtimestamp(file_stat.st_mtime, tz=self._timezone)
        else:
            file_modified = datetime.fromtimestamp(file_stat.st_mtime)
            # Assume timezone local se não há ZoneInfo disponível
        
        # Verifica se arquivo está no histórico
        file_entry = self._history.get("files", {}).get(filename)
        
        if not file_entry:
            logger.info(f"Arquivo novo encontrado: {filename}")
            return True
        
        # Compara timestamps
        last_modified_str = file_entry.get("last_modified")
        if not last_modified_str:
            logger.info(f"Arquivo sem timestamp de modificação no histórico: {filename}. Processando.")
            return True
        
        try:
            # Converte string ISO para datetime
            last_modified = datetime.fromisoformat(last_modified_str)
            if self._timezone and last_modified.tzinfo is None:
                # Se não tem timezone e temos timezone configurado, assume timezone configurado
                last_modified = last_modified.replace(tzinfo=self._timezone)
            
            # Compara timestamps
            if file_modified > last_modified:
                logger.info(
                    f"Arquivo modificado: {filename} "
                    f"(última modificação: {file_modified}, última sincronização: {last_modified})"
                )
                return True
            else:
                logger.debug(
                    f"Arquivo não modificado: {filename} "
                    f"(última modificação: {file_modified}, última sincronização: {last_modified})"
                )
                return False
        except (ValueError, TypeError) as e:
            logger.warning(f"Erro ao comparar timestamps para {filename}: {e}. Processando arquivo.")
            return True
    
    def update_file_history(
        self,
        filename: str,
        work_item_id: Optional[int],
        file_path: Optional[Path] = None,
        last_modified: Optional[str] = None
    ) -> None:
        """
        Atualiza histórico após processamento bem-sucedido de um arquivo.
        
        Args:
            filename: Nome do arquivo
            work_item_id: ID do Work Item (Feature) associado
            file_path: Caminho do arquivo (opcional, usado para obter timestamp se last_modified não fornecido)
            last_modified: Timestamp de modificação em formato ISO (opcional, usado para SharePoint)
        """
        if "files" not in self._history:
            self._history["files"] = {}
        
        # Obtém timestamp de modificação do arquivo
        file_modified = None
        if last_modified:
            # Usa timestamp fornecido (ex: do SharePoint)
            file_modified = last_modified
        elif file_path and file_path.exists():
            # Obtém do sistema de arquivos
            file_stat = file_path.stat()
            if self._timezone:
                file_modified = datetime.fromtimestamp(file_stat.st_mtime, tz=self._timezone).isoformat()
            else:
                file_modified = datetime.fromtimestamp(file_stat.st_mtime).isoformat()
        else:
            # Se não tem caminho nem timestamp fornecido, usa timestamp atual
            if self._timezone:
                file_modified = datetime.now(self._timezone).isoformat()
            else:
                file_modified = datetime.now().isoformat()
        
        # Atualiza ou cria entrada
        if filename not in self._history["files"]:
            self._history["files"][filename] = {
                "sync_count": 0,
                "first_sync": None,
                "last_sync": None,
                "last_modified": None,
                "work_item_id": None
            }
        
        entry = self._history["files"][filename]
        entry["sync_count"] = entry.get("sync_count", 0) + 1
        if self._timezone:
            entry["last_sync"] = datetime.now(self._timezone).isoformat()
        else:
            entry["last_sync"] = datetime.now().isoformat()
        entry["last_modified"] = file_modified
        if work_item_id:
            entry["work_item_id"] = work_item_id
        
        # Primeira sincronização
        if not entry.get("first_sync"):
            entry["first_sync"] = entry["last_sync"]
        
        logger.info(
            f"Histórico atualizado: {filename} "
            f"(sync_count: {entry['sync_count']}, work_item_id: {work_item_id})"
        )
    
    def get_file_info(self, filename: str) -> Optional[Dict]:
        """
        Obtém informações de um arquivo do histórico.
        
        Args:
            filename: Nome do arquivo
            
        Returns:
            Dicionário com informações do arquivo ou None se não encontrado
        """
        return self._history.get("files", {}).get(filename)
    
    def get_all_files(self) -> Dict:
        """
        Retorna todas as entradas do histórico.
        
        Returns:
            Dicionário com todas as entradas de arquivos
        """
        return self._history.get("files", {}).copy()
    
    def remove_file(self, filename: str) -> None:
        """
        Remove um arquivo do histórico.
        
        Args:
            filename: Nome do arquivo a remover
        """
        if filename in self._history.get("files", {}):
            del self._history["files"][filename]
            logger.info(f"Arquivo removido do histórico: {filename}")

