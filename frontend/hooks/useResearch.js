/**
 * useResearch — custom hook that handles the full research polling lifecycle.
 *
 * Usage:
 *   const { run, sources, submit, loading, error } = useResearch();
 */
"use client";

import { useState, useCallback, useRef } from "react";
import { startResearch, getResearchRun, getRunSources, getRunClaims } from "@/lib/api";

const POLL_INTERVAL_MS = 2500;
const TERMINAL_STATUSES = new Set(["complete", "failed"]);

export function useResearch() {
  const [run, setRun] = useState(null);
  const [sources, setSources] = useState([]);
  const [claims, setClaims] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const pollRef = useRef(null);

  const stopPolling = useCallback(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }, []);

  const startPolling = useCallback(
    (runId) => {
      stopPolling();
      pollRef.current = setInterval(async () => {
        try {
          const data = await getResearchRun(runId);
          setRun(data);

          if (TERMINAL_STATUSES.has(data.status)) {
            stopPolling();
            setLoading(false);

            // Fetch sources and claims once done
            const [srcs, clms] = await Promise.all([
              getRunSources(runId),
              getRunClaims(runId),
            ]);
            setSources(srcs);
            setClaims(clms);
          }
        } catch (err) {
          setError(err.message);
          stopPolling();
          setLoading(false);
        }
      }, POLL_INTERVAL_MS);
    },
    [stopPolling]
  );

  const submit = useCallback(
    async (question) => {
      setLoading(true);
      setError(null);
      setRun(null);
      setSources([]);
      setClaims([]);
      stopPolling();

      try {
        const created = await startResearch(question);
        // Immediately fetch state so UI shows "pending" right away
        const initial = await getResearchRun(created.run_id);
        setRun(initial);
        startPolling(created.run_id);
      } catch (err) {
        setError(err.message);
        setLoading(false);
      }
    },
    [startPolling, stopPolling]
  );

  return { run, sources, claims, submit, loading, error };
}
