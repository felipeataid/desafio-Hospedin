import os
from typing import List, Dict, Any
from qdrant_client import QdrantClient, models
from agno.embedder.google import GeminiEmbedder
from agno.document.reader.pdf_reader import PDFReader
from fastembed import SparseTextEmbedding
from src.core.config import settings
import structlog

logger = structlog.get_logger()

class RAGEngine:
    def __init__(self):
        self.client = QdrantClient(url=settings.QDRANT_URL)
        self.collection_name = settings.QDRANT_COLLECTION
        
        # Embedder denso para similaridade semântica
        self.dense_embedder = GeminiEmbedder(
            api_key=settings.GOOGLE_API_KEY,
            model=settings.EMBEDDING_MODEL 
        )
        
        # Embedder esparso para correspondência lexical (BM25)
        self.sparse_embedder = SparseTextEmbedding(model_name="Qdrant/bm25")
        self._ensure_collection()

    def _ensure_collection(self):
        if not self.client.collection_exists(self.collection_name):
            logger.info(f"Criando coleção híbrida: {self.collection_name}")
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=models.VectorParams(
                    size=768,
                    distance=models.Distance.COSINE
                ),
                sparse_vectors_config={
                    "bm25": models.SparseVectorParams(
                        index=models.SparseIndexParams(
                            on_disk=False,
                        )
                    )
                }
            )

    def load_documents(self, data_dir: str = "data/") -> Dict[str, Any]:
        if not os.path.exists(data_dir):
            return {"status": "error", "message": "Diretório não encontrado"}

        pdf_files = [f for f in os.listdir(data_dir) if f.endswith('.pdf')]
        total_chunks = 0
        
        for pdf in pdf_files:
            path = os.path.join(data_dir, pdf)
            logger.info(f"Processando documento: {pdf}")
            
            reader = PDFReader(chunk=True)
            documents = reader.read(path)
            
            # Log básico para validação do conteúdo extraído
            if documents:
                preview = documents[0].content[:100].replace('\n', ' ')
                logger.info(f"[Leitura] {pdf} | Chunks: {len(documents)} | Preview: '{preview}...'")
                if not documents[0].content.strip():
                    logger.warning(f"O arquivo {pdf} não possui texto extraível.")

            points = []
            for i, doc in enumerate(documents):
                content = doc.content
                if not content.strip(): continue  # ignora chunks vazios
                
                dense_vector = self.dense_embedder.get_embedding(content)
                sparse_vector = list(self.sparse_embedder.embed([content]))[0]

                points.append(models.PointStruct(
                    id=i + total_chunks,  # identificador sequencial simples
                    vector={
                        "": dense_vector,
                        "bm25": models.SparseVector(
                            indices=sparse_vector.indices.tolist(),
                            values=sparse_vector.values.tolist()
                        )
                    },
                    payload={
                        "content": content,
                        "source": pdf,
                        "page": doc.meta_data.get("page", 0)
                    }
                ))

            if points:
                self.client.upsert(
                    collection_name=self.collection_name,
                    points=points
                )
                total_chunks += len(points)

        return {
            "status": "success", 
            "files_indexed": len(pdf_files), 
            "chunks": total_chunks,
            "file_names": pdf_files
        }

    def search(self, query: str, limit: int = 5) -> str:
        logger.info(f"[Busca] Query recebida: '{query}'")
        
        dense_query = self.dense_embedder.get_embedding(query)
        sparse_query = list(self.sparse_embedder.embed([query]))[0]

        results = self.client.query_points(
            collection_name=self.collection_name,
            prefetch=[
                models.Prefetch(
                    query=dense_query,
                    limit=limit * 2,
                ),
                models.Prefetch(
                    query=models.SparseVector(
                        indices=sparse_query.indices.tolist(),
                        values=sparse_query.values.tolist()
                    ),
                    using="bm25",
                    limit=limit * 2,
                ),
            ],
            
            # Fusão de rankings entre busca semântica e lexical
            query=models.FusionQuery(fusion=models.Fusion.RRF),
            limit=limit
        )

        logger.info(f"[Busca] Documentos retornados: {len(results.points)}")
        context = ""
        for hit in results.points:
            score = hit.score if hasattr(hit, 'score') else 'N/A'
            logger.info(f"Resultado selecionado | score={score} | fonte={hit.payload.get('source')}")
            context += f"---\nFonte: {hit.payload.get('source')}\nConteúdo: {hit.payload.get('content')}\n"
        
        return context if context else "Nenhuma informação relevante encontrada nos documentos."
