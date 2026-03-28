"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { AppShell } from "src/components/ui/app-shell";
import { ApiClientError, createBrowserApiClient } from "src/lib/api/client";
import {
  buildViewPayload,
  createEmptyViewDraft,
  savedViewToDashboardSearch,
  viewDraftFromRecord,
} from "src/lib/views";

const api = createBrowserApiClient();

const SORT_OPTIONS = [
  { value: "posted_at", label: "Posted date" },
  { value: "company_name", label: "Company name" },
  { value: "title", label: "Title" },
];

export function ViewsScreen() {
  const [companies, setCompanies] = useState([]);
  const [viewsState, setViewsState] = useState({
    views: [],
    loading: true,
    error: "",
  });
  const [draft, setDraft] = useState(createEmptyViewDraft());
  const [formError, setFormError] = useState("");
  const [formStatus, setFormStatus] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    void loadPageData();
  }, []);

  async function loadPageData(nextSelectedId = "") {
    setViewsState((current) => ({ ...current, loading: true, error: "" }));

    try {
      const [viewsResponse, companiesResponse] = await Promise.all([
        api.getViews(),
        api.getCompanies(),
      ]);
      setCompanies(companiesResponse.data);
      setViewsState({
        views: viewsResponse.data,
        loading: false,
        error: "",
      });

      const selectedView =
        viewsResponse.data.find((view) => view.id === nextSelectedId) ??
        viewsResponse.data.find((view) => view.id === draft.id) ??
        viewsResponse.data[0];
      setDraft(selectedView ? viewDraftFromRecord(selectedView) : createEmptyViewDraft());
    } catch (caughtError) {
      setViewsState({
        views: [],
        loading: false,
        error:
          caughtError instanceof ApiClientError
            ? caughtError.message
            : "Could not load saved views",
      });
    }
  }

  function selectView(view) {
    setFormError("");
    setFormStatus("");
    setDraft(viewDraftFromRecord(view));
  }

  function updateDraft(key, value) {
    setDraft((current) => ({ ...current, [key]: value }));
  }

  function onMultiSelectChange(event, key) {
    updateDraft(
      key,
      Array.from(event.target.selectedOptions, (option) => option.value),
    );
  }

  async function onSubmit(event) {
    event.preventDefault();
    setFormError("");
    setFormStatus("");

    if (!draft.name.trim()) {
      setFormError("View name is required.");
      return;
    }

    setSaving(true);
    try {
      const payload = buildViewPayload(draft);
      const response = draft.id
        ? await api.updateView(draft.id, payload)
        : await api.createView(payload);

      setFormStatus(draft.id ? "View updated." : "View created.");
      await loadPageData(response.data.id);
    } catch (caughtError) {
      setFormError(
        caughtError instanceof ApiClientError
          ? caughtError.message
          : "Could not save this view",
      );
    } finally {
      setSaving(false);
    }
  }

  async function onDelete() {
    if (!draft.id) {
      return;
    }

    setFormError("");
    setFormStatus("");
    setSaving(true);
    try {
      await api.deleteView(draft.id);
      setDraft(createEmptyViewDraft());
      setFormStatus("View deleted.");
      await loadPageData();
    } catch (caughtError) {
      setFormError(
        caughtError instanceof ApiClientError
          ? caughtError.message
          : "Could not delete this view",
      );
    } finally {
      setSaving(false);
    }
  }

  return (
    <AppShell
      eyebrow="Saved views"
      title="Reuse the queries that matter."
      description="Create, edit, delete, and apply named job searches so the dashboard comes back exactly where you need it."
      actions={
        <div className="toolbar">
          <span className="metric-chip">
            {viewsState.views.length === 1 ? "1 saved view" : `${viewsState.views.length} saved views`}
          </span>
          <button
            type="button"
            className="ghost-link buttonish"
            onClick={() => {
              setFormError("");
              setFormStatus("");
              setDraft(createEmptyViewDraft());
            }}
          >
            New view
          </button>
        </div>
      }
    >
      <section className="management-grid">
        <aside className="collection-panel">
          <p className="eyebrow">Library</p>
          <h2>Saved query set</h2>
          <p>Default views float to the top and can be applied directly to the dashboard.</p>
          {viewsState.error ? <p className="inline-error">{viewsState.error}</p> : null}
          {viewsState.loading ? (
            <p>Loading saved views...</p>
          ) : viewsState.views.length ? (
            <div className="collection-list">
              {viewsState.views.map((view) => (
                <article
                  key={view.id}
                  className={draft.id === view.id ? "collection-item is-active" : "collection-item"}
                >
                  <span>
                    <strong>{view.name}</strong>
                    <small>{view.is_default ? "Default view" : "Custom view"}</small>
                  </span>
                  <div className="job-actions">
                    <button
                      type="button"
                      className="ghost-link buttonish"
                      onClick={() => selectView(view)}
                    >
                      Edit
                    </button>
                    <Link
                      href={`/dashboard?${savedViewToDashboardSearch(view)}`}
                      className="ghost-link"
                    >
                      Apply
                    </Link>
                  </div>
                </article>
              ))}
            </div>
          ) : (
            <section className="empty-panel compact-panel">
              <p className="eyebrow">No views</p>
              <h2>Create your first saved search.</h2>
              <p>Store the filters you revisit instead of rebuilding them from scratch.</p>
            </section>
          )}
        </aside>

        <form className="editor-panel" onSubmit={onSubmit}>
          <div className="editor-heading">
            <div>
              <p className="eyebrow">{draft.id ? "Edit view" : "Create view"}</p>
              <h2>{draft.id ? draft.name : "New saved query"}</h2>
            </div>
            {draft.id ? (
              <Link href={`/dashboard?${savedViewToDashboardSearch(draft)}`} className="primary-link">
                Open in dashboard
              </Link>
            ) : null}
          </div>

          <div className="panel-row">
            <label className="field">
              <span>Name</span>
              <input
                value={draft.name}
                onChange={(event) => updateDraft("name", event.target.value)}
                placeholder="Remote ML in Canada"
              />
            </label>
            <label className="field">
              <span>Title keyword</span>
              <input
                value={draft.title}
                onChange={(event) => updateDraft("title", event.target.value)}
                placeholder="ML Engineer"
              />
            </label>
          </div>

          <div className="panel-row">
            <label className="field">
              <span>Location</span>
              <input
                value={draft.location}
                onChange={(event) => updateDraft("location", event.target.value)}
                placeholder="Toronto"
              />
            </label>
            <label className="field">
              <span>Default view</span>
              <select
                value={draft.isDefault ? "yes" : "no"}
                onChange={(event) => updateDraft("isDefault", event.target.value === "yes")}
              >
                <option value="no">No</option>
                <option value="yes">Yes</option>
              </select>
            </label>
          </div>

          <div className="panel-row">
            <label className="field">
              <span>Companies</span>
              <select
                multiple
                value={draft.companyIds}
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
                value={draft.workModes}
                onChange={(event) => onMultiSelectChange(event, "workModes")}
              >
                <option value="remote">remote</option>
                <option value="hybrid">hybrid</option>
                <option value="onsite">onsite</option>
              </select>
            </label>
          </div>

          <div className="panel-row">
            <label className="field">
              <span>Posted after</span>
              <input
                type="date"
                value={draft.postedAfter}
                onChange={(event) => updateDraft("postedAfter", event.target.value)}
              />
            </label>
            <label className="field">
              <span>Posted before</span>
              <input
                type="date"
                value={draft.postedBefore}
                onChange={(event) => updateDraft("postedBefore", event.target.value)}
              />
            </label>
          </div>

          <div className="panel-row">
            <label className="field">
              <span>Sort field</span>
              <select
                value={draft.sortField}
                onChange={(event) => updateDraft("sortField", event.target.value)}
              >
                {SORT_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>
            <label className="field">
              <span>Direction</span>
              <select
                value={draft.sortDirection}
                onChange={(event) => updateDraft("sortDirection", event.target.value)}
              >
                <option value="desc">Descending</option>
                <option value="asc">Ascending</option>
              </select>
            </label>
          </div>

          {formError ? <p className="inline-error">{formError}</p> : null}
          {formStatus ? <p className="inline-success">{formStatus}</p> : null}

          <div className="panel-actions">
            <button className="primary-link buttonish" type="submit" disabled={saving}>
              {saving ? "Saving..." : draft.id ? "Save changes" : "Create view"}
            </button>
            {draft.id ? (
              <button
                className="ghost-link buttonish"
                type="button"
                disabled={saving}
                onClick={onDelete}
              >
                Delete view
              </button>
            ) : null}
          </div>
        </form>
      </section>
    </AppShell>
  );
}
