"use client";

import { useState } from "react";

export default function ClaimsTable({ claims }) {
  const [filter, setFilter] = useState("all");

  if (!claims || claims.length === 0) return null;

  const filteredClaims = filter === "all"
    ? claims
    : claims.filter((c) => (c.confidence || 0) >= 0.9);

  return (
    <div className="claims-panel">
      <div className="claims-header">
        <div className="claims-title-group">
          <span className="claims-icon">📊</span>
          <h3 className="claims-heading">
            Extracted Factual Claims <span className="claims-count-badge">{claims.length}</span>
          </h3>
        </div>
        <div className="claims-filters">
          <button
            className={`filter-btn ${filter === "all" ? "active" : ""}`}
            onClick={() => setFilter("all")}
          >
            All Claims ({claims.length})
          </button>
          <button
            className={`filter-btn ${filter === "high" ? "active" : ""}`}
            onClick={() => setFilter("high")}
          >
            High Confidence (≥90%)
          </button>
        </div>
      </div>

      <div className="claims-grid">
        {filteredClaims.map((claim, idx) => {
          const confidencePct = Math.round((claim.confidence || 0.85) * 100);
          let domain = "";
          try {
            domain = new URL(claim.source_url).hostname.replace("www.", "");
          } catch {
            domain = "Source";
          }

          return (
            <div key={claim.id || idx} className="claim-card">
              <div className="claim-top-row">
                <span className="claim-index">#{idx + 1}</span>
                {claim.sub_question && (
                  <span className="claim-subq" title={claim.sub_question}>
                    {claim.sub_question.length > 55
                      ? claim.sub_question.slice(0, 52) + "…"
                      : claim.sub_question}
                  </span>
                )}
                <span
                  className="claim-confidence"
                  style={{
                    background:
                      confidencePct >= 90
                        ? "rgba(52, 211, 153, 0.12)"
                        : "rgba(251, 191, 36, 0.12)",
                    color: confidencePct >= 90 ? "var(--emerald)" : "var(--amber)",
                    borderColor:
                      confidencePct >= 90
                        ? "rgba(52, 211, 153, 0.25)"
                        : "rgba(251, 191, 36, 0.25)",
                  }}
                >
                  {confidencePct}% Confidence
                </span>
              </div>

              <p className="claim-text">{claim.claim_text}</p>

              {claim.supporting_quote && (
                <blockquote className="claim-quote">
                  <span className="quote-mark">“</span>
                  {claim.supporting_quote}
                  <span className="quote-mark">”</span>
                </blockquote>
              )}

              <div className="claim-footer">
                <a
                  href={claim.source_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="claim-source-link"
                >
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71" />
                    <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71" />
                  </svg>
                  {domain}
                </a>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
