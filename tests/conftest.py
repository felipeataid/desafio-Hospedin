import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock
import sys
import os

# Garante que o projeto esteja acessível no PATH durante os testes
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.main import app
from src.services.rag_engine import RAGEngine
from src.services.cache_service import CacheService
# Dependências que serão sobrescritas nos testes
from src.api.routes import get_rag_engine, get_cache_service

# Fixture: mock do motor de RAG
@pytest.fixture
def mock_rag_engine():
    mock = MagicMock(spec=RAGEngine)
    mock.load_documents.return_value = {
        "status": "success", 
        "files_indexed": 5, 
        "file_names": ["teste.pdf"]
    }
    return mock

# Fixture: mock do serviço de cache
@pytest.fixture
def mock_cache_service():
    mock = MagicMock(spec=CacheService)
    # Por padrão, simula cache vazio (cache miss)
    mock.check_cache.return_value = None
    return mock

# Fixture: mock do agente conversacional
@pytest.fixture
def mock_agent(mocker):
    mock_agent_instance = MagicMock()
    mock_agent_instance.run.return_value.content = "Resposta simulada da IA"
    mock_agent_instance.run.return_value.metrics.input_tokens = 10
    mock_agent_instance.run.return_value.metrics.output_tokens = 5
    
    # O get_agent é chamado diretamente na rota, então usamos patch
    mocker.patch(
        "src.api.routes.get_agent",
        return_value=mock_agent_instance
    )
    return mock_agent_instance

# Fixture principal: cliente de teste com dependências sobrescritas
@pytest.fixture
def client(mock_rag_engine, mock_cache_service):
    app.dependency_overrides[get_rag_engine] = lambda: mock_rag_engine
    app.dependency_overrides[get_cache_service] = lambda: mock_cache_service

    headers = {"x-api-token": "segredo-do-hotel-123"}
    
    with TestClient(app, headers=headers) as c:
        yield c
    
    # Limpa overrides após cada teste
    app.dependency_overrides = {}