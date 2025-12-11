"""Testes para o router de conversão."""
import pytest
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient

from app.main import app
from app.models.devops_models import ConversionResult


@pytest.fixture
def client():
    """Fixture para criar cliente de teste."""
    return TestClient(app)


@pytest.fixture
def mock_parsed_files_data():
    """Fixture para mock de arquivos parseados."""
    from app.models.mpp_models import ParsedMPPData, MPPProject, MPPTask
    from datetime import datetime
    
    project = MPPProject(
        name="Test Project",
        work_item_id="12345",
        file_name="12345 - Test Project.mpp"
    )
    
    user_story = MPPTask(
        id="1",
        name="User Story 1",
        resource_name=None,
        is_user_story=True,
        parent_id=None,
        level=0,
        start_date=datetime(2025, 1, 1),
        finish_date=datetime(2025, 1, 5)
    )
    
    task = MPPTask(
        id="2",
        name="Task 1",
        resource_name="Test User",
        is_user_story=False,
        parent_id="1",
        level=1,
        start_date=datetime(2025, 1, 2),
        finish_date=datetime(2025, 1, 3)
    )
    
    parsed_data = ParsedMPPData(
        project=project,
        user_stories=[user_story],
        tasks=[task]
    )
    
    return {
        "test-file-id": {
            "file_id": "test-file-id",
            "parsed_data": parsed_data.model_dump()
        }
    }


class TestConvertRouter:
    """Testes para o router de conversão."""
    
    @patch('app.routers.convert.mapper_service')
    def test_convert_mpp_to_devops_success(self, mock_mapper, client, mock_parsed_files_data):
        """Testa conversão bem-sucedida de .mpp para DevOps."""
        from app.routers.convert import parsed_files
        
        # Configura dados reais
        parsed_files.update(mock_parsed_files_data)
        
        try:
            # Mock do resultado de conversão
            mock_result = ConversionResult(
                project_name="Test Project",
                created_user_stories=1,
                created_tasks=1,
                updated_user_stories=0,
                updated_tasks=0,
                skipped_user_stories=0,
                skipped_tasks=0,
                errors=[],
                work_items=[],
                sync_log=None
            )
            mock_mapper.convert_to_devops.return_value = mock_result
            
            response = client.post(
                "/api/v1/convert/",
                json={
                    "file_id": "test-file-id",
                    "skip_duplicates": True,
                    "update_existing": False
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["project_name"] == "Test Project"
            assert data["created_user_stories"] == 1
            assert data["created_tasks"] == 1
        finally:
            # Limpa após teste
            if "test-file-id" in parsed_files:
                del parsed_files["test-file-id"]
    
    @patch('app.routers.convert.parsed_files')
    def test_convert_file_not_found(self, mock_parsed_files, client):
        """Testa conversão com arquivo não encontrado."""
        mock_parsed_files.clear()
        
        response = client.post(
            "/api/v1/convert/",
            json={
                "file_id": "non-existent-id",
                "skip_duplicates": True
            }
        )
        
        assert response.status_code == 404
    
    @patch('app.routers.convert.mapper_service')
    def test_convert_with_error(self, mock_mapper, client, mock_parsed_files_data):
        """Testa conversão com erro."""
        from app.routers.convert import parsed_files
        
        parsed_files.update(mock_parsed_files_data)
        
        try:
            mock_mapper.convert_to_devops.side_effect = Exception("Conversion error")
            
            response = client.post(
                "/api/v1/convert/",
                json={
                    "file_id": "test-file-id",
                    "skip_duplicates": True
                }
            )
            
            assert response.status_code == 500
        finally:
            # Limpa após teste
            if "test-file-id" in parsed_files:
                del parsed_files["test-file-id"]
    
    @patch('app.routers.convert.analyzer')
    def test_sync_devops_to_mpp_success(self, mock_analyzer, client):
        """Testa sincronização de DevOps para .mpp."""
        mock_analyzer.analyze_work_item.return_value = {
            "id": 12345,
            "title": "Test Feature",
            "user_stories": [],
            "tasks": []
        }
        
        response = client.post(
            "/api/v1/convert/sync-from-devops",
            json={
                "work_item_id": 12345,
                "include_closed": True
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["work_item_id"] == 12345
    
    @patch('app.routers.convert.analyzer')
    def test_sync_devops_to_mpp_not_found(self, mock_analyzer, client):
        """Testa sincronização com Work Item não encontrado."""
        mock_analyzer.analyze_work_item.return_value = None
        
        response = client.post(
            "/api/v1/convert/sync-from-devops",
            json={
                "work_item_id": 99999,
                "include_closed": True
            }
        )
        
        assert response.status_code == 404

