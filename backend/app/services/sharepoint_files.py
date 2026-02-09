"""Serviço para listar e baixar arquivos do SharePoint"""
import logging
import requests
from pathlib import Path
from typing import List, Optional, Dict, Any, Union
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
    
    def _get_drive_id(self, site_id: str, return_all: bool = False, drive_name_preference: Optional[str] = None) -> Union[str, List[Dict[str, Any]]]:
        """
        Obtém o Drive ID (document library) do SharePoint.
        
        Args:
            site_id: Site ID do SharePoint
            return_all: Se True, retorna lista de todos os drives. Se False, retorna apenas o ID do drive preferido ou o primeiro disponível.
            drive_name_preference: Nome da biblioteca preferida (ex: "Documentações de Projetos"). Se None, tenta "Documentos Compartilhados" primeiro.
            
        Returns:
            Drive ID (string) ou lista de drives (dict) se return_all=True
            
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
            
            # Se return_all=True, retorna todos os drives
            if return_all:
                return drives
            
            # Lista de nomes preferidos (em ordem de prioridade)
            preferred_names = []
            if drive_name_preference:
                preferred_names.append(drive_name_preference)
            preferred_names.extend([
                "Documentações de Projetos",
                "Documentos Compartilhados",
                "Shared Documents"
            ])
            
            # Tenta encontrar biblioteca preferida
            for preferred_name in preferred_names:
                for drive in drives:
                    drive_name = drive.get("name", "")
                    if preferred_name.lower() in drive_name.lower():
                        drive_id = drive.get("id")
                        if drive_id:
                            logger.debug(f"Drive ID obtido ({drive_name}): {drive_id}")
                            return drive_id
            
            # Se não encontrou nenhuma preferida, usa o primeiro drive disponível
            drive_id = drives[0].get("id")
            
            if not drive_id:
                raise ValueError("Drive ID não encontrado")
            
            drive_name = drives[0].get("name", "Desconhecido")
            logger.debug(f"Drive ID obtido ({drive_name}): {drive_id}")
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
        # Microsoft Graph API requer codificação URL para o caminho
        # Tenta múltiplas variações de codificação
        from urllib.parse import quote, unquote
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json"
        }
        
        # Lista de variações de codificação para tentar
        encoding_variations = []
        
        # 1. Se já está codificado, tenta usar diretamente
        if "%" in folder_path:
            encoding_variations.append(folder_path)
            # Tenta decodificar e recodificar
            try:
                decoded = unquote(folder_path)
                encoding_variations.append(decoded)
            except:
                pass
        
        # 2. Codificação padrão (divide em partes e codifica cada parte)
        path_parts = folder_path.split("/")
        encoded_parts = [quote(part, safe="") for part in path_parts]
        encoding_variations.append("/".join(encoded_parts))
        
        # 3. Codificação com espaços como +
        path_with_plus = folder_path.replace(" ", "+")
        encoding_variations.append(path_with_plus)
        
        # 4. Sem codificação (caminho original)
        encoding_variations.append(folder_path)
        
        # Remove duplicatas mantendo ordem
        seen = set()
        unique_variations = []
        for var in encoding_variations:
            if var not in seen:
                seen.add(var)
                unique_variations.append(var)
        
        # Tenta cada variação
        last_error = None
        for i, encoded_path in enumerate(unique_variations, 1):
            url = f"{self.graph_base_url}/drives/{drive_id}/root:/{encoded_path}"
            try:
                response = requests.get(url, headers=headers, timeout=30)
                
                if response.status_code == 200:
                    folder_data = response.json()
                    folder_id = folder_data.get("id")
                    if folder_id:
                        logger.debug(f"Folder ID obtido (tentativa {i}): {folder_id} para {folder_path} (codificação: {encoded_path[:50]}...)")
                        return folder_id
                
                if response.status_code == 404:
                    logger.debug(f"Tentativa {i} falhou (404): {encoded_path[:50]}...")
                    continue
                    
                response.raise_for_status()
            except requests.exceptions.RequestException as e:
                last_error = e
                logger.debug(f"Tentativa {i} falhou: {e}")
                continue
        
        # Se nenhuma tentativa funcionou
        logger.warning(f"Pasta não encontrada após {len(unique_variations)} tentativas: {folder_path}")
        if last_error:
            logger.debug(f"Último erro: {last_error}")
        return None
            
    
    def list_mpp_files(self) -> List[Dict[str, Any]]:
        """
        Lista todos os arquivos .mpp na pasta principal e nas subpastas (ex.: pastas de clientes).
        
        A pasta configurada em folder_path é a pasta principal; dentro dela, todas as subpastas
        são percorridas (um nível) e os .mpp de cada uma são incluídos. A regra de última
        alteração (24h ou desde a última execução da pipeline) continua sendo aplicada pelo
        pipeline ao processar esta lista.
        
        Returns:
            Lista de dicionários com informações dos arquivos:
            - name: Nome do arquivo
            - id: ID do arquivo no SharePoint
            - size: Tamanho em bytes
            - last_modified: Data/hora da última modificação
            - web_url: URL do arquivo
            - folder_name: Nome da subpasta (vazio "" se estiver na pasta principal)
        """
        logger.info("Listando arquivos .mpp do SharePoint")
        
        try:
            # Obtém IDs necessários
            site_id = self._get_site_id()
            drive_id = self._get_drive_id(site_id)
            folder_id = self._get_folder_id(drive_id, self.folder_path)
            
            if not folder_id:
                logger.warning(f"Pasta não encontrada: {self.folder_path}. Tentando variações do caminho.")
                
                # Obtém access_token para debug
                access_token = self.auth_service.get_access_token()
                
                # Tenta listar pastas disponíveis na raiz para debug
                try:
                    debug_url = f"{self.graph_base_url}/drives/{drive_id}/root/children"
                    debug_response = requests.get(
                        debug_url,
                        headers={"Authorization": f"Bearer {access_token}", "Accept": "application/json"},
                        params={"$select": "name,id,folder"},
                        timeout=30
                    )
                    if debug_response.status_code == 200:
                        debug_data = debug_response.json()
                        items = debug_data.get("value", [])
                        folders = [item for item in items if item.get("folder") is not None]
                        files = [item for item in items if item.get("file") is not None]
                        
                        if folders:
                            folder_names = [f.get("name", "") for f in folders]
                            logger.info(f"📁 Pastas disponíveis na raiz: {', '.join(folder_names)}")
                        
                        if files:
                            file_names = [f.get("name", "") for f in files if f.get("name", "").lower().endswith(".mpp")]
                            if file_names:
                                logger.info(f"📄 Arquivos .mpp encontrados na raiz: {', '.join(file_names)}")
                except Exception as e:
                    logger.warning(f"Erro ao listar pastas para debug: {e}")
                
                # Tenta variações do caminho
                # Se o caminho original inclui "Documentos Compartilhados/", tenta sem essa parte também
                folder_path_clean = self.folder_path
                if folder_path_clean.startswith("Documentos Compartilhados/"):
                    folder_path_clean = folder_path_clean.replace("Documentos Compartilhados/", "", 1)
                
                folder_variations = [
                    self.folder_path,  # Caminho original completo
                    folder_path_clean,  # Sem "Documentos Compartilhados/" se estava presente
                    "Cronogramas - Project",  # Apenas subpasta
                    "Cronogramas-Project",    # Sem espaços
                    "CronogramasProject",     # Sem espaços e hífen
                ]
                
                # Remove duplicatas mantendo ordem
                seen = set()
                unique_variations = []
                for var in folder_variations:
                    if var and var not in seen:
                        seen.add(var)
                        unique_variations.append(var)
                
                for variation in unique_variations:
                    logger.info(f"Tentando caminho alternativo: {variation}")
                    folder_id = self._get_folder_id(drive_id, variation)
                    if folder_id:
                        logger.info(f"✅ Pasta encontrada com caminho: {variation}")
                        break
                
                if not folder_id:
                    logger.error(f"❌ Nenhuma variação do caminho funcionou. Verifique o caminho: {self.folder_path}")
                    return []  # Retorna vazio se nenhuma pasta for encontrada
            
            # Lista arquivos na pasta principal e em todas as subpastas (pastas de clientes)
            access_token = self.auth_service.get_access_token()
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json"
            }
            params = {
                "$select": "id,name,size,lastModifiedDateTime,webUrl,file,folder"
            }
            mpp_files = []

            def collect_mpp_from_folder(parent_folder_id: str, folder_name: str) -> None:
                """Coleta arquivos .mpp de uma pasta (paginação incluída). folder_name vazio = pasta principal."""
                nonlocal mpp_files
                url = f"{self.graph_base_url}/drives/{drive_id}/items/{parent_folder_id}/children"
                req_params = params
                while url:
                    response = requests.get(url, headers=headers, params=req_params, timeout=30)
                    response.raise_for_status()
                    data = response.json()
                    items = data.get("value", [])
                    for item in items:
                        name = item.get("name", "")
                        if item.get("folder") is not None:
                            # É uma subpasta: não percorre recursivamente além do primeiro nível
                            continue
                        if name.lower().endswith(".mpp") and item.get("file") is not None:
                            file_info = {
                                "name": name,
                                "id": item.get("id"),
                                "size": item.get("size", 0),
                                "last_modified": item.get("lastModifiedDateTime"),
                                "web_url": item.get("webUrl"),
                                "folder_name": folder_name,
                            }
                            mpp_files.append(file_info)
                    next_link = data.get("@odata.nextLink")
                    url = next_link if next_link else None
                    req_params = None  # próxima página já traz parâmetros na URL

            # 1) Arquivos .mpp na pasta principal (folder_name = "")
            collect_mpp_from_folder(folder_id, "")

            # 2) Lista subpastas da pasta principal e coleta .mpp de cada uma
            url = f"{self.graph_base_url}/drives/{drive_id}/items/{folder_id}/children"
            while url:
                response = requests.get(url, headers=headers, params=params, timeout=30)
                response.raise_for_status()
                data = response.json()
                items = data.get("value", [])
                for item in items:
                    if item.get("folder") is None:
                        continue
                    subfolder_id = item.get("id")
                    subfolder_name = item.get("name", "")
                    if not subfolder_id:
                        continue
                    logger.debug(f"Listando arquivos na subpasta: {subfolder_name}")
                    collect_mpp_from_folder(subfolder_id, subfolder_name)
                next_link = data.get("@odata.nextLink")
                url = next_link if next_link else None

            logger.info(f"Encontrados {len(mpp_files)} arquivo(s) .mpp (pasta principal + subpastas)")
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
    
    def upload_file(
        self,
        file_path: Path,
        folder_path: Optional[str] = None,
        overwrite: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Faz upload de um arquivo para o SharePoint.
        
        Args:
            file_path: Caminho do arquivo local para upload
            folder_path: Caminho da pasta no SharePoint (usa self.folder_path se não fornecido)
            overwrite: Se True, sobrescreve arquivo existente
            
        Returns:
            Dicionário com informações do arquivo enviado ou None se erro
        """
        logger.info(f"Fazendo upload de arquivo para SharePoint: {file_path.name}")
        
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"Arquivo não encontrado: {file_path}")
        
        # Obtém IDs necessários
        site_id = self._get_site_id()
        drive_id = self._get_drive_id(site_id)
        target_folder_path = folder_path or self.folder_path
        
        # Tenta encontrar a pasta (pode tentar variações do caminho)
        folder_id = self._get_folder_id(drive_id, target_folder_path)
        
        # Se não encontrou, tenta variações (mesma lógica usada em list_mpp_files)
        if not folder_id:
            logger.warning(f"Pasta não encontrada: {target_folder_path}. Tentando variações do caminho.")
            # Remove prefixo "Documentos Compartilhados/" se presente
            if target_folder_path.startswith("Documentos Compartilhados/"):
                alternative_path = target_folder_path.replace("Documentos Compartilhados/", "")
                logger.info(f"Tentando caminho alternativo: {alternative_path}")
                folder_id = self._get_folder_id(drive_id, alternative_path)
        
        if not folder_id:
            raise ValueError(f"Pasta não encontrada no SharePoint: {target_folder_path}")
        
        access_token = self.auth_service.get_access_token()
        
        # Lê conteúdo do arquivo
        with open(file_path, 'rb') as f:
            file_content = f.read()
        
        # URL para upload (usa método de upload simples para arquivos < 4MB)
        # Para arquivos maiores, seria necessário usar upload session
        file_name = file_path.name
        
        # Codifica nome do arquivo para URL (importante para caracteres especiais)
        from urllib.parse import quote
        encoded_file_name = quote(file_name, safe='')
        
        url = f"{self.graph_base_url}/drives/{drive_id}/items/{folder_id}:/{encoded_file_name}:/content"
        
        if overwrite:
            # Adiciona parâmetro para sobrescrever
            url += "?@microsoft.graph.conflictBehavior=replace"
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/octet-stream"
        }
        
        try:
            file_size_kb = len(file_content) / 1024
            logger.info(f"Fazendo upload de arquivo ({file_size_kb:.2f} KB)...")
            logger.debug(f"URL: {url}")
            
            # Para arquivos maiores que 4MB, usa upload session
            # Para arquivos menores, usa upload simples
            if len(file_content) > 4 * 1024 * 1024:  # 4MB
                logger.info("Arquivo maior que 4MB, usando upload session...")
                return self._upload_large_file(drive_id, folder_id, file_path, file_content, access_token)
            
            # Upload simples para arquivos < 4MB
            response = requests.put(
                url, 
                headers=headers, 
                data=file_content, 
                timeout=300,  # Aumenta timeout para 5 minutos
                stream=False
            )
            
            # Log resposta
            logger.debug(f"Status code: {response.status_code}")
            
            if response.status_code == 403:
                error_msg = "Erro 403: Permissão negada. Verifique se Sites.ReadWrite.All está concedido para o App Registration."
                logger.error(error_msg)
                if response.text:
                    logger.error(f"Resposta do servidor: {response.text[:500]}")
                raise ValueError(error_msg)
            
            response.raise_for_status()
            
            file_data = response.json()
            logger.info(f"Arquivo enviado com sucesso: {file_data.get('name', file_name)}")
            logger.info(f"   ID: {file_data.get('id')}")
            logger.info(f"   Tamanho: {file_data.get('size', 0) / 1024:.2f} KB")
            
            return {
                "id": file_data.get("id"),
                "name": file_data.get("name"),
                "size": file_data.get("size"),
                "web_url": file_data.get("webUrl"),
                "last_modified": file_data.get("lastModifiedDateTime")
            }
            
        except requests.exceptions.Timeout:
            error_msg = "Timeout ao fazer upload. Arquivo pode ser muito grande ou conexão lenta."
            logger.error(error_msg)
            raise ValueError(error_msg)
        except requests.exceptions.RequestException as e:
            logger.error(f"Erro ao fazer upload do arquivo: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Status code: {e.response.status_code}")
                logger.error(f"Resposta: {e.response.text[:500]}")
                if e.response.status_code == 403:
                    raise ValueError(
                        "Erro 403: Permissão negada. Verifique se Sites.ReadWrite.All está concedido "
                        "e se o consentimento do administrador foi dado no Azure Portal."
                    )
            raise ValueError(f"Falha ao fazer upload do arquivo para SharePoint: {e}")
    
    def _upload_large_file(
        self,
        drive_id: str,
        folder_id: str,
        file_path: Path,
        file_content: bytes,
        access_token: str
    ) -> Dict[str, Any]:
        """
        Faz upload de arquivo grande (>4MB) usando upload session.
        
        Args:
            drive_id: Drive ID
            folder_id: Folder ID
            file_path: Caminho do arquivo
            file_content: Conteúdo do arquivo em bytes
            access_token: Access token
            
        Returns:
            Dicionário com informações do arquivo enviado
        """
        file_name = file_path.name
        file_size = len(file_content)
        
        # Cria upload session
        session_url = f"{self.graph_base_url}/drives/{drive_id}/items/{folder_id}:/{file_name}:/createUploadSession"
        
        session_headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        session_body = {
            "item": {
                "@microsoft.graph.conflictBehavior": "replace",
                "name": file_name
            }
        }
        
        logger.info(f"Criando upload session para arquivo de {file_size / 1024 / 1024:.2f} MB...")
        session_response = requests.post(session_url, headers=session_headers, json=session_body, timeout=30)
        session_response.raise_for_status()
        session_data = session_response.json()
        upload_url = session_data.get("uploadUrl")
        
        if not upload_url:
            raise ValueError("Upload session não retornou uploadUrl")
        
        # Faz upload em chunks (4MB cada)
        chunk_size = 4 * 1024 * 1024  # 4MB
        total_chunks = (file_size + chunk_size - 1) // chunk_size
        
        logger.info(f"Fazendo upload em {total_chunks} chunk(s)...")
        
        for chunk_num in range(total_chunks):
            start = chunk_num * chunk_size
            end = min(start + chunk_size, file_size)
            chunk = file_content[start:end]
            
            chunk_headers = {
                "Content-Length": str(len(chunk)),
                "Content-Range": f"bytes {start}-{end-1}/{file_size}"
            }
            
            logger.debug(f"Enviando chunk {chunk_num + 1}/{total_chunks} ({len(chunk) / 1024:.2f} KB)...")
            
            chunk_response = requests.put(
                upload_url,
                headers=chunk_headers,
                data=chunk,
                timeout=300
            )
            
            if chunk_response.status_code in [200, 201]:
                # Upload completo
                file_data = chunk_response.json()
                logger.info(f"Upload completo: {file_data.get('name', file_name)}")
                return {
                    "id": file_data.get("id"),
                    "name": file_data.get("name"),
                    "size": file_data.get("size"),
                    "web_url": file_data.get("webUrl"),
                    "last_modified": file_data.get("lastModifiedDateTime")
                }
            elif chunk_response.status_code == 202:
                # Chunk aceito, continua
                continue
            else:
                chunk_response.raise_for_status()
        
        raise ValueError("Upload não foi completado")

