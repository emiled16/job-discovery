import Link from "next/link";

import { formatPostedDate, summarizeApplication } from "src/lib/dashboard";

import { ApplicationToggle } from "./application-toggle";

export function JobDetailPanel({ job, closeHref }) {
  if (!job) {
    return (
      <aside className="detail-panel detail-panel-empty">
        <p className="eyebrow">Job detail</p>
        <h2>Pick a role to inspect it without losing your current filters.</h2>
        <p>
          The detail panel keeps application tracking and the original posting within
          reach while you browse the current result set.
        </p>
      </aside>
    );
  }

  return (
    <aside className="detail-panel">
      <div className="detail-actions">
        <p className="eyebrow">Selected role</p>
        <Link href={closeHref} className="ghost-link">
          Close
        </Link>
      </div>
      <h2>{job.title}</h2>
      <p className="detail-company">{job.company.name}</p>
      <div className="detail-stack">
        <span className="tag">{job.work_mode || "Mode pending"}</span>
        <span className="tag">{job.employment_type || "Type pending"}</span>
        <span className="tag">{formatPostedDate(job.posted_at)}</span>
      </div>
      <div className="detail-meta">
        <span>{job.location_text || "Location flexible"}</span>
        <span>{job.company.lifecycle_status}</span>
        <span>{summarizeApplication(job.application)}</span>
      </div>
      <p className="detail-description">
        {job.description_text || "No detailed description was returned for this role yet."}
      </p>
      <div className="detail-footer">
        <ApplicationToggle jobId={job.id} application={job.application} />
        <a href={job.apply_url} target="_blank" rel="noreferrer" className="primary-link">
          Open original posting
        </a>
      </div>
    </aside>
  );
}
