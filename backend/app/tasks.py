"""
Background task runner for research runs.

Uses asyncio tasks (within FastAPI's event loop) in Phase 1.
Will be swapped for Celery/Redis workers in later phases.
"""
from __future__ import annotations

import asyncio
import logging

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models import Run, RunStatus, Source
from app.agents.phase1_chain import run_linear_chain

logger = logging.getLogger(__name__)


async def execute_research_run(run_id: str) -> None:
    """
    Entry point called as an asyncio background task.
    Drives the current active pipeline (Phase 1: linear chain).
    """
    logger.info("Starting research run %s", run_id)

    async with AsyncSessionLocal() as db:
        # Mark as researching
        await _set_status(db, run_id, RunStatus.RESEARCHING)

        # Fetch question
        result = await db.execute(select(Run).where(Run.id == run_id))
        run = result.scalar_one_or_none()
        if run is None:
            logger.error("Run %s not found", run_id)
            return

        question = run.question

    try:
        summary, sources = await run_linear_chain(question)

        # Persist sources + result
        async with AsyncSessionLocal() as db:
            # Save sources
            for s in sources:
                db.add(
                    Source(
                        run_id=run_id,
                        url=s["url"],
                        title=s.get("title"),
                        snippet=s.get("snippet"),
                        relevance_score=s.get("score"),
                    )
                )

            # Save result
            await db.execute(
                update(Run)
                .where(Run.id == run_id)
                .values(
                    status=RunStatus.COMPLETE,
                    result=summary,
                    metadata_={"source_count": len(sources)},
                )
            )
            await db.commit()

        logger.info("Run %s complete", run_id)

    except Exception as exc:
        logger.exception("Run %s failed: %s", run_id, exc)
        async with AsyncSessionLocal() as db:
            await db.execute(
                update(Run)
                .where(Run.id == run_id)
                .values(status=RunStatus.FAILED, error_message=str(exc))
            )
            await db.commit()


async def _set_status(db: AsyncSession, run_id: str, status: RunStatus) -> None:
    await db.execute(update(Run).where(Run.id == run_id).values(status=status))
    await db.commit()
