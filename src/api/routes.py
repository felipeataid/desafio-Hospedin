import time
import re
from fastapi import APIRouter, HTTPException, Depends, Security, status
from fastapi.security import APIKeyHeader
from src.api.models import ChatRequest, ChatResponse, ReloadResponse
from src.services.rag_engine import RAGEngine
from src.services.cache_service import CacheService
from src.services.agent import get_agent
from src.core.config import settings
import structlog
from functools import lru_cache

logger = structlog.get_logger()
router = APIRouter()

api_key_header = APIKeyHeader(name="x-api-token", auto_error=False)

async def verify_api_key(api_key: str = Security(api_key_header)):
    # Validação simples de token para acesso à API
    if api_key != settings.HOSPY_API_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de acesso inválido ou ausente"
        )
    return api_key

@lru_cache()
def get_rag_engine():
    # Instância única do motor de RAG
    return RAGEngine()

@lru_cache()
def get_cache_service():
    # Serviço de cache reutilizado entre requisições
    return CacheService()

@router.post(
    "/rag/reload",
    response_model=ReloadResponse,
    dependencies=[Depends(verify_api_key)]
)
async def reload_knowledge_base(
    rag_engine: RAGEngine = Depends(get_rag_engine)
):
    try:
        result = rag_engine.load_documents()
        return ReloadResponse(
            status=result["status"],
            files_indexed=result.get("files_indexed", 0),
            file_names=result.get("file_names", [])
        )
    except Exception as e:
        logger.error(f"Erro no reload: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post(
    "/chat",
    response_model=ChatResponse,
    dependencies=[Depends(verify_api_key)]
)
async def chat_endpoint(
    request: ChatRequest,
    cache_service: CacheService = Depends(get_cache_service)
):
    start_time = time.time()
    
    # Consulta cache antes de executar o agente
    cached_response = cache_service.check_cache(request.message)
    if cached_response:
        duration = time.time() - start_time
        return ChatResponse(
            response=cached_response,
            sources=["Cache"],
            tool_logs=[],
            metrics={
                "latency_seconds": round(duration, 4),
                "total_tokens": 0,
                "estimated_cost_usd": 0.0
            },
            cached=True
        )

    try:
        agent = get_agent(session_id=request.session_id)
        
        # Execução do agente pode retornar texto com logs internos
        agent_response = agent.run(request.message, stream=False)
        raw_text = agent_response.content
        
        # Extrai logs técnicos gerados durante a execução
        tool_logs = re.findall(r"(?:- )?Running:.*", raw_text)
        
        # Remove logs do texto exibido ao cliente
        clean_text = re.sub(
            r"(?:- )?Running:.*\n?", 
            "", 
            raw_text
        ).strip()

        # Cálculo simples de métricas de uso
        input_tokens = getattr(
            agent_response.metrics,
            'input_tokens',
            len(request.message) // 4
        )
        output_tokens = getattr(
            agent_response.metrics,
            'output_tokens',
            len(raw_text) // 4
        )
        total_tokens = input_tokens + output_tokens
        estimated_cost = (
            input_tokens * 0.000000075 +
            output_tokens * 0.0000003
        )

        # Cacheia apenas a resposta final, sem logs
        cache_service.save_to_cache(request.message, clean_text)

        duration = time.time() - start_time

        sources = []
        if hasattr(agent_response, 'sources') and agent_response.sources:
            sources = [s.name for s in agent_response.sources]

        return ChatResponse(
            response=clean_text,
            sources=sources,
            tool_logs=tool_logs,
            metrics={
                "latency_seconds": round(duration, 4),
                "total_tokens": total_tokens,
                "estimated_cost_usd": round(estimated_cost, 8)
            },
            cached=False
        )

    except Exception as e:
        logger.error(f"Erro no chat: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
