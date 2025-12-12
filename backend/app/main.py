"""Aplicação principal FastAPI com configuração profissional."""
import logging
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import settings
from app.routers import upload, workitems, projects, convert

# Configuração de logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL, logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gerencia o ciclo de vida da aplicação."""
    # Startup
    logger.info("Iniciando aplicação MPP to Azure DevOps Converter API")
    logger.info(f"Versão: 2.0.0")
    logger.info(f"Ambiente: {settings.AZURE_DEVOPS_ORG}")
    yield
    # Shutdown
    logger.info("Encerrando aplicação")


app = FastAPI(
    title="MPP to Azure DevOps Converter API",
    description="""
    API para conversão de arquivos .mpp (Microsoft Project) em User Stories e Tasks no Azure DevOps.
    
    **Funcionalidades principais:**
    - Upload e parse de arquivos .mpp
    - Conversão automática em User Stories e Tasks
    - Sincronização bidirecional (.mpp ↔ Azure DevOps)
    - Validação e prevenção de duplicatas
    - Registro detalhado de todas as operações
    
    **Endpoints principais:**
    - `/api/v1/upload/` - Upload de arquivos .mpp
    - `/api/v1/convert/` - Conversão para Azure DevOps
    - `/api/v1/workitems/` - Consulta de Work Items
    - `/api/v1/projects/` - Lista de Features/Projetos
    
    **Documentação completa:** Acesse `/docs` para ver todos os endpoints e exemplos.
    """,
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Routers
app.include_router(upload.router, prefix=settings.API_V1_PREFIX, tags=["Upload"])
app.include_router(workitems.router, prefix=settings.API_V1_PREFIX, tags=["Work Items"])
app.include_router(projects.router, prefix=settings.API_V1_PREFIX, tags=["Projects"])
app.include_router(convert.router, prefix=settings.API_V1_PREFIX, tags=["Convert"])


@app.get("/", response_model=Dict[str, Any])
async def root() -> Dict[str, Any]:
    """
    Endpoint raiz da API.
    
    Returns:
        Informações básicas da API incluindo versão e link para documentação
    """
    return {
        "message": "MPP to Azure DevOps Converter API",
        "version": "2.0.0",
        "docs": "/docs",
        "description": "API para conversão de arquivos .mpp em User Stories e Tasks no Azure DevOps",
        "status": "operational"
    }


@app.get("/health", response_model=Dict[str, str])
async def health_check() -> Dict[str, str]:
    """
    Health check endpoint para monitoramento.
    
    Returns:
        Status da aplicação
    """
    return {"status": "healthy"}


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError
) -> JSONResponse:
    """Handler para erros de validação."""
    logger.warning(f"Erro de validação em {request.url}: {exc.errors()}")
    return JSONResponse(
        status_code=422,
        content={
            "detail": "Erro de validação",
            "errors": exc.errors()
        }
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(
    request: Request,
    exc: StarletteHTTPException
) -> JSONResponse:
    """Handler para exceções HTTP."""
    logger.error(f"Erro HTTP {exc.status_code} em {request.url}: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )


@app.exception_handler(Exception)
async def global_exception_handler(
    request: Request,
    exc: Exception
) -> JSONResponse:
    """Handler global de exceções não tratadas."""
    logger.exception(f"Erro não tratado em {request.url}: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Erro interno do servidor",
            "message": "Ocorreu um erro inesperado. Por favor, tente novamente."
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level=settings.LOG_LEVEL.lower()
    )
