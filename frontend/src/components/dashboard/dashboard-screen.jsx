"use client";

import { useEffect, useState, useTransition } from "react";
import { useRouter, useSearchParams } from "next/navigation";

import { AppShell } from "src/components/ui/app-shell";
import { ApiClientError, createBrowserApiClient } from "src/lib/api/client";
import {
  createDashboardSearch,
  dashboardQueryFromState,
  defaultWorkModes,
  parseDashboardState,
} from "src/lib/dashboard";

import { JobDetailPanel } from "./job-detail-panel";
import { JobResults } from "./job-results";

const api = createBrowserApiClient();

const SORT_OPTIONS = [
  { value: "posted_at:desc", label: "Newest first" },
  { value: "posted_at:asc", label: "Oldest first" },
  { value: "company_name:asc", label: "Company A-Z" },
  { value: "title:asc", label: "Title A-Z" },
];

export function DashboardScreen() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [isRouting, startRouting] = useTransition();
  const [companies, setCompanies] = useState([]);
  const [jobsState, setJobsState] = useState({
    data: [],
    meta: { page: 1, per_page: 12, total: 0, total_pages: 0 },
    loading: true,
    error: "",
  });
  const [detailState, setDetailState] = useState({
    data: null,
    loading: false,
    error: "",
  });
  const [filterDraft, setFilterDraft] = useState(() => parseDashboardState(new URLSearchParams()));

  const state = parseDashboardState(searchParams);
  const searchKey = searchParams.toString();

  useEffect(() => {
    setFilterDraft(state);
  }, [searchKey]);

  useEffect(() => {
    let active = true;

    api
      .getCompanies()
      .then((response) => {
        if (active) {
          setCompanies(response.data);
        }
      })
      .catch(() => {
        if (active) {
          setCompanies([]);
        }
      });

    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    let active = true;
    setJobsState((current) => ({ ...current, loading: true, error: "" }));

    api
      .getJobs(dashboardQueryFromState(state))
      .then((response) => {
        if (!active) {
          return;
        }
        setJobsState({
          data: response.data,
          meta: response.meta,
          loading: false,
          error: "",
        });
      })
      .catch((caughtError) => {
        if (!active) {
          return;
        }
        setJobsState({
          data: [],
          meta: { page: 1, per_page: state.perPage, total: 0, total_pages: 0 },
          loading: false,
          error:
            caughtError instanceof ApiClientError
              ? caughtError.message
              : "Could not load jobs right now",
        });
      });

    return () => {
      active = false;
    };
  }, [searchKey]);

  useEffect(() => {
    if (!state.selectedJobId) {
      setDetailState({ data: null, loading: false, error: "" });
      return;
    }

    let active = true;
    setDetailState((current) => ({ ...current, loading: true, error: "" }));

    api
      .getJob(state.selectedJobId)
      .then((response) => {
        if (active) {
          setDetailState({ data: response.data, loading: false, error: "" });
        }
      })
      .catch((caughtError) => {
        if (active) {
          setDetailState({
            data: null,
            loading: false,
            error:
              caughtError instanceof ApiClientError
                ? caughtError.message
                : "Could not load role details",
          });
        }
      });

    return () => {
      active = false;
    };
  }, [state.selectedJobId]);

  function pushState(nextState) {
    startRouting(() => {
      router.push(`/dashboard?${createDashboardSearch(nextState)}`, { scroll: false });
    });
  }

  function updateFilterDraft(key, value) {
    setFilterDraft((current) => ({ ...current, [key]: value }));
  }

  function onMultiSelectChange(event, key) {
    const values = Array.from(event.target.selectedOptions, (option) => option.value);
    updateFilterDraft(key, values);
  }

  function onApplyFilters(event) {
    event.preventDefault();
    pushState({
      ...filterDraft,
      page: 1,
      perPage: state.perPage,
      sort: state.sort,
      order: state.order,
      viewMode: state.viewMode,
      selectedJobId: "",
    });
  }

  function onResetFilters() {
    pushState({
      title: "",
      location: "",
      companyIds: [],
      workModes: [],
      postedAfter: "",
      postedBefore: "",
      sort: state.sort,
      order: state.order,
      page: 1,
      perPage: state.perPage,
      viewMode: state.viewMode,
      selectedJobId: "",
    });
  }

  function onSortChange(value) {
    const [sort, order] = value.split(":");
    pushState({ ...state, sort, order, page: 1 });
  }

  function onViewModeChange(viewMode) {
    pushState({ ...state, viewMode });
  }

  function onPageChange(page) {
    pushState({ ...state, page, selectedJobId: "" });
  }

  function buildSelectSearch(jobId) {
    return createDashboardSearch({ ...state, selectedJobId: jobId });
  }

  const resultLabel =
    jobsState.meta.total === 1 ? "1 live role" : `${jobsState.meta.total} live roles`;

  return (
    <AppShell
      eyebrow="Dashboard"
      title="Search the live pipeline."
      description="Browse normalized roles, keep filters stable, and mark progress without leaving the result stream."
      actions={
        <div className="toolbar">
          <span className="metric-chip">{resultLabel}</span>
          <span className="metric-chip">
            {jobsState.meta.total_pages || 0} pages
          </span>
        </div>
      }
    >
      <section className="dashboard-shell">
        <div className="dashboard-controls">
          <form className="control-panel" onSubmit={onApplyFilters}>
            <div className="panel-row">
              <label className="field">
                <span>Title</span>
                <input
                  value={filterDraft.title}
                  onChange={(event) => updateFilterDraft("title", event.target.value)}
                  placeholder="ML engineer"
                />
              </label>
              <label className="field">
                <span>Location</span>
                <input
                  value={filterDraft.location}
                  onChange={(event) => updateFilterDraft("location", event.target.value)}
                  placeholder="Toronto"
                />
              </label>
            </div>
            <div className="panel-row">
              <label className="field">
                <span>Companies</span>
                <select
                  multiple
                  value={filterDraft.companyIds}
                  onChange={(event) => onMultiSelectChange(event, "companyIds")}
                >
                  {companies.map((company) => (
                    <option key={company.id} value={company.id}>
                      {company.name}
                    </option>
                  ))}
                </select>
              </label>
              <label className="field">
                <span>Work modes</span>
                <select
                  multiple
                  value={filterDraft.workModes}
                  onChange={(event) => onMultiSelectChange(event, "workModes")}
                >
                  {defaultWorkModes().map((mode) => (
                    <option key={mode} value={mode}>
                      {mode}
                    </option>
                  ))}
                </select>
              </label>
            </div>
            <div className="panel-row panel-row-dates">
              <label className="field">
                <span>Posted after</span>
                <input
                  type="date"
                  value={filterDraft.postedAfter}
                  onChange={(event) => updateFilterDraft("postedAfter", event.target.value)}
                />
              </label>
              <label className="field">
                <span>Posted before</span>
                <input
                  type="date"
                  value={filterDraft.postedBefore}
                  onChange={(event) => updateFilterDraft("postedBefore", event.target.value)}
                />
              </label>
            </div>
            <div className="panel-actions">
              <button className="primary-link buttonish" type="submit" disabled={isRouting}>
                {isRouting ? "Applying..." : "Apply filters"}
              </button>
              <button className="ghost-link buttonish" type="button" onClick={onResetFilters}>
                Reset
              </button>
            </div>
          </form>

          <div className="results-panel">
            <div className="results-toolbar">
              <div className="toolbar-group">
                <label className="field compact-field">
                  <span>Sort</span>
                  <select
                    value={`${state.sort}:${state.order}`}
                    onChange={(event) => onSortChange(event.target.value)}
                  >
                    {SORT_OPTIONS.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </label>
              </div>
              <div className="segmented-control" aria-label="Result layout">
                <button
                  type="button"
                  className={state.viewMode === "card" ? "segment is-active" : "segment"}
                  onClick={() => onViewModeChange("card")}
                >
                  Cards
                </button>
                <button
                  type="button"
                  className={state.viewMode === "table" ? "segment is-active" : "segment"}
                  onClick={() => onViewModeChange("table")}
                >
                  Table
                </button>
              </div>
            </div>

            {jobsState.error ? <p className="inline-error">{jobsState.error}</p> : null}
            {jobsState.loading ? (
              <section className="empty-panel">
                <p className="eyebrow">Loading</p>
                <h2>Fetching the latest roles.</h2>
                <p>The dashboard is refreshing against the API right now.</p>
              </section>
            ) : (
              <JobResults
                jobs={jobsState.data}
                emptyMessage="Try widening the title, location, company, or date range."
                selectedJobId={state.selectedJobId}
                viewMode={state.viewMode}
                buildSelectSearch={buildSelectSearch}
              />
            )}

            <div className="pagination-bar">
              <button
                type="button"
                className="ghost-link buttonish"
                onClick={() => onPageChange(Math.max(1, jobsState.meta.page - 1))}
                disabled={jobsState.meta.page <= 1}
              >
                Previous
              </button>
              <span>
                Page {jobsState.meta.page} of {Math.max(jobsState.meta.total_pages, 1)}
              </span>
              <button
                type="button"
                className="ghost-link buttonish"
                onClick={() =>
                  onPageChange(
                    Math.min(
                      Math.max(jobsState.meta.total_pages, 1),
                      jobsState.meta.page + 1,
                    ),
                  )
                }
                disabled={jobsState.meta.page >= Math.max(jobsState.meta.total_pages, 1)}
              >
                Next
              </button>
            </div>
          </div>
        </div>

        {detailState.error ? <p className="inline-error">{detailState.error}</p> : null}
        {detailState.loading ? (
          <aside className="detail-panel detail-panel-empty">
            <p className="eyebrow">Job detail</p>
            <h2>Loading role detail.</h2>
            <p>The current selection is being resolved from the API.</p>
          </aside>
        ) : (
          <JobDetailPanel
            job={detailState.data}
            closeHref={`/dashboard?${createDashboardSearch({ ...state, selectedJobId: "" })}`}
          />
        )}
      </section>
    </AppShell>
  );
}
