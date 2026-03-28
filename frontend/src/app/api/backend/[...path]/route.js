import { NextResponse } from "next/server";

import { getInternalApiBaseUrl } from "src/lib/api/config";

function buildUpstreamUrl(path, requestUrl) {
  const upstream = new URL(`${getInternalApiBaseUrl()}/${path.join("/")}`);
  const incoming = new URL(requestUrl);
  upstream.search = incoming.search;
  return upstream;
}

async function proxy(request, context) {
  const { path } = await context.params;
  const upstreamUrl = buildUpstreamUrl(path, request.url);
  const contentType = request.headers.get("content-type");
  const body =
    request.method === "GET" || request.method === "HEAD"
      ? undefined
      : await request.text();

  const response = await fetch(upstreamUrl, {
    method: request.method,
    headers: {
      Accept: request.headers.get("accept") ?? "application/json",
      ...(contentType ? { "Content-Type": contentType } : {}),
      ...(request.headers.get("x-request-id")
        ? { "X-Request-ID": request.headers.get("x-request-id") }
        : {}),
    },
    body,
    cache: "no-store",
  });

  const responseBody =
    response.status === 204 || response.status === 304 ? null : await response.text();
  return new NextResponse(responseBody, {
    status: response.status,
    headers: {
      ...(response.headers.get("content-type")
        ? { "content-type": response.headers.get("content-type") }
        : {}),
      ...(response.headers.get("x-request-id")
        ? { "x-request-id": response.headers.get("x-request-id") }
        : {}),
    },
  });
}

export const GET = proxy;
export const POST = proxy;
export const PUT = proxy;
export const PATCH = proxy;
export const DELETE = proxy;
