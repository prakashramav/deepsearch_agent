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
from app.models import Run, RunStatus, Source, Claim
from app.agents.planner import generate_plan
from app.agents.researcher import run_parallel_research, search_sub_question
from app.agents.synthesizer import synthesize_report
from app.agents.extractor import extract_claims
from app.agents.fact_checker import verify_claims

logger = logging.getLogger(__name__)


async def execute_research_run(run_id: str) -> None:
    """
    Entry point called as an asyncio background task.
    Drives the research pipeline:
      Phase 2: Planner (decompose question -> sub-questions)
      Phase 3: Parallel Researcher (concurrent Tavily search across sub-questions)
      Phase 4: Data Extractor (extract verifiable claims table from sources)
      Phase 3/6: Synthesizer (compile findings into cited report)
    """
    logger.info("Starting research run %s", run_id)

    async with AsyncSessionLocal() as db:
        # Mark as planning
        await _set_status(db, run_id, RunStatus.PLANNING)

        # Fetch question
        result = await db.execute(select(Run).where(Run.id == run_id))
        run = result.scalar_one_or_none()
        if run is None:
            logger.error("Run %s not found", run_id)
            return

        question = run.question

    try:
        # Step 1: Planning (Phase 2)
        logger.info("Run %s: generating research plan", run_id)
        plan = await generate_plan(question)

        # Persist plan and transition to RESEARCHING
        async with AsyncSessionLocal() as db:
            await db.execute(
                update(Run)
                .where(Run.id == run_id)
                .values(
                    status=RunStatus.RESEARCHING,
                    plan=plan,
                )
            )
            await db.commit()

        # Step 2: Parallel Research (Phase 3)
        sub_questions = plan.get("sub_questions", [])
        if not sub_questions:
            sub_questions = [{"id": 1, "question": question, "focus_area": "General"}]

        logger.info(
            "Run %s: running parallel research across %d sub-questions",
            run_id,
            len(sub_questions),
        )
        sources = await run_parallel_research(sub_questions)

        # Fallback to direct search if sub-questions produced 0 sources
        if not sources:
            logger.info(
                "Run %s: parallel research yielded 0 sources, attempting direct search fallback",
                run_id,
            )
            sources = await search_sub_question(
                {"question": question, "focus_area": "General"}, max_results=7
            )

        # Persist sources and transition to EXTRACTING
        async with AsyncSessionLocal() as db:
            for s in sources:
                db.add(
                    Source(
                        run_id=run_id,
                        url=s["url"],
                        title=s.get("title"),
                        snippet=s.get("snippet"),
                        relevance_score=s.get("score"),
                        sub_question=s.get("sub_question"),
                    )
                )
            await _set_status(db, run_id, RunStatus.EXTRACTING)

        # Step 3: Data Extraction (Phase 4)
        logger.info("Run %s: extracting factual claims from sources", run_id)
        raw_claims = await extract_claims(question, sources)

        # Step 4: Fact Checking & Conflict Detection (Phase 5)
        logger.info("Run %s: fact-checking %d claims across sources", run_id, len(raw_claims))
        async with AsyncSessionLocal() as db:
            await _set_status(db, run_id, RunStatus.FACT_CHECKING)

        verified_claims = await verify_claims(raw_claims, sources)

        # Persist verified claims with verification and conflict flags
        async with AsyncSessionLocal() as db:
            for c in verified_claims:
                db.add(
                    Claim(
                        run_id=run_id,
                        sub_question=c.get("sub_question"),
                        claim_text=c["claim_text"],
                        supporting_quote=c.get("supporting_quote"),
                        source_url=c["source_url"],
                        confidence=c.get("confidence"),
                        verified=c.get("verified"),
                        conflict_flag=c.get("conflict_flag"),
                    )
                )
            await db.commit()

        # Step 5: Synthesis
        logger.info("Run %s: synthesizing report from %d sources", run_id, len(sources))
        summary = await synthesize_report(question, plan, sources)

        # Calculate counts
        verified_count = sum(1 for c in verified_claims if c.get("verified"))
        conflict_count = sum(1 for c in verified_claims if c.get("conflict_flag"))

        # Save result and finalize run
        async with AsyncSessionLocal() as db:
            await db.execute(
                update(Run)
                .where(Run.id == run_id)
                .values(
                    status=RunStatus.COMPLETE,
                    result=summary,
                    metadata_={
                        "source_count": len(sources),
                        "sub_questions_count": len(sub_questions),
                        "claim_count": len(verified_claims),
                        "verified_count": verified_count,
                        "conflict_count": conflict_count,
                        "domain": plan.get("domain", "General Research"),
                    },
                )
            )
            await db.commit()

        logger.info(
            "Run %s complete: %d sources, %d claims (%d verified, %d conflicts)",
            run_id,
            len(sources),
            len(verified_claims),
            verified_count,
            conflict_count,
        )

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
