"use client";

import { useState, useEffect } from "react";

// Lazy-load react-markdown on the client to avoid SSR issues
let ReactMarkdown = null;

export default function ReportViewer({ result, question }) {
  const [MarkdownComponent, setMarkdownComponent] = useState(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    // Dynamically import react-markdown
    import("react-markdown").then((mod) => {
      setMarkdownComponent(() => mod.default);
    });
  }, []);

  if (!result) return null;

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(result);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (_) {}
  };

  const handleDownload = () => {
    const blob = new Blob([result], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `research-report-${Date.now()}.md`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="report-viewer">
      {/* Toolbar */}
      <div className="report-toolbar">
        <h2 className="report-title">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
            <polyline points="14 2 14 8 20 8" />
          </svg>
          Research Report
        </h2>
        <div className="toolbar-actions">
          <button
            className="toolbar-btn"
            onClick={handleCopy}
            id="copy-report-btn"
            title="Copy Markdown"
          >
            {copied ? "✅ Copied!" : "📋 Copy"}
          </button>
          <button
            className="toolbar-btn primary"
            onClick={handleDownload}
            id="download-report-btn"
            title="Download .md"
          >
            ⬇️ Download .md
          </button>
        </div>
      </div>

      {/* Question reminder */}
      <div className="report-question">
        <span className="q-label">Question:</span> {question}
      </div>

      {/* Rendered markdown */}
      <div className="report-body prose">
        {MarkdownComponent ? (
          <MarkdownComponent>{result}</MarkdownComponent>
        ) : (
          <pre className="report-raw">{result}</pre>
        )}
      </div>
    </div>
  );
}
