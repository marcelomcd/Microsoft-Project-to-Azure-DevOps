"""Router para upload de arquivos .mpp"""
import os
import uuid
import json
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException
from typing import Dict, Optional

from app.config import settings
from app.services.mpp_parser import MPPParser
from app.services.devops_client import AzureDevOpsClient

router = APIRouter(prefix="/upload", tags=["upload"])

# Cria diretório de uploads se não existir
upload_dir = Path(settings.UPLOAD_DIR)
upload_dir.mkdir(exist_ok=True)

# Cache de arquivos parseados
parsed_files: Dict[str, dict] = {}

def get_devops_client():
    """Obtém instância do cliente DevOps (lazy initialization)"""
    try:
        return AzureDevOpsClient()
    except ValueError as e:
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/",
    summary="Faz upload e parse de arquivo .mpp",
    description="""
    Faz upload de um arquivo .mpp e retorna os dados parseados.
    
    **Funcionalidades:**
    - Aceita arquivos .mpp (Microsoft Project)
    - Extrai Work Item ID do nome do arquivo (primeiros 5 dígitos)
    - Classifica tarefas em User Stories (sem recurso) e Tasks (com recurso)
    - Retorna dados estruturados prontos para conversão
    
    **Formato do nome do arquivo:**
    - Deve conter o Work Item ID nos primeiros 5 dígitos
    - Exemplo: `15404 025543-02 - Camil - Fluxo de alocação de pedidos.mpp`
    - Work Item ID extraído: `15404`
    
    **Classificação:**
    - Primeira linha: ID e título do projeto (excluída)
    - Sem recurso na coluna "Nomes dos recursos": User Story
    - Com recurso na coluna "Nomes dos recursos": Task
    
    **Retorno:**
    - file_id: ID único do arquivo (usar no endpoint /convert)
    - work_item_id: ID extraído do nome do arquivo
    - parsed_data: Dados parseados (projeto, User Stories, Tasks)
    """
)
async def upload_mpp_file(file: UploadFile = File(...)) -> Dict:
    """
    Faz upload de um arquivo .mpp e retorna os dados parseados.
    
    O arquivo é salvo temporariamente, parseado, e os dados são retornados.
    O arquivo parseado fica disponível para conversão usando o `file_id` retornado.
    
    Args:
        file: Arquivo .mpp (Microsoft Project)
        
    Returns:
        Dicionário com:
        - file_id: ID único do arquivo (usar em /convert)
        - filename: Nome original do arquivo
        - work_item_id: ID extraído do nome do arquivo
        - project_name: Nome do projeto
        - user_stories_count: Quantidade de User Stories encontradas
        - tasks_count: Quantidade de Tasks encontradas
        - parsed_data: Dados parseados completos
        
    Raises:
        HTTPException 400: Se o arquivo não for .mpp ou .csv
        HTTPException 500: Se houver erro no parse
    """
    # Valida extensão
    if not file.filename.endswith('.mpp') and not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Arquivo deve ser .mpp ou .csv")
    
    # Gera ID único para o arquivo
    file_id = str(uuid.uuid4())
    file_path = upload_dir / f"{file_id}.{file.filename.split('.')[-1]}"
    
    try:
        # Salva arquivo
        content = await file.read()
        if len(content) > settings.MAX_UPLOAD_SIZE:
            raise HTTPException(
                status_code=413,
                detail=f"Arquivo muito grande. Máximo: {settings.MAX_UPLOAD_SIZE / 1024 / 1024}MB"
            )
        
        with open(file_path, 'wb') as f:
            f.write(content)
        
        # IMPORTANTE: Usa o nome original do arquivo (file.filename) para extrair work_item_id
        # O arquivo salvo tem um UUID como nome, então precisamos usar o nome original
        original_filename = file.filename
        
        # Parse do arquivo (passa o nome original para o parser)
        parser = MPPParser()
        # O parser precisa receber o nome original, não o caminho do arquivo salvo
        parsed_data = parser.parse_file(str(file_path), original_filename=original_filename)
        
        # Debug: verifica se work_item_id foi extraído
        print(f"DEBUG: filename original: {original_filename}")
        print(f"DEBUG: filename salvo: {file_path.name}")
        print(f"DEBUG: work_item_id extraído do parser: {parsed_data.project.work_item_id}")
        print(f"DEBUG: work_item_id type: {type(parsed_data.project.work_item_id)}")
        print(f"DEBUG: project name: {parsed_data.project.name}")
        print(f"DEBUG: total tasks: {len(parsed_data.project.tasks)}")
        print(f"DEBUG: user stories: {len(parsed_data.user_stories)}")
        print(f"DEBUG: tasks: {len(parsed_data.tasks)}")
        
        # Garante que work_item_id seja string ou None (não vazio)
        work_item_id = parsed_data.project.work_item_id
        print(f"DEBUG: work_item_id do parsed_data.project: {work_item_id} (type: {type(work_item_id)})")
        
        if work_item_id is not None:
            # Converte para string se for número
            work_item_id = str(work_item_id).strip()
            print(f"DEBUG: work_item_id após str().strip(): '{work_item_id}'")
            if work_item_id == '' or work_item_id.lower() == 'none':
                print(f"DEBUG: work_item_id vazio ou 'none', definindo como None")
                work_item_id = None
            else:
                print(f"DEBUG: work_item_id válido: '{work_item_id}'")
        else:
            print(f"DEBUG: work_item_id é None no parsed_data.project")
            work_item_id = None
        
        print(f"DEBUG: work_item_id final antes de retornar: {work_item_id} (type: {type(work_item_id)})")
        print(f"DEBUG: work_item_id será retornado na resposta: {work_item_id}")
        print(f"DEBUG: work_item_id is None? {work_item_id is None}")
        print(f"DEBUG: work_item_id bool? {bool(work_item_id)}")
        
        # Busca Work Item do DevOps se houver ID
        work_item_data = None
        if work_item_id:
            try:
                client = get_devops_client()
                work_item = client.get_work_item_by_id(int(parsed_data.project.work_item_id))
                if work_item:
                    work_item_data = {
                        "id": work_item.id,
                        "title": work_item.fields.get('System.Title'),
                        "state": work_item.fields.get('System.State'),
                        "area_path": work_item.fields.get('System.AreaPath'),
                        "iteration_path": work_item.fields.get('System.IterationPath'),
                        "assigned_to": work_item.fields.get('System.AssignedTo'),
                        "url": work_item.url
                    }
            except Exception as e:
                # Ignora erro ao buscar Work Item, não é crítico
                pass
        
        # Armazena dados parseados
        # Usa model_dump se disponível (Pydantic v2), senão usa dict() (Pydantic v1)
        # Usa mode='json' para garantir serialização completa incluindo listas vazias
        try:
            # Pydantic v2: model_dump com mode='json' para serialização completa
            parsed_data_dict = parsed_data.model_dump(mode='json')
        except (AttributeError, TypeError):
            try:
                # Tenta model_dump sem mode (Pydantic v2 sem mode)
                parsed_data_dict = parsed_data.model_dump()
            except AttributeError:
                # Pydantic v1: usa dict()
                parsed_data_dict = parsed_data.dict()
        
        # Debug: verifica se project.tasks está presente
        project_tasks_count = len(parsed_data.project.tasks) if parsed_data.project.tasks else 0
        parsed_dict_tasks_count = len(parsed_data_dict.get('project', {}).get('tasks', []))
        print(f"DEBUG: parsed_data.project.tasks count: {project_tasks_count}")
        print(f"DEBUG: parsed_data_dict['project']['tasks'] count: {parsed_dict_tasks_count}")
        if project_tasks_count > 0 and parsed_dict_tasks_count == 0:
            print(f"DEBUG: AVISO - project.tasks não foi serializado corretamente!")
            # Força inclusão de tasks se não foi serializado
            if 'project' in parsed_data_dict:
                parsed_data_dict['project']['tasks'] = [
                    task.model_dump(mode='json') if hasattr(task, 'model_dump') else task.dict()
                    for task in parsed_data.project.tasks
                ]
        
        parsed_files[file_id] = {
            "file_id": file_id,
            "file_path": str(file_path),
            "filename": file.filename,
            "parsed_data": parsed_data_dict,
            "work_item_data": work_item_data
        }
        
        response_data = {
            "file_id": file_id,
            "filename": file.filename,
            "project_name": parsed_data.project.name,
            "work_item_id": work_item_id,  # Pode ser string ou None
            "user_stories_count": len(parsed_data.user_stories),
            "tasks_count": len(parsed_data.tasks),
            "parsed_data": parsed_data_dict,
            "work_item_data": work_item_data
        }
        
        print(f"DEBUG: Resposta final - work_item_id: {response_data.get('work_item_id')} (type: {type(response_data.get('work_item_id'))})")
        print(f"DEBUG: Resposta final - work_item_id is None? {response_data.get('work_item_id') is None}")
        print(f"DEBUG: Resposta final - work_item_id bool? {bool(response_data.get('work_item_id'))}")
        
        # Garante que work_item_id não seja None se foi extraído corretamente
        # Se parsed_data.project.work_item_id existe mas work_item_id é None, há um problema
        if parsed_data.project.work_item_id and not work_item_id:
            print(f"DEBUG: AVISO - parsed_data.project.work_item_id existe ({parsed_data.project.work_item_id}) mas work_item_id é None!")
            # Tenta usar diretamente do parsed_data
            work_item_id = str(parsed_data.project.work_item_id).strip()
            response_data["work_item_id"] = work_item_id
            print(f"DEBUG: Corrigido - work_item_id agora é: {work_item_id}")
        
        print(f"DEBUG: Resposta completa será retornada: {json.dumps(response_data, indent=2, default=str)}")
        
        return response_data
    except Exception as e:
        # Remove arquivo em caso de erro
        if file_path.exists():
            file_path.unlink()
        error_msg = str(e)
        if "binário" in error_msg.lower():
            raise HTTPException(status_code=400, detail=error_msg)
        raise HTTPException(status_code=500, detail=f"Erro ao processar arquivo: {error_msg}")


