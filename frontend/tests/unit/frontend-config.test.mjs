import { describe, expect, it } from "vitest";

import { loadConfig } from "../../scripts/validate-config.mjs";

describe("frontend config", () => {
  it("rejects invalid port", () => {
    expect(() => loadConfig({ FRONTEND_PORT: "0" })).toThrow(
      /FRONTEND_PORT must be an integer between 1 and 65535/,
    );
  });

  it("rejects invalid api base url", () => {
    expect(() => loadConfig({ NEXT_PUBLIC_API_BASE_URL: "/api" })).toThrow(
      /NEXT_PUBLIC_API_BASE_URL must be a valid absolute URL/,
    );
  });

  it("rejects invalid internal api base url", () => {
    expect(() => loadConfig({ API_INTERNAL_BASE_URL: "ftp://api" })).toThrow(
      /API_INTERNAL_BASE_URL must use http or https/,
    );
  });

  it("rejects invalid telemetry flag", () => {
    expect(() => loadConfig({ NEXT_TELEMETRY_DISABLED: "true" })).toThrow(
      /NEXT_TELEMETRY_DISABLED must be either 0 or 1/,
    );
  });
});
