import React, { createElement } from "react";

import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { JobResults } from "src/components/dashboard/job-results";
import { createDashboardSearch, parseDashboardState } from "src/lib/dashboard";

vi.mock("next/link", () => ({
  default: ({ href, children, ...props }) =>
    createElement(
      "a",
      { href: typeof href === "string" ? href : href?.pathname || "#", ...props },
      children,
    ),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ refresh() {} }),
}));

const sampleJobs = [
  {
    id: "job-1",
    title: "ML Engineer",
    company: { id: "c1", name: "OpenAI" },
    location_text: "Toronto",
    work_mode: "remote",
    posted_at: "2026-03-20T12:00:00Z",
    description_preview: "Preview",
    application: null,
  },
];

describe("dashboard helpers", () => {
  it("parses repeated filters and selected job ids", () => {
    const state = parseDashboardState(
      new URLSearchParams(
        "title=ML&company_ids=c1&company_ids=c2&work_modes=remote&job_id=job-9&page=2&view=table",
      ),
    );

    expect(state.title).toBe("ML");
    expect(state.companyIds).toEqual(["c1", "c2"]);
    expect(state.workModes).toEqual(["remote"]);
    expect(state.selectedJobId).toBe("job-9");
    expect(state.page).toBe(2);
    expect(state.viewMode).toBe("table");
  });

  it("creates stable dashboard search strings", () => {
    const query = createDashboardSearch({
      title: "ML",
      location: "",
      companyIds: ["c1"],
      workModes: ["remote"],
      postedAfter: "",
      postedBefore: "",
      sort: "posted_at",
      order: "desc",
      page: 1,
      perPage: 12,
      viewMode: "card",
      selectedJobId: "job-1",
    });

    expect(query).toContain("title=ML");
    expect(query).toContain("company_ids=c1");
    expect(query).toContain("job_id=job-1");
  });
});

describe("job results", () => {
  it("renders card mode roles", () => {
    render(
      <JobResults
        jobs={sampleJobs}
        emptyMessage="Nothing"
        selectedJobId=""
        viewMode="card"
        buildSelectSearch={(jobId) => `job_id=${jobId}`}
      />,
    );

    expect(screen.getByText("ML Engineer")).toBeInTheDocument();
    expect(screen.getByText("View details")).toBeInTheDocument();
  });

  it("renders table mode roles", () => {
    render(
      <JobResults
        jobs={sampleJobs}
        emptyMessage="Nothing"
        selectedJobId="job-1"
        viewMode="table"
        buildSelectSearch={(jobId) => `job_id=${jobId}`}
      />,
    );

    expect(screen.getByRole("table")).toBeInTheDocument();
    expect(screen.getByText("OpenAI")).toBeInTheDocument();
  });
});
