import { pathToFileURL } from "node:url";

const DEFAULTS = {
  FRONTEND_PORT: "3000",
  NEXT_PUBLIC_API_BASE_URL: "http://localhost:8000",
  NEXT_TELEMETRY_DISABLED: "1",
};

function parsePort(rawValue) {
  const value = Number.parseInt(rawValue, 10);
  if (!Number.isInteger(value) || value < 1 || value > 65535) {
    throw new Error("FRONTEND_PORT must be an integer between 1 and 65535");
  }

  return value;
}

function parseApiBaseUrl(rawValue) {
  let parsed;

  try {
    parsed = new URL(rawValue);
  } catch {
    throw new Error("NEXT_PUBLIC_API_BASE_URL must be a valid absolute URL");
  }

  if (!["http:", "https:"].includes(parsed.protocol)) {
    throw new Error("NEXT_PUBLIC_API_BASE_URL must use http or https");
  }

  return parsed.toString().replace(/\/$/, "");
}

function parseTelemetryFlag(rawValue) {
  if (!["0", "1"].includes(rawValue)) {
    throw new Error("NEXT_TELEMETRY_DISABLED must be either 0 or 1");
  }

  return rawValue;
}

export function loadConfig(env = process.env) {
  const rawPort = env.FRONTEND_PORT ?? env.PORT ?? DEFAULTS.FRONTEND_PORT;

  return {
    port: parsePort(rawPort),
    apiBaseUrl: parseApiBaseUrl(
      env.NEXT_PUBLIC_API_BASE_URL ?? DEFAULTS.NEXT_PUBLIC_API_BASE_URL,
    ),
    telemetryDisabled: parseTelemetryFlag(
      env.NEXT_TELEMETRY_DISABLED ?? DEFAULTS.NEXT_TELEMETRY_DISABLED,
    ),
  };
}

if (process.argv[1] && pathToFileURL(process.argv[1]).href === import.meta.url) {
  loadConfig();
}

