"use client";

const STATUS_META = {
  pending:       { label: "Queued",            icon: "⏳", color: "var(--status-pending)",  step: 0 },
  planning:      { label: "Planning",          icon: "🧠", color: "var(--status-planning)", step: 1 },
  researching:   { label: "Researching",       icon: "🔍", color: "var(--status-research)", step: 2 },
  extracting:    { label: "Extracting Data",   icon: "📊", color: "var(--status-extract)",  step: 3 },
  fact_checking: { label: "Fact Checking",     icon: "✅", color: "var(--status-check)",    step: 4 },
  synthesizing:  { label: "Synthesising",      icon: "🔬", color: "var(--status-synth)",    step: 5 },
  writing:       { label: "Writing Report",    icon: "✍️",  color: "var(--status-write)",    step: 6 },
  citing:        { label: "Adding Citations",  icon: "📚", color: "var(--status-cite)",     step: 7 },
  complete:      { label: "Complete",          icon: "🎉", color: "var(--status-done)",     step: 8 },
  failed:        { label: "Failed",            icon: "❌", color: "var(--status-fail)",     step: -1 },
};

const PIPELINE_STEPS = [
  "Queued", "Planning", "Researching", "Extracting",
  "Fact Checking", "Synthesising", "Writing", "Citing", "Complete",
];

export default function StatusTracker({ run }) {
  if (!run) return null;

  const meta = STATUS_META[run.status] || STATUS_META.pending;
  const currentStep = meta.step;
  const isFailed = run.status === "failed";

  return (
    <div className="status-tracker">
      {/* Current status badge */}
      <div className="status-badge" style={{ "--badge-color": meta.color }}>
        <span className="status-icon">{meta.icon}</span>
        <span className="status-label">{meta.label}</span>
        {!["complete", "failed"].includes(run.status) && (
          <span className="status-pulse" />
        )}
      </div>

      {/* Pipeline progress bar */}
      {!isFailed && (
        <div className="pipeline-track">
          {PIPELINE_STEPS.map((step, idx) => {
            const done = currentStep > idx;
            const active = currentStep === idx;
            return (
              <div key={step} className={`pipeline-step ${done ? "done" : ""} ${active ? "active" : ""}`}>
                <div className="step-dot">
                  {done && (
                    <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3">
                      <polyline points="20 6 9 17 4 12" />
                    </svg>
                  )}
                </div>
                <span className="step-label">{step}</span>
              </div>
            );
          })}
        </div>
      )}

      {/* Error message */}
      {isFailed && run.error_message && (
        <div className="error-box">
          <strong>Error:</strong> {run.error_message}
        </div>
      )}

      {/* Run metadata */}
      <div className="run-meta">
        <span className="run-id">Run ID: <code>{run.run_id}</code></span>
        {run.metadata?.sub_questions_count !== undefined && (
          <span className="source-count">
            🧠 {run.metadata.sub_questions_count} sub-questions
          </span>
        )}
        {run.metadata?.source_count !== undefined && (
          <span className="source-count">
            📚 {run.metadata.source_count} sources found
          </span>
        )}
      </div>
    </div>
  );
}
