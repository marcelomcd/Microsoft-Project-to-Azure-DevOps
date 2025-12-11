"""Analisador de Work Items do Azure DevOps"""
from typing import List, Dict, Any, Optional
from app.services.devops_client import AzureDevOpsClient
from app.models.devops_models import WorkItemResponse


class WorkItemAnalyzer:
    """Analisa Work Items e extrai informações estruturadas"""
    
    def __init__(self, devops_client: Optional[AzureDevOpsClient] = None):
        self.devops_client = devops_client or AzureDevOpsClient()
    
    def analyze_work_item(self, work_item_id: int) -> Dict[str, Any]:
        """
        Analisa um Work Item e retorna informações estruturadas.
        
        Args:
            work_item_id: ID do Work Item
            
        Returns:
            Dicionário com informações analisadas
        """
        work_item = self.devops_client.get_work_item_by_id(work_item_id)
        if not work_item:
            return {}
        
        fields = work_item.fields
        
        # Extrai informações básicas
        info = {
            "id": work_item.id,
            "type": fields.get("System.WorkItemType", ""),
            "title": fields.get("System.Title", ""),
            "state": fields.get("System.State", ""),
            "area_path": fields.get("System.AreaPath", ""),
            "iteration_path": fields.get("System.IterationPath", ""),
            "assigned_to": self._extract_assigned_to(fields),
            "start_date": fields.get("Microsoft.VSTS.Scheduling.StartDate"),
            "target_date": fields.get("Microsoft.VSTS.Scheduling.TargetDate"),
            "description": fields.get("System.Description", ""),
            "created_date": fields.get("System.CreatedDate"),
            "changed_date": fields.get("System.ChangedDate"),
        }
        
        # Extrai cliente do AreaPath
        info["cliente"] = self._extract_client_from_path(fields.get("System.AreaPath", ""))
        
        # Extrai responsável técnico (campo customizado)
        responsavel_tecnico = fields.get("Custom.ResponsavelTecnico")
        if responsavel_tecnico:
            if isinstance(responsavel_tecnico, dict):
                info["responsavel_tecnico"] = {
                    "nome": responsavel_tecnico.get("displayName", ""),
                    "email": responsavel_tecnico.get("uniqueName", "")
                }
            else:
                info["responsavel_tecnico"] = responsavel_tecnico
        
        # Busca filhos (User Stories e Tasks)
        children = self._get_children(work_item)
        info["children"] = children
        user_stories = [c for c in children if c.get("type") == "User Story"]
        info["tasks"] = [c for c in children if c.get("type") == "Task"]
        
        # Para cada User Story, busca suas Tasks filhas
        for us in user_stories:
            us_tasks = self._get_children_by_id(us["id"])
            us["tasks"] = [t for t in us_tasks if t.get("type") == "Task"]
        
        info["user_stories"] = user_stories
        
        # Informações do pai
        parent_info = self._get_parent_info(work_item)
        info["parent"] = parent_info
        
        # Campos customizados
        custom_fields = {k: v for k, v in fields.items() if k.startswith("Custom.")}
        info["custom_fields"] = custom_fields
        
        return info
    
    def _extract_assigned_to(self, fields: Dict[str, Any]) -> Optional[Dict[str, str]]:
        """Extrai informações do Assigned To"""
        assigned_to = fields.get("System.AssignedTo")
        if not assigned_to:
            return None
        
        if isinstance(assigned_to, dict):
            return {
                "nome": assigned_to.get("displayName", ""),
                "email": assigned_to.get("uniqueName", "")
            }
        return {"email": str(assigned_to)}
    
    def _extract_client_from_path(self, area_path: str) -> Optional[str]:
        """Extrai nome do cliente do AreaPath"""
        if not area_path:
            return None
        
        parts = area_path.split("\\")
        # Cliente normalmente está no último nível ou penúltimo
        if len(parts) >= 4:
            return parts[-1]  # Último nível
        return None
    
    def _get_children(self, work_item: WorkItemResponse) -> List[Dict[str, Any]]:
        """Busca e retorna filhos do Work Item"""
        children = []
        work_item_id = work_item.id
        
        # Usa query WIQL para buscar filhos diretamente (mais confiável)
        try:
            wiql_query = {
                "query": f"SELECT [System.Id], [System.Title], [System.WorkItemType], [System.State], [System.AssignedTo], [Microsoft.VSTS.Scheduling.StartDate], [Microsoft.VSTS.Scheduling.TargetDate] FROM WorkItems WHERE [System.Parent] = {work_item_id} ORDER BY [System.Id]"
            }
            
            response = self.devops_client._make_request(
                'POST',
                'wit/wiql',
                json=wiql_query
            )
            
            data = response.json()
            work_items = data.get('workItems', [])
            
            if work_items:
                # Busca detalhes dos filhos
                ids = [str(wi['id']) for wi in work_items]
                child_items = self.devops_client.get_work_items_by_ids(ids)
                
                for child in child_items:
                    fields = child.fields
                    children.append({
                        "id": child.id,
                        "type": fields.get("System.WorkItemType", ""),
                        "title": fields.get("System.Title", ""),
                        "name": fields.get("System.Title", ""),  # Adiciona 'name' para compatibilidade
                        "state": fields.get("System.State", ""),
                        "assigned_to": self._extract_assigned_to(fields),
                        "start_date": fields.get("Microsoft.VSTS.Scheduling.StartDate"),
                        "target_date": fields.get("Microsoft.VSTS.Scheduling.TargetDate"),
                    })
        except Exception as e:
            print(f"Erro ao buscar filhos via WIQL: {e}")
            import traceback
            traceback.print_exc()
            
            # Fallback: tenta usar relações se WIQL falhar
            if work_item.relations:
                child_relations = [
                    rel for rel in work_item.relations
                    if rel.get("rel") == "System.LinkTypes.Hierarchy-Forward"
                ]
                
                child_ids = []
                for rel in child_relations:
                    url = rel.get("url", "")
                    if "/workitems/" in url:
                        try:
                            item_id = int(url.split("/workitems/")[-1])
                            child_ids.append(item_id)
                        except ValueError:
                            continue
                
                if child_ids:
                    try:
                        child_items = self.devops_client.get_work_items_by_ids([str(id) for id in child_ids])
                        for child in child_items:
                            fields = child.fields
                            children.append({
                                "id": child.id,
                                "type": fields.get("System.WorkItemType", ""),
                                "title": fields.get("System.Title", ""),
                                "name": fields.get("System.Title", ""),
                                "state": fields.get("System.State", ""),
                                "assigned_to": self._extract_assigned_to(fields),
                                "start_date": fields.get("Microsoft.VSTS.Scheduling.StartDate"),
                                "target_date": fields.get("Microsoft.VSTS.Scheduling.TargetDate"),
                            })
                    except Exception as e2:
                        print(f"Erro ao buscar filhos via relações: {e2}")
        
        return children
    
    def _get_children_by_id(self, work_item_id: int) -> List[Dict[str, Any]]:
        """Busca filhos de um Work Item por ID (usado para buscar Tasks de User Stories)"""
        children = []
        
        try:
            wiql_query = {
                "query": f"SELECT [System.Id], [System.Title], [System.WorkItemType], [System.State], [System.AssignedTo], [Microsoft.VSTS.Scheduling.StartDate], [Microsoft.VSTS.Scheduling.TargetDate] FROM WorkItems WHERE [System.Parent] = {work_item_id} ORDER BY [System.Id]"
            }
            
            response = self.devops_client._make_request(
                'POST',
                'wit/wiql',
                json=wiql_query
            )
            
            data = response.json()
            work_items = data.get('workItems', [])
            
            if work_items:
                ids = [str(wi['id']) for wi in work_items]
                child_items = self.devops_client.get_work_items_by_ids(ids)
                
                for child in child_items:
                    fields = child.fields
                    children.append({
                        "id": child.id,
                        "type": fields.get("System.WorkItemType", ""),
                        "title": fields.get("System.Title", ""),
                        "name": fields.get("System.Title", ""),
                        "state": fields.get("System.State", ""),
                        "assigned_to": self._extract_assigned_to(fields),
                        "start_date": fields.get("Microsoft.VSTS.Scheduling.StartDate"),
                        "target_date": fields.get("Microsoft.VSTS.Scheduling.TargetDate"),
                    })
        except Exception as e:
            print(f"Erro ao buscar filhos do Work Item {work_item_id}: {e}")
        
        return children
    
    def _get_parent_info(self, work_item: WorkItemResponse) -> Optional[Dict[str, Any]]:
        """Busca e retorna informações do pai"""
        if not work_item.relations:
            return None
        
        # Busca relação com pai
        parent_relation = None
        for rel in work_item.relations:
            if rel.get("rel") == "System.LinkTypes.Hierarchy-Reverse":
                parent_relation = rel
                break
        
        # Também verifica campo System.Parent
        fields = work_item.fields
        parent_id = fields.get("System.Parent")
        
        if parent_id:
            parent = self.devops_client.get_work_item_by_id(parent_id)
            if parent:
                parent_fields = parent.fields
                return {
                    "id": parent.id,
                    "type": parent_fields.get("System.WorkItemType", ""),
                    "title": parent_fields.get("System.Title", "")
                }
        
        # Tenta extrair da relação
        if parent_relation:
            url = parent_relation.get("url", "")
            if "/workitems/" in url:
                try:
                    parent_id = int(url.split("/workitems/")[-1])
                    parent = self.devops_client.get_work_item_by_id(parent_id)
                    if parent:
                        parent_fields = parent.fields
                        return {
                            "id": parent.id,
                            "type": parent_fields.get("System.WorkItemType", ""),
                            "title": parent_fields.get("System.Title", "")
                        }
                except ValueError:
                    pass
        
        return None

