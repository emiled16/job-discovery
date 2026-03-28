import test from "node:test";
import assert from "node:assert/strict";

import { loadConfig } from "../../scripts/validate-config.mjs";

test("frontend config rejects invalid port", () => {
  assert.throws(
    () => loadConfig({ FRONTEND_PORT: "0" }),
    /FRONTEND_PORT must be an integer between 1 and 65535/,
  );
});

test("frontend config rejects invalid api base url", () => {
  assert.throws(
    () => loadConfig({ NEXT_PUBLIC_API_BASE_URL: "/api" }),
    /NEXT_PUBLIC_API_BASE_URL must be a valid absolute URL/,
  );
});

test("frontend config rejects invalid telemetry flag", () => {
  assert.throws(
    () => loadConfig({ NEXT_TELEMETRY_DISABLED: "true" }),
    /NEXT_TELEMETRY_DISABLED must be either 0 or 1/,
  );
});

