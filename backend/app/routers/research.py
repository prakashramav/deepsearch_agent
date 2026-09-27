"""API router — research endpoints."""
from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import HTMLResponse, PlainTextResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Run, RunStatus, Source, Claim
from app.schemas import ResearchRequest, RunCreate, RunResponse
from app.tasks import execute_research_run
from app.export import generate_printable_html

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


@router.get("/{run_id}/claims")
async def get_run_claims(
    run_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Return the list of extracted factual claims for a given run."""
    result = await db.execute(select(Claim).where(Claim.run_id == run_id))
    claims = result.scalars().all()
    return [
        {
            "id": c.id,
            "run_id": c.run_id,
            "claim_text": c.claim_text,
            "supporting_quote": c.supporting_quote,
            "source_url": c.source_url,
            "sub_question": c.sub_question,
            "confidence": c.confidence,
            "verified": c.verified,
            "conflict_flag": c.conflict_flag,
            "created_at": c.created_at,
        }
        for c in claims
    ]


@router.get("/{run_id}/export/markdown")
async def export_run_markdown(
    run_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Download the research report as a raw Markdown file."""
    result = await db.execute(select(Run).where(Run.id == run_id))
    run = result.scalar_one_or_none()
    if run is None or not run.result:
        raise HTTPException(status_code=404, detail="Run not found or report not yet generated")

    return PlainTextResponse(
        content=run.result,
        media_type="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="deepresearch-report-{run_id[:8]}.md"'},
    )


@router.get("/{run_id}/export/html", response_class=HTMLResponse)
@router.get("/{run_id}/export/pdf", response_class=HTMLResponse)
async def export_run_printable(
    run_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Render executive-grade standalone HTML document styled for print-to-PDF.
    Accessing with ?print=true automatically triggers the browser print dialog.
    """
    result = await db.execute(select(Run).where(Run.id == run_id))
    run = result.scalar_one_or_none()
    if run is None or not run.result:
        raise HTTPException(status_code=404, detail="Run not found or report not yet generated")

    html = generate_printable_html(
        question=run.question,
        result_markdown=run.result,
        run_id=run.id,
        metadata=run.metadata_,
    )
    return HTMLResponse(content=html)


async def _fire_and_forget(run_id: str) -> None:
    """Wrapper so BackgroundTasks can schedule the coroutine."""
    await execute_research_run(run_id)
