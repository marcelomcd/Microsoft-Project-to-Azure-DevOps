"""Cliente para Azure DevOps REST API com connection pooling e cache otimizado"""
import requests
from typing import List, Optional, Dict, Any
from datetime import datetime
from typing import Tuple
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from app.config import settings
from app.models.devops_models import (
    WorkItemResponse, 
    WorkItemCreate, 
    ProjectInfo,
    WorkItemField
)


class AzureDevOpsClient:
    """Cliente para interagir com Azure DevOps API com connection pooling"""
    
    def __init__(self, pat: Optional[str] = None):
        self.pat = pat or settings.AZURE_DEVOPS_PAT
        self.org = settings.AZURE_DEVOPS_ORG
        self.project = settings.AZURE_DEVOPS_PROJECT
        self.base_url = settings.azure_devops_base_url
        self.api_version = "7.1"
        
        # Valida PAT
        if not self.pat or self.pat.strip() == "" or self.pat == "SEU_PAT_AQUI":
            raise ValueError(
                "AZURE_DEVOPS_PAT não está configurado! "
                "Configure o PAT no arquivo .env na pasta backend. "
                "Exemplo: AZURE_DEVOPS_PAT=seu_token_aqui"
            )
        
        # Cria sessão com connection pooling
        self.session = requests.Session()
        
        # Configura retry strategy
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "POST", "PUT", "PATCH", "DELETE"]
        )
        
        # Configura adapter com connection pooling
        adapter = HTTPAdapter(
            pool_connections=10,  # Número de pools de conexão
            pool_maxsize=20,     # Tamanho máximo de cada pool
            max_retries=retry_strategy
        )
        
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Headers para autenticação
        self.session.headers.update({
            "Authorization": f"Basic {self._encode_pat()}",
            "Content-Type": "application/json"
        })
    
    def _encode_pat(self) -> str:
        """Codifica PAT para autenticação Basic"""
        import base64
        pat_bytes = f":{self.pat}".encode('utf-8')
        return base64.b64encode(pat_bytes).decode('utf-8')
    
    def _safe_json_parse(self, response: requests.Response) -> Dict[str, Any]:
        """Faz parse seguro de JSON da resposta, com tratamento de erros"""
        try:
            return response.json()
        except ValueError as e:
            # Tenta obter mais informações sobre o erro
            content_preview = response.text[:500] if response.text else "Resposta vazia"
            status_code = response.status_code
            url = response.url
            
            # Verifica se é um erro de autenticação
            if '/_signin' in str(url) or status_code in [401, 403]:
                raise Exception(
                    f"Erro de autenticação. Verifique se o AZURE_DEVOPS_PAT está configurado corretamente no arquivo .env. "
                    f"Status: {status_code}"
                )
            
            # Verifica se a resposta é HTML (geralmente indica erro)
            content_type = response.headers.get('Content-Type', '')
            if 'text/html' in content_type:
                raise Exception(
                    f"Resposta inesperada do servidor (HTML ao invés de JSON). "
                    f"Status: {status_code}, URL: {url}. "
                    f"Verifique a autenticação e a configuração do Azure DevOps."
                )
            
            raise Exception(
                f"Erro ao processar resposta JSON da API. "
                f"Status: {status_code}, Erro: {str(e)}, "
                f"Conteúdo: {content_preview}"
            )
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """Faz requisição à API do Azure DevOps usando connection pooling"""
        from urllib.parse import quote
        # URL-encode o nome do projeto para evitar problemas com espaços e caracteres especiais
        # Usa encoding UTF-8 explícito para caracteres acentuados (ç, ã, etc.)
        # O Azure DevOps espera espaços como %20 e caracteres especiais codificados em UTF-8
        project_encoded = quote(self.project, safe='', encoding='utf-8')
        url = f"{self.base_url}/{project_encoded}/_apis/{endpoint}"
        params = kwargs.pop('params', {})
        params['api-version'] = self.api_version
        
        # Log detalhado para debug
        print(f"DevOpsClient: {method} {url}")
        print(f"DevOpsClient: Projeto original: '{self.project}'")
        print(f"DevOpsClient: Projeto codificado: '{project_encoded}'")
        print(f"DevOpsClient: Org: {self.org}")
        print(f"DevOpsClient: Base URL: {self.base_url}")
        
        # Merge headers se fornecidos
        headers = kwargs.pop('headers', {})
        if headers:
            # Cria headers temporários para esta requisição
            temp_headers = self.session.headers.copy()
            temp_headers.update(headers)
            kwargs['headers'] = temp_headers
        
        try:
            response = self.session.request(
                method=method,
                url=url,
                params=params,
                timeout=30,
                **kwargs
            )
            
            # Verifica se a resposta é um redirecionamento para login (erro de autenticação)
            if response.status_code in [401, 403] or '/_signin' in response.url:
                error_msg = f"Erro de autenticação. Verifique se o AZURE_DEVOPS_PAT está configurado corretamente no arquivo .env"
                raise requests.exceptions.HTTPError(error_msg, response=response)
            
            # Verifica se a resposta é HTML (geralmente indica erro de autenticação ou projeto não encontrado)
            content_type = response.headers.get('Content-Type', '')
            if 'text/html' in content_type and response.status_code != 200:
                from urllib.parse import quote
                html_preview = response.text[:500] if response.text else "Resposta vazia"
                error_msg = (
                    f"Resposta inesperada do servidor (HTML ao invés de JSON). "
                    f"Status: {response.status_code}, URL: {response.url}. "
                    f"Projeto configurado: '{self.project}' (codificado: '{quote(self.project, safe='')}'). "
                    f"Org: {self.org}. "
                    f"Verifique se o projeto '{self.project}' existe na organização '{self.org}'. "
                    f"Preview HTML: {html_preview[:200]}"
                )
                print(f"DevOpsClient: ERRO - {error_msg}")
                raise requests.exceptions.HTTPError(error_msg, response=response)
            
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            # Re-raise com mensagem mais clara
            if hasattr(e, 'response') and e.response is not None:
                if '/_signin' in str(e.response.url):
                    raise Exception(f"Erro de autenticação: Verifique se o AZURE_DEVOPS_PAT está configurado corretamente no arquivo .env")
            raise
    
    def close(self):
        """Fecha a sessão e libera recursos"""
        if self.session:
            self.session.close()
    
    def list_projects(self, limit: Optional[int] = None, use_cache: bool = True) -> List[ProjectInfo]:
        """
        Lista todos os projetos/Features.
        
        Args:
            limit: Limite de resultados (None = todos)
            use_cache: Se True, usa cache quando disponível
        """
        from app.utils.cache import project_cache
        
        # Verifica cache
        cache_key = f"projects_list_{limit or 'all'}"
        if use_cache:
            cached_data = project_cache.get(cache_key)
            if cached_data is not None:
                return cached_data
        
        try:
            # Busca Features (projetos) com filtro de Area Path e excluindo status "Encerrado"
            # Filtra por Area Path que contém "Quali IT ! Gestao de Projetos"
            wiql_query = {
                "query": "SELECT [System.Id], [System.Title], [System.AreaPath], [System.IterationPath], [System.State] FROM WorkItems WHERE [System.WorkItemType] = 'Feature' AND [System.AreaPath] UNDER 'Quali IT - Inovação e Tecnologia\\Quali IT ! Gestao de Projetos' AND [System.State] <> 'Encerrado' ORDER BY [System.Id] DESC"
            }
            
            response = self._make_request(
                'POST',
                'wit/wiql',
                json=wiql_query
            )
            
            data = self._safe_json_parse(response)
            work_items = data.get('workItems', [])
            
            if not work_items:
                return []
            
            # Aplica limite se especificado (None = todos)
            # Nota: Azure DevOps WIQL retorna no máximo 20000 itens por padrão
            if limit is not None:
                work_items = work_items[:limit]
            
            # Busca detalhes dos Work Items em lotes (máximo 200 por vez)
            all_projects = []
            batch_size = 200
            
            for i in range(0, len(work_items), batch_size):
                batch = work_items[i:i + batch_size]
                ids = [str(wi['id']) for wi in batch]
                work_items_details = self.get_work_items_by_ids(ids)
                
                for wi in work_items_details:
                    fields = wi.fields
                    
                    # Filtra projetos com status "Encerrado" (double check)
                    state = fields.get('System.State', '')
                    if state and state.lower() in ['encerrado', 'closed', 'resolvido', 'resolved']:
                        continue  # Pula projetos encerrados
                    
                    # Extrai campos customizados
                    numero_proposta = fields.get('Custom.NumeroProposta', None)
                    responsavel_tecnico = fields.get('Custom.ResponsavelTecnico', None)
                    horas_projeto = fields.get('Custom.Horas Projeto', None)
                    criticidade = fields.get('Custom.Criticidade', None)
                    situacao_pendente = fields.get('Custom.SituacaoPendenteList', None)
                    data_liberada_homologacao = fields.get('Custom.DataLiberadaHomologacao', None)
                    target_date = fields.get('Microsoft.VSTS.Scheduling.TargetDate', None)
                    created_by = fields.get('System.CreatedBy', None)
                    
                    # Extrai parent do AreaPath (nome do cliente)
                    area_path = fields.get('System.AreaPath', '')
                    parent = None
                    if area_path:
                        parts = area_path.split('\\')
                        if len(parts) > 0:
                            parent = parts[-1]  # Último nível do Area Path
                    
                    # Conta User Stories e Tasks filhos usando relações
                    user_stories_count = 0
                    tasks_count = 0
                    if wi.relations:
                        # Busca apenas IDs dos filhos
                        child_ids = []
                        for relation in wi.relations:
                            if relation.get('rel') == 'System.LinkTypes.Hierarchy-Forward':
                                url = relation.get('url', '')
                                # Extrai ID da URL
                                if '/workItems/' in url:
                                    try:
                                        child_id = int(url.split('/workItems/')[-1])
                                        child_ids.append(child_id)
                                    except:
                                        pass
                        
                        # Busca tipos dos filhos em lote se houver muitos
                        if child_ids:
                            try:
                                child_items = self.get_work_items_by_ids([str(id) for id in child_ids[:50]])  # Limita a 50 para performance
                                for child in child_items:
                                    child_type = child.fields.get('System.WorkItemType', '')
                                    if child_type == 'User Story':
                                        user_stories_count += 1
                                    elif child_type == 'Task':
                                        tasks_count += 1
                            except:
                                pass
                    
                    all_projects.append(ProjectInfo(
                        id=str(wi.id),
                        name=fields.get('System.Title', ''),
                        description=fields.get('System.Description', None),
                        url=wi.url,
                        area_path=area_path,
                        iteration_path=fields.get('System.IterationPath', None),
                        numero_proposta=numero_proposta,
                        responsavel_tecnico=responsavel_tecnico,
                        horas_projeto=horas_projeto,
                        target_date=target_date,
                        created_by=created_by,
                        criticidade=criticidade,
                        situacao_pendente=situacao_pendente,
                        data_liberada_homologacao=data_liberada_homologacao,
                        parent=parent,
                        user_stories_count=user_stories_count,
                        tasks_count=tasks_count
                    ))
            
            # Armazena no cache
            if use_cache:
                project_cache.set(cache_key, all_projects)
            
            return all_projects
        except requests.exceptions.HTTPError as e:
            error_msg = f"Erro HTTP ao listar projetos: {e.response.status_code} - {e.response.text}"
            print(error_msg)
            raise Exception(error_msg)
        except Exception as e:
            error_msg = f"Erro ao listar projetos: {str(e)}"
            print(error_msg)
            raise Exception(error_msg)
    
    def get_work_items_by_ids(self, ids: List[str]) -> List[WorkItemResponse]:
        """Obtém Work Items por IDs"""
        if not ids:
            return []
        
        ids_str = ','.join(ids)
        response = self._make_request(
            'GET',
            f'wit/workitems',
            params={'ids': ids_str, '$expand': 'all'}
        )
        
        data = self._safe_json_parse(response)
        work_items = []
        
        if 'value' in data:
            for item in data['value']:
                work_items.append(WorkItemResponse(
                    id=item['id'],
                    rev=item['rev'],
                    fields=item.get('fields', {}),
                    relations=item.get('relations', None),
                    url=item.get('url', '')
                ))
        
        return work_items
    
    def get_work_item_by_id(self, work_item_id: int, expand: str = "relations", use_cache: bool = True) -> Optional[WorkItemResponse]:
        """Obtém um Work Item por ID com relações expandidas (com cache)"""
        from app.utils.cache import work_item_cache
        
        # Verifica cache
        cache_key = f"work_item_{work_item_id}"
        if use_cache:
            cached_item = work_item_cache.get(cache_key)
            if cached_item is not None:
                return cached_item
        
        try:
            response = self._make_request(
                'GET',
                f'wit/workitems/{work_item_id}',
                params={'$expand': 'all'}
            )
            
            item = self._safe_json_parse(response)
            work_item = WorkItemResponse(
                id=item['id'],
                rev=item['rev'],
                fields=item.get('fields', {}),
                relations=item.get('relations', None),
                url=item.get('url', '')
            )
            
            # Armazena no cache
            if use_cache:
                work_item_cache.set(cache_key, work_item, ttl_minutes=30)
            
            return work_item
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Work Item {work_item_id} não encontrado (404) no projeto {self.project}")
                return None
            error_msg = f"Erro HTTP ao buscar Work Item {work_item_id}: {e.response.status_code} - {e.response.text}"
            import logging
            logger = logging.getLogger(__name__)
            logger.error(error_msg)
            print(error_msg)
            raise Exception(error_msg)
        except Exception as e:
            error_msg = f"Erro ao buscar Work Item {work_item_id}: {str(e)}"
            import logging
            logger = logging.getLogger(__name__)
            logger.error(error_msg, exc_info=True)
            print(error_msg)
            raise Exception(error_msg)
    
    def search_work_items_by_title(
        self, 
        title: str, 
        work_item_type: Optional[str] = None,
        area_path: Optional[str] = None
    ) -> List[WorkItemResponse]:
        """
        Busca Work Items por título (case-insensitive).
        Usado para verificar duplicatas.
        """
        try:
            # Constrói query WIQL
            # Escapa aspas simples no título (substitui ' por '')
            escaped_title = title.replace("'", "''")
            query_parts = [f"[System.Title] = '{escaped_title}'"]
            
            if work_item_type:
                query_parts.append(f"[System.WorkItemType] = '{work_item_type}'")
            
            if area_path:
                query_parts.append(f"[System.AreaPath] UNDER '{area_path}'")
            
            wiql_query = {
                "query": f"SELECT [System.Id], [System.Title] FROM WorkItems WHERE {' AND '.join(query_parts)}"
            }
            
            response = self._make_request(
                'POST',
                'wit/wiql',
                json=wiql_query
            )
            
            data = self._safe_json_parse(response)
            work_items = data.get('workItems', [])
            
            if not work_items:
                return []
            
            # Busca detalhes
            ids = [str(wi['id']) for wi in work_items]
            return self.get_work_items_by_ids(ids)
            
        except Exception as e:
            print(f"Erro ao buscar Work Items: {e}")
            return []
    
    def create_work_item(self, work_item: WorkItemCreate) -> Optional[WorkItemResponse]:
        """Cria um novo Work Item no Azure DevOps"""
        try:
            # Prepara campos para criação
            fields = [
                {"op": "add", "path": "/fields/System.Title", "value": work_item.title}
            ]
            
            if work_item.assigned_to:
                fields.append({
                    "op": "add",
                    "path": "/fields/System.AssignedTo",
                    "value": work_item.assigned_to
                })
            
            if work_item.area_path:
                fields.append({
                    "op": "add",
                    "path": "/fields/System.AreaPath",
                    "value": work_item.area_path
                })
            
            if work_item.iteration_path:
                fields.append({
                    "op": "add",
                    "path": "/fields/System.IterationPath",
                    "value": work_item.iteration_path
                })
            
            # Start Date e Target Date
            # Para Tasks, Start Date e Target Date são obrigatórios
            from datetime import datetime
            now = datetime.now()
            
            # Tenta usar start_date do work_item, senão usa target_date, senão usa data atual
            start_date = work_item.start_date or work_item.target_date or now
            target_date = work_item.target_date or start_date
            
            if work_item.work_item_type == "Task" or work_item.target_date or work_item.start_date:
                fields.append({
                    "op": "add",
                    "path": "/fields/Microsoft.VSTS.Scheduling.StartDate",
                    "value": start_date.isoformat() if isinstance(start_date, datetime) else start_date
                })
                fields.append({
                    "op": "add",
                    "path": "/fields/Microsoft.VSTS.Scheduling.TargetDate",
                    "value": target_date.isoformat() if isinstance(target_date, datetime) else target_date
                })
            
            if work_item.description:
                fields.append({
                    "op": "add",
                    "path": "/fields/System.Description",
                    "value": work_item.description
                })
            
            # Campos customizados
            if work_item.custom_fields:
                for field_name, field_value in work_item.custom_fields.items():
                    fields.append({
                        "op": "add",
                        "path": f"/fields/{field_name}",
                        "value": field_value
                    })
            
            # Relação com parent se houver
            if work_item.parent_id:
                fields.append({
                    "op": "add",
                    "path": "/relations/-",
                    "value": {
                        "rel": "System.LinkTypes.Hierarchy-Reverse",
                        "url": f"{self.base_url}/{self.project}/_apis/wit/workitems/{work_item.parent_id}"
                    }
                })
            
            # Converte tipo para formato da API (espaços viram %20)
            # Formato correto: wit/workitems/$Task ou wit/workitems/$User%20Story
            work_item_type_encoded = work_item.work_item_type.replace(' ', '%20')
            endpoint = f'wit/workitems/${work_item_type_encoded}'
            
            print(f"DevOpsClient: Criando {work_item.work_item_type} no endpoint: {endpoint}")
            print(f"DevOpsClient: Campos: {len(fields)} campos")
            
            try:
                response = self._make_request(
                    'POST',
                    endpoint,
                    json=fields,
                    headers={'Content-Type': 'application/json-patch+json'}
                )
                
                item = self._safe_json_parse(response)
                return WorkItemResponse(
                    id=item['id'],
                    rev=item['rev'],
                    fields=item.get('fields', {}),
                    relations=item.get('relations', None),
                    url=item.get('url', '')
                )
            except Exception as req_error:
                # Captura resposta de erro detalhada
                error_detail = str(req_error)
                if hasattr(req_error, 'response') and req_error.response is not None:
                    try:
                        error_body = req_error.response.text
                        print(f"DevOpsClient: Erro detalhado da API: {error_body}")
                    except:
                        pass
                raise req_error
        except Exception as e:
            print(f"Erro ao criar Work Item: {e}")
            raise
    
    def update_work_item(
        self, 
        work_item_id: int,
        title: str = None,
        description: str = None,
        assigned_to: str = None,
        target_date: Optional[datetime] = None,
        start_date: Optional[datetime] = None,
        custom_fields: Optional[Dict[str, Any]] = None,
        parent_id: Optional[int] = None
    ) -> Optional[WorkItemResponse]:
        """Atualiza um Work Item existente no Azure DevOps"""
        try:
            fields = []
            
            if title:
                fields.append({
                    "op": "replace",
                    "path": "/fields/System.Title",
                    "value": title
                })
            
            if description:
                fields.append({
                    "op": "replace",
                    "path": "/fields/System.Description",
                    "value": description
                })
            
            if assigned_to:
                fields.append({
                    "op": "replace",
                    "path": "/fields/System.AssignedTo",
                    "value": assigned_to
                })
            
            if start_date:
                fields.append({
                    "op": "replace",
                    "path": "/fields/Microsoft.VSTS.Scheduling.StartDate",
                    "value": start_date.isoformat()
                })
            
            if target_date:
                fields.append({
                    "op": "replace",
                    "path": "/fields/Microsoft.VSTS.Scheduling.TargetDate",
                    "value": target_date.isoformat()
                })
            
            if custom_fields:
                for field_name, field_value in custom_fields.items():
                    fields.append({
                        "op": "replace",
                        "path": f"/fields/{field_name}",
                        "value": field_value
                    })
            
            # Atualiza parent se fornecido
            if parent_id is not None:
                # Primeiro, obtém o Work Item atual para verificar relações existentes
                current_item = self.get_work_item_by_id(work_item_id)
                if current_item:
                    # Remove relação de parent antiga se existir
                    if current_item.relations:
                        for idx, rel in enumerate(current_item.relations):
                            if rel.get("rel") == "System.LinkTypes.Hierarchy-Reverse":
                                fields.append({
                                    "op": "remove",
                                    "path": f"/relations/{idx}"
                                })
                                break  # Remove apenas a primeira relação de parent encontrada
                    
                    # Adiciona nova relação de parent
                    fields.append({
                        "op": "add",
                        "path": "/relations/-",
                        "value": {
                            "rel": "System.LinkTypes.Hierarchy-Reverse",
                            "url": f"{self.base_url}/{self.project}/_apis/wit/workitems/{parent_id}"
                        }
                    })
            
            if not fields:
                # Nada para atualizar
                return self.get_work_item_by_id(work_item_id)
            
            # PATCH para atualização
            endpoint = f'wit/workitems/{work_item_id}'
            
            response = self._make_request(
                'PATCH',
                endpoint,
                json=fields,
                headers={'Content-Type': 'application/json-patch+json'}
            )
            
            item = self._safe_json_parse(response)
            return WorkItemResponse(
                id=item['id'],
                rev=item['rev'],
                fields=item.get('fields', {}),
                relations=item.get('relations', None),
                url=item.get('url', '')
            )
        except Exception as e:
            print(f"Erro ao atualizar Work Item {work_item_id}: {e}")
            raise
    
    def get_project_work_items(self, project_id: Optional[str] = None) -> List[WorkItemResponse]:
        """Lista todos os Work Items de um projeto"""
        try:
            wiql_query = {
                "query": "SELECT [System.Id], [System.Title], [System.WorkItemType] FROM WorkItems ORDER BY [System.Id]"
            }
            
            response = self._make_request(
                'POST',
                'wit/wiql',
                json=wiql_query
            )
            
            data = self._safe_json_parse(response)
            work_items = data.get('workItems', [])
            
            if not work_items:
                return []
            
            ids = [str(wi['id']) for wi in work_items]
            return self.get_work_items_by_ids(ids)
        except Exception as e:
            print(f"Erro ao listar Work Items do projeto: {e}")
            return []
    
    def get_custom_fields(self) -> Dict[str, Any]:
        """Obtém campos customizados disponíveis"""
        try:
            response = self._make_request(
                'GET',
                'wit/fields',
                params={'$expand': 'all'}
            )
            
            data = self._safe_json_parse(response)
            custom_fields = {}
            
            if 'value' in data:
                for field in data['value']:
                    if field.get('custom', False):
                        custom_fields[field['referenceName']] = {
                            'name': field.get('name', ''),
                            'type': field.get('type', ''),
                            'description': field.get('description', '')
                        }
            
            return custom_fields
        except Exception as e:
            print(f"Erro ao obter campos customizados: {e}")
            return {}

