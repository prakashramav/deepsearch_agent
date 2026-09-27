"""
Phase 8 Export & PDF formatting unit tests.

Tests markdown-to-printable HTML generation, print styles, and export endpoints.
"""
from app.export import generate_printable_html

MOCK_MD = (
    "# Strategic EV Analysis\n\n"
    "## Overview\n"
    "India is accelerating EV adoption rapidly [1].\n\n"
    "| OEM | Segment | Share |\n"
    "|---|---|---|\n"
    "| Tata | 4W | 65% |\n"
    "| Ola | 2W | 35% |\n\n"
    "## References\n"
    "1. https://example.com/source1\n"
)


def test_generate_printable_html():
    """generate_printable_html produces standalone HTML with tables, cover metadata, and print CSS."""
    html = generate_printable_html(
        question="Analyze EV market in India",
        result_markdown=MOCK_MD,
        run_id="abcdef12-3456-7890-abcd-ef1234567890",
        metadata={
            "domain": "Market Analysis",
            "source_count": 8,
            "claim_count": 6,
            "verified_count": 5,
            "unique_sources_cited": 7,
        },
    )

    assert "<!DOCTYPE html>" in html
    assert "DeepResearch Report — abcdef12" in html
    assert "Analyze EV market in India" in html
    assert "<table>" in html
    assert "<td>Tata</td>" in html
    assert "@media print" in html
    assert "Print / Save as PDF" in html
