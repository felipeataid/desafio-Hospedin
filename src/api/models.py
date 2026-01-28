from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class ChatRequest(BaseModel):
    message: str = Field(..., description="Mensagem enviada pelo usuário")
    session_id: Optional[str] = Field(
        None, 
        description="Identificador opcional da sessão para manter contexto"
    )

class ChatResponse(BaseModel):
    response: str = Field(..., description="Resposta final retornada ao cliente")
    sources: List[str] = Field(
        default=[], 
        description="Fontes utilizadas na geração da resposta"
    )
    tool_logs: List[str] = []
    metrics: Dict[str, Any] = Field(
        ..., 
        description="Informações de execução e custo da requisição"
    )
    cached: bool = Field(
        False, 
        description="Indica se a resposta foi retornada a partir do cache"
    )

class ReloadResponse(BaseModel):
    status: str
    files_indexed: int
    file_names: List[str]