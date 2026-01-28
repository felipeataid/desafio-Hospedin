import os
from dotenv import load_dotenv

_ = load_dotenv()

class Settings:
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
    QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")

    HOSPY_API_TOKEN = os.getenv("HOSPY_API_TOKEN", "segredo-do-hotel-123")

    # Coleção principal usada para indexação dos documentos do hotel
    # Nome fixo para evitar conflitos com versões antigas
    QDRANT_COLLECTION: str = "hospy_knowledge_final"
    
    # Coleção auxiliar para cache de perguntas recentes
    CACHE_COLLECTION = os.getenv("CACHE_COLLECTION", "hospy_cache")
    
    # Configuração dos modelos utilizados pela IA
    EMBEDDING_MODEL: str = "gemini-embedding-001"
    LLM_MODEL = "gemini-2.5-flash"
    
    # Caminho padrão dos arquivos de dados (container)
    DATA_PATH = "/app/data"

settings = Settings()