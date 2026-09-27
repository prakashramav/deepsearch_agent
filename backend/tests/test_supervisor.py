"""
Phase 7 Supervisor Agent & LangGraph State Machine unit tests.

Tests StateGraph compilation, end-to-end execution, checkpointing callbacks,
and conditional retry routing.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.models import RunStatus
from app.agents.supervisor import (
    create_research_graph,
    MIN_SOURCES_THRESHOLD,
    ResearchState,
)

MOCK_PLAN = {
    "sub_questions": [
        {"id": 1, "question": "Sub-Q 1", "focus_area": "Focus 1"},
        {"id": 2, "question": "Sub-Q 2", "focus_area": "Focus 2"},
    ],
    "research_strategy": "Direct parallel query",
    "domain": "Test Domain",
}

MOCK_SOURCES = [
    {"url": f"https://example.com/source{i}", "title": f"Source {i}", "snippet": f"Data {i}", "score": 0.9}
    for i in range(1, 5)
]

MOCK_CLAIMS = [
    {"claim_text": "A valid factual claim with sufficient length", "source_url": "https://example.com/source1", "confidence": 0.95}
]


@pytest.mark.asyncio
async def test_supervisor_graph_end_to_end():
    """Supervisor LangGraph StateGraph executes all nodes through completion."""
    callbacks_received: list[RunStatus] = []

    async def mock_callback(run_id, status, state):
        callbacks_received.append(status)

    with (
        patch("app.agents.supervisor.generate_plan", AsyncMock(return_value=MOCK_PLAN)),
        patch("app.agents.supervisor.run_parallel_research", AsyncMock(return_value=MOCK_SOURCES)),
        patch("app.agents.supervisor.extract_claims", AsyncMock(return_value=MOCK_CLAIMS)),
        patch("app.agents.supervisor.verify_claims", AsyncMock(return_value=[{**MOCK_CLAIMS[0], "verified": True, "conflict_flag": False}])),
        patch("app.agents.supervisor.analyze_research", AsyncMock(return_value="Detailed strategic analysis.")),
        patch("app.agents.supervisor.draft_report", AsyncMock(return_value="# Final Report\n\nExecutive summary citing [1].")),
    ):
        graph = create_research_graph(status_callback=mock_callback)
        result: dict = await graph.ainvoke(
            {
                "run_id": "test-run-123",
                "question": "Analyze test topic",
            }
        )

    assert "final_report" in result
    assert "## 📚 References & Source Audit" in result["final_report"]
    assert len(result["sources"]) == 4
    assert len(result["claims"]) == 1

    # Verify callbacks were called across the lifecycle
    assert RunStatus.PLANNING in callbacks_received
    assert RunStatus.RESEARCHING in callbacks_received
    assert RunStatus.EXTRACTING in callbacks_received
    assert RunStatus.FACT_CHECKING in callbacks_received
    assert RunStatus.SYNTHESIZING in callbacks_received
    assert RunStatus.WRITING in callbacks_received
    assert RunStatus.CITING in callbacks_received


@pytest.mark.asyncio
async def test_supervisor_refines_research_when_sources_sparse():
    """Supervisor triggers refine_research branch when initial source yield is below threshold."""
    sparse_sources = [{"url": "https://example.com/only-one", "title": "Only One", "score": 0.8}]
    refinement_sources = [{"url": "https://example.com/extra-source", "title": "Extra Source", "score": 0.85}]

    with (
        patch("app.agents.supervisor.generate_plan", AsyncMock(return_value=MOCK_PLAN)),
        patch("app.agents.supervisor.run_parallel_research", AsyncMock(return_value=sparse_sources)),
        patch("app.agents.supervisor.search_sub_question", AsyncMock(return_value=refinement_sources)),
        patch("app.agents.supervisor.extract_claims", AsyncMock(return_value=MOCK_CLAIMS)),
        patch("app.agents.supervisor.verify_claims", AsyncMock(return_value=MOCK_CLAIMS)),
        patch("app.agents.supervisor.analyze_research", AsyncMock(return_value="Analysis")),
        patch("app.agents.supervisor.draft_report", AsyncMock(return_value="# Report [1]")),
    ):
        graph = create_research_graph()
        result: dict = await graph.ainvoke(
            {
                "run_id": "sparse-run",
                "question": "Very niche topic",
                "retry_counts": {"research": 0, "writer": 0},
            }
        )

    # Both initial and supplementary sources should be present
    assert len(result["sources"]) == 2
    assert result["retry_counts"]["research"] == 1
    assert any("supplementary" in note.lower() for note in result.get("supervisor_notes", []))
