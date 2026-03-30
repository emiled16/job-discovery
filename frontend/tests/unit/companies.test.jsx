import React, { createElement } from "react";

import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const { router, getCompaniesSpy, getJobsSpy, createCompanySpy, updateCompanySpy, triggerCompanySyncSpy } = vi.hoisted(() => ({
  router: { push: vi.fn(), replace: vi.fn() },
  getCompaniesSpy: vi.fn().mockResolvedValue({
    data: [
      {
        id: "company-1",
        slug: "openai",
        name: "OpenAI",
        description: "Research and product company.",
        lifecycle_status: "active",
        website_url: "https://openai.com",
        updated_at: "2026-03-20T12:00:00Z",
        sources: [{ source_type: "greenhouse", is_enabled: true }],
      },
      {
        id: "company-2",
        slug: "vercel",
        name: "Vercel",
        description: "Frontend cloud platform.",
        lifecycle_status: "paused",
        website_url: "https://vercel.com",
        updated_at: "2026-03-18T12:00:00Z",
        sources: [{ source_type: "greenhouse", is_enabled: false }],
      },
    ],
  }),
  getJobsSpy: vi.fn().mockResolvedValue({
    data: [
      {
        id: "job-1",
        title: "ML Engineer",
        location_text: "Toronto",
        work_mode: "remote",
        posted_at: "2026-03-20T12:00:00Z",
      },
    ],
  }),
  createCompanySpy: vi.fn(),
  updateCompanySpy: vi.fn(),
  triggerCompanySyncSpy: vi.fn(),
}));

vi.mock("next/link", () => ({
  default: ({ href, children, ...props }) =>
    createElement(
      "a",
      { href: typeof href === "string" ? href : href?.pathname || "#", ...props },
      children,
    ),
}));

vi.mock("next/navigation", () => ({
  usePathname: () => "/companies",
  useRouter: () => router,
  useSearchParams: () => new URLSearchParams("company_id=company-1"),
}));

vi.mock("src/lib/api/client", () => ({
  ApiClientError: class ApiClientError extends Error {},
  createBrowserApiClient: () => ({
    getCompanies: getCompaniesSpy,
    getJobs: getJobsSpy,
    createCompany: createCompanySpy,
    updateCompany: updateCompanySpy,
    triggerCompanySync: triggerCompanySyncSpy,
  }),
}));

import { CompaniesScreen } from "src/components/companies/companies-screen";

describe("companies screen", () => {
  beforeEach(() => {
    router.push.mockReset();
    router.replace.mockReset();
    getCompaniesSpy.mockClear();
    getJobsSpy.mockClear();
    triggerCompanySyncSpy.mockReset();
    triggerCompanySyncSpy.mockResolvedValue({ data: { pipeline_run_id: "run-1" } });
  });

  it("renders tracked companies and deep-links into jobs", async () => {
    render(<CompaniesScreen />);

    expect((await screen.findAllByText("OpenAI")).length).toBeGreaterThan(0);
    expect(screen.getAllByText("Research and product company.").length).toBeGreaterThan(0);

    await waitFor(() => {
      expect(router.replace).not.toHaveBeenCalled();
    });

    await waitFor(() => {
      expect(getJobsSpy).toHaveBeenCalledWith({
        company_ids: ["company-1"],
        sort: "posted_at",
        order: "desc",
        page: 1,
        per_page: 6,
      });
    });

    expect(screen.getAllByText("View jobs")[0].getAttribute("href")).toContain(
      "/jobs?company_ids=company-1",
    );
    expect(screen.getByText("Open company jobs").getAttribute("href")).toContain(
      "/jobs?company_ids=company-1",
    );
  });

  it("filters companies by lifecycle and source state", async () => {
    render(<CompaniesScreen />);

    expect((await screen.findAllByText("OpenAI")).length).toBeGreaterThan(0);
    expect(screen.getByText("Vercel")).toBeInTheDocument();

    fireEvent.change(screen.getAllByLabelText("Lifecycle")[0], {
      target: { value: "active" },
    });

    await waitFor(() => {
      expect(screen.queryByText("Vercel")).not.toBeInTheDocument();
    });
    expect(screen.getAllByText("OpenAI").length).toBeGreaterThan(0);

    fireEvent.change(screen.getByLabelText("Source state"), {
      target: { value: "paused" },
    });

    await waitFor(() => {
      expect(screen.getByText("No companies match your filters.")).toBeInTheDocument();
    });
  });

  it("queues manual sync for selected companies from table checkboxes", async () => {
    render(<CompaniesScreen />);

    expect((await screen.findAllByText("OpenAI")).length).toBeGreaterThan(0);

    const bulkQueueButton = screen.getByRole("button", {
      name: "Queue sync for selected (0)",
    });
    expect(bulkQueueButton).toBeDisabled();

    fireEvent.click(screen.getByRole("checkbox", { name: "Select OpenAI" }));
    fireEvent.click(screen.getByRole("checkbox", { name: "Select Vercel" }));

    const enabledBulkQueueButton = screen.getByRole("button", {
      name: "Queue sync for selected (2)",
    });
    expect(enabledBulkQueueButton).toBeEnabled();

    fireEvent.click(enabledBulkQueueButton);

    await waitFor(() => {
      expect(triggerCompanySyncSpy).toHaveBeenCalledTimes(2);
    });
    expect(triggerCompanySyncSpy).toHaveBeenCalledWith("company-1");
    expect(triggerCompanySyncSpy).toHaveBeenCalledWith("company-2");
  });
});
