"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useRef, useState, useTransition } from "react";

import { AppShell } from "src/components/ui/app-shell";
import { ApiClientError, createBrowserApiClient } from "src/lib/api/client";
import {
  buildCompanyCreatePayload,
  buildCompanyPatchPayload,
  companyDraftFromRecord,
  createEmptyCompanyDraft,
} from "src/lib/admin";
import { createDashboardSearch, formatPostedDate } from "src/lib/dashboard";

const api = createBrowserApiClient();

const SOURCE_OPTIONS = [
  { value: "greenhouse", label: "Greenhouse" },
  { value: "lever", label: "Lever" },
  { value: "manual", label: "Manual" },
];

const LIFECYCLE_OPTIONS = [
  { value: "draft", label: "Draft" },
  { value: "active", label: "Active" },
  { value: "paused", label: "Paused" },
  { value: "archived", label: "Archived" },
];

const LIFECYCLE_FILTER_OPTIONS = [
  { value: "", label: "All lifecycle states" },
  ...LIFECYCLE_OPTIONS,
];

const SOURCE_STATE_FILTER_OPTIONS = [
  { value: "", label: "All source states" },
  { value: "enabled", label: "Source enabled" },
  { value: "paused", label: "Source paused" },
  { value: "missing", label: "No source attached" },
];

function formatUpdatedDate(value) {
  if (!value) {
    return "Unknown update";
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "Unknown update";
  }

  return new Intl.DateTimeFormat("en-CA", {
    month: "short",
    day: "numeric",
    year: "numeric",
  }).format(date);
}

function buildJobsHref(companyId) {
  return `/jobs?${createDashboardSearch({
    title: "",
    location: "",
    companyIds: companyId ? [companyId] : [],
    workModes: [],
    postedAfter: "",
    postedBefore: "",
    sort: "posted_at",
    order: "desc",
    page: 1,
    perPage: 12,
    selectedJobId: "",
  })}`;
}

function primarySource(company) {
  return company.sources?.[0] ?? null;
}

