"use client";

import { useState } from "react";

const EXAMPLE_QUESTIONS = [
  "Analyze the current electric vehicle market in India and compare major manufacturers, pricing, and technology trends.",
  "What are the latest breakthroughs in quantum computing and their potential commercial applications?",
  "Compare the top 5 cloud providers in 2024 by pricing, performance, and AI/ML capabilities.",
  "Analyze the global semiconductor supply chain: key players, bottlenecks, and geopolitical risks.",
];

export default function QuestionForm({ onSubmit, disabled }) {
  const [question, setQuestion] = useState("");

  const handleSubmit = (e) => {
    e.preventDefault();
    const q = question.trim();
    if (q.length < 10) return;
    onSubmit(q);
  };

  const handleExample = (q) => {
    setQuestion(q);
  };

  const charCount = question.length;
  const isValid = charCount >= 10 && charCount <= 2000;

  return (
    <div className="question-form-container">
      <form onSubmit={handleSubmit} className="question-form">
        <div className="textarea-wrapper">
          <textarea
            id="research-question"
            className="question-textarea"
            placeholder="Ask a deep research question… e.g. 'Analyze the EV market in India — major manufacturers, pricing, battery technology trends, and competitive landscape.'"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            disabled={disabled}
            rows={4}
            maxLength={2000}
            autoFocus
          />
          <span className={`char-count ${charCount > 1800 ? "warn" : ""}`}>
            {charCount}/2000
          </span>
        </div>

        <button
          type="submit"
          id="submit-research-btn"
          className="submit-btn"
          disabled={disabled || !isValid}
        >
          {disabled ? (
            <>
              <span className="spinner" />
              Researching…
            </>
          ) : (
            <>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                <circle cx="11" cy="11" r="8" />
                <line x1="21" y1="21" x2="16.65" y2="16.65" />
              </svg>
              Start Research
            </>
          )}
        </button>
      </form>

      {/* Example questions */}
      <div className="examples-section">
        <p className="examples-label">Try an example:</p>
        <div className="examples-grid">
          {EXAMPLE_QUESTIONS.map((q, i) => (
            <button
              key={i}
              className="example-chip"
              onClick={() => handleExample(q)}
              disabled={disabled}
              type="button"
            >
              {q.length > 80 ? q.slice(0, 77) + "…" : q}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
