"use client";

import { useState } from "react";

export default function ClaimsTable({ claims }) {
  const [filter, setFilter] = useState("all");

  if (!claims || claims.length === 0) return null;

  const verifiedCount = claims.filter((c) => c.verified).length;
  const conflictCount = claims.filter((c) => c.conflict_flag).length;

  const filteredClaims = claims.filter((c) => {
    if (filter === "verified") return c.verified;
    if (filter === "conflicts") return c.conflict_flag;
    if (filter === "high") return (c.confidence || 0) >= 0.9;
    return true;
  });

  return (
    <div className="claims-panel">
      <div className="claims-header">
        <div className="claims-title-group">
          <span className="claims-icon">📊</span>
          <h3 className="claims-heading">
            Extracted Factual Claims & Verification
            <span className="claims-count-badge">{claims.length}</span>
          </h3>
        </div>
        <div className="claims-filters">
          <button
            className={`filter-btn ${filter === "all" ? "active" : ""}`}
            onClick={() => setFilter("all")}
          >
            All ({claims.length})
          </button>
          <button
            className={`filter-btn ${filter === "verified" ? "active" : ""}`}
            onClick={() => setFilter("verified")}
          >
            ✓ Verified ({verifiedCount})
          </button>
          {conflictCount > 0 && (
            <button
              className={`filter-btn conflict-tab ${filter === "conflicts" ? "active" : ""}`}
              onClick={() => setFilter("conflicts")}
            >
              ⚠️ Conflicts ({conflictCount})
            </button>
          )}
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
            <div
              key={claim.id || idx}
              className={`claim-card ${claim.conflict_flag ? "has-conflict" : ""} ${claim.verified ? "is-verified" : ""}`}
            >
              <div className="claim-top-row">
                <span className="claim-index">#{idx + 1}</span>

                {claim.verified && (
                  <span className="claim-status-badge verified">
                    ✓ Verified
                  </span>
                )}

                {claim.conflict_flag && (
                  <span className="claim-status-badge conflict">
                    ⚠️ Conflict Flagged
                  </span>
                )}

                {!claim.verified && !claim.conflict_flag && (
                  <span className="claim-status-badge unverified">
                    Single Source
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

              {claim.sub_question && (
                <div className="claim-subq-row">
                  <span className="claim-subq" title={claim.sub_question}>
                    🔍 {claim.sub_question}
                  </span>
                </div>
              )}

              <p className="claim-text">{claim.claim_text}</p>

              {claim.supporting_quote && (
                <blockquote className="claim-quote">
                  <span className="quote-mark">“</span>
                  {claim.supporting_quote}
                  <span className="quote-mark">”</span>
                </blockquote>
              )}

              {claim.verification_notes && (
                <div className="claim-verification-note">
                  <span className="note-label">Fact Check:</span> {claim.verification_notes}
                </div>
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
