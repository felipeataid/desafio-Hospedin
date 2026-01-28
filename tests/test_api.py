def test_health_check(client):
    """Verifica se a API está respondendo corretamente."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"status": "online", "service": "Hospy AI"}

def test_rag_reload(client, mock_rag_engine):
    """Valida o endpoint de recarga da base de conhecimento."""
    response = client.post("/rag/reload")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["files_indexed"] == 5

    # Garante que a indexação foi acionada
    mock_rag_engine.load_documents.assert_called_once()

def test_chat_no_cache(client, mock_cache_service, mock_agent):
    """
    Cenário: cache vazio.
    A requisição deve acionar o agente e salvar a resposta no cache.
    """
    mock_cache_service.check_cache.return_value = None

    payload = {"message": "Como funciona o checkin?"}
    response = client.post("/chat", json=payload)

    assert response.status_code == 200
    data = response.json()
    
    assert data["response"] == "Resposta simulada da IA"
    assert data["cached"] is False
    assert data["metrics"]["total_tokens"] > 0

    # Confirma que a resposta foi persistida no cache
    mock_cache_service.save_to_cache.assert_called_once()

def test_chat_with_cache(client, mock_cache_service, mock_agent):
    """
    Cenário: resposta já disponível em cache.
    O agente não deve ser executado.
    """
    mock_cache_service.check_cache.return_value = "Resposta antiga do cache"

    payload = {"message": "Como funciona o checkin?"}
    response = client.post("/chat", json=payload)

    assert response.status_code == 200
    data = response.json()

    assert data["response"] == "Resposta antiga do cache"
    assert data["cached"] is True
    assert data["metrics"]["estimated_cost_usd"] == 0.0

    # Garante que o agente não foi chamado
    mock_agent.run.assert_not_called()
