"""Configuração compartilhada para testes."""
import pytest
from unittest.mock import Mock, MagicMock
from typing import Dict, Any, List
from pathlib import Path
import sys

# Adiciona o diretório backend ao path
backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from app.services.devops_client import AzureDevOpsClient
from app.services.mpp_parser import MPPParser
from app.services.mapper_service import MapperService
from app.models.devops_models import WorkItemResponse, WorkItemCreate, ProjectInfo
from app.models.mpp_models import MPPProject, MPPTask, ParsedMPPData


@pytest.fixture
def mock_requests_response() -> Mock:
    """Fixture para mock de resposta HTTP."""
    response = Mock()
    response.status_code = 200
    response.raise_for_status = Mock()
    response.json.return_value = {}
    response.text = ""
    return response


@pytest.fixture
def mock_work_item_response() -> Dict[str, Any]:
    """Fixture para mock de Work Item do Azure DevOps."""
    return {
        "id": 12345,
        "rev": 1,
        "fields": {
            "System.Id": 12345,
            "System.Title": "Test Work Item",
            "System.WorkItemType": "Task",
            "System.State": "New",
            "System.AreaPath": "Quali IT - Inovação e Tecnologia\\Test Project",
            "System.IterationPath": "Quali IT - Inovação e Tecnologia\\Sprint 1",
            "System.AssignedTo": {
                "displayName": "Test User",
                "uniqueName": "test@example.com"
            },
            "Microsoft.VSTS.Scheduling.StartDate": "2025-01-01T00:00:00Z",
            "Microsoft.VSTS.Scheduling.TargetDate": "2025-01-31T00:00:00Z",
            "System.Description": "Test description"
        },
        "relations": [],
        "url": "https://dev.azure.com/test/org/project/_apis/wit/workitems/12345"
    }


@pytest.fixture
def mock_project_info() -> Dict[str, Any]:
    """Fixture para mock de ProjectInfo."""
    return {
        "id": "12345",
        "name": "Test Project",
        "description": "Test Description",
        "url": "https://dev.azure.com/test",
        "area_path": "Quali IT - Inovação e Tecnologia\\Test Project",
        "iteration_path": "Quali IT - Inovação e Tecnologia\\Sprint 1",
        "user_stories_count": 5,
        "tasks_count": 10
    }


@pytest.fixture
def mock_parsed_mpp_data() -> ParsedMPPData:
    """Fixture para mock de dados parseados do MPP."""
    project = MPPProject(
        name="Test Project",
        work_item_id="12345",  # String ao invés de int
        file_name="12345 - Test Project.mpp"
    )
    
    user_story = MPPTask(
        id="1",
        name="Test User Story",
        resource_name=None,
        is_user_story=True,
        parent_id=None,
        level=0
    )
    
    task = MPPTask(
        id="2",
        name="Test Task",
        resource_name="Test User",
        is_user_story=False,
        parent_id="1",
        level=1
    )
    
    return ParsedMPPData(
        project=project,
        user_stories=[user_story],
        tasks=[task]
    )


@pytest.fixture
def devops_client(monkeypatch) -> AzureDevOpsClient:
    """Fixture para AzureDevOpsClient com mock."""
    # Mock do settings para evitar validação de PAT
    monkeypatch.setattr("app.config.settings.AZURE_DEVOPS_PAT", "test_pat")
    return AzureDevOpsClient(pat="test_pat")


@pytest.fixture
def mpp_parser() -> MPPParser:
    """Fixture para MPPParser."""
    return MPPParser()


@pytest.fixture
def mapper_service(devops_client) -> MapperService:
    """Fixture para MapperService."""
    return MapperService(devops_client=devops_client)

