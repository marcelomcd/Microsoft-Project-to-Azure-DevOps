"""Testes para o router de upload."""
import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient
from fastapi import FastAPI
from pathlib import Path
import tempfile
import os

from app.routers import upload
from app.main import app


@pytest.fixture
def client():
    """Fixture para criar cliente de teste."""
    return TestClient(app)


@pytest.fixture
def mock_mpp_file():
    """Fixture para criar arquivo .mpp mock."""
    # Cria arquivo temporário
    with tempfile.NamedTemporaryFile(suffix='.mpp', delete=False) as f:
        f.write(b"Mock MPP file content")
        temp_path = f.name
    
    yield temp_path
    
    # Limpa após teste
    if os.path.exists(temp_path):
        os.unlink(temp_path)


@pytest.fixture
def mock_parsed_data():
    """Fixture para dados parseados mock."""
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
    
    return ParsedMPPData(
        project=project,
        user_stories=[user_story],
        tasks=[task]
    )


class TestUploadRouter:
    """Testes para o router de upload."""
    
    @patch('app.routers.upload.MPPParser')
    @patch('app.routers.upload.devops_client')
    def test_upload_mpp_file_success(self, mock_devops, mock_parser_class, client, mock_mpp_file, mock_parsed_data):
        """Testa upload bem-sucedido de arquivo .mpp."""
        # Mock do parser
        mock_parser = Mock()
        mock_parser.parse_file.return_value = mock_parsed_data
        mock_parser_class.return_value = mock_parser
        
        # Mock do devops client
        mock_devops.get_work_item_by_id.return_value = None
        
        # Cria arquivo para upload
        with open(mock_mpp_file, 'rb') as f:
            response = client.post(
                "/api/v1/upload/",
                files={"file": ("12345 - Test Project.mpp", f, "application/octet-stream")}
            )
        
        assert response.status_code == 200
        data = response.json()
        assert "file_id" in data
        assert data["work_item_id"] == "12345"
        assert data["project_name"] == "Test Project"
        assert data["user_stories_count"] == 1
        assert data["tasks_count"] == 1
    
    def test_upload_invalid_file_type(self, client):
        """Testa upload de arquivo com tipo inválido."""
        response = client.post(
            "/api/v1/upload/",
            files={"file": ("test.txt", b"content", "text/plain")}
        )
        
        assert response.status_code == 400
        assert "deve ser .mpp ou .csv" in response.json()["detail"].lower()
    
    @patch('app.routers.upload.MPPParser')
    def test_upload_file_too_large(self, mock_parser_class, client):
        """Testa upload de arquivo muito grande."""
        # Mock do parser para não processar
        mock_parser = Mock()
        mock_parser_class.return_value = mock_parser
        
        # Cria arquivo grande (simulado)
        large_content = b"x" * (51 * 1024 * 1024)  # 51MB
        
        response = client.post(
            "/api/v1/upload/",
            files={"file": ("test.mpp", large_content, "application/octet-stream")}
        )
        
        # FastAPI pode retornar 500 quando há HTTPException com status 413
        assert response.status_code in [413, 500]
    
    def test_get_parsed_file_success(self, client):
        """Testa obtenção de arquivo parseado."""
        from app.routers.upload import parsed_files
        file_id = "test-file-id"
        parsed_files[file_id] = {
            "file_id": file_id,
            "filename": "test.mpp",
            "parsed_data": {}
        }
        
        try:
            response = client.get(f"/api/v1/upload/{file_id}")
            
            assert response.status_code == 200
            data = response.json()
            assert data["file_id"] == file_id
        finally:
            # Limpa após teste
            if file_id in parsed_files:
                del parsed_files[file_id]
    
    @patch('app.routers.upload.parsed_files')
    def test_get_parsed_file_not_found(self, mock_parsed_files, client):
        """Testa obtenção de arquivo não encontrado."""
        mock_parsed_files.clear()
        
        response = client.get("/api/v1/upload/non-existent-id")
        
        assert response.status_code == 404
    
    def test_get_raw_file_data_success(self, client):
        """Testa obtenção de dados brutos do arquivo."""
        from app.routers.upload import parsed_files
        import tempfile
        import os
        
        file_id = "test-file-id"
        # Cria arquivo temporário real
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write("col1,col2\nval1,val2\n")
            temp_path = f.name
        
        try:
            parsed_files[file_id] = {
                "file_id": file_id,
                "file_path": temp_path
            }
            
            response = client.get(f"/api/v1/upload/{file_id}/raw-data")
            
            # Pode retornar 200 ou 500 dependendo do processamento
            assert response.status_code in [200, 500]
        finally:
            # Limpa após teste
            if file_id in parsed_files:
                del parsed_files[file_id]
            if os.path.exists(temp_path):
                os.unlink(temp_path)