@router.get("/{file_id}")
async def get_parsed_file(file_id: str) -> Dict:
    """
    Obtém dados parseados de um arquivo pelo ID.
    
    Args:
        file_id: ID do arquivo
        
    Returns:
        Dados parseados
    """
    if file_id not in parsed_files:
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")
    
    return parsed_files[file_id]


@router.get("/{file_id}/raw-data")
async def get_raw_file_data(file_id: str) -> Dict:
    """
    Obtém dados brutos (linhas e colunas) do arquivo parseado.
    Retorna vazio se o arquivo for binário.
    
    Args:
        file_id: ID do arquivo
        
    Returns:
        Dados brutos do arquivo
    """
    if file_id not in parsed_files:
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")
    
    file_data = parsed_files[file_id]
    file_path = file_data.get("file_path")
    
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Arquivo físico não encontrado")
    
    # Verifica se é arquivo binário
    try:
        with open(file_path, 'rb') as f:
            first_bytes = f.read(1024)
            if b'\x00' in first_bytes[:100] or (first_bytes[0] if first_bytes else 0) > 127:
                # Arquivo binário - retorna vazio
                return {
                    "headers": [],
                    "rows": [],
                    "total_rows": 0,
                    "is_binary": True,
                    "message": "Arquivo .mpp binário. Exporte para CSV no Microsoft Project para visualizar dados brutos."
                }
    except Exception:
        pass
    
    # Lê arquivo como CSV e retorna todas as linhas e colunas
    raw_data = []
    headers = []
    try:
        import csv
        encodings = ['utf-8-sig', 'utf-8', 'latin-1', 'cp1252']
        used_encoding = None
        
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    reader = csv.DictReader(f)
                    headers = reader.fieldnames or []
                    # Testa se consegue ler primeira linha
                    try:
                        first_row = next(reader)
                        raw_data.append(dict(first_row))
                        # Lê resto do arquivo
                        for row in reader:
                            raw_data.append(dict(row))
                        used_encoding = encoding
                        break
                    except StopIteration:
                        break
            except (UnicodeDecodeError, UnicodeError):
                continue
        
        if used_encoding is None:
            return {
                "headers": [],
                "rows": [],
                "total_rows": 0,
                "is_binary": True,
                "message": "Não foi possível ler o arquivo como texto. Exporte para CSV no Microsoft Project."
            }
        
        return {
            "headers": headers,
            "rows": raw_data,
            "total_rows": len(raw_data),
            "is_binary": False
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao ler dados brutos: {str(e)}")
