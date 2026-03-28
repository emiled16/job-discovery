import { describe, expect, it } from "vitest";

import {
  buildCompanyCreatePayload,
  buildPipelineRunQuery,
  companyDraftFromRecord,
  createEmptyCompanyDraft,
} from "src/lib/admin";

describe("admin helpers", () => {
  it("normalizes a company record into an editable draft", () => {
    const draft = companyDraftFromRecord({
      id: "company-1",
      slug: "openai",
      name: "OpenAI",
      website_url: "https://openai.com",
      description: "AI research lab",
      lifecycle_status: "active",
      sources: [
        {
          source_type: "greenhouse",
          external_key: "openai",
          base_url: "https://boards.greenhouse.io/openai",
          is_enabled: true,
        },
      ],
    });

    expect(draft.sourceType).toBe("greenhouse");
    expect(draft.baseUrl).toContain("greenhouse");
    expect(draft.lifecycleStatus).toBe("active");
  });

  it("builds create payloads in backend shape", () => {
    const payload = buildCompanyCreatePayload({
      ...createEmptyCompanyDraft(),
      slug: " openai ",
      name: " OpenAI ",
      sourceType: "lever",
      baseUrl: "https://jobs.lever.co/openai",
    });

    expect(payload).toEqual({
      slug: "openai",
      name: "OpenAI",
      website_url: null,
      description: null,
      lifecycle_status: "draft",
      source: {
        source_type: "lever",
        external_key: null,
        base_url: "https://jobs.lever.co/openai",
        configuration: {},
        is_enabled: true,
      },
    });
  });

  it("builds pipeline run query filters", () => {
    expect(
      buildPipelineRunQuery({
        companyId: "company-1",
        status: "failed",
        startedAfter: "2026-01-01",
        startedBefore: "",
      }),
    ).toEqual({
      company_id: "company-1",
      statuses: ["failed"],
      started_after: "2026-01-01",
      started_before: undefined,
      page: 1,
      per_page: 20,
    });
  });
});
