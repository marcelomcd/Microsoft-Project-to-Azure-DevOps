"""Testes unitários para MapperService."""
import pytest
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any

from app.services.mapper_service import MapperService
from app.services.devops_client import AzureDevOpsClient
from app.models.mpp_models import ParsedMPPData, MPPProject, MPPTask
from app.models.devops_models import ConversionResult, WorkItemResponse


class TestMapperService:
    """Testes para MapperService."""

    @pytest.fixture
    def mock_devops_client(self):
        """Cria mock do AzureDevOpsClient."""
        client = Mock(spec=AzureDevOpsClient)
        return client

    @pytest.fixture
    def mapper_service(self, mock_devops_client):
        """Cria MapperService com cliente mockado."""
        return MapperService(devops_client=mock_devops_client)

    @pytest.fixture
    def parsed_data(self):
        """Cria dados parseados de teste."""
        project = MPPProject(
            name="Test Project",
            work_item_id="12345",  # String ao invés de int
            file_name="12345 - Test Project.mpp"
        )
        
        user_story = MPPTask(
            id="1",
            name="User Story 1",
            resource_name=None,
            is_user_story=True,
            parent_id=None,
            level=0
        )
        
        task = MPPTask(
            id="2",
            name="Task 1",
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

    def test_mapper_service_initialization(self, mapper_service):
        """Testa inicialização do MapperService."""
        assert mapper_service is not None
        assert mapper_service.devops_client is not None
        assert mapper_service.sync_logger is not None

    @patch('app.services.mapper_service.AzureDevOpsClient')
    def test_mapper_service_default_client(self, mock_client_class):
        """Testa criação com cliente padrão."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        service = MapperService()
        assert service.devops_client is not None

    def test_resolve_parent_feature_id_from_parsed_data(
        self, mapper_service, parsed_data, mock_devops_client
    ):
        """Testa resolução de parent_feature_id a partir dos dados parseados."""
        result = mapper_service._resolve_parent_feature_id(parsed_data, None)
        assert result == 12345

    def test_resolve_parent_feature_id_provided(
        self, mapper_service, parsed_data
    ):
        """Testa resolução quando parent_feature_id é fornecido."""
        result = mapper_service._resolve_parent_feature_id(parsed_data, 99999)
        assert result == 99999

    def test_resolve_paths_from_feature(
        self, mapper_service, mock_devops_client, parsed_data
    ):
        """Testa resolução de paths a partir da Feature."""
        mock_feature = Mock()
        mock_feature.fields = {
            "System.AreaPath": "Area\\Path",
            "System.IterationPath": "Iteration\\Path"
        }
        mock_devops_client.get_work_item_by_id.return_value = mock_feature

        area_path, iteration_path = mapper_service._resolve_paths(
            parsed_data, 12345, None, None
        )

        assert area_path == "Area\\Path"
        assert iteration_path == "Iteration\\Path"

    def test_resolve_paths_defaults(
        self, mapper_service, mock_devops_client, parsed_data
    ):
        """Testa resolução de paths com valores padrão."""
        mock_devops_client.get_work_item_by_id.return_value = None

        area_path, iteration_path = mapper_service._resolve_paths(
            parsed_data, 12345, None, None
        )

        # Deve usar valores padrão
        assert area_path is not None
        assert iteration_path is not None

    @patch('app.services.mapper_service.MapperService._process_user_stories')
    @patch('app.services.mapper_service.MapperService._process_tasks')
    def test_convert_to_devops(
        self,
        mock_process_tasks,
        mock_process_user_stories,
        mapper_service,
        parsed_data,
        mock_devops_client
    ):
        """Testa conversão completa para DevOps."""
        mock_devops_client.get_work_item_by_id.return_value = Mock(
            fields={
                "System.AreaPath": "Area\\Path",
                "System.IterationPath": "Iteration\\Path"
            }
        )

        result = mapper_service.convert_to_devops(
            parsed_data,
            parent_feature_id=12345
        )

        assert isinstance(result, ConversionResult)
        assert result.project_name == "Test Project"
        mock_process_user_stories.assert_called_once()
        mock_process_tasks.assert_called_once()

