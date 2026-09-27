/**
 * API client for the DeepResearch backend.
 * Centralises all fetch calls so components never talk to the backend directly.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function startResearch(question) {
  const res = await fetch(`${API_BASE}/api/v1/research`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json(); // { run_id, status, message }
}

export async function getResearchRun(runId) {
  const res = await fetch(`${API_BASE}/api/v1/research/${runId}`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

export async function getRunSources(runId) {
  const res = await fetch(`${API_BASE}/api/v1/research/${runId}/sources`);
  if (!res.ok) return [];
  return res.json();
}

export async function healthCheck() {
  const res = await fetch(`${API_BASE}/health`);
  if (!res.ok) throw new Error("Backend unreachable");
  return res.json();
}
