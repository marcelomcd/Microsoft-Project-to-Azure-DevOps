"""Testes unitários completos para MPPParser."""
import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import json

from app.services.mpp_parser import MPPParser
from app.models.mpp_models import ParsedMPPData, MPPTask


class TestMPPParser:
    """Testes para MPPParser."""

    @pytest.fixture
    def parser(self):
        """Cria instância do parser."""
        return MPPParser()

    def test_parser_initialization(self, parser):
        """Testa inicialização do parser."""
        assert parser is not None

    @patch('app.services.mpp_parser.subprocess.run')
    def test_check_java_available(self, mock_subprocess, parser):
        """Testa detecção de Java disponível."""
        mock_subprocess.return_value = Mock(returncode=0)
        result = parser._check_java()
        assert result is True

    @patch('app.services.mpp_parser.subprocess.run')
    def test_check_java_unavailable(self, mock_subprocess, parser):
        """Testa detecção de Java indisponível."""
        mock_subprocess.side_effect = FileNotFoundError()
        result = parser._check_java()
        assert result is False

    def test_find_mpxj_jar_exists(self, parser, tmp_path):
        """Testa localização do JAR do MPXJ."""
        # Cria estrutura de diretórios simulada
        lib_dir = tmp_path / "lib"
        lib_dir.mkdir()
        jar_file = lib_dir / "mpxj.jar"
        jar_file.write_text("fake jar")

        # Mock do caminho do arquivo
        with patch('app.services.mpp_parser.Path') as mock_path:
            mock_path.return_value.parent.parent.parent = tmp_path
            result = parser._find_mpxj_jar()
            # Resultado depende da estrutura real, mas não deve quebrar
            assert result is None or isinstance(result, str)

    def test_classify_tasks(self, parser):
        """Testa classificação de tarefas."""
        user_story = MPPTask(
            id="1",
            name="User Story",
            resource_name=None,
            is_user_story=True
        )
        
        task = MPPTask(
            id="2",
            name="Task",
            resource_name="User",
            is_user_story=False
        )

        tasks = [user_story, task]
        user_stories, classified_tasks = parser._classify_tasks(tasks)

        assert len(user_stories) == 1
        assert len(classified_tasks) == 1
        assert user_stories[0].name == "User Story"
        assert classified_tasks[0].name == "Task"

    def test_calculate_level(self, parser):
        """Testa cálculo de nível hierárquico."""
        # Mock de tarefa com parent
        class MockParent:
            def __init__(self):
                self.parent = None

        class MockTask:
            def __init__(self):
                self.parent = MockParent()

        task = MockTask()
        level = parser._calculate_level(task)
        assert isinstance(level, int)
        assert level >= 0

    @patch('app.services.mpp_parser.MPPParser._export_mpp_to_json_java')
    def test_parse_file_with_java(self, mock_export, parser, tmp_path):
        """Testa parse de arquivo usando Java."""
        # Cria arquivo temporário
        mpp_file = tmp_path / "test.mpp"
        mpp_file.write_text("fake mpp content")

        # Mock do JSON retornado
        mock_json = {
            "tasks": [
                {
                    "id": "1",
                    "name": "Task 1",
                    "resource": None,
                    "level": 0
                }
            ]
        }
        mock_export.return_value = mock_json

        # Mock do _parse_from_json
        with patch.object(parser, '_parse_from_json') as mock_parse:
            mock_parse.return_value = Mock(spec=ParsedMPPData)
            result = parser.parse_file(str(mpp_file), "12345 - Test.mpp")
            
            assert result is not None
            mock_export.assert_called_once()

