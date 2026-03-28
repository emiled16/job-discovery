import { describe, expect, it } from "vitest";

import {
  buildViewPayload,
  createEmptyViewDraft,
  savedViewToDashboardSearch,
  viewDraftFromRecord,
} from "src/lib/views";

describe("saved view helpers", () => {
  it("normalizes a saved view into an editable draft", () => {
    const draft = viewDraftFromRecord({
      id: "view-1",
      name: "Remote ML",
      filters: {
        title: "ML",
        location: "Toronto",
        company_ids: ["company-1"],
        work_modes: ["remote"],
        posted_after: "2026-01-01",
        posted_before: "2026-01-31",
      },
      sort: { field: "posted_at", direction: "desc" },
      is_default: true,
    });

    expect(draft.companyIds).toEqual(["company-1"]);
    expect(draft.workModes).toEqual(["remote"]);
    expect(draft.isDefault).toBe(true);
  });

  it("builds a valid API payload from the draft", () => {
    const payload = buildViewPayload({
      ...createEmptyViewDraft(),
      name: "  Remote ML  ",
      title: " ML ",
      workModes: ["remote"],
    });

    expect(payload).toEqual({
      name: "Remote ML",
      filters: {
        title: "ML",
        location: null,
        company_ids: [],
        work_modes: ["remote"],
        posted_after: null,
        posted_before: null,
      },
      sort: { field: "posted_at", direction: "desc" },
      is_default: false,
    });
  });

  it("converts a view into dashboard query hydration", () => {
    const search = savedViewToDashboardSearch({
      name: "Remote ML",
      filters: {
        title: "ML",
        company_ids: ["company-1"],
        work_modes: ["remote"],
      },
      sort: { field: "title", direction: "asc" },
      is_default: false,
    });

    expect(search).toContain("title=ML");
    expect(search).toContain("company_ids=company-1");
    expect(search).toContain("sort=title");
    expect(search).toContain("order=asc");
  });
});
