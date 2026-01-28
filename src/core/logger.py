import logging
import sys
import structlog

def configure_logger():
    # Configura logging estruturado usando structlog.
    # Todos os logs da aplicação passam por aqui.
    
    # Processadores comuns, independentes do ambiente
    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]

    # Configuração principal do structlog
    structlog.configure(
        processors=shared_processors + [
            # Renderer em JSON para facilitar ingestão por ferramentas de observabilidade
            structlog.processors.JSONRenderer()
            # Para debug local, pode ser trocado por ConsoleRenderer
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Integra logging padrão do Python com o structlog
    # Garante que logs de FastAPI/Uvicorn sigam o mesmo formato
    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            structlog.processors.JSONRenderer(),
        ],
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    
    root_logger = logging.getLogger()
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.INFO)

configure_logger()