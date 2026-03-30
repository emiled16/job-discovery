const DEFAULT_PER_PAGE = 12;
const MAX_PER_PAGE = 100;
const DEFAULT_SORT = "posted_at";
const DEFAULT_ORDER = "desc";
const DEFAULT_WORK_MODES = ["remote", "hybrid", "onsite"];

function asArray(value) {
  if (Array.isArray(value)) {
    return value.filter(Boolean);
  }
  if (typeof value === "string" && value) {
    return [value];
  }
  return [];
}

function asPositiveInt(value, fallback) {
  const parsed = Number.parseInt(String(value ?? ""), 10);
  return Number.isInteger(parsed) && parsed > 0 ? parsed : fallback;
}

export function parseDashboardState(searchParamsLike) {
  const params =
    searchParamsLike instanceof URLSearchParams
      ? searchParamsLike
      : new URLSearchParams(searchParamsLike ?? {});

  const companyIds = params.getAll("company_ids");
  const workModes = params.getAll("work_modes");
  const selectedJobId = params.get("job_id") ?? "";

  return {
    title: params.get("title") ?? "",
    location: params.get("location") ?? "",
    companyIds,
    workModes,
    postedAfter: params.get("posted_after") ?? "",
    postedBefore: params.get("posted_before") ?? "",
    sort: params.get("sort") ?? DEFAULT_SORT,
    order: params.get("order") ?? DEFAULT_ORDER,
    page: asPositiveInt(params.get("page"), 1),
    perPage: Math.min(asPositiveInt(params.get("per_page"), DEFAULT_PER_PAGE), MAX_PER_PAGE),
    selectedJobId,
  };
}

export function dashboardQueryFromState(state) {
  return {
    title: state.title,
    location: state.location,
    company_ids: asArray(state.companyIds),
    work_modes: asArray(state.workModes),
    posted_after: state.postedAfter,
    posted_before: state.postedBefore,
    sort: state.sort,
    order: state.order,
    page: state.page,
    per_page: state.perPage,
  };
}

export function createDashboardSearch(state) {
  const params = new URLSearchParams();
  if (state.title) {
    params.set("title", state.title);
  }
  if (state.location) {
    params.set("location", state.location);
  }
  for (const companyId of asArray(state.companyIds)) {
    params.append("company_ids", companyId);
  }
  for (const workMode of asArray(state.workModes)) {
    params.append("work_modes", workMode);
  }
  if (state.postedAfter) {
    params.set("posted_after", state.postedAfter);
  }
  if (state.postedBefore) {
    params.set("posted_before", state.postedBefore);
  }
  params.set("sort", state.sort ?? DEFAULT_SORT);
  params.set("order", state.order ?? DEFAULT_ORDER);
  params.set("page", String(state.page ?? 1));
  params.set("per_page", String(state.perPage ?? DEFAULT_PER_PAGE));
  if (state.selectedJobId) {
    params.set("job_id", state.selectedJobId);
  }
  return params.toString();
}

export function defaultWorkModes() {
  return [...DEFAULT_WORK_MODES];
}

export function formatPostedDate(value) {
  if (!value) {
    return "Unknown date";
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "Unknown date";
  }

  return new Intl.DateTimeFormat("en-CA", {
    month: "short",
    day: "numeric",
    year: "numeric",
  }).format(date);
}

export function summarizeApplication(application) {
  if (!application) {
    return "Not tracked";
  }
  if (application.status === "saved") {
    return "Saved";
  }
  return application.status.replace(/_/g, " ");
}
