"""
Serviço de mapeamento MPP para Azure DevOps - Versão Refatorada (Clean Code)

Este serviço converte dados parseados de arquivos .mpp em Work Items no Azure DevOps,
seguindo princípios de clean code:
- Métodos pequenos e focados
- Nomes descritivos
- Validações e double check antes de criar itens
- Registro detalhado de todas as operações
"""
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime

from app.models.mpp_models import ParsedMPPData, MPPTask
from app.models.devops_models import WorkItemCreate, ConversionResult, WorkItemResponse
from app.services.devops_client import AzureDevOpsClient
from app.services.sync_logger import SyncLogger
from app.utils.resource_mapper import get_email_by_resource_name
from app.utils.validators import sanitize_title


class MapperService:
    """
    Serviço para mapear dados MPP para Azure DevOps.
    
    Responsabilidades:
    - Converter User Stories e Tasks do arquivo .mpp em Work Items no Azure DevOps
    - Validar e verificar duplicatas antes de criar
    - Vincular Tasks às User Stories corretas
    - Registrar todas as operações para auditoria
    """
    
    def __init__(self, devops_client: Optional[AzureDevOpsClient] = None):
        """
        Inicializa o serviço de mapeamento.
        
        Args:
            devops_client: Cliente do Azure DevOps (opcional, cria novo se não fornecido)
        """
        self.devops_client = devops_client or AzureDevOpsClient()
        self.sync_logger = SyncLogger()
    
    def convert_to_devops(
        self, 
        parsed_data: ParsedMPPData,
        area_path: Optional[str] = None,
        iteration_path: Optional[str] = None,
        skip_duplicates: bool = True,
        parent_feature_id: Optional[int] = None,
        update_existing: bool = False,
        closed_tasks_collector: Optional[List[Dict[str, Any]]] = None,
    ) -> ConversionResult:
        """
        Converte dados parseados do MPP para Work Items no Azure DevOps.
        
        Este método é o ponto de entrada principal e orquestra todo o processo:
        1. Valida e prepara os dados
        2. Processa User Stories
        3. Processa Tasks
        4. Gera registro de alterações
        
        Args:
            parsed_data: Dados parseados do arquivo .mpp
            area_path: Area Path do projeto (opcional, será determinado automaticamente se não fornecido)
            iteration_path: Iteration Path do projeto (opcional, será determinado automaticamente se não fornecido)
            skip_duplicates: Se True, pula itens duplicados (padrão: True)
            parent_feature_id: ID da Feature pai para vincular User Stories (opcional)
            update_existing: Se True, atualiza itens existentes ao invés de apenas pular (padrão: False)
            
        Returns:
            ConversionResult com estatísticas da conversão e registro detalhado
        """
        # Inicia registro de sincronização
        sync_id = self.sync_logger.start_sync(
            feature_id=parent_feature_id,
            project_name=parsed_data.project.name,
            file_name=parsed_data.project.file_name or "unknown.mpp",
            total_user_stories=len(parsed_data.user_stories),
            total_tasks=len(parsed_data.tasks)
        )
        
        # Prepara resultado
        result = ConversionResult(
            project_name=parsed_data.project.name,
            work_items=[]
        )
        
        # Determina parent_feature_id se não fornecido
        parent_feature_id = self._resolve_parent_feature_id(parsed_data, parent_feature_id)
        
        # Log informativo sobre a Feature (não bloqueia processamento)
        import logging
        logger = logging.getLogger(__name__)
        
        if parent_feature_id:
            logger.info(f"🔍 Processando com Feature {parent_feature_id}")
            logger.info(f"   Projeto: {self.devops_client.project}")
            logger.info(f"   Org: {self.devops_client.org}")
            # Tenta validar mas não bloqueia se falhar (pode ser problema de permissão/cache)
            if self._validate_parent_exists(parent_feature_id):
                logger.info(f"✅ Feature {parent_feature_id} encontrada")
            else:
                logger.warning(f"⚠️  Feature {parent_feature_id} não encontrada na validação inicial (pode ser cache/permissão)")
                logger.warning(f"   Continuando processamento - itens serão buscados pelo nome exato dentro da Feature")
        else:
            logger.warning("⚠️  Nenhum parent_feature_id fornecido - User Stories e Tasks serão criadas sem parent")
        
        # Determina Area Path e Iteration Path
        area_path, iteration_path = self._resolve_paths(
            parsed_data, 
            parent_feature_id, 
            area_path, 
            iteration_path
        )
        
        # Mapeia itens criados: task_id -> work_item_id
        item_map: Dict[str, Optional[int]] = {}
        user_story_map: Dict[str, Optional[int]] = {}
        
        # Processa User Stories primeiro (elas serão parents das Tasks)
        self._process_user_stories(
            parsed_data=parsed_data,
            result=result,
            parent_feature_id=parent_feature_id,
            area_path=area_path,
            iteration_path=iteration_path,
            skip_duplicates=skip_duplicates,
            update_existing=update_existing,
            item_map=item_map,
            user_story_map=user_story_map
        )
        
        # Processa Tasks
        self._process_tasks(
            parsed_data=parsed_data,
            result=result,
            parent_feature_id=parent_feature_id,
            area_path=area_path,
            iteration_path=iteration_path,
            skip_duplicates=skip_duplicates,
            update_existing=update_existing,
            item_map=item_map,
            user_story_map=user_story_map,
            closed_tasks_collector=closed_tasks_collector,
        )
        
        # Finaliza registro e adiciona ao resultado
        sync_log = self.sync_logger.finish_sync()
        result.sync_log = sync_log
        
        return result
    
    def _resolve_parent_feature_id(
        self, 
        parsed_data: ParsedMPPData, 
        parent_feature_id: Optional[int]
    ) -> Optional[int]:
        """
        Resolve o parent_feature_id se não foi fornecido.
        
        Tenta obter do work_item_id do projeto parseado.
        
        Args:
            parsed_data: Dados parseados
            parent_feature_id: ID fornecido (pode ser None)
            
        Returns:
            parent_feature_id resolvido ou None
        """
        if parent_feature_id:
            return parent_feature_id
        
        if parsed_data.project.work_item_id:
            try:
                return int(parsed_data.project.work_item_id)
            except (ValueError, TypeError):
                pass
        
        return None
    
    def _resolve_paths(
        self,
        parsed_data: ParsedMPPData,
        parent_feature_id: Optional[int],
        area_path: Optional[str],
        iteration_path: Optional[str]
    ) -> Tuple[str, str]:
        """
        Resolve Area Path e Iteration Path se não foram fornecidos.
        
        Args:
            parsed_data: Dados parseados
            parent_feature_id: ID da Feature pai
            area_path: Area Path fornecido (pode ser None)
            iteration_path: Iteration Path fornecido (pode ser None)
            
        Returns:
            Tupla (area_path, iteration_path)
        """
        if not area_path:
            area_path = self._determine_area_path(parsed_data, parent_feature_id)
        if not iteration_path:
            iteration_path = self._determine_iteration_path(parsed_data, parent_feature_id)
        
        return area_path, iteration_path
    
    def _process_user_stories(
        self,
        parsed_data: ParsedMPPData,
        result: ConversionResult,
        parent_feature_id: Optional[int],
        area_path: str,
        iteration_path: str,
        skip_duplicates: bool,
        update_existing: bool,
        item_map: Dict[str, Optional[int]],
        user_story_map: Dict[str, Optional[int]]
    ):
        """
        Processa todas as User Stories do arquivo .mpp.
        
        Para cada User Story:
        1. Valida dados
        2. Verifica duplicatas (se skip_duplicates=True)
        3. Atualiza existente ou cria nova
        4. Registra operação
        
        Args:
            parsed_data: Dados parseados
            result: Resultado da conversão (será atualizado)
            parent_feature_id: ID da Feature pai
            area_path: Area Path
            iteration_path: Iteration Path
            skip_duplicates: Se True, verifica duplicatas
            update_existing: Se True, atualiza existentes
            item_map: Mapa de task_id -> work_item_id
            user_story_map: Mapa de task_id -> work_item_id (apenas User Stories)
        """
        for user_story in parsed_data.user_stories:
            title = sanitize_title(user_story.name)
            task_id = user_story.id or user_story.name
            
            # Validação: título não pode estar vazio
            if not title or not title.strip():
                error_msg = f"User Story com título vazio (ID: {task_id})"
                result.errors.append(error_msg)
                self.sync_logger.log_failed_user_story(
                    title=user_story.name,
                    error=error_msg,
                    parent_id=parent_feature_id,
                    mpp_task_id=task_id
                )
                continue
            
            # Verifica duplicata se necessário
            existing_id = None
            if skip_duplicates and parent_feature_id:
                existing_id = self._find_existing_user_story(
                    title=title,
                    parent_feature_id=parent_feature_id
                )
            
            # Processa User Story (cria ou atualiza)
            if existing_id:
                if update_existing:
                    self._update_user_story(
                        user_story=user_story,
                        title=title,
                        task_id=task_id,
                        existing_id=existing_id,
                        result=result,
                        item_map=item_map,
                        user_story_map=user_story_map
                    )
                else:
                    self._skip_user_story(
                        title=title,
                        task_id=task_id,
                        existing_id=existing_id,
                        result=result,
                        item_map=item_map,
                        user_story_map=user_story_map
                    )
            else:
                self._create_user_story(
                    user_story=user_story,
                    title=title,
                    task_id=task_id,
                    parent_feature_id=parent_feature_id,
                    area_path=area_path,
                    iteration_path=iteration_path,
                    result=result,
                    item_map=item_map,
                    user_story_map=user_story_map
                )
    
    def _process_tasks(
        self,
        parsed_data: ParsedMPPData,
        result: ConversionResult,
        parent_feature_id: Optional[int],
        area_path: str,
        iteration_path: str,
        skip_duplicates: bool,
        update_existing: bool,
        item_map: Dict[str, Optional[int]],
        user_story_map: Dict[str, Optional[int]],
        closed_tasks_collector: Optional[List[Dict[str, Any]]] = None,
    ):
        """
        Processa todas as Tasks do arquivo .mpp.
        
        Para cada Task:
        1. Valida dados
        2. Filtra tasks com status "Removed" (não serão processadas)
        3. Determina parent (User Story ou Feature)
        4. Verifica duplicatas (se skip_duplicates=True)
        5. Atualiza existente ou cria nova
        6. Registra operação
        
        Args:
            parsed_data: Dados parseados
            result: Resultado da conversão (será atualizado)
            parent_feature_id: ID da Feature pai
            area_path: Area Path
            iteration_path: Iteration Path
            skip_duplicates: Se True, verifica duplicatas
            update_existing: Se True, atualiza existentes
            item_map: Mapa de task_id -> work_item_id
            user_story_map: Mapa de task_id -> work_item_id (apenas User Stories)
        """
        # Ordena Tasks por level para garantir que parents sejam processados primeiro
        sorted_tasks = sorted(parsed_data.tasks, key=lambda t: (t.level or 0, t.id or ""))
        
        for task in sorted_tasks:
            # Filtra tasks com status "Removed" - não serão processadas
            if task.status:
                status_lower = task.status.strip().lower()
                if status_lower in ['removed', 'removida', 'removido']:
                    print(f"MapperService: Task '{task.name}' ignorada (status: {task.status})")
                    continue
            title = sanitize_title(task.name)
            task_id = task.id or task.name
            
            # Validação: título não pode estar vazio
            if not title or not title.strip():
                error_msg = f"Task com título vazio (ID: {task_id})"
                result.errors.append(error_msg)
                self.sync_logger.log_failed_task(
                    title=task.name,
                    error=error_msg,
                    parent_id=parent_feature_id,
                    mpp_task_id=task_id,
                    assigned_to=task.resource_name,
                    start_date=task.start_date,
                    target_date=task.finish_date,
                    original_estimate_hours=task.work_hours
                )
                continue
            
            # Determina parent (User Story ou Feature)
            parent_id = self._determine_task_parent(
                task=task,
                parsed_data=parsed_data,
                parent_feature_id=parent_feature_id,
                item_map=item_map,
                user_story_map=user_story_map
            )
            
            # Double check: valida que parent existe se foi especificado
            if parent_id and parent_id != parent_feature_id:
                if not self._validate_parent_exists(parent_id):
                    # Se parent não existe, vincula à Feature
                    parent_id = parent_feature_id
            
            # Verifica duplicata se necessário
            existing_id = None
            existing_parent_id = None
            if skip_duplicates and parent_feature_id:
                existing_id, existing_parent_id = self._find_existing_task(
                    title=title,
                    parent_id=parent_id,
                    parent_feature_id=parent_feature_id
                )
            
            # Processa Task (cria ou atualiza)
            if existing_id:
                # Verifica se precisa re-vincular a Task ao User Story correto
                needs_reparent = False
                if parent_id and existing_parent_id != parent_id:
                    # Task existe mas está vinculada ao parent errado
                    needs_reparent = True
                elif not parent_id and existing_parent_id and existing_parent_id != parent_feature_id:
                    # Task está vinculada a um User Story mas deveria estar na Feature
                    # (caso raro, mas pode acontecer)
                    needs_reparent = False  # Mantém vinculação se já está em User Story
                elif parent_id and not existing_parent_id:
                    # Task existe mas está solta (sem parent) e deveria estar em User Story
                    needs_reparent = True
                
                if update_existing:
                    self._update_task(
                        task=task,
                        title=title,
                        task_id=task_id,
                        existing_id=existing_id,
                        assigned_to=self._get_assigned_to(task),
                        result=result,
                        item_map=item_map,
                        correct_parent_id=parent_id if needs_reparent else None,
                        devops_state=self._map_status_to_devops_state(task.status),
                        start_date=task.start_date,
                        target_date=task.finish_date,
                        parent_feature_id=parent_feature_id,
                        closed_tasks_collector=closed_tasks_collector,
                    )
                else:
                    # Mesmo sem update_existing, re-vincula se necessário
                    if needs_reparent and parent_id:
                        try:
                            self.devops_client.update_work_item(
                                work_item_id=existing_id,
                                parent_id=parent_id
                            )
                            print(f"MapperService: Task {existing_id} re-vinculada ao User Story {parent_id}")
                        except Exception as e:
                            print(f"MapperService: Erro ao re-vincular Task {existing_id}: {e}")
                    
                    self._skip_task(
                        title=title,
                        task_id=task_id,
                        existing_id=existing_id,
                        result=result,
                        item_map=item_map,
                        task=task
                    )
            else:
                self._create_task(
                    task=task,
                    title=title,
                    task_id=task_id,
                    parent_id=parent_id or parent_feature_id,
                    area_path=area_path,
                    iteration_path=iteration_path,
                    assigned_to=self._get_assigned_to(task),
                    result=result,
                    item_map=item_map,
                    devops_state=self._map_status_to_devops_state(task.status)
                )
    
    # Métodos auxiliares para User Stories
    
    def _find_existing_user_story(
        self,
        title: str,
        parent_feature_id: int
    ) -> Optional[int]:
        """
        Busca User Story existente na Feature.
        
        Args:
            title: Título da User Story
            parent_feature_id: ID da Feature pai
            
        Returns:
            ID da User Story existente ou None
        """
        try:
            title_escaped = title.replace("'", "''")
            wiql_query = {
                "query": (
                    f"SELECT [System.Id], [System.Title] FROM WorkItems "
                    f"WHERE [System.Parent] = {parent_feature_id} "
                    f"AND [System.WorkItemType] = 'User Story' "
                    f"AND [System.Title] = '{title_escaped}'"
                )
            }
            response = self.devops_client._make_request('POST', 'wit/wiql', json=wiql_query)
            data = response.json()
            existing_items = data.get('workItems', [])
            
            if existing_items:
                return existing_items[0]['id']
        except Exception as e:
            print(f"MapperService: Erro ao buscar User Story existente '{title}': {e}")
        
        return None
    
    def _create_user_story(
        self,
        user_story: MPPTask,
        title: str,
        task_id: str,
        parent_feature_id: Optional[int],
        area_path: str,
        iteration_path: str,
        result: ConversionResult,
        item_map: Dict[str, Optional[int]],
        user_story_map: Dict[str, Optional[int]]
    ):
        """
        Cria uma nova User Story no Azure DevOps.
        
        Args:
            user_story: Dados da User Story do MPP
            title: Título sanitizado
            task_id: ID da tarefa no MPP
            parent_feature_id: ID da Feature pai
            area_path: Area Path
            iteration_path: Iteration Path
            result: Resultado da conversão (será atualizado)
            item_map: Mapa de task_id -> work_item_id
            user_story_map: Mapa de task_id -> work_item_id (apenas User Stories)
        """
        # Não valida Feature aqui - deixa o Azure DevOps retornar erro real se não existir
        # A busca por título exato já funciona mesmo se a validação falhar
        
        work_item = WorkItemCreate(
            title=title,
            work_item_type="User Story",
            area_path=area_path,
            iteration_path=iteration_path,
            start_date=user_story.start_date,
            target_date=user_story.finish_date,
            description=user_story.notes,
            parent_id=parent_feature_id
        )
        
        try:
            created = self.devops_client.create_work_item(work_item)
            if created:
                result.created_user_stories += 1
                result.work_items.append(created)
                item_map[task_id] = created.id
                user_story_map[task_id] = created.id
                
                self.sync_logger.log_created_user_story(
                    title=title,
                    work_item_id=created.id,
                    parent_id=parent_feature_id,
                    mpp_task_id=task_id
                )
        except Exception as e:
            error_msg = f"Erro ao criar User Story '{title}': {str(e)}"
            result.errors.append(error_msg)
            self.sync_logger.log_failed_user_story(
                title=title,
                error=error_msg,
                parent_id=parent_feature_id,
                mpp_task_id=task_id
            )
    
    def _update_user_story(
        self,
        user_story: MPPTask,
        title: str,
        task_id: str,
        existing_id: int,
        result: ConversionResult,
        item_map: Dict[str, Optional[int]],
        user_story_map: Dict[str, Optional[int]]
    ):
        """
        Atualiza uma User Story existente no Azure DevOps.
        
        Args:
            user_story: Dados da User Story do MPP
            title: Título sanitizado
            task_id: ID da tarefa no MPP
            existing_id: ID da User Story existente
            result: Resultado da conversão (será atualizado)
            item_map: Mapa de task_id -> work_item_id
            user_story_map: Mapa de task_id -> work_item_id (apenas User Stories)
        """
        try:
            updated = self.devops_client.update_work_item(
                work_item_id=existing_id,
                title=title,
                description=user_story.notes,
                start_date=user_story.start_date,
                target_date=user_story.finish_date
            )
            if updated:
                result.updated_user_stories += 1
                result.work_items.append(updated)
                item_map[task_id] = existing_id
                user_story_map[task_id] = existing_id
                
                parent_id = updated.fields.get('System.Parent')
                if isinstance(parent_id, dict):
                    parent_id = parent_id.get('id')
                
                self.sync_logger.log_updated_user_story(
                    title=title,
                    work_item_id=existing_id,
                    parent_id=parent_id,
                    mpp_task_id=task_id
                )
        except Exception as e:
            error_msg = f"Erro ao atualizar User Story '{title}': {str(e)}"
            result.errors.append(error_msg)
            self.sync_logger.log_failed_user_story(
                title=title,
                error=error_msg,
                parent_id=None,
                mpp_task_id=task_id
            )
    
    def _skip_user_story(
        self,
        title: str,
        task_id: str,
        existing_id: int,
        result: ConversionResult,
        item_map: Dict[str, Optional[int]],
        user_story_map: Dict[str, Optional[int]]
    ):
        """
        Pula uma User Story duplicada (não atualiza).
        
        Args:
            title: Título da User Story
            task_id: ID da tarefa no MPP
            existing_id: ID da User Story existente
            result: Resultado da conversão (será atualizado)
            item_map: Mapa de task_id -> work_item_id
            user_story_map: Mapa de task_id -> work_item_id (apenas User Stories)
        """
        result.skipped_user_stories += 1
        item_map[task_id] = existing_id
        user_story_map[task_id] = existing_id
        
        # Busca parent da User Story existente
        try:
            existing_us = self.devops_client.get_work_item_by_id(existing_id)
            parent_id = None
            if existing_us:
                parent_id = existing_us.fields.get('System.Parent')
                if isinstance(parent_id, dict):
                    parent_id = parent_id.get('id')
        except:
            parent_id = None
        
        self.sync_logger.log_skipped_user_story(
            title=title,
            work_item_id=existing_id,
            parent_id=parent_id,
            mpp_task_id=task_id
        )
    
    # Métodos auxiliares para Tasks
    
    def _determine_task_parent(
        self,
        task: MPPTask,
        parsed_data: ParsedMPPData,
        parent_feature_id: Optional[int],
        item_map: Dict[str, Optional[int]],
        user_story_map: Dict[str, Optional[int]]
    ) -> Optional[int]:
        """
        Determina o parent correto para uma Task baseado na hierarquia do MPP.
        
        Estratégias (em ordem de prioridade):
        1. Se parent_id aponta diretamente para uma User Story → usa essa User Story
        2. Se parent_id aponta para outra Task → sobe na hierarquia até encontrar User Story
        3. Se parent_id não está no mapa mas existe no MPP → busca User Story pai na hierarquia
        4. User Story baseada em level hierárquico mais próximo
        5. User Story existente no DevOps (se não há User Stories no arquivo)
        6. Última User Story criada do arquivo (fallback)
        
        Args:
            task: Task do MPP
            parsed_data: Dados parseados completos
            parent_feature_id: ID da Feature pai
            item_map: Mapa de task_id -> work_item_id
            user_story_map: Mapa de task_id -> work_item_id (apenas User Stories)
            
        Returns:
            ID do parent (User Story ou Feature) ou None
        """
        # Estratégia 1: Se parent_id aponta diretamente para uma User Story
        if task.parent_id:
            # Verifica se parent_id é uma User Story
            if task.parent_id in user_story_map:
                return user_story_map[task.parent_id]
            
            # Se parent_id não é User Story, busca no MPP e sobe na hierarquia
            parent_task = self._find_task_by_id(parsed_data, task.parent_id)
            if parent_task:
                # Recursivamente busca a User Story pai subindo na hierarquia
                parent_us_id = self._find_parent_user_story(
                    parent_task, parsed_data, item_map, user_story_map
                )
                if parent_us_id:
                    return parent_us_id
        
        # Estratégia 2: User Story baseada em level hierárquico mais próximo
        task_level = task.level or 0
        best_match = None
        best_level_diff = float('inf')
        
        for us in parsed_data.user_stories:
            us_level = us.level or 0
            us_id = us.id or us.name
            
            # Task deve estar em nível maior que User Story
            if task_level > us_level and us_id in user_story_map:
                level_diff = task_level - us_level
                # Prefere User Story mais próxima (menor diferença de nível)
                if level_diff < best_level_diff:
                    best_level_diff = level_diff
                    best_match = us_id
        
        if best_match:
            return user_story_map[best_match]
        
        # Estratégia 3: User Story existente no DevOps (se não há User Stories no arquivo)
        if not parsed_data.user_stories and parent_feature_id:
            try:
                from app.services.workitem_analyzer import WorkItemAnalyzer
                analyzer = WorkItemAnalyzer(self.devops_client)
                analysis = analyzer.analyze_work_item(parent_feature_id)
                devops_user_stories = analysis.get('user_stories', [])
                
                if devops_user_stories:
                    return devops_user_stories[0].get('id')
            except Exception:
                pass
        
        # Estratégia 4: Última User Story criada (fallback)
        if parsed_data.user_stories:
            for us in reversed(parsed_data.user_stories):
                us_id = us.id or us.name
                if us_id in user_story_map:
                    return user_story_map[us_id]
        
        return None
    
    def _find_task_by_id(self, parsed_data: ParsedMPPData, task_id: str) -> Optional[MPPTask]:
        """
        Encontra uma Task ou User Story no MPP pelo ID.
        
        Args:
            parsed_data: Dados parseados
            task_id: ID da tarefa no MPP
            
        Returns:
            MPPTask encontrada ou None
        """
        # Busca em User Stories primeiro
        for us in parsed_data.user_stories:
            us_id = us.id or us.name
            if us_id == task_id:
                return us
        
        # Busca em Tasks
        for t in parsed_data.tasks:
            t_id = t.id or t.name
            if t_id == task_id:
                return t
        
        return None
    
    def _find_parent_user_story(
        self,
        task: MPPTask,
        parsed_data: ParsedMPPData,
        item_map: Dict[str, Optional[int]],
        user_story_map: Dict[str, Optional[int]]
    ) -> Optional[int]:
        """
        Sobe na hierarquia até encontrar a User Story pai.
        
        Args:
            task: Task do MPP
            parsed_data: Dados parseados
            item_map: Mapa de task_id -> work_item_id
            user_story_map: Mapa de task_id -> work_item_id (apenas User Stories)
            
        Returns:
            ID da User Story pai ou None
        """
        # Se esta task é uma User Story, retorna seu ID
        task_id = task.id or task.name
        if task_id in user_story_map:
            return user_story_map[task_id]
        
        # Se tem parent, sobe na hierarquia
        if task.parent_id:
            parent_task = self._find_task_by_id(parsed_data, task.parent_id)
            if parent_task:
                return self._find_parent_user_story(
                    parent_task, parsed_data, item_map, user_story_map
                )
        
        return None
    
    def _find_existing_task(
        self,
        title: str,
        parent_id: Optional[int],
        parent_feature_id: int
    ) -> Tuple[Optional[int], Optional[int]]:
        """
        Busca Task existente e retorna seu ID e parent atual.
        
        Busca primeiro no parent específico (User Story), depois na Feature e em todas as User Stories.
        
        Args:
            title: Título da Task
            parent_id: ID do parent desejado (User Story ou None)
            parent_feature_id: ID da Feature
            
        Returns:
            Tupla (task_id, current_parent_id) ou (None, None) se não encontrada
        """
        try:
            title_escaped = title.replace("'", "''")
            
            # Busca primeiro no parent específico
            if parent_id:
                wiql_query = {
                    "query": (
                        f"SELECT [System.Id] FROM WorkItems "
                        f"WHERE [System.Parent] = {parent_id} "
                        f"AND [System.WorkItemType] = 'Task' "
                        f"AND [System.Title] = '{title_escaped}'"
                    )
                }
                response = self.devops_client._make_request('POST', 'wit/wiql', json=wiql_query)
                data = response.json()
                existing_items = data.get('workItems', [])
                if existing_items:
                    task_id = existing_items[0]['id']
                    return (task_id, parent_id)
            
            # Busca em todas as User Stories da Feature primeiro (preferência)
            us_query = {
                "query": (
                    f"SELECT [System.Id] FROM WorkItems "
                    f"WHERE [System.Parent] = {parent_feature_id} "
                    f"AND [System.WorkItemType] = 'User Story'"
                )
            }
            us_response = self.devops_client._make_request('POST', 'wit/wiql', json=us_query)
            us_data = us_response.json()
            us_ids = [item['id'] for item in us_data.get('workItems', [])]
            
            for us_id in us_ids:
                task_query = {
                    "query": (
                        f"SELECT [System.Id] FROM WorkItems "
                        f"WHERE [System.Parent] = {us_id} "
                        f"AND [System.WorkItemType] = 'Task' "
                        f"AND [System.Title] = '{title_escaped}'"
                    )
                }
                task_response = self.devops_client._make_request('POST', 'wit/wiql', json=task_query)
                task_data = task_response.json()
                existing_items = task_data.get('workItems', [])
                if existing_items:
                    task_id = existing_items[0]['id']
                    return (task_id, us_id)
            
            # Busca na Feature (Tasks soltas)
            wiql_query = {
                "query": (
                    f"SELECT [System.Id] FROM WorkItems "
                    f"WHERE [System.Parent] = {parent_feature_id} "
                    f"AND [System.WorkItemType] = 'Task' "
                    f"AND [System.Title] = '{title_escaped}'"
                )
            }
            response = self.devops_client._make_request('POST', 'wit/wiql', json=wiql_query)
            data = response.json()
            existing_items = data.get('workItems', [])
            if existing_items:
                task_id = existing_items[0]['id']
                # Obtém o parent atual da Task
                task_item = self.devops_client.get_work_item_by_id(task_id)
                current_parent = None
                if task_item:
                    current_parent = task_item.fields.get('System.Parent')
                    if isinstance(current_parent, dict):
                        current_parent = current_parent.get('id')
                    elif isinstance(current_parent, int):
                        current_parent = current_parent
                return (task_id, current_parent)
        except Exception as e:
            print(f"MapperService: Erro ao buscar Task existente '{title}': {e}")
        
        return (None, None)
    
    def _create_task(
        self,
        task: MPPTask,
        title: str,
        task_id: str,
        parent_id: Optional[int],
        area_path: str,
        iteration_path: str,
        assigned_to: Optional[str],
        result: ConversionResult,
        item_map: Dict[str, Optional[int]],
        devops_state: Optional[str] = None
    ):
        """
        Cria uma nova Task no Azure DevOps.
        
        Args:
            task: Dados da Task do MPP
            title: Título sanitizado
            task_id: ID da tarefa no MPP
            parent_id: ID do parent (User Story ou Feature)
            area_path: Area Path
            iteration_path: Iteration Path
            assigned_to: Email do responsável
            result: Resultado da conversão (será atualizado)
            item_map: Mapa de task_id -> work_item_id
            devops_state: State do Azure DevOps (mapeado do status do Project)
        """
        # Não valida parent aqui - deixa o Azure DevOps retornar erro real se não existir
        # A busca por título exato já funciona mesmo se a validação falhar
        
        # Prepara campos customizados
        custom_fields = self._prepare_custom_fields(task)
        
        # NÃO adiciona System.State em custom_fields - será enviado via endpoint separadamente se necessário
        # Para criação, o state padrão será usado (geralmente "New")
        # O state pode ser atualizado em uma segunda chamada se necessário
        
        work_item = WorkItemCreate(
            title=title,
            work_item_type="Task",
            assigned_to=assigned_to,
            area_path=area_path,
            iteration_path=iteration_path,
            start_date=task.start_date,
            target_date=task.finish_date,
            description=task.notes,
            parent_id=parent_id,
            custom_fields=custom_fields if custom_fields else None
        )
        
        try:
            created = self.devops_client.create_work_item(work_item)
            if created:
                result.created_tasks += 1
                result.work_items.append(created)
                item_map[task_id] = created.id
                self.sync_logger.log_created_task(
                    title=title,
                    work_item_id=created.id,
                    parent_id=parent_id,
                    mpp_task_id=task_id,
                    assigned_to=task.resource_name,
                    start_date=task.start_date,
                    target_date=task.finish_date,
                    original_estimate_hours=task.work_hours
                )
        except Exception as e:
            error_msg = f"Erro ao criar Task '{title}': {str(e)}"
            result.errors.append(error_msg)
            self.sync_logger.log_failed_task(
                title=title,
                error=error_msg,
                parent_id=parent_id,
                mpp_task_id=task_id,
                assigned_to=task.resource_name,
                start_date=task.start_date,
                target_date=task.finish_date,
                original_estimate_hours=task.work_hours
            )
    
    def _update_task(
        self,
        task: MPPTask,
        title: str,
        task_id: str,
        existing_id: int,
        assigned_to: Optional[str],
        result: ConversionResult,
        item_map: Dict[str, Optional[int]],
        correct_parent_id: Optional[int] = None,
        devops_state: Optional[str] = None,
        start_date: Optional[datetime] = None,
        target_date: Optional[datetime] = None,
        parent_feature_id: Optional[int] = None,
        closed_tasks_collector: Optional[List[Dict[str, Any]]] = None,
    ):
        """
        Atualiza uma Task existente no Azure DevOps.
        
        IMPORTANTE: Se a Task estiver com status "Closed", "Removed" ou "Resolved" no Azure DevOps, 
        o status NÃO será alterado, mesmo que o arquivo .mpp tenha outro status.
        Isso evita reabrir Tasks que já foram concluídas, removidas ou resolvidas.
        
        Args:
            task: Dados da Task do MPP
            title: Título sanitizado
            task_id: ID da tarefa no MPP
            existing_id: ID da Task existente
            assigned_to: Email do responsável
            correct_parent_id: ID do parent correto (se precisa re-vincular)
            devops_state: State do Azure DevOps (mapeado do status do Project)
            start_date: Data de início (opcional, sobrescreve task.start_date)
            target_date: Data de término (opcional, sobrescreve task.finish_date)
            result: Resultado da conversão (será atualizado)
            item_map: Mapa de task_id -> work_item_id
        """
        try:
            # Verifica o estado atual da Task no Azure DevOps
            current_task = self.devops_client.get_work_item_by_id(existing_id, use_cache=False)
            current_state = None
            if current_task and current_task.fields:
                current_state = current_task.fields.get('System.State', '')
            
            # REGRA CRÍTICA: Se a Task está "Closed", "Removed" ou "Resolved" no Azure DevOps, 
            # NÃO altera o status mesmo que o arquivo .mpp tenha outro status.
            # Isso evita reabrir Tasks que já foram concluídas, removidas ou resolvidas.
            should_update_state = True
            protected_states = ['closed', 'removed', 'resolved']
            
            if current_state:
                current_state_lower = current_state.lower()
                if current_state_lower in protected_states:
                    if devops_state and devops_state.lower() not in protected_states:
                        print(f"MapperService: Task '{title}' (ID: {existing_id}) está '{current_state}' no Azure DevOps. "
                              f"Status do MPP ('{task.status}' -> '{devops_state}') será ignorado para evitar alterar o status protegido.")
                        should_update_state = False
                        # Registra para notificação Teams (PMO): Task fechada no DevOps mas não no MPP
                        if closed_tasks_collector is not None and parent_feature_id is not None:
                            closed_tasks_collector.append({
                                "feature_id": parent_feature_id,
                                "task_id": existing_id,
                                "title": title,
                                "mpp_status": task.status or "",
                                "devops_state": current_state,
                            })
                    elif devops_state and devops_state.lower() == current_state_lower:
                        # Se ambos têm o mesmo status protegido, pode atualizar (mantém o status)
                        should_update_state = True
                    else:
                        # Se não há devops_state do MPP ou é diferente, não atualiza
                        should_update_state = False
            
            custom_fields = self._prepare_custom_fields(task)
            
            # NÃO adiciona System.State em custom_fields - será enviado separadamente via parâmetro state
            # O campo System.State não deve estar em custom_fields porque é um campo padrão
            
            # Usa start_date/target_date fornecidos ou os da task
            update_start_date = start_date if start_date is not None else task.start_date
            update_target_date = target_date if target_date is not None else task.finish_date
            
            # Prepara parâmetros - só envia campos válidos
            update_params = {
                "work_item_id": existing_id,
                "title": title,
            }
            
            # Atualiza description apenas se não for None
            if task.notes is not None:
                update_params["description"] = task.notes
            
            # Atualiza assigned_to se fornecido
            # Se assigned_to for None e o recurso for "Cliente", envia string vazia para remover responsável
            if assigned_to is not None:
                update_params["assigned_to"] = assigned_to
            elif task.resource_name:
                resource_lower = task.resource_name.lower().strip()
                if 'cliente' in resource_lower:
                    update_params["assigned_to"] = ""
            
            # Atualiza datas se fornecidas
            if update_start_date:
                update_params["start_date"] = update_start_date
            if update_target_date:
                update_params["target_date"] = update_target_date
            
            # Atualiza custom_fields se houver
            if custom_fields:
                update_params["custom_fields"] = custom_fields
            
            # Atualiza parent_id apenas se fornecido (None = não atualizar parent)
            if correct_parent_id is not None:
                update_params["parent_id"] = correct_parent_id
            
            # Atualiza state apenas se permitido (não atualiza se Task está Closed e MPP tem outro status)
            if devops_state and should_update_state:
                update_params["state"] = devops_state
            
            updated = self.devops_client.update_work_item(**update_params)
            if updated:
                result.updated_tasks += 1
                result.work_items.append(updated)
                item_map[task_id] = existing_id
                parent_id = updated.fields.get('System.Parent')
                if isinstance(parent_id, dict):
                    parent_id = parent_id.get('id')
                if correct_parent_id:
                    print(f"MapperService: Task '{title}' (ID: {existing_id}) re-vinculada ao parent {correct_parent_id}")
                self.sync_logger.log_updated_task(
                    title=title,
                    work_item_id=existing_id,
                    parent_id=parent_id,
                    mpp_task_id=task_id,
                    assigned_to=task.resource_name,
                    start_date=task.start_date,
                    target_date=task.finish_date,
                    original_estimate_hours=task.work_hours
                )
        except Exception as e:
            error_msg = f"Erro ao atualizar Task '{title}': {str(e)}"
            result.errors.append(error_msg)
            self.sync_logger.log_failed_task(
                title=title,
                error=error_msg,
                parent_id=None,
                mpp_task_id=task_id,
                assigned_to=task.resource_name,
                start_date=task.start_date,
                target_date=task.finish_date,
                original_estimate_hours=task.work_hours
            )
    
    def _skip_task(
        self,
        title: str,
        task_id: str,
        existing_id: int,
        result: ConversionResult,
        item_map: Dict[str, Optional[int]],
        task: Optional[MPPTask] = None
    ):
        """
        Pula uma Task duplicada (não atualiza).
        
        Args:
            title: Título da Task
            task_id: ID da tarefa no MPP
            existing_id: ID da Task existente
            result: Resultado da conversão (será atualizado)
            item_map: Mapa de task_id -> work_item_id
            task: Dados da Task do MPP (opcional, para preencher recurso/datas/estimativa no log)
        """
        result.skipped_tasks += 1
        item_map[task_id] = existing_id
        
        # Busca parent da Task existente
        try:
            existing_task = self.devops_client.get_work_item_by_id(existing_id)
            parent_id = None
            if existing_task:
                parent_id = existing_task.fields.get('System.Parent')
                if isinstance(parent_id, dict):
                    parent_id = parent_id.get('id')
        except:
            parent_id = None
        
        self.sync_logger.log_skipped_task(
            title=title,
            work_item_id=existing_id,
            parent_id=parent_id,
            mpp_task_id=task_id,
            assigned_to=task.resource_name if task else None,
            start_date=task.start_date if task else None,
            target_date=task.finish_date if task else None,
            original_estimate_hours=task.work_hours if task else None
        )
    
    # Métodos auxiliares gerais
    
    def _get_assigned_to(self, task: MPPTask) -> Optional[str]:
        """
        Obtém email do responsável pela Task.
        
        REGRA ESPECIAL: Se o nome do recurso contém "Cliente" (ex: "Cliente", "Cliente [1]", "Cliente [2]"),
        retorna None para deixar o responsável em branco ("No one selected").
        
        Args:
            task: Task do MPP
            
        Returns:
            Email do responsável ou None (se for Cliente ou não houver recurso)
        """
        if task.resource_name:
            # Verifica se o recurso contém "Cliente" (case-insensitive)
            resource_lower = task.resource_name.lower().strip()
            if 'cliente' in resource_lower:
                print(f"MapperService: Recurso '{task.resource_name}' contém 'Cliente'. Deixando responsável em branco.")
                return None
            return get_email_by_resource_name(task.resource_name)
        return None
    
    def _map_status_to_devops_state(self, status: Optional[str]) -> Optional[str]:
        """
        Mapeia status do Microsoft Project para State do Azure DevOps.
        
        Regras de mapeamento:
        - Project "Concluída" -> Azure "Closed" (baseado nas opções disponíveis no DevOps)
        - Project "Tarefa futura" -> Azure "New"
        - Project "No Prazo" ou "Atrasada" -> Azure "Active"
        - Status "Removed" -> None (não será processado)
        
        Args:
            status: Status da tarefa no Microsoft Project
            
        Returns:
            State do Azure DevOps ou None se status for "Removed" ou desconhecido
        """
        if not status:
            return None
        
        status_lower = status.strip().lower()
        
        # Status "Removed" não será processado
        if status_lower in ['removed', 'removida', 'removido']:
            return None
        
        # Mapeamento conforme regras (baseado nas opções do Azure DevOps: New, Active, Closed, Removed)
        if status_lower in ['concluída', 'concluida', 'concluído', 'concluido', 'completed', 'finished', 'conclu']:
            return "Closed"  # Usa "Closed" que é a opção disponível no DevOps (equivalente a Resolved)
        elif status_lower in ['tarefa futura', 'futura', 'future', 'not started', 'tarefa futura']:
            return "New"
        elif status_lower in ['no prazo', 'no-prazo', 'em andamento', 'in progress', 'active', 'atrasada', 'atrasado', 'late', 'on time', 'no prazo']:
            return "Active"
        
        # Se não encontrou mapeamento específico, retorna None (não atualiza state)
        print(f"MapperService: Status '{status}' não mapeado, usando None")
        return None
    
    def _prepare_custom_fields(self, task: MPPTask) -> Dict[str, Any]:
        """
        Prepara campos customizados para criação/atualização de Task.
        
        Args:
            task: Task do MPP
            
        Returns:
            Dicionário com campos customizados
        """
        custom_fields = {}
        
        # NOTA: O campo CompletedWork (Horas Consumidas) NÃO deve ser preenchido pelo script.
        # Este campo é gerenciado manualmente no Azure DevOps.
        
        if task.priority is not None:
            custom_fields['Microsoft.VSTS.Common.Priority'] = task.priority
        
        # Campo "Trabalho" (work) convertido para horas
        # Tenta usar Custom.Original Estimate, se não existir usa Microsoft.VSTS.Scheduling.OriginalEstimate
        # Apenas para Tasks (não User Stories)
        if not task.is_user_story and task.work_hours is not None and task.work_hours > 0:
            # Tenta campo customizado primeiro, se falhar usa campo padrão
            # Nota: Se Custom.Original Estimate não existir no projeto, será usado OriginalEstimate padrão
            custom_fields['Microsoft.VSTS.Scheduling.OriginalEstimate'] = float(task.work_hours)
        
        return custom_fields
    
    def _validate_parent_exists(self, parent_id: int) -> bool:
        """
        Valida que um Work Item parent existe no Azure DevOps.
        
        IMPORTANTE: A Feature sempre deve existir. Este método apenas valida sua existência.
        Se a Feature não for encontrada, pode ser problema de permissão, projeto incorreto, ou cache.
        
        Args:
            parent_id: ID do Work Item parent (Feature)
            
        Returns:
            True se existe, False caso contrário
        """
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            # Tenta buscar sem cache primeiro para garantir que está buscando do servidor
            work_item = self.devops_client.get_work_item_by_id(parent_id, use_cache=False)
            if work_item is None:
                logger.error(f"❌ Feature {parent_id} não encontrada no Azure DevOps (retornou None)")
                logger.error(f"   Verifique se a Feature existe e se o projeto está correto: {self.devops_client.project}")
                return False
            
            # Verifica se é do tipo esperado (Feature, Epic, etc.)
            work_item_type = work_item.fields.get('System.WorkItemType', '')
            work_item_title = work_item.fields.get('System.Title', 'N/A')
            logger.info(f"✅ Feature {parent_id} encontrada: tipo={work_item_type}, título={work_item_title}")
            return True
        except Exception as e:
            logger.error(f"❌ Erro ao validar Feature {parent_id}: {type(e).__name__}: {str(e)}")
            logger.error(f"   Projeto configurado: {self.devops_client.project}")
            logger.error(f"   Org configurada: {self.devops_client.org}")
            import traceback
            logger.debug(f"Traceback completo: {traceback.format_exc()}")
            return False
    
    def _determine_area_path(
        self, 
        parsed_data: ParsedMPPData, 
        parent_feature_id: Optional[int] = None
    ) -> str:
        """
        Determina Area Path baseado no projeto ou Feature pai.
        
        Args:
            parsed_data: Dados parseados
            parent_feature_id: ID da Feature pai
            
        Returns:
            Area Path determinado
        """
        if parent_feature_id:
            try:
                work_item = self.devops_client.get_work_item_by_id(parent_feature_id)
                if work_item:
                    area_path = work_item.fields.get('System.AreaPath')
                    if area_path:
                        return area_path
            except Exception:
                pass
        
        if parsed_data.project.work_item_id:
            try:
                work_item = self.devops_client.get_work_item_by_id(
                    int(parsed_data.project.work_item_id)
                )
                if work_item:
                    area_path = work_item.fields.get('System.AreaPath')
                    if area_path:
                        return area_path
            except Exception:
                pass
        
        from app.config import settings
        return f"{settings.AZURE_DEVOPS_PROJECT}\\{parsed_data.project.name}"
    
    def _determine_iteration_path(
        self, 
        parsed_data: ParsedMPPData, 
        parent_feature_id: Optional[int] = None
    ) -> str:
        """
        Determina Iteration Path baseado no projeto ou Feature pai.
        
        Args:
            parsed_data: Dados parseados
            parent_feature_id: ID da Feature pai
            
        Returns:
            Iteration Path determinado
        """
        if parent_feature_id:
            try:
                work_item = self.devops_client.get_work_item_by_id(parent_feature_id)
                if work_item:
                    iteration_path = work_item.fields.get('System.IterationPath')
                    if iteration_path:
                        return iteration_path
            except Exception:
                pass
        
        if parsed_data.project.work_item_id:
            try:
                work_item = self.devops_client.get_work_item_by_id(
                    int(parsed_data.project.work_item_id)
                )
                if work_item:
                    iteration_path = work_item.fields.get('System.IterationPath')
                    if iteration_path:
                        return iteration_path
            except Exception:
                pass
        
        from app.config import settings
        return f"{settings.AZURE_DEVOPS_PROJECT}\\{parsed_data.project.name}"