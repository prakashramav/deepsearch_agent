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
from app.agents.supervisor import create_research_graph

logger = logging.getLogger(__name__)


async def execute_research_run(run_id: str) -> None:
    """
    Entry point called as an asyncio background task.
    Drives the research pipeline via the LangGraph Supervisor StateGraph
    with checkpointing and dynamic retry/refinement loops.
    """
    logger.info("Starting research run %s via LangGraph Supervisor", run_id)

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Run).where(Run.id == run_id))
        run = result.scalar_one_or_none()
        if run is None:
            logger.error("Run %s not found", run_id)
            return
        question = run.question

    async def _on_status_change(r_id: str, status: RunStatus, state: dict[str, Any]) -> None:
        """Checkpoint status and plan artifacts to DB as graph transitions."""
        async with AsyncSessionLocal() as db:
            updates: dict[str, Any] = {"status": status}
            if "plan" in state and state["plan"]:
                updates["plan"] = state["plan"]
            await db.execute(update(Run).where(Run.id == r_id).values(**updates))
            await db.commit()

    graph = create_research_graph(status_callback=_on_status_change)

    try:
        final_state: dict[str, Any] = await graph.ainvoke(
            {
                "run_id": run_id,
                "question": question,
                "retry_counts": {"research": 0, "writer": 0},
                "supervisor_notes": [],
            }
        )

        sources = final_state.get("sources", [])
        claims = final_state.get("claims", [])
        plan = final_state.get("plan", {})
        final_report = final_state.get("final_report", "")
        citation_meta = final_state.get("citation_meta", {})
        supervisor_notes = final_state.get("supervisor_notes", [])

        # Persist sources, claims, and final report with metadata
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
                        sub_question=s.get("sub_question"),
                    )
                )

            # Save claims
            for c in claims:
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

            verified_count = sum(1 for c in claims if c.get("verified"))
            conflict_count = sum(1 for c in claims if c.get("conflict_flag"))

            await db.execute(
                update(Run)
                .where(Run.id == run_id)
                .values(
                    status=RunStatus.COMPLETE,
                    result=final_report,
                    metadata_={
                        "source_count": len(sources),
                        "sub_questions_count": len(plan.get("sub_questions", [])),
                        "claim_count": len(claims),
                        "verified_count": verified_count,
                        "conflict_count": conflict_count,
                        "citations_found": citation_meta.get("total_citations_found", 0),
                        "unique_sources_cited": citation_meta.get("unique_sources_cited", 0),
                        "citation_coverage_pct": citation_meta.get("citation_coverage_pct", 0),
                        "domain": plan.get("domain", "General Research"),
                        "supervisor_notes": supervisor_notes,
                    },
                )
            )
            await db.commit()

        logger.info(
            "LangGraph Supervisor research run %s COMPLETE: %d sources, %d claims (%d verified, %d conflicts)",
            run_id,
            len(sources),
            len(claims),
            verified_count,
            conflict_count,
        )

    except Exception as exc:
        logger.exception("Supervisor graph execution for run %s failed: %s", run_id, exc)
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
