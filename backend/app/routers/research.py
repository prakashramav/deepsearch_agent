"""API router — research endpoints."""
from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Run, RunStatus, Source
from app.schemas import ResearchRequest, RunCreate, RunResponse
from app.tasks import execute_research_run

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/research", tags=["research"])


@router.post("", response_model=RunCreate, status_code=202)
async def create_research_run(
    body: ResearchRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """
    Accept a research question, create a run record, and kick off the
    background pipeline.  Returns immediately with the run_id for polling.
    """
    run_id = str(uuid.uuid4())
    run = Run(id=run_id, question=body.question, status=RunStatus.PENDING)
    db.add(run)
    await db.flush()

    # Schedule background task (asyncio in Phase 1; Celery in later phases)
    background_tasks.add_task(_fire_and_forget, run_id)

    logger.info("Created run %s for question: %s", run_id, body.question[:60])
    return RunCreate(run_id=run_id, status=RunStatus.PENDING)


@router.get("/{run_id}", response_model=RunResponse)
async def get_research_run(
    run_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Poll the status of a research run.  Frontend calls this every N seconds
    until status == 'complete' or 'failed'.
    """
    result = await db.execute(select(Run).where(Run.id == run_id))
    run = result.scalar_one_or_none()
    if run is None:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")

    return RunResponse(
        run_id=run.id,
        question=run.question,
        status=run.status,
        plan=run.plan,
        result=run.result,
        error_message=run.error_message,
        metadata=run.metadata_,
        created_at=run.created_at,
        updated_at=run.updated_at,
    )


@router.get("/{run_id}/sources")
async def get_run_sources(
    run_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Return the list of sources discovered for a given run."""
    result = await db.execute(select(Source).where(Source.run_id == run_id))
    sources = result.scalars().all()
    return [
        {
            "id": s.id,
            "url": s.url,
            "title": s.title,
            "snippet": s.snippet,
            "relevance_score": s.relevance_score,
            "sub_question": s.sub_question,
            "fetched_at": s.fetched_at,
        }
        for s in sources
    ]


async def _fire_and_forget(run_id: str) -> None:
    """Wrapper so BackgroundTasks can schedule the coroutine."""
    await execute_research_run(run_id)
