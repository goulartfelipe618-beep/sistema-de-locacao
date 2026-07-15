"""Ponto de entrada da aplicação FastAPI.

Monta as duas superfícies que compartilham a mesma camada de negócio:
    * **Web (SSR)**: painel administrativo em Jinja2/HTMX/Alpine (respostas HTML).
    * **API REST (JSON)**: contrato versionado (``/api/v1``) para futuros consumidores.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

# Garante que todos os modelos sejam registrados na metadata.
import app.core.registry  # noqa: F401
from app import __version__
from app.api.v1.router import api_router
from app.core.cache import close_redis
from app.core.config import settings
from app.core.csrf import CSRFMiddleware
from app.core.database import dispose_engine
from app.core.exceptions import AppError, AuthenticationError
from app.core.logging import configure_logging, get_logger
from app.core.middleware import RequestContextMiddleware
from app.core.templating import render
from app.web.router import web_router

logger = get_logger(__name__)

_STATIC_DIR = Path(__file__).resolve().parent / "web" / "static"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Gerencia o ciclo de vida da aplicação (startup/shutdown)."""
    configure_logging()
    logger.info("Aplicação iniciada", extra={"version": __version__, "env": settings.environment})
    try:
        yield
    finally:
        await dispose_engine()
        await close_redis()
        logger.info("Aplicação encerrada com liberação de recursos.")


def _is_api_request(request: Request) -> bool:
    return request.url.path.startswith("/api")


def create_app() -> FastAPI:
    """Fábrica da aplicação (facilita testes e múltiplas instâncias)."""
    app = FastAPI(
        title=settings.app_name,
        version=__version__,
        description="ERP SaaS Multiempresa para Locadoras de Veículos — Sistema Administrativo.",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )

    # ---------------------------------------------------------- Middlewares
    # Ordem de registro (o último adicionado é o mais externo):
    #   CORS -> Session -> CSRF -> RequestContext -> app
    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(CSRFMiddleware)
    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.secret_key,
        session_cookie=settings.session_cookie_name,
        max_age=settings.session_max_age_seconds,
        https_only=settings.session_https_only,
        same_site="lax",
    )
    if settings.cors_origins_list:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins_list,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    # -------------------------------------------------------------- Estáticos
    app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")

    @app.get("/favicon.ico", include_in_schema=False)
    async def favicon() -> RedirectResponse:
        """Browsers pedem /favicon.ico por padrão."""
        return RedirectResponse(url="/static/favicon.svg", status_code=302)

    # ---------------------------------------------------------------- Rotas
    app.include_router(api_router)
    app.include_router(web_router)

    _register_exception_handlers(app)
    return app


def _register_exception_handlers(app: FastAPI) -> None:
    """Registra handlers que traduzem exceções para JSON (API) ou HTML (Web)."""

    @app.exception_handler(AppError)
    async def _app_error_handler(request: Request, exc: AppError) -> Response:
        if _is_api_request(request):
            return JSONResponse(status_code=exc.status_code, content=exc.to_dict())
        if isinstance(exc, AuthenticationError):
            request.session["_flash"] = {"type": "danger", "message": exc.message}
            return RedirectResponse(url="/login", status_code=303)
        return render(
            request,
            "error.html",
            {
                "status_code": exc.status_code,
                "error_title": "Não foi possível concluir a operação",
                "error_message": exc.message,
            },
            status_code=exc.status_code,
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_handler(request: Request, exc: RequestValidationError) -> Response:
        if _is_api_request(request):
            return JSONResponse(
                status_code=422,
                content={"error": {"code": "validation_error", "message": "Dados inválidos.",
                                    "details": exc.errors()}},
            )
        return render(
            request,
            "error.html",
            {"status_code": 422, "error_title": "Dados inválidos",
             "error_message": "Verifique os campos e tente novamente."},
            status_code=422,
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http_handler(request: Request, exc: StarletteHTTPException) -> Response:
        if _is_api_request(request):
            return JSONResponse(
                status_code=exc.status_code,
                content={"error": {"code": "http_error", "message": str(exc.detail)}},
            )
        if exc.status_code == 401:
            return RedirectResponse(url="/login", status_code=303)
        titles = {403: "Acesso negado", 404: "Página não encontrada"}
        return render(
            request,
            "error.html",
            {
                "status_code": exc.status_code,
                "error_title": titles.get(exc.status_code, "Erro"),
                "error_message": str(exc.detail),
            },
            status_code=exc.status_code,
        )

    @app.exception_handler(Exception)
    async def _unhandled_handler(request: Request, exc: Exception) -> Response:
        logger.exception("Erro não tratado: %s", exc)
        if _is_api_request(request):
            return JSONResponse(
                status_code=500,
                content={
                    "error": {"code": "internal_error", "message": "Erro interno do servidor."}
                },
            )
        return render(
            request,
            "error.html",
            {"status_code": 500, "error_title": "Erro interno",
             "error_message": "Ocorreu um erro inesperado. Tente novamente."},
            status_code=500,
        )


app = create_app()
