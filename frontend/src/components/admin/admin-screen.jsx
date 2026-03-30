"use client";

import { useEffect, useState } from "react";

import { AppShell } from "src/components/ui/app-shell";
import { ApiClientError, createBrowserApiClient } from "src/lib/api/client";
import { buildPipelineRunQuery } from "src/lib/admin";

const api = createBrowserApiClient();

const RUN_STATUS_OPTIONS = [
  { value: "", label: "All statuses" },
  { value: "queued", label: "Queued" },
  { value: "running", label: "Running" },
  { value: "succeeded", label: "Succeeded" },
  { value: "partial", label: "Partial" },
  { value: "failed", label: "Failed" },
];

function formatTimestamp(value) {
  if (!value) {
    return "Pending";
  }

  const date = new Date(value);
  return new Intl.DateTimeFormat("en-CA", {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(date);
}

export function AdminScreen() {
  const [companiesState, setCompaniesState] = useState({
    companies: [],
    loading: true,
    error: "",
  });
  const [runFilters, setRunFilters] = useState({
    companyId: "",
    status: "",
    startedAfter: "",
    startedBefore: "",
  });
  const [runsState, setRunsState] = useState({
    runs: [],
    loading: true,
    error: "",
  });
  const [selectedRunId, setSelectedRunId] = useState("");
  const [runDetailState, setRunDetailState] = useState({
    data: null,
    loading: false,
    error: "",
  });

  useEffect(() => {
    void loadCompanies();
  }, []);

  useEffect(() => {
    void loadRuns();
  }, [runFilters.companyId, runFilters.status, runFilters.startedAfter, runFilters.startedBefore]);

  useEffect(() => {
    if (!selectedRunId) {
      setRunDetailState({ data: null, loading: false, error: "" });
      return;
    }
    void loadRunDetail(selectedRunId);
  }, [selectedRunId]);

  async function loadCompanies() {
    setCompaniesState((current) => ({ ...current, loading: true, error: "" }));
    try {
      const response = await api.getCompanies();
      setCompaniesState({ companies: response.data, loading: false, error: "" });
      setRunFilters((current) => ({
        ...current,
        companyId:
          response.data.some((company) => company.id === current.companyId) ? current.companyId : "",
      }));
    } catch (caughtError) {
      setCompaniesState({
        companies: [],
        loading: false,
        error:
          caughtError instanceof ApiClientError
            ? caughtError.message
            : "Could not load companies",
      });
    }
  }

  async function loadRuns(nextSelectedRunId = "") {
    setRunsState((current) => ({ ...current, loading: true, error: "" }));
    try {
      const response = await api.getPipelineRuns(buildPipelineRunQuery(runFilters));
      setRunsState({ runs: response.data, loading: false, error: "" });
      const selectedRun =
        response.data.find((run) => run.id === nextSelectedRunId) ??
        response.data.find((run) => run.id === selectedRunId) ??
        response.data[0];
      setSelectedRunId(selectedRun?.id ?? "");
    } catch (caughtError) {
      setRunsState({
        runs: [],
        loading: false,
        error:
          caughtError instanceof ApiClientError
            ? caughtError.message
            : "Could not load pipeline runs",
      });
    }
  }

  async function loadRunDetail(runId) {
    setRunDetailState((current) => ({ ...current, loading: true, error: "" }));
    try {
      const response = await api.getPipelineRun(runId);
      setRunDetailState({ data: response.data, loading: false, error: "" });
    } catch (caughtError) {
      setRunDetailState({
        data: null,
        loading: false,
        error:
          caughtError instanceof ApiClientError
            ? caughtError.message
            : "Could not load run detail",
      });
    }
  }

  return (
    <AppShell
      eyebrow="Admin"
      title="Monitor pipeline health."
      description="Use the admin surface for operational visibility only: inspect recent runs, filter by company or status, and read the event stream when a sync fails or degrades."
      actions={
        <div className="toolbar">
          <span className="metric-chip">
            {runsState.runs.length === 1 ? "1 recent run" : `${runsState.runs.length} recent runs`}
          </span>
          <span className="metric-chip">
            {companiesState.companies.length === 1
              ? "1 tracked company"
              : `${companiesState.companies.length} tracked companies`}
          </span>
        </div>
      }
    >
      <section className="management-grid">
        <aside className="collection-panel">
          <p className="eyebrow">Pipeline runs</p>
          <h2>Run monitor</h2>
          <p>Filter recent executions and inspect the event stream for failures or partial syncs.</p>

          <div className="summary-toolbar">
            <label className="field compact-field">
              <span>Company</span>
              <select
                value={runFilters.companyId}
                onChange={(event) =>
                  setRunFilters((current) => ({ ...current, companyId: event.target.value }))
                }
              >
                <option value="">All companies</option>
                {companiesState.companies.map((company) => (
                  <option key={company.id} value={company.id}>
                    {company.name}
                  </option>
                ))}
              </select>
            </label>

            <label className="field compact-field">
              <span>Status</span>
              <select
                value={runFilters.status}
                onChange={(event) =>
                  setRunFilters((current) => ({ ...current, status: event.target.value }))
                }
              >
                {RUN_STATUS_OPTIONS.map((option) => (
                  <option key={option.value || "all"} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>

            <label className="field compact-field">
              <span>Started after</span>
              <input
                type="date"
                value={runFilters.startedAfter}
                onChange={(event) =>
                  setRunFilters((current) => ({
                    ...current,
                    startedAfter: event.target.value,
                  }))
                }
              />
            </label>
          </div>

          {companiesState.error ? <p className="inline-error">{companiesState.error}</p> : null}
          {runsState.error ? <p className="inline-error">{runsState.error}</p> : null}
          {runsState.loading ? (
            <p>Loading pipeline runs...</p>
          ) : (
            <div className="collection-list">
              {runsState.runs.map((run) => (
                <button
                  key={run.id}
                  type="button"
                  className={selectedRunId === run.id ? "collection-item is-active" : "collection-item"}
                  onClick={() => setSelectedRunId(run.id)}
                >
                  <span>
                    <strong>{run.company?.name ?? "Global run"}</strong>
                    <small>
                      {run.status} · {run.trigger_type} · {formatTimestamp(run.started_at)}
                    </small>
                  </span>
                </button>
              ))}
            </div>
          )}
        </aside>

        <section className="editor-panel">
          <div className="editor-heading">
            <div>
              <p className="eyebrow">Run detail</p>
              <h2>{runDetailState.data?.company?.name ?? "Select a pipeline run"}</h2>
            </div>
          </div>

          {runDetailState.error ? <p className="inline-error">{runDetailState.error}</p> : null}
          {runDetailState.loading ? (
            <p>Loading run detail...</p>
          ) : runDetailState.data ? (
            <div className="event-stream">
              <div className="detail-meta">
                <span>Status: {runDetailState.data.status}</span>
                <span>Trigger: {runDetailState.data.trigger_type}</span>
                <span>Started: {formatTimestamp(runDetailState.data.started_at)}</span>
                <span>Finished: {formatTimestamp(runDetailState.data.finished_at)}</span>
              </div>

              {(runDetailState.data.events ?? []).map((event) => (
                <article key={event.id} className="event-item">
                  <div className="event-head">
                    <strong>{event.event_type}</strong>
                    <span className="metric-chip">{event.level}</span>
                  </div>
                  <p>{event.message}</p>
                  <small>
                    Step {event.sequence_number} · {formatTimestamp(event.created_at)}
                  </small>
                </article>
              ))}
            </div>
          ) : (
            <p>Select a run from the monitor to inspect its event stream.</p>
          )}
        </section>
      </section>
    </AppShell>
  );
}
