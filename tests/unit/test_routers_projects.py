"""Testes para o router de projetos."""
import pytest
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient

from app.main import app
from app.models.devops_models import ProjectInfo


@pytest.fixture
def client():
    """Fixture para criar cliente de teste."""
    return TestClient(app)


@pytest.fixture
def mock_project_info():
    """Fixture para mock de ProjectInfo."""
    return ProjectInfo(
        id="12345",
        name="Test Project",
        description="Test Description",
        url="https://dev.azure.com/test",
        area_path="Quali IT - Inovação e Tecnologia\\Test Project",
        iteration_path="Quali IT - Inovação e Tecnologia\\Sprint 1",
        user_stories_count=5,
        tasks_count=10
    )


class TestProjectsRouter:
    """Testes para o router de projetos."""
    
    @patch('app.routers.projects.devops_client')
    def test_list_projects_success(self, mock_client, client, mock_project_info):
        """Testa listagem de projetos."""
        mock_client.list_projects.return_value = [mock_project_info]
        
        response = client.get("/api/v1/projects/")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == "12345"
        assert data[0]["name"] == "Test Project"
    
    @patch('app.routers.projects.devops_client')
    def test_list_projects_with_limit(self, mock_client, client, mock_project_info):
        """Testa listagem com limite."""
        mock_client.list_projects.return_value = [mock_project_info]
        
        response = client.get("/api/v1/projects/?limit=10")
        
        assert response.status_code == 200
        mock_client.list_projects.assert_called_once_with(limit=10, use_cache=True)
    
    @patch('app.routers.projects.devops_client')
    def test_list_projects_without_cache(self, mock_client, client, mock_project_info):
        """Testa listagem sem cache."""
        mock_client.list_projects.return_value = [mock_project_info]
        
        response = client.get("/api/v1/projects/?use_cache=false")
        
        assert response.status_code == 200
        mock_client.list_projects.assert_called_once_with(limit=100, use_cache=False)
    
    @patch('app.routers.projects.devops_client')
    def test_list_projects_error(self, mock_client, client):
        """Testa listagem com erro."""
        mock_client.list_projects.side_effect = Exception("API Error")
        
        response = client.get("/api/v1/projects/")
        
        assert response.status_code == 500
    
    @patch('app.routers.projects.devops_client')
    def test_get_project_work_items(self, mock_client, client):
        """Testa obtenção de Work Items de um projeto."""
        from app.models.devops_models import WorkItemResponse
        
        mock_work_item = WorkItemResponse(
            id=123,
            rev=1,
            fields={"System.Title": "Test"},
            relations=[],
            url="https://test.com"
        )
        mock_client.get_project_work_items.return_value = [mock_work_item]
        
        response = client.get("/api/v1/projects/12345/workitems")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
    
    @patch('app.routers.projects.project_cache')
    def test_clear_cache(self, mock_cache, client):
        """Testa limpeza de cache."""
        response = client.post("/api/v1/projects/cache/clear")
        
        assert response.status_code == 200
        mock_cache.clear.assert_called_once()
    
    @patch('app.routers.projects.project_cache')
    def test_get_cache_stats(self, mock_cache, client):
        """Testa obtenção de estatísticas de cache."""
        mock_cache.get_stats.return_value = {
            "total_items": 5,
            "keys": ["key1", "key2"],
            "hits": 10,
            "misses": 2,
            "hit_rate": "83.33%"
        }
        
        response = client.get("/api/v1/projects/cache/stats")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_items"] == 5
        assert "hit_rate" in data

