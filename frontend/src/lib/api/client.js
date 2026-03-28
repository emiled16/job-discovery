import { getInternalApiBaseUrl } from "./config";

export class ApiClientError extends Error {
  constructor(message, options = {}) {
    super(message);
    this.name = "ApiClientError";
    this.status = options.status ?? 500;
    this.code = options.code ?? "request_failed";
    this.details = options.details ?? [];
    this.requestId = options.requestId ?? null;
  }
}

function appendQuery(url, query) {
  if (!query) {
    return;
  }

  for (const [key, value] of Object.entries(query)) {
    if (value === undefined || value === null || value === "") {
      continue;
    }

    if (Array.isArray(value)) {
      for (const item of value) {
        if (item !== undefined && item !== null && item !== "") {
          url.searchParams.append(key, String(item));
        }
      }
      continue;
    }

    url.searchParams.set(key, String(value));
  }
}

async function readBody(response) {
  if (response.status === 204) {
    return null;
  }

  const contentType = response.headers.get("content-type") ?? "";
  if (!contentType.includes("application/json")) {
    const text = await response.text();
    return text ? { message: text } : null;
  }

  return response.json();
}

export function createApiClient(options = {}) {
  const fetchImpl = options.fetchImpl ?? fetch;
  const baseUrl = (options.baseUrl ?? "").replace(/\/$/, "");
  const basePath = (options.basePath ?? "/api/backend/api/v1").replace(/\/$/, "");

  async function request(path, requestOptions = {}) {
    const url = new URL(`${basePath}${path}`, baseUrl || "http://localhost");
    appendQuery(url, requestOptions.query);

    const response = await fetchImpl(baseUrl ? url.toString() : `${url.pathname}${url.search}`, {
      method: requestOptions.method ?? "GET",
      headers: {
        Accept: "application/json",
        ...(requestOptions.body ? { "Content-Type": "application/json" } : {}),
        ...requestOptions.headers,
      },
      body: requestOptions.body ? JSON.stringify(requestOptions.body) : undefined,
      cache: requestOptions.cache ?? "no-store",
    });

    const payload = await readBody(response);
    if (!response.ok) {
      throw new ApiClientError(
        payload?.error?.message ?? payload?.message ?? "Request failed",
        {
          status: response.status,
          code: payload?.error?.code,
          details: payload?.error?.details,
          requestId: payload?.request_id ?? response.headers.get("x-request-id"),
        },
      );
    }

    return payload;
  }

  return {
    getJobs(query) {
      return request("/jobs", { query });
    },
    getJob(jobId) {
      return request(`/jobs/${jobId}`);
    },
    upsertApplication(jobId, body) {
      return request(`/jobs/${jobId}/application`, { method: "PUT", body });
    },
    getCompanies() {
      return request("/admin/companies");
    },
    getViews() {
      return request("/views");
    },
    createView(body) {
      return request("/views", { method: "POST", body });
    },
    updateView(viewId, body) {
      return request(`/views/${viewId}`, { method: "PATCH", body });
    },
    deleteView(viewId) {
      return request(`/views/${viewId}`, { method: "DELETE" });
    },
    getSummaryMetrics() {
      return request("/summary/metrics");
    },
    getSummaryTimeseries(query) {
      return request("/summary/timeseries", { query });
    },
    getPipelineRuns(query) {
      return request("/admin/pipeline-runs", { query });
    },
    getPipelineRun(runId) {
      return request(`/admin/pipeline-runs/${runId}`);
    },
    createCompany(body) {
      return request("/admin/companies", { method: "POST", body });
    },
    updateCompany(companyId, body) {
      return request(`/admin/companies/${companyId}`, { method: "PATCH", body });
    },
    triggerCompanySync(companyId) {
      return request(`/admin/companies/${companyId}/sync`, { method: "POST" });
    },
  };
}

export function createBrowserApiClient() {
  return createApiClient({
    baseUrl: "",
    basePath: "/api/backend/api/v1",
  });
}

export function createServerApiClient(env = process.env) {
  return createApiClient({
    baseUrl: getInternalApiBaseUrl(env),
    basePath: "/api/v1",
  });
}
