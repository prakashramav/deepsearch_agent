"use client";

export default function PlanViewer({ plan }) {
  if (!plan) return null;

  const {
    sub_questions = [],
    research_strategy,
    domain,
    estimated_sources_needed,
  } = plan;

  return (
    <div className="plan-viewer">
      <div className="plan-header">
        <div className="plan-header-title">
          <span className="plan-icon">🧠</span>
          <h3>Research Plan & Strategy</h3>
        </div>
        <div className="plan-badges">
          {domain && <span className="plan-badge domain">{domain}</span>}
          {estimated_sources_needed && (
            <span className="plan-badge sources">
              Target: ~{estimated_sources_needed} sources
            </span>
          )}
        </div>
      </div>

      {research_strategy && (
        <div className="plan-strategy">
          <span className="strategy-icon">🎯</span>
          <p>{research_strategy}</p>
        </div>
      )}

      {sub_questions.length > 0 && (
        <div className="sub-questions-container">
          <div className="sub-questions-title">Decomposed Sub-Questions ({sub_questions.length})</div>
          <div className="sub-questions-grid">
            {sub_questions.map((sq, idx) => (
              <div key={sq.id || idx} className="sub-question-item">
                <div className="sq-number">{String(idx + 1).padStart(2, "0")}</div>
                <div className="sq-content">
                  <span className="sq-focus">{sq.focus_area || "Focus Area"}</span>
                  <p className="sq-text">{sq.question}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
