import React from "react";
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { SummaryChart } from "src/components/summary/summary-chart";

describe("summary chart", () => {
  it("renders an empty state for no trend data", () => {
    render(<SummaryChart series={[]} bucket="week" />);

    expect(
      screen.getByText("No tracked applications in the selected range."),
    ).toBeInTheDocument();
  });

  it("renders trend buckets and values", () => {
    render(
      <SummaryChart
        bucket="week"
        series={[
          { bucket_start: "2026-01-05", count: 2 },
          { bucket_start: "2026-01-12", count: 1 },
        ]}
      />,
    );

    expect(screen.getByText("Applications over time")).toBeInTheDocument();
    expect(screen.getByText("2026-01-05")).toBeInTheDocument();
    expect(screen.getByText("2026-01-12")).toBeInTheDocument();
  });
});
