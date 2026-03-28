"use client";

import { startTransition, useState } from "react";
import { useRouter } from "next/navigation";

import { ApiClientError, createBrowserApiClient } from "src/lib/api/client";

const api = createBrowserApiClient();

export function ApplicationToggle({ jobId, application, compact = false }) {
  const router = useRouter();
  const [current, setCurrent] = useState(application);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");

  const isApplied = current && current.status !== "saved";

  async function onToggle() {
    setPending(true);
    setError("");

    try {
      const response = await api.upsertApplication(jobId, {
        status: isApplied ? "saved" : "applied",
      });
      setCurrent({
        id: response.data.id,
        status: response.data.status,
        applied_at: response.data.applied_at,
        notes: response.data.notes,
      });
      startTransition(() => {
        router.refresh();
      });
    } catch (caughtError) {
      setError(
        caughtError instanceof ApiClientError
          ? caughtError.message
          : "Could not update application state",
      );
    } finally {
      setPending(false);
    }
  }

  return (
    <div className={compact ? "application-toggle compact" : "application-toggle"}>
      <button
        type="button"
        className={isApplied ? "pill-button is-active" : "pill-button"}
        onClick={onToggle}
        disabled={pending}
        aria-pressed={isApplied}
      >
        {pending ? "Saving..." : isApplied ? "Applied" : "Mark applied"}
      </button>
      {error ? <p className="inline-error">{error}</p> : null}
    </div>
  );
}
