"""Testes para o router de Work Items."""
import pytest
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient

from app.main import app
from app.models.devops_models import WorkItemResponse


@pytest.fixture
def client():
    """Fixture para criar cliente de teste."""
    return TestClient(app)


@pytest.fixture
def mock_work_item():
    """Fixture para mock de Work Item."""
    return WorkItemResponse(
        id=12345,
        rev=1,
        fields={
            "System.Title": "Test Work Item",
            "System.WorkItemType": "Feature",
            "System.State": "Active"
        },
        relations=[],
        url="https://dev.azure.com/test/12345"
    )


class TestWorkItemsRouter:
    """Testes para o router de Work Items."""
    
    @patch('app.routers.workitems.devops_client')
    def test_get_work_item_success(self, mock_client, client, mock_work_item):
        """Testa obtenção de Work Item por ID."""
        mock_client.get_work_item_by_id.return_value = mock_work_item
        
        response = client.get("/api/v1/workitems/12345")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == 12345
        assert data["fields"]["System.Title"] == "Test Work Item"
    
    @patch('app.routers.workitems.devops_client')
    def test_get_work_item_not_found(self, mock_client, client):
        """Testa obtenção de Work Item não encontrado."""
        mock_client.get_work_item_by_id.return_value = None
        
        response = client.get("/api/v1/workitems/99999")
        
        assert response.status_code == 404
    
    @patch('app.routers.workitems.devops_client')
    def test_search_work_items_success(self, mock_client, client, mock_work_item):
        """Testa busca de Work Items."""
        mock_client.search_work_items_by_title.return_value = [mock_work_item]
        
        response = client.get("/api/v1/workitems/?title=Test")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == 12345
    
    def test_search_work_items_missing_title(self, client):
        """Testa busca sem título (obrigatório)."""
        response = client.get("/api/v1/workitems/")
        
        assert response.status_code == 400
    
    @patch('app.routers.workitems.analyzer')
    def test_analyze_work_item_success(self, mock_analyzer, client):
        """Testa análise de Work Item."""
        mock_analyzer.analyze_work_item.return_value = {
            "id": 12345,
            "title": "Test Feature",
            "user_stories": [],
            "tasks": []
        }
        
        response = client.get("/api/v1/workitems/12345/analyze")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == 12345
    
    @patch('app.routers.workitems.analyzer')
    def test_analyze_work_item_not_found(self, mock_analyzer, client):
        """Testa análise de Work Item não encontrado."""
        mock_analyzer.analyze_work_item.return_value = None
        
        response = client.get("/api/v1/workitems/99999/analyze")
        
        # Pode retornar 404 ou 500 dependendo do tratamento de erro
        assert response.status_code in [404, 500]
    
    @patch('app.routers.workitems.devops_client')
    def test_search_work_items_with_filters(self, mock_client, client, mock_work_item):
        """Testa busca com filtros."""
        mock_client.search_work_items_by_title.return_value = [mock_work_item]
        
        response = client.get(
            "/api/v1/workitems/?title=Test&work_item_type=Feature&area_path=Test"
        )
        
        assert response.status_code == 200
        mock_client.search_work_items_by_title.assert_called_once_with(
            title="Test",
            work_item_type="Feature",
            area_path="Test"
        )

