const DEFAULT_PUBLIC_API_BASE_URL = "http://localhost:8000";

function normalizeUrl(rawValue, fieldName) {
  if (!rawValue) {
    throw new Error(`${fieldName} must be configured`);
  }

  let parsed;
  try {
    parsed = new URL(rawValue);
  } catch {
    throw new Error(`${fieldName} must be a valid absolute URL`);
  }

  if (!["http:", "https:"].includes(parsed.protocol)) {
    throw new Error(`${fieldName} must use http or https`);
  }

  return parsed.toString().replace(/\/$/, "");
}

export function getPublicApiBaseUrl(env = process.env) {
  return normalizeUrl(
    env.NEXT_PUBLIC_API_BASE_URL ?? DEFAULT_PUBLIC_API_BASE_URL,
    "NEXT_PUBLIC_API_BASE_URL",
  );
}

export function getInternalApiBaseUrl(env = process.env) {
  return normalizeUrl(
    env.API_INTERNAL_BASE_URL ??
      env.NEXT_PUBLIC_API_BASE_URL ??
      DEFAULT_PUBLIC_API_BASE_URL,
    "API_INTERNAL_BASE_URL",
  );
}
