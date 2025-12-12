"""Serviço para listar e baixar arquivos do SharePoint"""
import logging
import requests
from pathlib import Path
from typing import List, Optional, Dict, Any
from urllib.parse import urlparse, urljoin
import tempfile

from app.services.sharepoint_auth import SharePointAuthService
from app.config import settings

logger = logging.getLogger(__name__)


class SharePointFileService:
    """Gerencia acesso a arquivos no SharePoint"""
    
    def __init__(
        self,
        site_url: Optional[str] = None,
        folder_path: Optional[str] = None,
        auth_service: Optional[SharePointAuthService] = None
    ):
        """
        Inicializa o serviço de arquivos SharePoint.
        
        Args:
            site_url: URL do site SharePoint
            folder_path: Caminho da pasta no SharePoint (ex: "Documentos Compartilhados/Cronogramas - Project")
            auth_service: Serviço de autenticação (opcional, cria novo se não fornecido)
        """
        self.site_url = site_url or settings.SHAREPOINT_SITE_URL
        self.folder_path = folder_path or settings.SHAREPOINT_FOLDER_PATH
        
        if not self.site_url:
            raise ValueError("SHAREPOINT_SITE_URL não está configurado")
        
        # Normaliza URL do site (remove trailing slash)
        self.site_url = self.site_url.rstrip('/')
        
        # Inicializa serviço de autenticação
        self.auth_service = auth_service or SharePointAuthService()
        
        # Base URL para Microsoft Graph API
        self.graph_base_url = "https://graph.microsoft.com/v1.0"
        
        # Extrai informações do site da URL
        self._parse_site_info()
    
    def _parse_site_info(self) -> None:
        """Extrai informações do site SharePoint da URL"""
        parsed = urlparse(self.site_url)
        hostname = parsed.netloc
        
        # Extrai nome do site (geralmente após /sites/)
        path_parts = [p for p in parsed.path.split('/') if p]
        
        # Procura por "sites" no path
        if 'sites' in path_parts:
            sites_index = path_parts.index('sites')
            if sites_index + 1 < len(path_parts):
                self.site_name = path_parts[sites_index + 1]
            else:
                self.site_name = ""
        elif path_parts:
            # Se não tem "sites", usa última parte
            self.site_name = path_parts[-1]
        else:
            # Se não há path, assume site raiz
            self.site_name = ""
        
        self.hostname = hostname
        
        logger.debug(f"Site SharePoint: {self.site_name} em {self.hostname}")
    
    def _get_site_id(self) -> str:
        """
        Obtém o Site ID do SharePoint usando Microsoft Graph API.
        
        Returns:
            Site ID do SharePoint
            
        Raises:
            ValueError: Se não conseguir obter Site ID
        """
        access_token = self.auth_service.get_access_token()
        
        # Busca site pelo hostname e nome
        if self.site_name:
            url = f"{self.graph_base_url}/sites/{self.hostname}:/sites/{self.site_name}"
        else:
            url = f"{self.graph_base_url}/sites/{self.hostname}"
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json"
        }
        
        try:
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            site_data = response.json()
            site_id = site_data.get("id")
            
            if not site_id:
                raise ValueError("Site ID não encontrado na resposta")
            
            logger.debug(f"Site ID obtido: {site_id}")
            return site_id
        except requests.exceptions.RequestException as e:
            logger.error(f"Erro ao obter Site ID: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Resposta: {e.response.text}")
            raise ValueError(f"Falha ao obter Site ID do SharePoint: {e}")
    
    def _get_drive_id(self, site_id: str) -> str:
        """
        Obtém o Drive ID (document library) do SharePoint.
        
        Args:
            site_id: Site ID do SharePoint
            
        Returns:
            Drive ID
            
        Raises:
            ValueError: Se não conseguir obter Drive ID
        """
        access_token = self.auth_service.get_access_token()
        
        # Busca drives (document libraries) do site
        url = f"{self.graph_base_url}/sites/{site_id}/drives"
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json"
        }
        
        try:
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            drives_data = response.json()
            drives = drives_data.get("value", [])
            
            if not drives:
                raise ValueError("Nenhum drive encontrado no site")
            
            # Usa o primeiro drive (geralmente "Documentos" ou "Documentos Compartilhados")
            drive_id = drives[0].get("id")
            
            if not drive_id:
                raise ValueError("Drive ID não encontrado")
            
            logger.debug(f"Drive ID obtido: {drive_id}")
            return drive_id
        except requests.exceptions.RequestException as e:
            logger.error(f"Erro ao obter Drive ID: {e}")
            raise ValueError(f"Falha ao obter Drive ID do SharePoint: {e}")
    
    def _get_folder_id(self, drive_id: str, folder_path: str) -> Optional[str]:
        """
        Obtém o ID de uma pasta no SharePoint.
        
        Args:
            drive_id: Drive ID
            folder_path: Caminho da pasta (ex: "Documentos Compartilhados/Cronogramas - Project")
            
        Returns:
            Folder ID ou None se não encontrada
        """
        if not folder_path:
            return "root"  # Pasta raiz
        
        access_token = self.auth_service.get_access_token()
        
        # Busca pasta pelo caminho
        # Escapa caracteres especiais no caminho
        folder_path_encoded = folder_path.replace("'", "''")
        url = f"{self.graph_base_url}/drives/{drive_id}/root:/{folder_path_encoded}"
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json"
        }
        
        try:
            response = requests.get(url, headers=headers, timeout=30)
            
            if response.status_code == 404:
                logger.warning(f"Pasta não encontrada: {folder_path}")
                return None
            
            response.raise_for_status()
            folder_data = response.json()
            folder_id = folder_data.get("id")
            
            logger.debug(f"Folder ID obtido: {folder_id} para {folder_path}")
            return folder_id
        except requests.exceptions.RequestException as e:
            logger.warning(f"Erro ao obter Folder ID para {folder_path}: {e}")
            return None
    
    def list_mpp_files(self) -> List[Dict[str, Any]]:
        """
        Lista todos os arquivos .mpp no SharePoint.
        
        Returns:
            Lista de dicionários com informações dos arquivos:
            - name: Nome do arquivo
            - id: ID do arquivo no SharePoint
            - size: Tamanho em bytes
            - last_modified: Data/hora da última modificação
            - web_url: URL do arquivo
        """
        logger.info("Listando arquivos .mpp do SharePoint")
        
        try:
            # Obtém IDs necessários
            site_id = self._get_site_id()
            drive_id = self._get_drive_id(site_id)
            folder_id = self._get_folder_id(drive_id, self.folder_path)
            
            if not folder_id:
                logger.warning(f"Pasta não encontrada: {self.folder_path}. Tentando pasta raiz.")
                folder_id = "root"
            
            # Lista arquivos na pasta
            access_token = self.auth_service.get_access_token()
            
            # Lista todos os arquivos (filtrar .mpp depois)
            url = f"{self.graph_base_url}/drives/{drive_id}/items/{folder_id}/children"
            params = {
                "$select": "id,name,size,lastModifiedDateTime,webUrl,file"
            }
            
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json"
            }
            
            mpp_files = []
            
            # Processa resultados paginados
            while url:
                response = requests.get(url, headers=headers, params=params, timeout=30)
                response.raise_for_status()
                
                data = response.json()
                items = data.get("value", [])
                
                for item in items:
                    # Filtra apenas arquivos .mpp (não pastas)
                    name = item.get("name", "")
                    if name.lower().endswith(".mpp") and item.get("file") is not None:
                        file_info = {
                            "name": name,
                            "id": item.get("id"),
                            "size": item.get("size", 0),
                            "last_modified": item.get("lastModifiedDateTime"),
                            "web_url": item.get("webUrl")
                        }
                        mpp_files.append(file_info)
                
                # Verifica se há próxima página
                next_link = data.get("@odata.nextLink")
                if next_link:
                    url = next_link
                    params = None  # URL já tem parâmetros
                else:
                    break
            
            logger.info(f"Encontrados {len(mpp_files)} arquivo(s) .mpp")
            return mpp_files
            
        except Exception as e:
            logger.exception(f"Erro ao listar arquivos do SharePoint: {e}")
            raise
    
    def download_file(self, file_id: str, destination: Optional[Path] = None) -> Path:
        """
        Baixa um arquivo do SharePoint.
        
        Args:
            file_id: ID do arquivo no SharePoint
            destination: Caminho de destino (opcional, usa arquivo temporário se não fornecido)
            
        Returns:
            Path do arquivo baixado
        """
        logger.debug(f"Baixando arquivo do SharePoint: {file_id}")
        
        # Obtém drive_id necessário
        site_id = self._get_site_id()
        drive_id = self._get_drive_id(site_id)
        
        access_token = self.auth_service.get_access_token()
        
        # Obtém conteúdo do arquivo
        url = f"{self.graph_base_url}/drives/{drive_id}/items/{file_id}/content"
        
        headers = {
            "Authorization": f"Bearer {access_token}"
        }
        
        try:
            response = requests.get(url, headers=headers, stream=True, timeout=60)
            response.raise_for_status()
            
            # Salva arquivo
            if destination is None:
                # Cria arquivo temporário
                suffix = ".mpp"
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
                destination = Path(temp_file.name)
                temp_file.close()
            
            destination = Path(destination)
            destination.parent.mkdir(parents=True, exist_ok=True)
            
            # Escreve conteúdo
            with open(destination, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            logger.info(f"Arquivo baixado: {destination}")
            return destination
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Erro ao baixar arquivo {file_id}: {e}")
            raise ValueError(f"Falha ao baixar arquivo do SharePoint: {e}")

