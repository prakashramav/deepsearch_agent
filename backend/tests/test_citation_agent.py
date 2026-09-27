"""
Phase 6 Citation Agent unit tests.

Tests inline citation auditing, reference synthesis, and coverage calculation.
"""
from app.agents.citation_agent import audit_and_finalize_report

MOCK_REPORT = (
    "# EV Market in India\n\n"
    "Tata Motors dominates passenger EVs with ~65% share [1].\n"
    "Meanwhile, Ola Electric leads in the two-wheeler category [2].\n"
    "Some sources suggest rapid battery cost drops [1, 2].\n"
)

MOCK_SOURCES = [
    {"url": "https://example.com/tata", "title": "Tata Motors Report", "score": 0.95},
    {"url": "https://example.com/ola", "title": "Ola Electric Overview", "score": 0.88},
    {"url": "https://example.com/uncited", "title": "Background Material", "score": 0.70},
]


def test_audit_and_finalize_report_citations():
    """Citation agent validates citations, appends References & Source Audit, and computes stats."""
    final_report, meta = audit_and_finalize_report(MOCK_REPORT, MOCK_SOURCES)

    assert "## 📚 References & Source Audit" in final_report
    assert "[1] **[Tata Motors Report](https://example.com/tata)**" in final_report
    assert "[2] **[Ola Electric Overview](https://example.com/ola)**" in final_report
    assert "✅ Cited" in final_report
    assert "🔍 Context Source" in final_report

    assert meta["total_citations_found"] >= 3
    assert meta["unique_sources_cited"] == 2
    assert meta["total_sources_available"] == 3
    assert meta["citation_coverage_pct"] == 66.7
    assert meta["audit_status"] == "passed"


def test_audit_and_finalize_report_empty_sources():
    """Citation agent handles empty sources gracefully."""
    final_report, meta = audit_and_finalize_report("Some report without sources", [])
    assert meta["audit_status"] == "no_sources"
    assert "References & Source Audit" not in final_report
