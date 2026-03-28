"use client";

import { useEffect, useState } from "react";

import { AppShell } from "src/components/ui/app-shell";
import { ApiClientError, createBrowserApiClient } from "src/lib/api/client";
import {
  buildCompanyCreatePayload,
  buildCompanyPatchPayload,
  buildPipelineRunQuery,
  companyDraftFromRecord,
  createEmptyCompanyDraft,
} from "src/lib/admin";

const api = createBrowserApiClient();

const SOURCE_OPTIONS = [
  { value: "greenhouse", label: "Greenhouse" },
  { value: "lever", label: "Lever" },
];

const LIFECYCLE_OPTIONS = [
  { value: "draft", label: "Draft" },
  { value: "active", label: "Active" },
  { value: "paused", label: "Paused" },
  { value: "archived", label: "Archived" },
];

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
  const [draft, setDraft] = useState(createEmptyCompanyDraft());
  const [companyMessage, setCompanyMessage] = useState("");
  const [companyError, setCompanyError] = useState("");
  const [companySaving, setCompanySaving] = useState(false);

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

  async function loadCompanies(nextSelectedId = "") {
    setCompaniesState((current) => ({ ...current, loading: true, error: "" }));
    try {
      const response = await api.getCompanies();
      setCompaniesState({ companies: response.data, loading: false, error: "" });

      const selectedCompany =
        response.data.find((company) => company.id === nextSelectedId) ??
        response.data.find((company) => company.id === draft.id) ??
        response.data[0];
      setDraft(selectedCompany ? companyDraftFromRecord(selectedCompany) : createEmptyCompanyDraft());
      setRunFilters((current) => ({
        ...current,
        companyId:
          current.companyId ||
          response.data.find((company) => company.id === nextSelectedId)?.id ||
          "",
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

  function updateDraft(key, value) {
    setDraft((current) => ({ ...current, [key]: value }));
  }

  async function onCompanySubmit(event) {
    event.preventDefault();
    setCompanyError("");
    setCompanyMessage("");

    if (!draft.slug.trim() || !draft.name.trim()) {
      setCompanyError("Slug and company name are required.");
      return;
    }

    setCompanySaving(true);
    try {
      const response = draft.id
        ? await api.updateCompany(draft.id, buildCompanyPatchPayload(draft))
        : await api.createCompany(buildCompanyCreatePayload(draft));

      setCompanyMessage(draft.id ? "Company updated." : "Company created.");
      await loadCompanies(response.data.id);
    } catch (caughtError) {
      setCompanyError(
        caughtError instanceof ApiClientError
          ? caughtError.message
          : "Could not save the company",
      );
    } finally {
      setCompanySaving(false);
    }
  }

  async function onManualSync(companyId) {
    setCompanyError("");
    setCompanyMessage("");
    try {
      const response = await api.triggerCompanySync(companyId);
      setCompanyMessage(`Sync queued for run ${response.data.pipeline_run_id}.`);
      await loadRuns(response.data.pipeline_run_id);
    } catch (caughtError) {
      setCompanyError(
        caughtError instanceof ApiClientError
          ? caughtError.message
          : "Could not queue a sync for this company",
      );
    }
  }

  return (
    <AppShell
      eyebrow="Admin"
      title="Operate the ingestion surface."
      description="Manage companies, queue manual syncs, and inspect the event history for each pipeline run without leaving the control plane."
      actions={
        <div className="toolbar">
          <span className="metric-chip">
            {companiesState.companies.length === 1
              ? "1 company"
              : `${companiesState.companies.length} companies`}
          </span>
          <button
            type="button"
            className="ghost-link buttonish"
            onClick={() => {
              setCompanyError("");
              setCompanyMessage("");
              setDraft(createEmptyCompanyDraft());
            }}
          >
            New company
          </button>
        </div>
      }
    >
      <section className="summary-stack">
        <div className="management-grid">
          <aside className="collection-panel">
            <p className="eyebrow">Companies</p>
            <h2>Registry</h2>
            <p>Operators can add sources, adjust lifecycle status, and launch immediate syncs.</p>
            {companiesState.error ? <p className="inline-error">{companiesState.error}</p> : null}
            {companiesState.loading ? (
              <p>Loading companies...</p>
            ) : (
              <div className="collection-list">
                {companiesState.companies.map((company) => (
                  <article
                    key={company.id}
                    className={draft.id === company.id ? "collection-item is-active" : "collection-item"}
                  >
                    <span>
                      <strong>{company.name}</strong>
                      <small>
                        {company.lifecycle_status} · {company.sources?.[0]?.source_type ?? "no source"}
                      </small>
                    </span>
                    <div className="job-actions">
                      <button
                        type="button"
                        className="ghost-link buttonish"
                        onClick={() => setDraft(companyDraftFromRecord(company))}
                      >
                        Edit
                      </button>
                      <button
                        type="button"
                        className="ghost-link buttonish"
                        onClick={() => onManualSync(company.id)}
                      >
                        Sync now
                      </button>
                    </div>
                  </article>
                ))}
              </div>
            )}
          </aside>

          <form className="editor-panel" onSubmit={onCompanySubmit}>
            <div className="editor-heading">
              <div>
                <p className="eyebrow">{draft.id ? "Edit company" : "Create company"}</p>
                <h2>{draft.id ? draft.name : "New company"}</h2>
              </div>
              {draft.id ? (
                <button
                  type="button"
                  className="primary-link buttonish"
                  onClick={() => onManualSync(draft.id)}
                >
                  Queue sync
                </button>
              ) : null}
            </div>

            <div className="panel-row">
              <label className="field">
                <span>Slug</span>
                <input
                  value={draft.slug}
                  onChange={(event) => updateDraft("slug", event.target.value)}
                  placeholder="openai"
                />
              </label>
              <label className="field">
                <span>Name</span>
                <input
                  value={draft.name}
                  onChange={(event) => updateDraft("name", event.target.value)}
                  placeholder="OpenAI"
                />
              </label>
            </div>

            <div className="panel-row">
              <label className="field">
                <span>Website URL</span>
                <input
                  value={draft.websiteUrl}
                  onChange={(event) => updateDraft("websiteUrl", event.target.value)}
                  placeholder="https://openai.com"
                />
              </label>
              <label className="field">
                <span>Lifecycle</span>
                <select
                  value={draft.lifecycleStatus}
                  onChange={(event) => updateDraft("lifecycleStatus", event.target.value)}
                >
                  {LIFECYCLE_OPTIONS.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </label>
            </div>

            <label className="field">
              <span>Description</span>
              <textarea
                rows="4"
                value={draft.description}
                onChange={(event) => updateDraft("description", event.target.value)}
                placeholder="Why this company is worth tracking."
              />
            </label>

            <div className="panel-row">
              <label className="field">
                <span>Source type</span>
                <select
                  value={draft.sourceType}
                  onChange={(event) => updateDraft("sourceType", event.target.value)}
                >
                  {SOURCE_OPTIONS.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </label>
              <label className="field">
                <span>Source enabled</span>
                <select
                  value={draft.isEnabled ? "yes" : "no"}
                  onChange={(event) => updateDraft("isEnabled", event.target.value === "yes")}
                >
                  <option value="yes">Yes</option>
                  <option value="no">No</option>
                </select>
              </label>
            </div>

            <div className="panel-row">
              <label className="field">
                <span>External key</span>
                <input
                  value={draft.externalKey}
                  onChange={(event) => updateDraft("externalKey", event.target.value)}
                  placeholder="openai"
                />
              </label>
              <label className="field">
                <span>Base URL</span>
                <input
                  value={draft.baseUrl}
                  onChange={(event) => updateDraft("baseUrl", event.target.value)}
                  placeholder="https://boards.greenhouse.io/openai"
                />
              </label>
            </div>

            {companyError ? <p className="inline-error">{companyError}</p> : null}
            {companyMessage ? <p className="inline-success">{companyMessage}</p> : null}

            <div className="panel-actions">
              <button className="primary-link buttonish" type="submit" disabled={companySaving}>
                {companySaving ? "Saving..." : draft.id ? "Save company" : "Create company"}
              </button>
            </div>
          </form>
        </div>

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
                    {event.payload ? (
                      <pre className="event-payload">
                        {JSON.stringify(event.payload, null, 2)}
                      </pre>
                    ) : null}
                  </article>
                ))}
              </div>
            ) : (
              <section className="empty-panel compact-panel">
                <p className="eyebrow">No run selected</p>
                <h2>Choose a pipeline run to inspect its event stream.</h2>
                <p>Queued and completed syncs will surface their diagnostic events here.</p>
              </section>
            )}
          </section>
        </section>
      </section>
    </AppShell>
  );
}
