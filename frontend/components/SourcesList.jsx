"use client";

export default function SourcesList({ sources }) {
  if (!sources || sources.length === 0) return null;

  return (
    <div className="sources-panel">
      <h3 className="sources-heading">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71" />
          <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71" />
        </svg>
        Sources <span className="source-badge">{sources.length}</span>
      </h3>
      <div className="sources-list">
        {sources.map((s, i) => (
          <a
            key={s.id || i}
            href={s.url}
            target="_blank"
            rel="noopener noreferrer"
            className="source-card"
            id={`source-${i + 1}`}
          >
            <div className="source-num">[{i + 1}]</div>
            <div className="source-info">
              <span className="source-title">{s.title || "Untitled"}</span>
              <span className="source-url">{s.url}</span>
              {s.snippet && (
                <span className="source-snippet">
                  {s.snippet.length > 120 ? s.snippet.slice(0, 117) + "…" : s.snippet}
                </span>
              )}
            </div>
            {s.relevance_score != null && (
              <div className="source-score" title="Relevance score">
                {(s.relevance_score * 100).toFixed(0)}%
              </div>
            )}
          </a>
        ))}
      </div>
    </div>
  );
}
