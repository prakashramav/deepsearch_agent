"""FastAPI application factory."""
from __future__ import annotations

import logging

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
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
