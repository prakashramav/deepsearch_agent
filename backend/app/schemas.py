"""Pydantic schemas for API request/response shapes."""
from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, Field

from app.models import RunStatus


# ── Request bodies ────────────────────────────────────────────────────────────

class ResearchRequest(BaseModel):
    question: str = Field(..., min_length=10, max_length=2000, description="The research question")


# ── Response shapes ───────────────────────────────────────────────────────────

class RunCreate(BaseModel):
    run_id: str
    status: RunStatus
    message: str = "Research started"


class RunResponse(BaseModel):
    run_id: str
    question: str
    status: RunStatus
    plan: Optional[Any] = None
    result: Optional[str] = None
    error_message: Optional[str] = None
    metadata_: Optional[dict] = Field(None, alias="metadata")
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True, "populate_by_name": True}


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str = "0.1.0"
    environment: str
