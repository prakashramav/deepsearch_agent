"""
Phase 8 — Export & PDF Generation

Formats research runs into standalone, executive-quality printable documents
ready for browser-based PDF printing or direct markdown download.
"""
from __future__ import annotations

from typing import Any
import markdown


def generate_printable_html(
    question: str,
    result_markdown: str,
    run_id: str,
    metadata: dict[str, Any] | None = None,
) -> str:
    """
    Convert Markdown research report into an executive-grade, standalone HTML document
    with typography, print styling, and PDF print headers.
    """
    html_content = markdown.markdown(
        result_markdown or "",
        extensions=["tables", "fenced_code", "nl2br"],
    )

    domain = (metadata or {}).get("domain", "General Research")
    sources_count = (metadata or {}).get("source_count", 0)
    claims_count = (metadata or {}).get("claim_count", 0)
    verified_count = (metadata or {}).get("verified_count", 0)
    citations_count = (metadata or {}).get("unique_sources_cited", 0)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>DeepResearch Report — {run_id[:8]}</title>
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

    :root {{
      --font-sans: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      --font-mono: 'JetBrains Mono', monospace;
    }}

    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: var(--font-sans);
      color: #1e293b;
      background: #ffffff;
      line-height: 1.65;
      padding: 40px;
      max-width: 900px;
      margin: 0 auto;
    }}

    /* Header */
    .report-cover {{
      border-bottom: 2px solid #e2e8f0;
      padding-bottom: 24px;
      margin-bottom: 32px;
    }}
    .brand-bar {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 16px;
    }}
    .brand-title {{
      font-size: 1.1rem;
      font-weight: 700;
      color: #4f46e5;
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }}
    .report-meta-tag {{
      font-family: var(--font-mono);
      font-size: 0.75rem;
      color: #64748b;
      background: #f1f5f9;
      padding: 4px 8px;
      border-radius: 4px;
    }}

    .question-box {{
      background: #f8fafc;
      border-left: 4px solid #4f46e5;
      padding: 12px 16px;
      border-radius: 0 6px 6px 0;
      margin-bottom: 16px;
    }}
    .question-label {{
      font-size: 0.75rem;
      font-weight: 600;
      text-transform: uppercase;
      color: #64748b;
      margin-bottom: 4px;
    }}
    .question-text {{
      font-size: 1.05rem;
      font-weight: 600;
      color: #0f172a;
    }}

    .metrics-bar {{
      display: flex;
      gap: 16px;
      flex-wrap: wrap;
      font-size: 0.8rem;
      color: #475569;
    }}
    .metric-item {{
      background: #f1f5f9;
      padding: 4px 10px;
      border-radius: 4px;
      font-weight: 500;
    }}

    /* Typography in Prose */
    .prose h1 {{
      font-size: 1.8rem;
      font-weight: 800;
      color: #0f172a;
      margin: 28px 0 16px;
      line-height: 1.3;
    }}
    .prose h2 {{
      font-size: 1.35rem;
      font-weight: 700;
      color: #1e293b;
      margin: 28px 0 12px;
      padding-bottom: 6px;
      border-bottom: 1px solid #e2e8f0;
      page-break-after: avoid;
    }}
    .prose h3 {{
      font-size: 1.1rem;
      font-weight: 600;
      color: #334155;
      margin: 20px 0 8px;
      page-break-after: avoid;
    }}
    .prose p {{
      margin-bottom: 16px;
      font-size: 0.95rem;
      color: #334155;
    }}
    .prose ul, .prose ol {{
      margin: 0 0 16px 24px;
      font-size: 0.95rem;
      color: #334155;
    }}
    .prose li {{ margin-bottom: 6px; }}

    .prose table {{
      width: 100%;
      border-collapse: collapse;
      margin: 20px 0;
      font-size: 0.88rem;
      page-break-inside: avoid;
    }}
    .prose th, .prose td {{
      border: 1px solid #cbd5e1;
      padding: 8px 12px;
      text-align: left;
    }}
    .prose th {{
      background: #f8fafc;
      font-weight: 600;
      color: #0f172a;
    }}
    .prose tr:nth-child(even) {{ background: #f8fafc; }}

    .prose blockquote {{
      border-left: 3px solid #6366f1;
      padding: 8px 14px;
      background: #f5f3ff;
      margin: 16px 0;
      font-style: italic;
      color: #4338ca;
    }}

    .prose code {{
      font-family: var(--font-mono);
      font-size: 0.85em;
      background: #f1f5f9;
      padding: 2px 5px;
      border-radius: 4px;
      color: #0f172a;
    }}

    .prose a {{
      color: #4f46e5;
      text-decoration: none;
    }}

    /* Print Controls */
    .print-controls {{
      position: fixed;
      top: 16px;
      right: 16px;
      display: flex;
      gap: 8px;
      background: rgba(255, 255, 255, 0.95);
      box-shadow: 0 4px 12px rgba(0,0,0,0.15);
      border: 1px solid #cbd5e1;
      padding: 8px 12px;
      border-radius: 8px;
      z-index: 1000;
    }}
    .print-btn {{
      background: #4f46e5;
      color: white;
      border: none;
      padding: 6px 14px;
      border-radius: 6px;
      cursor: pointer;
      font-weight: 600;
      font-size: 0.85rem;
    }}
    .print-btn:hover {{ background: #4338ca; }}

    /* Print Media Rules */
    @media print {{
      .print-controls {{ display: none !important; }}
      body {{
        padding: 0;
        max-width: 100%;
        color: #000;
      }}
      @page {{
        margin: 1.8cm 1.5cm;
        size: A4;
      }}
      .prose h2 {{ page-break-after: avoid; }}
      .prose table, .prose blockquote {{ page-break-inside: avoid; }}
    }}
  </style>
</head>
<body>
  <div class="print-controls">
    <button class="print-btn" onclick="window.print()">🖨️ Print / Save as PDF</button>
  </div>

  <div class="report-cover">
    <div class="brand-bar">
      <span class="brand-title">🔬 DeepResearch Intelligence Report</span>
      <span class="report-meta-tag">Run ID: {run_id[:8]}</span>
    </div>
    <div class="question-box">
      <div class="question-label">Research Objective</div>
      <div class="question-text">{question}</div>
    </div>
    <div class="metrics-bar">
      <span class="metric-item">🌐 Domain: {domain}</span>
      <span class="metric-item">📚 {sources_count} Sources</span>
      <span class="metric-item">📊 {claims_count} Claims ({verified_count} Verified)</span>
      <span class="metric-item">🏷️ {citations_count} Sources Cited</span>
    </div>
  </div>

  <article class="prose">
    {html_content}
  </article>

  <script>
    // Auto-trigger print dialog if '?print=true' query param is present
    if (new URLSearchParams(window.location.search).get('print') === 'true') {{
      window.onload = function() {{ window.print(); }};
    }}
  </script>
</body>
</html>"""
