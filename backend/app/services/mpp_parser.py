"""Parser de arquivos .mpp"""
import os
import json
import subprocess
import tempfile
from typing import List, Optional
from datetime import datetime
from pathlib import Path

try:
    # Tenta importar mpxj - pode precisar de instalação Java
    # Nota: mpxj requer Java instalado
    import mpxj
    MPXJ_PYTHON_AVAILABLE = True
except (ImportError, Exception):
    MPXJ_PYTHON_AVAILABLE = False

# Fallback: tentar ler como CSV se mpxj não estiver disponível
import csv

from app.models.mpp_models import MPPProject, MPPTask, ParsedMPPData
from app.utils.validators import validate_mpp_filename


class MPPParser:
    """Parser para arquivos .mpp com cache de parsing"""
    
    def __init__(self):
        # Permite inicialização mesmo sem mpxj (usará fallback CSV)
        self.java_available = self._check_java()
        self.mpxj_jar_path = self._find_mpxj_jar()
        from app.utils.cache import parsing_cache
        self.cache = parsing_cache
    
    def _check_java(self) -> bool:
        """Verifica se Java está disponível"""
        try:
            result = subprocess.run(['java', '-version'], 
                                 capture_output=True, 
                                 text=True,
                                 timeout=5)
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False
    
    def _find_mpxj_jar(self) -> Optional[str]:
        """Encontra o JAR do MPXJ"""
        backend_dir = Path(__file__).parent.parent.parent
        jar_path = backend_dir / 'lib' / 'mpxj.jar'
        
        if jar_path.exists():
            return str(jar_path)
        return None
    
    def _export_mpp_to_json_java(self, mpp_file: str) -> Optional[dict]:
        """Exporta arquivo .mpp para JSON usando MPXJ via Java CLI"""
        if not self.java_available:
            print("MPPParser: Java não está disponível")
            return None
        if not self.mpxj_jar_path:
            print("MPPParser: mpxj.jar não encontrado no diretório lib")
            return None
        print(f"MPPParser: Usando Java MPXJ - JAR: {self.mpxj_jar_path}")
        
        try:
            # Cria arquivo JSON temporário
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                json_file = f.name
            
            try:
                # Compila o script Java se necessário
                lib_dir = Path(self.mpxj_jar_path).parent
                java_script = lib_dir / 'MppToJson.java'
                class_file = lib_dir / 'MppToJson.class'
                
                # Compila se necessário
                if not class_file.exists() or java_script.exists():
                    if java_script.exists():
                        # Adiciona dependências do POI ao classpath de compilação
                        poi_jar = lib_dir / 'poi.jar'
                        poi_ooxml_jar = lib_dir / 'poi-ooxml.jar'
                        # Adiciona todos os JARs do diretório lib ao classpath de compilação
                        compile_cp = str(lib_dir)
                        if self.mpxj_jar_path:
                            compile_cp += f'{os.pathsep}{self.mpxj_jar_path}'
                        
                        # Adiciona todos os JARs do diretório lib
                        for jar_file in lib_dir.glob('*.jar'):
                            if jar_file.name != 'mpxj.jar':  # Já adicionado acima
                                compile_cp += f'{os.pathsep}{jar_file}'
                        
                        compile_cmd = [
                            'javac',
                            '-cp', compile_cp,
                            str(java_script)
                        ]
                        result = subprocess.run(compile_cmd, 
                                              capture_output=True, 
                                              text=True,
                                              cwd=str(lib_dir),
                                              timeout=30)
                        if result.returncode != 0:
                            print(f"Erro ao compilar MppToJson: {result.stderr}")
                            return None
                
                # Executa o script Java com todas as dependências
                # Adiciona todos os JARs do diretório lib ao classpath
                classpath = str(lib_dir)
                if self.mpxj_jar_path:
                    classpath += f'{os.pathsep}{self.mpxj_jar_path}'
                
                # Adiciona todos os JARs do diretório lib
                for jar_file in lib_dir.glob('*.jar'):
                    if jar_file.name != 'mpxj.jar':  # Já adicionado acima
                        classpath += f'{os.pathsep}{jar_file}'
                
                run_cmd = [
                    'java',
                    '-cp', classpath,
                    'MppToJson',
                    mpp_file,
                    json_file
                ]
                
                result = subprocess.run(run_cmd,
                                      capture_output=True,
                                      text=True,
                                      timeout=60)
                
                if result.returncode != 0:
                    print(f"MPPParser: Erro ao executar MppToJson (código {result.returncode})")
                    print(f"MPPParser: stderr: {result.stderr}")
                    print(f"MPPParser: stdout: {result.stdout}")
                    return None
                
                # Lê o JSON gerado
                with open(json_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
                    
            finally:
                # Limpa arquivo temporário
                try:
                    os.unlink(json_file)
                except:
                    pass
                    
        except Exception as e:
            print(f"Erro ao exportar .mpp para JSON via Java: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def parse_file(self, file_path: str, original_filename: Optional[str] = None, use_cache: bool = True) -> ParsedMPPData:
        """
        Parse um arquivo .mpp e retorna os dados estruturados (com cache).
        
        Args:
            file_path: Caminho para o arquivo .mpp
            original_filename: Nome original do arquivo (usado para extrair work_item_id)
                              Se não fornecido, usa o nome do arquivo no caminho
            use_cache: Se True, usa cache quando disponível
            
        Returns:
            ParsedMPPData com os dados parseados
        """
        # Verifica cache primeiro
        if use_cache:
            cached_data = self.cache.get_by_file(file_path)
            if cached_data is not None:
                print(f"MPPParser: Dados obtidos do cache para {file_path}")
                return cached_data
        
        # Usa o nome original se fornecido, senão usa o nome do arquivo no caminho
        # Isso é importante porque o arquivo salvo pode ter um UUID como nome
        filename = original_filename if original_filename else os.path.basename(file_path)
        work_item_id, project_name_from_file = validate_mpp_filename(filename)
        
        print(f"MPPParser: filename={filename}, work_item_id={work_item_id}, project_name_from_file={project_name_from_file}")
        
        # Tenta usar MPXJ via Java CLI primeiro (método mais confiável)
        json_data = self._export_mpp_to_json_java(file_path)
        
        parsed_data = None
        if json_data:
            print(f"MPPParser: Arquivo exportado para JSON via Java MPXJ")
            parsed_data = self._parse_from_json(json_data, filename, work_item_id, project_name_from_file)
            
            # Se obteve sucesso via Java MPXJ, retorna imediatamente
            if parsed_data and len(parsed_data.project.tasks) > 0:
                print(f"MPPParser: Sucesso via Java MPXJ - {len(parsed_data.project.tasks)} tarefas parseadas")
                # Armazena no cache
                if use_cache and parsed_data:
                    self.cache.set_by_file(file_path, parsed_data)
                return parsed_data
        
        # Se o método Java falhou, tenta CSV como fallback
        if not parsed_data:
            print("MPPParser: Java MPXJ falhou, tentando fallback CSV")
            parsed_data = self.parse_csv_fallback(file_path, original_filename=original_filename)
            if parsed_data:
                # Armazena no cache
                if use_cache:
                    self.cache.set_by_file(file_path, parsed_data)
                return parsed_data
            # Se CSV também falhou, retorna erro
            raise ValueError(f"Não foi possível extrair tarefas do arquivo {filename}. Verifique se o arquivo é um .mpp válido e se Java está instalado.")
        
        # Se chegou aqui, parsed_data foi criado com sucesso via Java MPXJ
        return parsed_data
    
    def _parse_from_json(self, json_data: dict, filename: str, work_item_id: Optional[str], project_name_from_file: Optional[str]) -> ParsedMPPData:
        """Parse dados de um JSON exportado pelo MPXJ"""
        # Extrai nome do projeto
        project_name = json_data.get('name') or json_data.get('title') or project_name_from_file or "Projeto Sem Nome"
        
        # Cria mapa de resources por unique_id
        resources_map = {}
        for resource in json_data.get('resources', []):
            unique_id = resource.get('unique_id')
            name = resource.get('name', '')
            if unique_id and name:
                resources_map[unique_id] = name
        
        # Cria mapa de assignments por task_unique_id
        assignments_by_task = {}
        for assignment in json_data.get('assignments', []):
            task_unique_id = assignment.get('task_unique_id')
            resource_unique_id = assignment.get('resource_unique_id')
            
            if task_unique_id and resource_unique_id:
                resource_name = resources_map.get(resource_unique_id)
                if resource_name:
                    if task_unique_id not in assignments_by_task:
                        assignments_by_task[task_unique_id] = []
                    assignments_by_task[task_unique_id].append(resource_name)
        
        # Extrai tarefas
        tasks = []
        tasks_data = json_data.get('tasks', [])
        
        # A primeira tarefa geralmente é o projeto (summary task de nível 0)
        first_task_processed = False
        
        for task_data in tasks_data:
            # Pula a primeira tarefa se for summary de nível 0 (projeto)
            is_first_task = not first_task_processed
            task_level = task_data.get('level', 0) or 0
            is_summary = task_data.get('summary', False) or False
            
            if is_first_task and is_summary and task_level == 0:
                first_task_processed = True
                print(f"MPPParser: Pulando primeira tarefa (projeto): {task_data.get('name', 'N/A')}")
                continue
            
            first_task_processed = True
            
            # Adiciona recursos dos assignments à tarefa
            task_unique_id = task_data.get('unique_id')
            if task_unique_id and task_unique_id in assignments_by_task:
                if 'resources' not in task_data:
                    task_data['resources'] = []
                for resource_name in assignments_by_task[task_unique_id]:
                    task_data['resources'].append({'name': resource_name})
                print(f"MPPParser: Tarefa '{task_data.get('name', 'N/A')[:50]}' tem recursos: {assignments_by_task[task_unique_id]}")
            
            task = self._parse_task_from_json(task_data)
            if task:
                tasks.append(task)
                # Debug: mostra resource_name extraído
                if task.resource_name:
                    print(f"MPPParser: Tarefa parseada '{task.name[:50]}' -> resource_name='{task.resource_name}' -> é Task")
                else:
                    print(f"MPPParser: Tarefa parseada '{task.name[:50]}' -> resource_name=None/vazio -> é User Story")
        
        print(f"MPPParser: {len(tasks)} tarefas extraídas do JSON (projeto excluído)")
        
        # Classifica em User Stories e Tasks
        # Inclui todas as tarefas (summary tasks também podem ser User Stories se não tiverem recurso)
        user_stories, classified_tasks = self._classify_tasks(tasks)
        
        print(f"MPPParser: Classificação - User Stories: {len(user_stories)}, Tasks: {len(classified_tasks)}")
        print(f"MPPParser: Total de tarefas para project.tasks: {len(tasks)}")
        
        # Cria modelo do projeto
        # IMPORTANTE: project.tasks deve conter TODAS as tarefas (não apenas classificadas)
        # Isso permite que a visualização mostre a estrutura completa do arquivo .mpp
        mpp_project = MPPProject(
            name=project_name,
            file_name=filename,
            work_item_id=work_item_id,
            tasks=tasks  # Inclui TODAS as tarefas (User Stories + Tasks + Summary), mantendo ordem original
        )
        
        parsed_data = ParsedMPPData(
            project=mpp_project,
            user_stories=user_stories,  # Apenas User Stories (para contagem)
            tasks=classified_tasks  # Apenas Tasks (para contagem)
        )
        
        print(f"MPPParser: parsed_data.project.tasks count: {len(parsed_data.project.tasks)}")
        print(f"MPPParser: parsed_data.user_stories count: {len(parsed_data.user_stories)}")
        print(f"MPPParser: parsed_data.tasks count: {len(parsed_data.tasks)}")
        
        return parsed_data
    
    def _parse_task_from_json(self, task_data: dict) -> Optional[MPPTask]:
        """Converte dados JSON de tarefa para MPPTask"""
        try:
            # Extrai campos básicos
            task_id = str(task_data.get('id', '')) if task_data.get('id') else None
            name = task_data.get('name', 'Sem nome')
            
            # Datas
            start_date = self._parse_json_date(task_data.get('start'))
            finish_date = self._parse_json_date(task_data.get('finish'))
            
            # Duração
            duration = task_data.get('duration', '')
            if isinstance(duration, dict):
                duration = duration.get('duration', '')
            
            # Percentual completo
            percent_complete = task_data.get('percentageComplete', 0) or 0
            
            # Recursos - pode estar em 'resources' ou 'assignments'
            resource_names = []
            
            # Tenta 'resources' primeiro
            resources = task_data.get('resources', [])
            if resources:
                for r in resources:
                    if isinstance(r, dict):
                        resource_name = r.get('name', '')
                        if resource_name and resource_name.strip():
                            resource_names.append(resource_name)
                    elif isinstance(r, str) and r.strip():
                        resource_names.append(r)
            
            # Se não encontrou, tenta 'assignments'
            if not resource_names:
                assignments = task_data.get('assignments', [])
                if assignments:
                    for a in assignments:
                        if isinstance(a, dict):
                            # Assignment pode ter 'resource' como objeto ou nome direto
                            resource = a.get('resource')
                            if resource:
                                if isinstance(resource, dict):
                                    resource_name = resource.get('name', '')
                                else:
                                    resource_name = str(resource)
                                if resource_name and resource_name.strip():
                                    resource_names.append(resource_name)
            
            # Junta todos os recursos em uma string
            resource_name = ', '.join(resource_names) if resource_names else None
            
            # Predecessoras
            predecessors = task_data.get('predecessors', [])
            pred_list = []
            for pred in predecessors:
                if isinstance(pred, dict):
                    pred_id = pred.get('id')
                    if pred_id:
                        pred_list.append(str(pred_id))
            predecessors_str = ', '.join(pred_list) if pred_list else None
            
            # Nível hierárquico
            level = task_data.get('level', 0) or 0
            summary = task_data.get('summary', False) or False
            
            # Parent
            parent = task_data.get('parent')
            parent_id = None
            if parent:
                if isinstance(parent, dict):
                    parent_id = str(parent.get('id')) if parent.get('id') else None
                else:
                    parent_id = str(parent)
            
            # Work
            work = task_data.get('work', '')
            work_hours = task_data.get('workHours', 0) or 0
            
            # Tipo e modo
            task_type = task_data.get('type', None)
            task_mode = 'Summary' if summary else task_data.get('taskMode', 'Fixed Duration')
            
            # Determina se é User Story ou Task baseado em "Nomes dos recursos"
            # REGRA: 
            # - Se "Nomes dos recursos" estiver vazio ou None → User Story
            # - Se "Nomes dos recursos" tiver valor → Task
            # Isso se aplica tanto para summary tasks quanto para tasks normais
            is_user_story = False
            # Se não tem resource_name ou está vazio, é User Story
            if resource_name is None or (isinstance(resource_name, str) and resource_name.strip() == ""):
                is_user_story = True
            else:
                is_user_story = False
            
            return MPPTask(
                id=task_id,
                name=name,
                resource_name=resource_name,
                start_date=start_date,
                finish_date=finish_date,
                duration=str(duration) if duration else None,
                percent_complete=percent_complete,
                priority=None,
                notes=None,
                is_user_story=is_user_story,
                parent_id=parent_id,
                level=level,
                summary=summary,
                work=str(work) if work else None,
                work_hours=work_hours,
                predecessors=predecessors_str,
                type=str(task_type) if task_type else None,
                task_mode=task_mode
            )
        except Exception as e:
            print(f"Erro ao parsear tarefa do JSON: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _parse_json_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """Converte string de data do JSON para datetime"""
        if not date_str:
            return None
        
        try:
            # Formato ISO comum: "2025-11-28T00:00:00" ou "2025-11-28T00:00:00.000"
            if 'T' in date_str:
                # Remove timezone se presente
                date_str = date_str.split('+')[0].split('Z')[0]
                # Tenta com e sem milissegundos
                for fmt in ['%Y-%m-%dT%H:%M:%S.%f', '%Y-%m-%dT%H:%M:%S']:
                    try:
                        return datetime.strptime(date_str, fmt)
                    except ValueError:
                        continue
            else:
                # Formato de data simples
                return datetime.strptime(date_str, '%Y-%m-%d')
        except Exception as e:
            print(f"Erro ao parsear data '{date_str}': {e}")
            return None
    
    def _extract_tasks(self, project_file) -> List[MPPTask]:
        """Extrai tarefas do arquivo de projeto"""
        tasks = []
        task_map = {}  # Para mapear IDs e hierarquia
        first_task = True  # Flag para identificar primeira tarefa (projeto)
        
        for task in project_file.tasks:
            # Inclui todas as tarefas, incluindo summary tasks
            # A primeira tarefa geralmente é o projeto (summary task de nível 0)
            
            # Extrai recursos (primeiro recurso atribuído)
            resource_name = None
            if task.resources:
                resource_name = task.resources[0].name if task.resources else None
            
            # Converte datas
            start_date = None
            finish_date = None
            if task.start:
                start_date = task.start
            if task.finish:
                finish_date = task.finish
            
            # Duração
            duration = None
            if task.duration:
                try:
                    # Tenta converter duração para dias
                    if hasattr(task.duration, 'days'):
                        days = task.duration.days
                        if days > 0:
                            duration = f"{days} dias"
                        else:
                            # Se não tem dias, tenta horas
                            if hasattr(task.duration, 'total_seconds'):
                                hours = task.duration.total_seconds() / 3600.0
                                if hours >= 1:
                                    duration = f"{int(hours)} hrs"
                                else:
                                    duration = str(task.duration)
                            else:
                                duration = str(task.duration)
                    else:
                        duration = str(task.duration)
                except Exception as e:
                    duration = str(task.duration)
                    print(f"Erro ao formatar duração: {e}")
            
            # Percentual completo
            percent_complete = None
            if task.percentage_complete is not None:
                percent_complete = float(task.percentage_complete)
            
            # Notas
            notes = None
            if task.notes:
                notes = task.notes
            
            # Prioridade
            priority = None
            if task.priority is not None:
                priority = int(task.priority)
            
            # Work (trabalho em horas)
            work = None
            work_hours = None
            if hasattr(task, 'work') and task.work:
                try:
                    # Tenta converter para horas
                    if hasattr(task.work, 'hours'):
                        work_hours = float(task.work.hours)
                        work = f"{work_hours:.1f} hrs"
                    elif hasattr(task.work, 'total_seconds'):
                        # Se for um timedelta, converte para horas
                        total_seconds = task.work.total_seconds()
                        work_hours = total_seconds / 3600.0
                        work = f"{work_hours:.1f} hrs"
                    else:
                        work = str(task.work)
                except Exception as e:
                    work = str(task.work)
                    print(f"Erro ao converter work para horas: {e}")
            
            # Predecessoras
            predecessors = None
            if hasattr(task, 'predecessors') and task.predecessors:
                pred_list = []
                for pred in task.predecessors:
                    try:
                        if hasattr(pred, 'id'):
                            pred_id = str(pred.id)
                            # Adiciona tipo de link se disponível (FS, SS, FF, SF)
                            link_type = ''
                            if hasattr(pred, 'type'):
                                link_type = str(pred.type)
                            elif hasattr(pred, 'link_type'):
                                link_type = str(pred.link_type)
                            
                            if link_type:
                                pred_list.append(f"{pred_id}{link_type}")
                            else:
                                pred_list.append(pred_id)
                    except Exception as e:
                        print(f"Erro ao processar predecessora: {e}")
                        continue
                if pred_list:
                    predecessors = ', '.join(pred_list)
            
            # Tipo de tarefa
            task_type = None
            if hasattr(task, 'type'):
                task_type = str(task.type)
            
            # Modo da tarefa
            task_mode = None
            if hasattr(task, 'task_mode'):
                task_mode = str(task.task_mode)
            elif task.summary:
                task_mode = 'Summary'
            else:
                task_mode = 'Fixed Duration'
            
            # Primeira tarefa geralmente é o projeto (summary de nível 0)
            is_project = first_task and (task.summary or self._calculate_level(task) == 0)
            
            # Determina se é User Story ou Task baseado em "Nomes dos recursos"
            # REGRA: 
            # - Se "Nomes dos recursos" estiver vazio ou None → User Story
            # - Se "Nomes dos recursos" tiver valor → Task
            # Isso se aplica tanto para summary tasks quanto para tasks normais
            # A primeira linha (projeto) nunca é User Story
            is_user_story = False
            if not is_project:
                if resource_name is None or (isinstance(resource_name, str) and resource_name.strip() == ""):
                    is_user_story = True
                else:
                    is_user_story = False
            
            mpp_task = MPPTask(
                id=str(task.id) if task.id else None,
                name=task.name or "Sem nome",
                resource_name=resource_name,
                start_date=start_date,
                finish_date=finish_date,
                duration=duration,
                percent_complete=percent_complete,
                priority=priority,
                notes=notes,
                is_user_story=is_user_story,
                parent_id=str(task.parent.id) if task.parent and task.parent.id else None,
                level=self._calculate_level(task),
                summary=task.summary if hasattr(task, 'summary') else False,
                work=work,
                work_hours=work_hours,
                predecessors=predecessors,
                type=task_type,
                task_mode=task_mode
            )
            
            tasks.append(mpp_task)
            task_map[str(task.id)] = mpp_task
            first_task = False
        
        return tasks
    
    def _calculate_level(self, task) -> int:
        """Calcula o nível hierárquico da tarefa"""
        level = 0
        current = task.parent
        while current:
            level += 1
            current = current.parent
        return level
    
    def _classify_tasks(self, tasks: List[MPPTask]) -> tuple[List[MPPTask], List[MPPTask]]:
        """
        Classifica tarefas em User Stories e Tasks.
        REGRA:
        - Primeira linha = ID e título do projeto (já foi excluída antes de chamar este método)
        - User Story: campo "Nomes dos recursos" (resource_name) está vazio ou None
        - Task: campo "Nomes dos recursos" (resource_name) tem algum valor
        - Isso se aplica tanto para summary tasks quanto para tasks normais
        
        A vinculação de Tasks às User Stories é feita baseada na hierarquia:
        1. Se a Task tem parent_id que aponta para uma User Story, usa esse parent_id
        2. Caso contrário, encontra a User Story mais próxima na hierarquia baseado no level
        """
        user_stories = []
        classified_tasks = []
        
        # Organiza por nível hierárquico e ID
        sorted_tasks = sorted(tasks, key=lambda t: (t.level or 0, t.id or ""))
        
        # Classifica cada tarefa em User Story ou Task
        # REGRA: User Story = resource_name vazio/None, Task = resource_name tem valor
        for task in sorted_tasks:
            resource_name = task.resource_name
            
            # Determina se é User Story ou Task baseado APENAS em resource_name
            # (ignora task.is_user_story que pode estar incorreto)
            is_user_story = (
                resource_name is None or 
                (isinstance(resource_name, str) and resource_name.strip() == "")
            )
            
            if is_user_story:
                user_stories.append(task)
            else:
                # Tem resource_name, então é Task
                classified_tasks.append(task)
        
        print(f"MPPParser._classify_tasks: Total tasks analisadas: {len(sorted_tasks)}")
        print(f"MPPParser._classify_tasks: User Stories encontradas: {len(user_stories)}")
        print(f"MPPParser._classify_tasks: Tasks encontradas: {len(classified_tasks)}")
        
        # Debug: mostra algumas tarefas para verificar classificação
        if len(sorted_tasks) > 0:
            print(f"MPPParser._classify_tasks: Exemplo de tarefas:")
            for i, task in enumerate(sorted_tasks[:5]):  # Primeiras 5 tarefas
                print(f"  Task {i+1}: name='{task.name[:50]}', resource_name='{task.resource_name}', is_user_story={task.is_user_story}")
        
        # Cria mapa de task_id -> User Story para busca rápida
        us_map: Dict[str, MPPTask] = {}
        for us in user_stories:
            us_id = us.id or us.name
            us_map[us_id] = us
        
        # Agora processa todas as tasks e vincula às User Stories corretas
        # Ordena por ID numérico para manter a ordem do arquivo
        def get_numeric_id(task_or_us):
            task_id = task_or_us.id
            if task_id:
                try:
                    return int(task_id)
                except (ValueError, TypeError):
                    return 0
            return 0
        
        # Ordena todas as tarefas (User Stories + Tasks) por ID
        all_tasks_sorted = sorted(tasks, key=get_numeric_id)
        
        # Cria mapa de User Stories por ID
        us_by_id = {}
        for us in user_stories:
            us_id = us.id or us.name
            us_by_id[us_id] = us
        
        # Processa Tasks na ordem do arquivo para vincular às User Stories corretas
        # IMPORTANTE: Não adiciona tasks novamente, apenas atualiza o parent_id das tasks já classificadas
        current_user_story = None
        
        # Cria um mapa de tasks por ID para atualização rápida
        tasks_by_id = {task.id: task for task in classified_tasks}
        
        for task_item in all_tasks_sorted:
            # Verifica se é User Story baseado em resource_name
            resource_name = task_item.resource_name
            is_user_story = (
                resource_name is None or 
                (isinstance(resource_name, str) and resource_name.strip() == "") or
                task_item.is_user_story
            )
            
            if is_user_story:
                # Atualiza User Story atual
                current_user_story = task_item
                continue
            
            # É uma Task - apenas atualiza o parent_id se a task já estiver em classified_tasks
            if task_item.id in tasks_by_id:
                task_to_update = tasks_by_id[task_item.id]
                
                # Estratégia 1: Verifica se o parent_id direto do JSON aponta para uma User Story
                if task_item.parent_id and task_item.parent_id in us_map:
                    # Parent é uma User Story - perfeito!
                    task_to_update.parent_id = task_item.parent_id
                elif current_user_story:
                    # Estratégia 2: Vincula à User Story atual (última User Story encontrada antes desta Task)
                    us_id = current_user_story.id or current_user_story.name
                    task_to_update.parent_id = us_id
                else:
                    # Estratégia 3: Encontra a User Story mais próxima por ID
                    task_id_num = get_numeric_id(task_item)
                    best_user_story: Optional[MPPTask] = None
                    best_id_diff = float('inf')
                    
                    for us in user_stories:
                        us_id_num = get_numeric_id(us)
                        # Task deve ter ID maior que User Story
                        if task_id_num > us_id_num:
                            id_diff = task_id_num - us_id_num
                            if id_diff < best_id_diff:
                                best_id_diff = id_diff
                                best_user_story = us
                    
                    if best_user_story:
                        # Vincula à User Story com ID mais próximo
                        us_id = best_user_story.id or best_user_story.name
                        task_to_update.parent_id = us_id
        
        print(f"MPPParser._classify_tasks: Após vinculação - User Stories: {len(user_stories)}, Tasks: {len(classified_tasks)}")
        
        return user_stories, classified_tasks
    
    def parse_csv_fallback(self, file_path: str, original_filename: Optional[str] = None) -> ParsedMPPData:
        """
        Fallback: parse de arquivo CSV exportado do MS Project.
        Usado quando mpxj não está disponível.
        """
        # Usa o nome original se fornecido, senão usa o nome do arquivo no caminho
        filename = original_filename if original_filename else os.path.basename(file_path)
        work_item_id, project_name_from_file = validate_mpp_filename(filename)
        
        tasks = []
        project_name = project_name_from_file or "Projeto Sem Nome"
        
        # Detecta se é arquivo binário .mpp ou CSV
        is_binary = False
        try:
            with open(file_path, 'rb') as f:
                first_bytes = f.read(1024)
                # Verifica se parece ser binário (não é texto válido)
                if len(first_bytes) > 0:
                    # Arquivos .mpp binários geralmente começam com bytes específicos
                    # Verifica se tem caracteres de controle não-texto
                    if b'\x00' in first_bytes[:100] or (first_bytes[0] if first_bytes else 0) > 127:
                        # Tenta decodificar como UTF-8 para confirmar
                        try:
                            decoded = first_bytes.decode('utf-8')
                            # Se conseguir mas tiver muitos caracteres não-imprimíveis, é binário
                            non_printable = sum(1 for c in decoded[:100] if ord(c) < 32 and c not in '\n\r\t')
                            if non_printable > 10:
                                is_binary = True
                        except UnicodeDecodeError:
                            # Se não conseguir UTF-8, pode ser outro encoding ou binário
                            # Verifica se tem muitos bytes não-ASCII consecutivos
                            non_ascii_count = sum(1 for b in first_bytes[:100] if b > 127)
                            if non_ascii_count > 50:
                                is_binary = True
        except Exception:
            is_binary = True
        
        if is_binary:
            raise Exception(
                "Arquivo .mpp binário detectado. Para usar este arquivo, você precisa:\n"
                "1. Instalar Java e Microsoft Visual C++ Build Tools para usar mpxj, OU\n"
                "2. Exportar o arquivo .mpp para CSV no Microsoft Project e fazer upload do CSV"
            )
        
        # Tenta diferentes encodings
        encodings = ['utf-8-sig', 'utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
        used_encoding = None
        
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    test_reader = csv.DictReader(f)
                    # Testa se consegue ler primeira linha
                    try:
                        next(test_reader)
                        used_encoding = encoding
                        break
                    except (StopIteration, Exception):
                        continue
            except (UnicodeDecodeError, UnicodeError):
                continue
        
        if used_encoding is None:
            raise Exception("Não foi possível ler o arquivo. Tente exportar para CSV no Microsoft Project.")
        
        with open(file_path, 'r', encoding=used_encoding) as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                task_name = row.get('Nome da Tarefa', row.get('Task Name', ''))
                resource_name = row.get('Nome do recurso', row.get('Resource Name', ''))
                
                if not task_name:
                    continue
                
                # Tenta parsear datas
                start_date = None
                finish_date = None
                if 'Data de Início' in row or 'Start Date' in row:
                    date_str = row.get('Data de Início', row.get('Start Date', ''))
                    try:
                        start_date = datetime.strptime(date_str, '%Y-%m-%d')
                    except:
                        pass
                
                if 'Data de Conclusão' in row or 'Finish Date' in row:
                    date_str = row.get('Data de Conclusão', row.get('Finish Date', ''))
                    try:
                        finish_date = datetime.strptime(date_str, '%Y-%m-%d')
                    except:
                        pass
                
                task = MPPTask(
                    id=row.get('ID', None),
                    name=task_name,
                    resource_name=resource_name if resource_name else None,
                    start_date=start_date,
                    finish_date=finish_date,
                    duration=row.get('Duração', row.get('Duration', None)),
                    is_user_story=(not resource_name or resource_name.strip() == "")
                )
                tasks.append(task)
        
        # Primeira linha pode ser o nome do projeto
        if tasks and tasks[0].name:
            project_name = tasks[0].name
        
        mpp_project = MPPProject(
            name=project_name,
            file_name=filename,
            work_item_id=work_item_id,
            tasks=tasks
        )
        
        user_stories, classified_tasks = self._classify_tasks(tasks)
        
        return ParsedMPPData(
            project=mpp_project,
            user_stories=user_stories,
            tasks=classified_tasks
        )