export function CompaniesScreen() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [, startRouting] = useTransition();
  const [companiesState, setCompaniesState] = useState({
    data: [],
    loading: true,
    error: "",
  });
  const [selectedCompanyId, setSelectedCompanyId] = useState("");
  const [selectedCompanyIds, setSelectedCompanyIds] = useState([]);
  const [companyJobsState, setCompanyJobsState] = useState({
    data: [],
    loading: false,
    error: "",
  });
  const [draft, setDraft] = useState(createEmptyCompanyDraft());
  const [companyMessage, setCompanyMessage] = useState("");
  const [companyError, setCompanyError] = useState("");
  const [companySaving, setCompanySaving] = useState(false);
  const [bulkSyncing, setBulkSyncing] = useState(false);
  const [companyFilters, setCompanyFilters] = useState({
    lifecycleStatus: "",
    sourceState: "",
  });
  const selectAllCheckboxRef = useRef(null);

  const companyIdFromSearch = searchParams.get("company_id") ?? "";

  const filteredCompanies = companiesState.data.filter((company) => {
    if (
      companyFilters.lifecycleStatus &&
      company.lifecycle_status !== companyFilters.lifecycleStatus
    ) {
      return false;
    }

    if (!companyFilters.sourceState) {
      return true;
    }

    const source = primarySource(company);
    if (companyFilters.sourceState === "missing") {
      return source === null;
    }
    if (companyFilters.sourceState === "enabled") {
      return source?.is_enabled === true;
    }
    if (companyFilters.sourceState === "paused") {
      return source !== null && source.is_enabled === false;
    }
    return true;
  });

  useEffect(() => {
    let active = true;
    setCompaniesState((current) => ({ ...current, loading: true, error: "" }));

    api
      .getCompanies()
      .then((response) => {
        if (!active) {
          return;
        }

        const nextCompanies = response.data;
        const resolvedCompanyId =
          nextCompanies.find((company) => company.id === companyIdFromSearch)?.id ??
          nextCompanies.find((company) => company.id === selectedCompanyId)?.id ??
          nextCompanies[0]?.id ??
          "";
        const resolvedCompany =
          nextCompanies.find((company) => company.id === draft.id) ??
          nextCompanies.find((company) => company.id === resolvedCompanyId) ??
          null;

        setCompaniesState({ data: nextCompanies, loading: false, error: "" });
        setSelectedCompanyId(resolvedCompanyId);
        setDraft(resolvedCompany ? companyDraftFromRecord(resolvedCompany) : createEmptyCompanyDraft());

        if (resolvedCompanyId !== companyIdFromSearch) {
          startRouting(() => {
            router.replace(
              resolvedCompanyId ? `/companies?company_id=${resolvedCompanyId}` : "/companies",
              { scroll: false },
            );
          });
        }
      })
      .catch((caughtError) => {
        if (!active) {
          return;
        }

        setCompaniesState({
          data: [],
          loading: false,
          error:
            caughtError instanceof ApiClientError
              ? caughtError.message
              : "Could not load companies right now",
        });
        setSelectedCompanyId("");
      });

    return () => {
      active = false;
    };
  }, [companyIdFromSearch]);

  useEffect(() => {
    if (companiesState.loading) {
      return;
    }

    const nextSelectedId =
      filteredCompanies.find((company) => company.id === selectedCompanyId)?.id ??
      filteredCompanies[0]?.id ??
      "";

    if (nextSelectedId === selectedCompanyId) {
      return;
    }

    setSelectedCompanyId(nextSelectedId);
    startRouting(() => {
      router.replace(nextSelectedId ? `/companies?company_id=${nextSelectedId}` : "/companies", {
        scroll: false,
      });
    });
  }, [
    companiesState.data,
    companiesState.loading,
    companyFilters.lifecycleStatus,
    companyFilters.sourceState,
    selectedCompanyId,
  ]);

  useEffect(() => {
    setSelectedCompanyIds((current) => {
      if (!current.length) {
        return current;
      }

      const visibleCompanyIds = new Set(filteredCompanies.map((company) => company.id));
      const nextSelection = current.filter((companyId) => visibleCompanyIds.has(companyId));
      return nextSelection.length === current.length ? current : nextSelection;
    });
  }, [filteredCompanies]);

  useEffect(() => {
    if (!selectedCompanyId) {
      setCompanyJobsState({ data: [], loading: false, error: "" });
      return;
    }

    let active = true;
    setCompanyJobsState((current) => ({ ...current, loading: true, error: "" }));

    api
      .getJobs({
        company_ids: [selectedCompanyId],
        sort: "posted_at",
        order: "desc",
        page: 1,
        per_page: 6,
      })
      .then((response) => {
        if (active) {
          setCompanyJobsState({ data: response.data, loading: false, error: "" });
        }
      })
      .catch((caughtError) => {
        if (active) {
          setCompanyJobsState({
            data: [],
            loading: false,
            error:
              caughtError instanceof ApiClientError
                ? caughtError.message
                : "Could not load jobs for this company",
          });
        }
      });

    return () => {
      active = false;
    };
  }, [selectedCompanyId]);

  function onInspectCompany(companyId) {
    setSelectedCompanyId(companyId);
    startRouting(() => {
      router.push(`/companies?company_id=${companyId}`, { scroll: false });
    });
  }

  function onEditCompany(company) {
    setCompanyError("");
    setCompanyMessage("");
    setDraft(companyDraftFromRecord(company));
    onInspectCompany(company.id);
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
      setSelectedCompanyId(response.data.id);
      startRouting(() => {
        router.replace(`/companies?company_id=${response.data.id}`, { scroll: false });
      });
      const refreshed = await api.getCompanies();
      setCompaniesState({ data: refreshed.data, loading: false, error: "" });
      const refreshedCompany =
        refreshed.data.find((company) => company.id === response.data.id) ?? response.data;
      setDraft(companyDraftFromRecord(refreshedCompany));
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
    } catch (caughtError) {
      setCompanyError(
        caughtError instanceof ApiClientError
          ? caughtError.message
          : "Could not queue a sync for this company",
      );
    }
  }

  async function onManualSyncSelectedCompanies() {
    if (!selectedCompanyIds.length) {
      return;
    }

    setCompanyError("");
    setCompanyMessage("");
    setBulkSyncing(true);

    try {
      const results = await Promise.allSettled(
        selectedCompanyIds.map((companyId) => api.triggerCompanySync(companyId)),
      );

      const successCount = results.filter((result) => result.status === "fulfilled").length;
      const failedCount = results.length - successCount;

      if (successCount) {
        setCompanyMessage(
          successCount === 1
            ? "Sync queued for 1 company."
            : `Sync queued for ${successCount} companies.`,
        );
      }
      if (failedCount) {
        setCompanyError(
          failedCount === 1
            ? "Could not queue a sync for 1 selected company."
            : `Could not queue syncs for ${failedCount} selected companies.`,
        );
      }
    } finally {
      setBulkSyncing(false);
    }
  }

  function onToggleCompanySelection(companyId) {
    setSelectedCompanyIds((current) =>
      current.includes(companyId)
        ? current.filter((selectedId) => selectedId !== companyId)
        : [...current, companyId],
    );
  }

  function onToggleVisibleCompanySelection(checked) {
    const visibleCompanyIds = filteredCompanies.map((company) => company.id);
    const visibleCompanyIdSet = new Set(visibleCompanyIds);

    setSelectedCompanyIds((current) => {
      if (checked) {
        return Array.from(new Set([...current, ...visibleCompanyIds]));
      }
      return current.filter((companyId) => !visibleCompanyIdSet.has(companyId));
    });
  }

  const selectedVisibleCompanyCount = filteredCompanies.reduce(
    (count, company) => count + (selectedCompanyIds.includes(company.id) ? 1 : 0),
    0,
  );
  const allVisibleCompaniesSelected =
    filteredCompanies.length > 0 && selectedVisibleCompanyCount === filteredCompanies.length;
  const someVisibleCompaniesSelected =
    selectedVisibleCompanyCount > 0 && !allVisibleCompaniesSelected;

  useEffect(() => {
    if (selectAllCheckboxRef.current) {
      selectAllCheckboxRef.current.indeterminate = someVisibleCompaniesSelected;
    }
  }, [someVisibleCompaniesSelected]);

  const selectedCompany = filteredCompanies.find((company) => company.id === selectedCompanyId) ?? null;
  const selectedCompanyPrimarySource = selectedCompany ? primarySource(selectedCompany) : null;

  return (
    <AppShell
      eyebrow="Companies"
      title="Track and manage company sources."
      description="Own the company registry here: add sources, update lifecycle state, queue syncs, and jump straight into the jobs for any tracked company."
      actions={
        <div className="toolbar">
          <span className="metric-chip">
            {companiesState.data.length === 1
              ? "1 company tracked"
              : `${companiesState.data.length} companies tracked`}
          </span>
          <button
            type="button"
            className="primary-link buttonish"
            onClick={onManualSyncSelectedCompanies}
            disabled={!selectedCompanyIds.length || bulkSyncing}
          >
            {bulkSyncing
              ? "Queueing syncs..."
              : selectedCompanyIds.length === 1
                ? "Queue sync for 1 selected"
                : `Queue sync for selected (${selectedCompanyIds.length})`}
          </button>
          {selectedCompany ? (
            <Link href={buildJobsHref(selectedCompany.id)} className="primary-link">
              Open company jobs
            </Link>
          ) : null}
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
      <section className="companies-layout">
        <div className="company-grid">
          <div className="summary-toolbar company-summary-toolbar">
            <label className="field compact-field">
              <span>Lifecycle</span>
              <select
                value={companyFilters.lifecycleStatus}
                onChange={(event) =>
                  setCompanyFilters((current) => ({
                    ...current,
                    lifecycleStatus: event.target.value,
                  }))
                }
              >
                {LIFECYCLE_FILTER_OPTIONS.map((option) => (
                  <option key={option.value || "all"} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>
            <label className="field compact-field">
              <span>Source state</span>
              <select
                value={companyFilters.sourceState}
                onChange={(event) =>
                  setCompanyFilters((current) => ({
                    ...current,
                    sourceState: event.target.value,
                  }))
                }
              >
                {SOURCE_STATE_FILTER_OPTIONS.map((option) => (
                  <option key={option.value || "all"} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>
            <div className="field compact-field company-filter-actions">
              <span>Results</span>
              <div className="toolbar">
                <span className="metric-chip">
                  Showing {filteredCompanies.length} of {companiesState.data.length}
                </span>
                <button
                  type="button"
                  className="ghost-link buttonish"
                  onClick={() =>
                    setCompanyFilters({
                      lifecycleStatus: "",
                      sourceState: "",
                    })
                  }
                >
                  Reset filters
                </button>
              </div>
            </div>
          </div>
          {companiesState.error ? <p className="inline-error">{companiesState.error}</p> : null}
          {companiesState.loading ? (
            <section className="empty-panel">
              <p className="eyebrow">Loading</p>
              <h2>Fetching tracked companies.</h2>
              <p>The registry is loading from the API.</p>
            </section>
          ) : filteredCompanies.length ? (
            <div className="jobs-table-wrap company-table-wrap">
              <table className="jobs-table company-table">
                <thead>
                  <tr>
                    <th className="company-selection-cell">
                      <input
                        ref={selectAllCheckboxRef}
                        type="checkbox"
                        aria-label="Select all visible companies"
                        checked={allVisibleCompaniesSelected}
                        onChange={(event) => onToggleVisibleCompanySelection(event.target.checked)}
                      />
                    </th>
                    <th>Company</th>
                    <th>Lifecycle</th>
                    <th>Source</th>
                    <th>Source status</th>
                    <th>Updated</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredCompanies.map((company) => {
                    const source = primarySource(company);
                    return (
                      <tr
                        key={company.id}
                        className={company.id === selectedCompanyId ? "is-selected" : ""}
                      >
                        <td className="company-selection-cell">
                          <input
                            type="checkbox"
                            aria-label={`Select ${company.name}`}
                            checked={selectedCompanyIds.includes(company.id)}
                            onChange={() => onToggleCompanySelection(company.id)}
                          />
                        </td>
                        <td>
                          <button
                            type="button"
                            className="table-link company-name-button"
                            onClick={() => onInspectCompany(company.id)}
                          >
                            {company.name}
                          </button>
                          <p className="company-row-subtle">{company.slug}</p>
                        </td>
                        <td>
                          <span className="tag">{company.lifecycle_status}</span>
                        </td>
                        <td>{source?.source_type ?? "source pending"}</td>
                        <td>
                          {source === null
                            ? "source missing"
                            : source.is_enabled
                              ? "source enabled"
                              : "source paused"}
                        </td>
                        <td>Updated {formatUpdatedDate(company.updated_at)}</td>
                        <td>
                          <div className="company-row-actions">
                            <button
                              type="button"
                              className="ghost-link buttonish"
                              onClick={() => onInspectCompany(company.id)}
                            >
                              Inspect
                            </button>
                            <button
                              type="button"
                              className="ghost-link buttonish"
                              onClick={() => onEditCompany(company)}
                            >
                              Edit
                            </button>
                            <button
                              type="button"
                              className="ghost-link buttonish"
                              onClick={() => onManualSync(company.id)}
                            >
                              Queue sync
                            </button>
                            <Link href={buildJobsHref(company.id)} className="primary-link">
                              View jobs
                            </Link>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          ) : companiesState.data.length ? (
            <section className="empty-panel compact-panel">
              <p className="eyebrow">No matches</p>
              <h2>No companies match your filters.</h2>
              <p>Adjust lifecycle or source state filters to widen the results.</p>
            </section>
          ) : (
            <section className="empty-panel">
              <p className="eyebrow">Empty</p>
              <h2>No companies are tracked yet.</h2>
              <p>Create one below to start collecting jobs from a source.</p>
            </section>
          )}
        </div>

        <aside className="detail-panel company-detail-panel">
          {selectedCompany ? (
            <div className="company-detail-stack">
              <div className="detail-actions">
                <p className="eyebrow">Selected company</p>
                <div className="job-actions">
                  <button
                    type="button"
                    className="ghost-link buttonish"
                    onClick={() => setDraft(companyDraftFromRecord(selectedCompany))}
                  >
                    Edit company
                  </button>
                  <button
                    type="button"
                    className="primary-link buttonish"
                    onClick={() => onManualSync(selectedCompany.id)}
                  >
                    Queue sync
                  </button>
                </div>
              </div>
              <h2>{selectedCompany.name}</h2>
              <p className="detail-description">
                {selectedCompany.description ||
                  "This company is in the registry and ready to route into the jobs stream."}
              </p>
              <div className="detail-stack">
                <span className="tag">{selectedCompany.lifecycle_status}</span>
                <span className="tag">
                  {selectedCompanyPrimarySource?.source_type ?? "source pending"}
                </span>
                <span className="tag">
                  {selectedCompanyPrimarySource?.is_enabled ? "source enabled" : "source paused"}
                </span>
              </div>
              <div className="detail-meta">
                <span>Updated {formatUpdatedDate(selectedCompany.updated_at)}</span>
                <span>{selectedCompany.slug}</span>
              </div>
              {selectedCompany.website_url ? (
                <a
                  href={selectedCompany.website_url}
                  target="_blank"
                  rel="noreferrer"
                  className="table-link"
                >
                  Visit company website
                </a>
              ) : null}
              <div className="company-detail-jobs">
                <div className="editor-heading">
                  <div>
                    <p className="eyebrow">Latest jobs</p>
                    <h2>Recent roles</h2>
                  </div>
                  <Link href={buildJobsHref(selectedCompany.id)} className="ghost-link">
                    See all jobs
                  </Link>
                </div>
                {companyJobsState.error ? (
                  <p className="inline-error">{companyJobsState.error}</p>
                ) : companyJobsState.loading ? (
                  <p>Loading jobs for this company...</p>
                ) : companyJobsState.data.length ? (
                  <div className="company-role-list">
                    {companyJobsState.data.map((job) => (
                      <article key={job.id} className="company-role-item">
                        <div>
                          <strong>{job.title}</strong>
                          <p>
                            {job.location_text || "Location flexible"} · {job.work_mode || "mode pending"}
                          </p>
                        </div>
                        <span className="metric-chip">{formatPostedDate(job.posted_at)}</span>
                      </article>
                    ))}
                  </div>
                ) : (
                  <p>No jobs are currently attached to this company.</p>
                )}
              </div>
            </div>
          ) : (
            <div className="company-detail-stack">
              <p className="eyebrow">Companies</p>
              <h2>Select a company to inspect it in more detail.</h2>
              <p className="detail-description">
                The detail panel keeps source state and the latest roles visible while you move
                through the company registry.
              </p>
            </div>
          )}
        </aside>
      </section>

      <form className="editor-panel" onSubmit={onCompanySubmit}>
        <div className="editor-heading">
          <div>
            <p className="eyebrow">{draft.id ? "Edit company" : "Create company"}</p>
            <h2>{draft.id ? draft.name || "Company draft" : "New company"}</h2>
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
              onChange={(event) => setDraft((current) => ({ ...current, slug: event.target.value }))}
              placeholder="openai"
            />
          </label>
          <label className="field">
            <span>Name</span>
            <input
              value={draft.name}
              onChange={(event) => setDraft((current) => ({ ...current, name: event.target.value }))}
              placeholder="OpenAI"
            />
          </label>
        </div>

        <div className="panel-row">
          <label className="field">
            <span>Website URL</span>
            <input
              value={draft.websiteUrl}
              onChange={(event) =>
                setDraft((current) => ({ ...current, websiteUrl: event.target.value }))
              }
              placeholder="https://openai.com"
            />
          </label>
          <label className="field">
            <span>Lifecycle</span>
            <select
              value={draft.lifecycleStatus}
              onChange={(event) =>
                setDraft((current) => ({ ...current, lifecycleStatus: event.target.value }))
              }
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
            onChange={(event) =>
              setDraft((current) => ({ ...current, description: event.target.value }))
            }
            placeholder="Why this company is worth tracking."
          />
        </label>

        <div className="panel-row">
          <label className="field">
            <span>Source type</span>
            <select
              value={draft.sourceType}
              onChange={(event) =>
                setDraft((current) => ({ ...current, sourceType: event.target.value }))
              }
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
              onChange={(event) =>
                setDraft((current) => ({ ...current, isEnabled: event.target.value === "yes" }))
              }
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
              onChange={(event) =>
                setDraft((current) => ({ ...current, externalKey: event.target.value }))
              }
              placeholder="openai"
            />
          </label>
          <label className="field">
            <span>Base URL</span>
            <input
              value={draft.baseUrl}
              onChange={(event) => setDraft((current) => ({ ...current, baseUrl: event.target.value }))}
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
    </AppShell>
  );
}
