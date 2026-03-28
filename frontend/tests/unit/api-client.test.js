import { describe, expect, it, vi } from "vitest";

import { createApiClient } from "src/lib/api/client";

describe("api client", () => {
  it("builds list queries with repeated params", async () => {
    const fetchImpl = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ data: [], meta: {} }), {
        status: 200,
        headers: { "content-type": "application/json" },
      }),
    );
    const client = createApiClient({
      baseUrl: "",
      basePath: "/api/backend/api/v1",
      fetchImpl,
    });

    await client.getJobs({
      title: "ML",
      company_ids: ["c1", "c2"],
      work_modes: ["remote"],
      page: 2,
    });

    expect(fetchImpl).toHaveBeenCalledWith(
      "/api/backend/api/v1/jobs?title=ML&company_ids=c1&company_ids=c2&work_modes=remote&page=2",
      expect.objectContaining({ method: "GET" }),
    );
  });

  it("maps backend error envelopes into ApiClientError", async () => {
    const fetchImpl = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          error: { code: "validation_error", message: "Bad filters", details: [] },
          request_id: "req-1",
        }),
        {
          status: 422,
          headers: { "content-type": "application/json" },
        },
      ),
    );
    const client = createApiClient({ fetchImpl });

    await expect(client.getJobs({})).rejects.toEqual(
      expect.objectContaining({
        name: "ApiClientError",
        message: "Bad filters",
        status: 422,
        code: "validation_error",
        requestId: "req-1",
      }),
    );
  });

  it("supports application updates", async () => {
    const fetchImpl = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ data: { id: "app-1", status: "applied" } }), {
        status: 200,
        headers: { "content-type": "application/json" },
      }),
    );
    const client = createApiClient({ fetchImpl });

    const response = await client.upsertApplication("job-1", { status: "applied" });

    expect(response.data.status).toBe("applied");
    expect(fetchImpl).toHaveBeenCalledWith(
      "/api/backend/api/v1/jobs/job-1/application",
      expect.objectContaining({
        method: "PUT",
        body: JSON.stringify({ status: "applied" }),
      }),
    );
  });
});
