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
const PER_PAGE_OPTIONS = [12, 25, 50, 100];

function FilterToggleGroup({ label, options, selectedValues, onToggle, emptyLabel }) {
  return (
    <div className="filter-section">
      <div className="filter-section-head">
        <span>{label}</span>
        <small>{selectedValues.length ? `${selectedValues.length} selected` : emptyLabel}</small>
      </div>
      <div className="filter-choice-grid">
        {options.map((option) => (
          <button
            key={option.value}
            type="button"
            className={
              selectedValues.includes(option.value) ? "filter-chip is-active" : "filter-chip"
            }
            onClick={() => onToggle(option.value)}
          >
            {option.label}
          </button>
        ))}
      </div>
    </div>
  );
}

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
      router.push(`/jobs?${createDashboardSearch(nextState)}`, { scroll: false });
    });
  }

  function updateFilterDraft(key, value) {
    setFilterDraft((current) => ({ ...current, [key]: value }));
  }

  function toggleMultiValue(key, value) {
    setFilterDraft((current) => {
      const currentValues = current[key] ?? [];
      const nextValues = currentValues.includes(value)
        ? currentValues.filter((entry) => entry !== value)
        : [...currentValues, value];
      return { ...current, [key]: nextValues };
    });
  }

  function onApplyFilters(event) {
    event.preventDefault();
    pushState({
      ...filterDraft,
      page: 1,
      perPage: state.perPage,
      sort: state.sort,
      order: state.order,
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
      selectedJobId: "",
    });
  }

  function onSortChange(value) {
    const [sort, order] = value.split(":");
    pushState({ ...state, sort, order, page: 1 });
  }

  function onPerPageChange(value) {
    const parsed = Number.parseInt(value, 10);
    if (!Number.isInteger(parsed) || parsed < 1) {
      return;
    }
    pushState({ ...state, perPage: Math.min(parsed, 100), page: 1, selectedJobId: "" });
  }

  function onPageChange(page) {
    pushState({ ...state, page, selectedJobId: "" });
  }

  function buildSelectSearch(jobId) {
    return createDashboardSearch({ ...state, selectedJobId: jobId });
  }

  const resultLabel =
    jobsState.meta.total === 1 ? "1 live role" : `${jobsState.meta.total} live roles`;
  const selectedCompanyNames = companies
    .filter((company) => filterDraft.companyIds.includes(company.id))
    .map((company) => company.name);

  return (
    <AppShell
      eyebrow="Jobs"
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
            <div className="filter-heading">
              <div>
                <p className="eyebrow">Search filters</p>
                <h2>Shape the jobs stream.</h2>
              </div>
              <p>Keep the result set narrow without losing the live detail panel.</p>
            </div>

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
            <FilterToggleGroup
              label="Companies"
              options={companies.map((company) => ({ value: company.id, label: company.name }))}
              selectedValues={filterDraft.companyIds}
              onToggle={(value) => toggleMultiValue("companyIds", value)}
              emptyLabel="all companies"
            />
            <FilterToggleGroup
              label="Work modes"
              options={defaultWorkModes().map((mode) => ({ value: mode, label: mode }))}
              selectedValues={filterDraft.workModes}
              onToggle={(value) => toggleMultiValue("workModes", value)}
              emptyLabel="all modes"
            />
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
            {filterDraft.title ||
            filterDraft.location ||
            selectedCompanyNames.length ||
            filterDraft.workModes.length ||
            filterDraft.postedAfter ||
            filterDraft.postedBefore ? (
              <div className="filter-summary">
                {filterDraft.title ? <span className="metric-chip">Title: {filterDraft.title}</span> : null}
                {filterDraft.location ? (
                  <span className="metric-chip">Location: {filterDraft.location}</span>
                ) : null}
                {selectedCompanyNames.map((name) => (
                  <span key={name} className="metric-chip">
                    {name}
                  </span>
                ))}
                {filterDraft.workModes.map((mode) => (
                  <span key={mode} className="metric-chip">
                    {mode}
                  </span>
                ))}
                {filterDraft.postedAfter ? (
                  <span className="metric-chip">After {filterDraft.postedAfter}</span>
                ) : null}
                {filterDraft.postedBefore ? (
                  <span className="metric-chip">Before {filterDraft.postedBefore}</span>
                ) : null}
              </div>
            ) : null}
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
                <label className="field compact-field">
                  <span>Per page</span>
                  <select
                    value={String(state.perPage)}
                    onChange={(event) => onPerPageChange(event.target.value)}
                  >
                    {PER_PAGE_OPTIONS.includes(state.perPage) ? null : (
                      <option value={String(state.perPage)}>{state.perPage}</option>
                    )}
                    {PER_PAGE_OPTIONS.map((option) => (
                      <option key={option} value={String(option)}>
                        {option}
                      </option>
                    ))}
                  </select>
                </label>
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
            closeHref={`/jobs?${createDashboardSearch({ ...state, selectedJobId: "" })}`}
          />
        )}
      </section>
    </AppShell>
  );
}
