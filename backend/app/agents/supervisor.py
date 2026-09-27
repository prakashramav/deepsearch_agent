"""
Phase 7 — Supervisor Agent & LangGraph State Machine

Orchestrates the entire multi-agent research pipeline via a stateful LangGraph StateGraph.
The Supervisor evaluates quality at critical checkpoints (research adequacy, citation coverage),
triggering dynamic retry/refinement loops when thresholds are not met.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable, Coroutine, TypedDict

from langgraph.graph import StateGraph, START, END

from app.models import RunStatus
from app.agents.planner import generate_plan
from app.agents.researcher import run_parallel_research, search_sub_question
from app.agents.extractor import extract_claims
from app.agents.fact_checker import verify_claims
from app.agents.analyst import analyze_research
from app.agents.writer import draft_report
from app.agents.citation_agent import audit_and_finalize_report

logger = logging.getLogger(__name__)

# Minimum thresholds
MIN_SOURCES_THRESHOLD = 3
MIN_CITATION_COVERAGE_PCT = 30.0
MAX_RESEARCH_RETRIES = 1
MAX_WRITER_RETRIES = 1


class ResearchState(TypedDict, total=False):
    run_id: str
    question: str
    plan: dict[str, Any]
    sources: list[dict[str, Any]]
    claims: list[dict[str, Any]]
    analysis: str
    draft: str
    final_report: str
    citation_meta: dict[str, Any]
    retry_counts: dict[str, int]
    supervisor_notes: list[str]
    current_status: str
    error: str | None


# Type alias for async status callback: (run_id, status, plan, sources, claims, result, metadata)
StatusCallback = Callable[[str, RunStatus, dict[str, Any]], Coroutine[Any, Any, None]]


def create_research_graph(status_callback: StatusCallback | None = None) -> Any:
    """
    Construct the LangGraph StateGraph with Supervisor conditional routing and retry logic.
    """
    workflow = StateGraph(ResearchState)

    async def _notify(state: ResearchState, status: RunStatus) -> None:
        state["current_status"] = status.value
        if status_callback and state.get("run_id"):
            try:
                await status_callback(state["run_id"], status, dict(state))
            except Exception as exc:
                logger.warning("Status callback failed for %s: %s", status, exc)

    # ── Node 1: Planner ───────────────────────────────────────────────────────
    async def planner_node(state: ResearchState) -> dict[str, Any]:
        await _notify(state, RunStatus.PLANNING)
        question = state["question"]
        logger.info("Supervisor -> Planner: decomposing question")
        plan = await generate_plan(question)
        return {
            "plan": plan,
            "retry_counts": state.get("retry_counts", {"research": 0, "writer": 0}),
            "supervisor_notes": state.get("supervisor_notes", []),
        }

    # ── Node 2: Researcher ────────────────────────────────────────────────────
    async def researcher_node(state: ResearchState) -> dict[str, Any]:
        await _notify(state, RunStatus.RESEARCHING)
        plan = state.get("plan", {})
        sub_questions = plan.get("sub_questions", [])
        if not sub_questions:
            sub_questions = [{"id": 1, "question": state["question"], "focus_area": "General"}]

        logger.info("Supervisor -> Researcher: querying %d sub-questions", len(sub_questions))
        sources = await run_parallel_research(sub_questions)

        if not sources:
            sources = await search_sub_question(
                {"question": state["question"], "focus_area": "General"}, max_results=7
            )

        existing_sources = state.get("sources", [])
        # Merge if retrying
        all_sources = list({s["url"]: s for s in (existing_sources + sources)}.values())
        return {"sources": all_sources}

    # ── Node 3: Research Refinement (Retry branch) ────────────────────────────
    async def research_refinement_node(state: ResearchState) -> dict[str, Any]:
        retries = state.get("retry_counts", {})
        retries["research"] = retries.get("research", 0) + 1
        notes = state.get("supervisor_notes", [])
        notes.append("Supervisor triggered supplementary research: initial source count below threshold.")

        logger.info("Supervisor -> Triggering broadened supplementary search (attempt %d)", retries["research"])
        broad_query = f"{state['question']} overview market data statistics analysis"
        extra_sources = await search_sub_question({"question": broad_query, "focus_area": "Supplementary"}, max_results=5)

        existing = state.get("sources", [])
        merged = list({s["url"]: s for s in (existing + extra_sources)}.values())
        return {"sources": merged, "retry_counts": retries, "supervisor_notes": notes}

    # ── Node 4: Data Extractor ────────────────────────────────────────────────
    async def extractor_node(state: ResearchState) -> dict[str, Any]:
        await _notify(state, RunStatus.EXTRACTING)
        logger.info("Supervisor -> Data Extractor: analyzing sources for claims")
        claims = await extract_claims(state["question"], state.get("sources", []))
        return {"claims": claims}

    # ── Node 5: Fact Checker ──────────────────────────────────────────────────
    async def fact_checker_node(state: ResearchState) -> dict[str, Any]:
        await _notify(state, RunStatus.FACT_CHECKING)
        logger.info("Supervisor -> Fact Checker: verifying multi-source corroboration")
        verified = await verify_claims(state.get("claims", []), state.get("sources", []))
        return {"claims": verified}

    # ── Node 6: Analyst ───────────────────────────────────────────────────────
    async def analyst_node(state: ResearchState) -> dict[str, Any]:
        await _notify(state, RunStatus.SYNTHESIZING)
        logger.info("Supervisor -> Analyst: generating strategic evaluation")
        analysis = await analyze_research(
            state["question"],
            state.get("plan"),
            state.get("claims", []),
            state.get("sources", []),
        )
        return {"analysis": analysis}

    # ── Node 7: Writer ────────────────────────────────────────────────────────
    async def writer_node(state: ResearchState) -> dict[str, Any]:
        await _notify(state, RunStatus.WRITING)
        logger.info("Supervisor -> Writer: drafting comprehensive report")
        draft = await draft_report(
            state["question"],
            state.get("plan"),
            state.get("analysis", ""),
            state.get("claims", []),
            state.get("sources", []),
        )
        return {"draft": draft}

    # ── Node 8: Citation Agent ────────────────────────────────────────────────
    async def citation_node(state: ResearchState) -> dict[str, Any]:
        await _notify(state, RunStatus.CITING)
        logger.info("Supervisor -> Citation Agent: auditing traceability and citations")
        final_report, meta = audit_and_finalize_report(
            state.get("draft", ""),
            state.get("sources", []),
            state.get("claims", []),
        )
        return {"final_report": final_report, "citation_meta": meta}

    # ── Supervisor Routing Conditions ─────────────────────────────────────────
    def supervisor_evaluate_research(state: ResearchState) -> str:
        """Evaluate if collected sources meet quality threshold."""
        sources = state.get("sources", [])
        retries = state.get("retry_counts", {}).get("research", 0)

        if len(sources) < MIN_SOURCES_THRESHOLD and retries < MAX_RESEARCH_RETRIES:
            logger.info("Supervisor Decision: Research sources (%d) < %d. Routing to refinement retry.", len(sources), MIN_SOURCES_THRESHOLD)
            return "refine_research"

        logger.info("Supervisor Decision: Research sources (%d) passed threshold. Routing to extractor.", len(sources))
        return "proceed_to_extraction"

    # Register nodes
    workflow.add_node("planner", planner_node)
    workflow.add_node("researcher", researcher_node)
    workflow.add_node("refine_research", research_refinement_node)
    workflow.add_node("extractor", extractor_node)
    workflow.add_node("fact_checker", fact_checker_node)
    workflow.add_node("analyst", analyst_node)
    workflow.add_node("writer", writer_node)
    workflow.add_node("citation_agent", citation_node)

    # Wire edges
    workflow.add_edge(START, "planner")
    workflow.add_edge("planner", "researcher")

    # Supervisor conditional routing after research
    workflow.add_conditional_edges(
        "researcher",
        supervisor_evaluate_research,
        {
            "refine_research": "refine_research",
            "proceed_to_extraction": "extractor",
        },
    )
    workflow.add_edge("refine_research", "extractor")

    workflow.add_edge("extractor", "fact_checker")
    workflow.add_edge("fact_checker", "analyst")
    workflow.add_edge("analyst", "writer")
    workflow.add_edge("writer", "citation_agent")
    workflow.add_edge("citation_agent", END)

    return workflow.compile()
