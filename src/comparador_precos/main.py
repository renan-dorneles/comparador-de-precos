# ============================================================
# src/comparador_precos/main.py
# ============================================================
"""Ponto de entrada da aplicação FastAPI."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from comparador_precos.core.config import get_settings
from comparador_precos.core.database import close_db, init_db

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown da aplicação."""
    # Em produção as tabelas são criadas via `alembic upgrade head`
    await init_db()
    yield
    await close_db()


app = FastAPI(
    title=settings.app_name,
    description=(
        "API de comparação de preços com economia baseada em créditos, "
        "ingestão de NFC-e via QR Code e busca geolocalizada com PostGIS."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["system"])
async def health_check():
    """Health check da API."""
    return {"status": "ok", "service": settings.app_name, "version": "0.1.0"}


@app.get("/", tags=["system"])
async def root():
    """Raiz da API com links de documentação."""
    return {
        "message": "Comparador de Preços API",
        "docs": "/docs",
        "redoc": "/redoc",
        "openapi": "/openapi.json",
    }


# Rotas da API (Fases 0-5 do PLAN.md)
# Import tardio para evitar import circular (api.routes -> core.dependencies -> models)
from comparador_precos.api.routes import auth, credits  # noqa: E402

app.include_router(auth.router)
app.include_router(credits.router)
