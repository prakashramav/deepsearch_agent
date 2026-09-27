"use client";

import { useState, useEffect } from "react";
import QuestionForm from "@/components/QuestionForm";
import StatusTracker from "@/components/StatusTracker";
import ReportViewer from "@/components/ReportViewer";
import SourcesList from "@/components/SourcesList";
import PlanViewer from "@/components/PlanViewer";
import ClaimsTable from "@/components/ClaimsTable";
import { useResearch } from "@/hooks/useResearch";

export default function HomePage() {
  const { run, sources, claims, submit, loadRun, loading, error } = useResearch();
  const [question, setQuestion] = useState("");
  const [lookupId, setLookupId] = useState("");
  const [showLookup, setShowLookup] = useState(false);

  useEffect(() => {
    if (typeof window !== "undefined") {
      const params = new URLSearchParams(window.location.search);
      const urlRunId = params.get("run_id");
      if (urlRunId) {
        loadRun(urlRunId);
      }
    }
  }, [loadRun]);

  const handleSubmit = (q) => {
    setQuestion(q);
    submit(q);
  };

  const handleLookup = (e) => {
    e.preventDefault();
    if (lookupId.trim()) {
      loadRun(lookupId.trim());
    }
  };

  const isComplete = run?.status === "complete";
  const isFailed = run?.status === "failed";
  const hasResult = isComplete && run?.result;

  return (
    <div className="app-shell">
      {/* ── Hero Header ── */}
      <header className="hero-header">
        <div className="hero-glow" />
        <div className="hero-content">
          <div className="logo-mark">
            <svg width="36" height="36" viewBox="0 0 48 48" fill="none">
              <defs>
                <linearGradient id="logoGrad" x1="0" y1="0" x2="48" y2="48" gradientUnits="userSpaceOnUse">
                  <stop offset="0%" stopColor="#818cf8" />
                  <stop offset="100%" stopColor="#38bdf8" />
                </linearGradient>
              </defs>
              <circle cx="24" cy="24" r="20" stroke="url(#logoGrad)" strokeWidth="2.5" />
              <path d="M14 24 Q24 12 34 24 Q24 36 14 24Z" fill="url(#logoGrad)" opacity="0.8" />
              <circle cx="24" cy="24" r="4" fill="white" />
            </svg>
          </div>
          <h1 className="hero-title">
            Deep<span className="gradient-text">Research</span>
          </h1>
          <p className="hero-subtitle">
            Multi-agent AI research — parallel web search, fact verification, and cited reports
          </p>
          <div className="hero-badges">
            <span className="badge">🤖 Claude Sonnet</span>
            <span className="badge">🔍 Tavily Search</span>
            <span className="badge">⚡ LangGraph</span>
            <span className="badge">📊 Fact Verified</span>
          </div>
        </div>
      </header>

      {/* ── Main Content ── */}
      <main className="main-content">
        {/* Question Input */}
        <section className="card input-card">
          <div className="card-header-row">
            <h2 className="card-title">
              <span className="card-title-icon">💡</span>
              {showLookup ? "Inspect Existing Run" : "Research Question"}
            </h2>
            <button
              type="button"
              className="lookup-toggle-btn"
              onClick={() => setShowLookup(!showLookup)}
            >
              {showLookup ? "← New Question" : "🔍 Inspect Run ID"}
            </button>
          </div>

          {showLookup ? (
            <form onSubmit={handleLookup} className="lookup-form">
              <input
                type="text"
                className="lookup-input"
                placeholder="Paste Run ID (e.g. 9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d)"
                value={lookupId}
                onChange={(e) => setLookupId(e.target.value)}
              />
              <button type="submit" className="lookup-submit-btn" disabled={loading || !lookupId.trim()}>
                Load Run
              </button>
            </form>
          ) : (
            <QuestionForm onSubmit={handleSubmit} disabled={loading} />
          )}
        </section>

        {/* Error banner */}
        {error && (
          <div className="error-banner" role="alert">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="10" /><line x1="12" y1="8" x2="12" y2="12" /><line x1="12" y1="16" x2="12.01" y2="16" />
            </svg>
            {error}
          </div>
        )}

        {/* Pipeline status */}
        {run && (
          <section className="card status-card">
            <h2 className="card-title">
              <span className="card-title-icon">🚀</span>
              Pipeline Status
            </h2>
            <StatusTracker run={run} />
          </section>
        )}

        {/* Phase 2: Research Plan */}
        {run?.plan && (
          <section className="card plan-card">
            <PlanViewer plan={run.plan} />
          </section>
        )}

        {/* Result area */}
        {hasResult && (
          <div className="results-grid">
            {/* Report */}
            <section className="card report-card">
              <ReportViewer
                result={run.result}
                question={run.question || question}
                runId={run.run_id}
              />
            </section>

            {/* Sources sidebar */}
            {sources.length > 0 && (
              <aside className="sources-sidebar">
                <SourcesList sources={sources} />
              </aside>
            )}
          </div>
        )}

        {/* Phase 4: Extracted Factual Claims */}
        {hasResult && claims.length > 0 && (
          <section className="card claims-card">
            <ClaimsTable claims={claims} />
          </section>
        )}

        {/* Loading skeleton */}
        {loading && !hasResult && (
          <div className="loading-section">
            <div className="agent-pulse">
              {["Research Agent", "Data Agent", "Analyst", "Fact Checker", "Writer"].map((a, i) => (
                <div
                  key={a}
                  className="agent-chip"
                  style={{ "--delay": `${i * 0.3}s` }}
                >
                  <span className="chip-dot" />
                  {a}
                </div>
              ))}
            </div>
            <p className="loading-hint">
              Agents are working… this typically takes 15–60 seconds
            </p>
          </div>
        )}
      </main>

      {/* ── Footer ── */}
      <footer className="app-footer">
        <p>DeepResearch Agent · Phase 1 · Powered by Claude + Tavily + LangGraph</p>
      </footer>
    </div>
  );
}
