"use client";

import { useEffect, useState } from "react";

import { AppShell } from "src/components/ui/app-shell";
import { ApiClientError, createBrowserApiClient } from "src/lib/api/client";

import { SummaryChart } from "./summary-chart";

const api = createBrowserApiClient();

function createDefaultFilters() {
  return {
    bucket: "week",
    startDate: "",
    endDate: "",
  };
}

function formatPercent(value) {
  return `${Math.round((value ?? 0) * 100)}%`;
}

export function SummaryScreen() {
  const [filters, setFilters] = useState(createDefaultFilters());
  const [metricsState, setMetricsState] = useState({
    data: null,
    loading: true,
    error: "",
  });
  const [seriesState, setSeriesState] = useState({
    data: [],
    loading: true,
    error: "",
  });

  useEffect(() => {
    void loadMetrics();
  }, []);

  useEffect(() => {
    void loadSeries();
  }, [filters.bucket, filters.startDate, filters.endDate]);

  async function loadMetrics() {
    setMetricsState((current) => ({ ...current, loading: true, error: "" }));
    try {
      const response = await api.getSummaryMetrics();
      setMetricsState({ data: response.data, loading: false, error: "" });
    } catch (caughtError) {
      setMetricsState({
        data: null,
        loading: false,
        error:
          caughtError instanceof ApiClientError
            ? caughtError.message
            : "Could not load summary metrics",
      });
    }
  }

  async function loadSeries() {
    setSeriesState((current) => ({ ...current, loading: true, error: "" }));
    try {
      const response = await api.getSummaryTimeseries({
        bucket: filters.bucket,
        start_date: filters.startDate || undefined,
        end_date: filters.endDate || undefined,
      });
      setSeriesState({ data: response.data, loading: false, error: "" });
    } catch (caughtError) {
      setSeriesState({
        data: [],
        loading: false,
        error:
          caughtError instanceof ApiClientError
            ? caughtError.message
            : "Could not load trend data",
      });
    }
  }

  const metrics = metricsState.data ?? {
    total_jobs: 0,
    applied_jobs: 0,
    saved_views: 0,
    application_rate: 0,
  };

  return (
    <AppShell
      eyebrow="Summary"
      title="Measure search progress, not just raw volume."
      description="Track live job coverage, applications, saved-view inventory, and the cadence of your search over time."
      actions={
        <div className="toolbar">
          <span className="metric-chip">{metrics.total_jobs} active roles</span>
          <span className="metric-chip">{formatPercent(metrics.application_rate)} application rate</span>
        </div>
      }
    >
      <section className="summary-stack">
        {metricsState.error ? <p className="inline-error">{metricsState.error}</p> : null}
        <div className="kpi-grid">
          <article className="kpi-card">
            <p className="eyebrow">Live jobs</p>
            <strong>{metricsState.loading ? "..." : metrics.total_jobs}</strong>
            <span>Roles currently active in the aggregated feed.</span>
          </article>
          <article className="kpi-card">
            <p className="eyebrow">Applied</p>
            <strong>{metricsState.loading ? "..." : metrics.applied_jobs}</strong>
            <span>Tracked applications that moved beyond a saved state.</span>
          </article>
          <article className="kpi-card">
            <p className="eyebrow">Saved views</p>
            <strong>{metricsState.loading ? "..." : metrics.saved_views}</strong>
            <span>Reusable searches available for quick dashboard resets.</span>
          </article>
          <article className="kpi-card">
            <p className="eyebrow">Rate</p>
            <strong>{metricsState.loading ? "..." : formatPercent(metrics.application_rate)}</strong>
            <span>Applied jobs divided by currently active jobs.</span>
          </article>
        </div>

        <div className="summary-toolbar">
          <label className="field compact-field">
            <span>Bucket</span>
            <select
              value={filters.bucket}
              onChange={(event) =>
                setFilters((current) => ({ ...current, bucket: event.target.value }))
              }
            >
              <option value="week">Week</option>
              <option value="day">Day</option>
            </select>
          </label>
          <label className="field compact-field">
            <span>Start date</span>
            <input
              type="date"
              value={filters.startDate}
              onChange={(event) =>
                setFilters((current) => ({ ...current, startDate: event.target.value }))
              }
            />
          </label>
          <label className="field compact-field">
            <span>End date</span>
            <input
              type="date"
              value={filters.endDate}
              onChange={(event) =>
                setFilters((current) => ({ ...current, endDate: event.target.value }))
              }
            />
          </label>
        </div>

        {seriesState.error ? <p className="inline-error">{seriesState.error}</p> : null}
        {seriesState.loading ? (
          <section className="empty-panel">
            <p className="eyebrow">Loading</p>
            <h2>Refreshing the application trend.</h2>
            <p>The summary page is querying the latest timeseries buckets.</p>
          </section>
        ) : (
          <SummaryChart series={seriesState.data} bucket={filters.bucket} />
        )}
      </section>
    </AppShell>
  );
}
