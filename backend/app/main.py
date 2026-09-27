"""FastAPI application factory."""
from __future__ import annotations

import asyncio
import logging
import sys

# psycopg on Windows requires SelectorEventLoop for async operations
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import init_db
from app.routers.research import router as research_router
from app.schemas import HealthResponse

logging.basicConfig(
    level=get_settings().log_level,
    format="%(asctime)s  %(name)s  %(levelname)s  %(message)s",
)

logger = logging.getLogger(__name__)
settings = get_settings()

app = FastAPI(
    title="DeepResearch Agent API",
    description=(
        "Multi-agent research system — takes a question, runs parallel web research, "
        "fact-checks claims, and produces a cited Markdown report."
    ),
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS ─────────────────────────────────────────────────────────────────────
origins = settings.cors_origins_list
allow_all = "*" in origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=r"^https?://.*" if allow_all else None,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Root endpoint ─────────────────────────────────────────────────────────────
@app.get("/", tags=["root"])
async def root() -> dict[str, str]:
    return {
        "status": "online",
        "message": "DeepResearch Agent API is running",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/health",
        "api": "/api/v1/research",
    }


# ── Lifecycle ─────────────────────────────────────────────────────────────────
@app.on_event("startup")
async def on_startup() -> None:
    logger.info("Initialising database …")
    await init_db()
    logger.info("DeepResearch API ready 🚀")


# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(research_router, prefix="/api/v1")


# ── Health check ──────────────────────────────────────────────────────────────
@app.get("/health", response_model=HealthResponse, tags=["health"])
async def health() -> HealthResponse:
    return HealthResponse(environment=settings.environment)
