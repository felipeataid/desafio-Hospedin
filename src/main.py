from fastapi import FastAPI
from contextlib import asynccontextmanager
import structlog
import src.core.logger
from src.api.routes import router
from src.services.rag_engine import RAGEngine

logger = structlog.get_logger()

# Lifecycle da aplicação (startup / shutdown)
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Executado no boot da API
    try:
        logger.info("Inicializando API e verificando base de conhecimento.")
        engine = RAGEngine()
        # Pode ser habilitado caso queira reindexar automaticamente no restart
        # engine.load_documents()
        logger.info("Motor RAG pronto para uso.")
    except Exception as e:
        logger.error(
            f"Falha ao inicializar o RAG no startup: {e}"
        )
    
    yield
    
    # Executado no encerramento da API
    logger.info("Encerrando API.")

app = FastAPI(
    title="Hospy Concierge AI",
    description="API de atendimento conversacional com RAG para hotelaria",
    version="1.0.0",
    lifespan=lifespan
)

# Rotas principais da aplicação
app.include_router(router)

@app.get("/")
def health_check():
    # Endpoint simples para verificação de status
    return {"status": "online", "service": "Hospy AI"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
