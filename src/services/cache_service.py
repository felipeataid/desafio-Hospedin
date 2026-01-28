import time
from datetime import datetime
from qdrant_client import QdrantClient, models
from agno.embedder.google import GeminiEmbedder
from src.core.config import settings
import structlog

logger = structlog.get_logger()

class CacheService:
    def __init__(self):
        self.client = QdrantClient(url=settings.QDRANT_URL)
        self.collection_name = "hospy_cache"
        
        # Similaridade mínima para considerar reutilização do cache
        self.threshold = 0.95 
        
        # Tempo máximo de validade do cache (3 dias)
        self.ttl_seconds = 259200 
        
        self.embedder = GeminiEmbedder(
            api_key=settings.GOOGLE_API_KEY,
            model=settings.EMBEDDING_MODEL 
        )

        self._ensure_collection()
    
    def _ensure_collection(self):
        if not self.client.collection_exists(self.collection_name):
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=models.VectorParams(
                    size=768,
                    distance=models.Distance.COSINE
                )
            )

    def check_cache(self, query: str) -> str | None:
        try:
            query_vector = self.embedder.get_embedding(query)
            
            # Timestamp mínimo aceito para respostas ainda válidas
            cutoff_time = time.time() - self.ttl_seconds

            search_result = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                limit=1,
                query_filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="timestamp",
                            range=models.Range(gte=cutoff_time)
                        )
                    ]
                )
            )
            
            if search_result and search_result[0].score >= self.threshold:
                logger.info(
                    f"Cache hit | score={search_result[0].score:.4f}"
                )
                return search_result[0].payload["response"]
            
            return None
        except Exception as e:
            logger.error(f"Erro ao consultar cache: {e}")
            return None

    def save_to_cache(self, query: str, response: str):
        try:
            query_vector = self.embedder.get_embedding(query)
            
            # ID determinístico para evitar duplicação de perguntas idênticas
            import hashlib
            point_id = hashlib.md5(query.encode()).hexdigest()

            self.client.upsert(
                collection_name=self.collection_name,
                points=[
                    models.PointStruct(
                        id=point_id,
                        vector=query_vector,
                        payload={
                            "query": query, 
                            "response": response,
                            "timestamp": time.time()
                        }
                    )
                ]
            )
        except Exception as e:
            logger.error(f"Erro ao salvar no cache: {e}")