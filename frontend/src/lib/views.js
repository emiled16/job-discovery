import { createDashboardSearch } from "./dashboard";

export function createEmptyViewDraft() {
  return {
    id: "",
    name: "",
    title: "",
    location: "",
    companyIds: [],
    workModes: [],
    postedAfter: "",
    postedBefore: "",
    sortField: "posted_at",
    sortDirection: "desc",
    isDefault: false,
  };
}

function asArray(value) {
  return Array.isArray(value) ? value.filter(Boolean) : [];
}

export function viewDraftFromRecord(view) {
  if (!view) {
    return createEmptyViewDraft();
  }

  return {
    id: view.id,
    name: view.name ?? "",
    title: view.filters?.title ?? "",
    location: view.filters?.location ?? "",
    companyIds: asArray(view.filters?.company_ids),
    workModes: asArray(view.filters?.work_modes),
    postedAfter: view.filters?.posted_after ?? "",
    postedBefore: view.filters?.posted_before ?? "",
    sortField: view.sort?.field ?? "posted_at",
    sortDirection: view.sort?.direction ?? "desc",
    isDefault: Boolean(view.is_default),
  };
}

export function buildViewPayload(draft) {
  return {
    name: draft.name.trim(),
    filters: {
      title: draft.title.trim() || null,
      location: draft.location.trim() || null,
      company_ids: asArray(draft.companyIds),
      work_modes: asArray(draft.workModes),
      posted_after: draft.postedAfter || null,
      posted_before: draft.postedBefore || null,
    },
    sort: {
      field: draft.sortField,
      direction: draft.sortDirection,
    },
    is_default: Boolean(draft.isDefault),
  };
}

export function savedViewToDashboardSearch(viewLike) {
  const draft =
    "sortField" in viewLike && "sortDirection" in viewLike
      ? viewLike
      : viewDraftFromRecord(viewLike);
  return createDashboardSearch({
    title: draft.title,
    location: draft.location,
    companyIds: draft.companyIds,
    workModes: draft.workModes,
    postedAfter: draft.postedAfter,
    postedBefore: draft.postedBefore,
    sort: draft.sortField,
    order: draft.sortDirection,
    page: 1,
    perPage: 12,
    selectedJobId: "",
  });
}
