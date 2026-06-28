"use client";

import { useState } from "react";

import { getApiReadiness, type ApiHealth } from "@/lib/api";

type RequestState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "success"; data: ApiHealth }
  | { status: "error"; message: string };

export function SystemCheck() {
  const [state, setState] = useState<RequestState>({ status: "idle" });

  async function runCheck() {
    setState({ status: "loading" });

    try {
      const data = await getApiReadiness();
      setState({ status: "success", data });
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unknown health-check error";
      setState({ status: "error", message });
    }
  }

  return (
    <section className="system-panel" aria-labelledby="system-status-heading">
      <div>
        <p className="eyebrow">Live infrastructure check</p>
        <h2 id="system-status-heading">Verify the local platform</h2>
        <p className="panel-copy">
          This calls FastAPI, which then verifies PostgreSQL and Redis concurrently.
        </p>
      </div>

      <button className="primary-button" onClick={runCheck} disabled={state.status === "loading"}>
        {state.status === "loading" ? "Checking…" : "Run system check"}
      </button>

      <div className="result" aria-live="polite">
        {state.status === "idle" && <span className="muted">No check has run yet.</span>}
        {state.status === "loading" && <span className="muted">Contacting the API…</span>}
        {state.status === "error" && <span className="error-text">{state.message}</span>}
        {state.status === "success" && (
          <div className="check-grid">
            <StatusItem label="API" value={state.data.status} />
            <StatusItem label="PostgreSQL" value={state.data.checks?.database ?? "unhealthy"} />
            <StatusItem label="Redis" value={state.data.checks?.redis ?? "unhealthy"} />
          </div>
        )}
      </div>
    </section>
  );
}

function StatusItem({ label, value }: { label: string; value: "healthy" | "unhealthy" }) {
  return (
    <div className="status-item">
      <span>{label}</span>
      <strong className={value === "healthy" ? "status-good" : "status-bad"}>{value}</strong>
    </div>
  );
}
