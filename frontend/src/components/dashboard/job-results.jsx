import Link from "next/link";

import { formatPostedDate, summarizeApplication } from "src/lib/dashboard";

import { ApplicationToggle } from "./application-toggle";

function QueryLink({ search, children, className }) {
  return (
    <Link href={search ? `/dashboard?${search}` : "/dashboard"} className={className}>
      {children}
    </Link>
  );
}

function JobMeta({ job }) {
  return (
    <div className="job-meta">
      <span>{job.company.name}</span>
      <span>{job.location_text || "Location flexible"}</span>
      <span>{job.work_mode || "Mode pending"}</span>
      <span>{formatPostedDate(job.posted_at)}</span>
    </div>
  );
}

function JobCard({ job, isSelected, selectSearch }) {
  return (
    <article className={isSelected ? "job-card is-selected" : "job-card"}>
      <div className="job-card-main">
        <div className="job-card-header">
          <div>
            <p className="job-company">{job.company.name}</p>
            <h2>{job.title}</h2>
          </div>
          <span className="tag">{job.work_mode || "unknown"}</span>
        </div>
        <JobMeta job={job} />
        <p className="job-preview">{job.description_preview || "No description preview yet."}</p>
        <div className="job-card-footer">
          <span className="status-note">{summarizeApplication(job.application)}</span>
          <div className="job-actions">
            <ApplicationToggle jobId={job.id} application={job.application} compact />
            <QueryLink search={selectSearch} className="ghost-link">
              View details
            </QueryLink>
          </div>
        </div>
      </div>
    </article>
  );
}

function JobTable({ jobs, selectedJobId, buildSelectSearch }) {
  return (
    <div className="jobs-table-wrap">
      <table className="jobs-table">
        <thead>
          <tr>
            <th>Role</th>
            <th>Company</th>
            <th>Location</th>
            <th>Mode</th>
            <th>Posted</th>
            <th>Applied</th>
          </tr>
        </thead>
        <tbody>
          {jobs.map((job) => (
            <tr key={job.id} className={selectedJobId === job.id ? "is-selected" : undefined}>
              <td>
                <QueryLink search={buildSelectSearch(job.id)} className="table-link">
                  {job.title}
                </QueryLink>
              </td>
              <td>{job.company.name}</td>
              <td>{job.location_text || "Flexible"}</td>
              <td>{job.work_mode || "Unknown"}</td>
              <td>{formatPostedDate(job.posted_at)}</td>
              <td>
                <ApplicationToggle jobId={job.id} application={job.application} compact />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function JobResults({
  jobs,
  emptyMessage,
  selectedJobId,
  viewMode,
  buildSelectSearch,
}) {
  if (!jobs.length) {
    return (
      <section className="empty-panel">
        <p className="eyebrow">No matches</p>
        <h2>Nothing fits the current filters.</h2>
        <p>{emptyMessage}</p>
      </section>
    );
  }

  if (viewMode === "table") {
    return (
      <JobTable
        jobs={jobs}
        selectedJobId={selectedJobId}
        buildSelectSearch={buildSelectSearch}
      />
    );
  }

  return (
    <div className="job-grid">
      {jobs.map((job) => (
        <JobCard
          key={job.id}
          job={job}
          isSelected={selectedJobId === job.id}
          selectSearch={buildSelectSearch(job.id)}
        />
      ))}
    </div>
  );
}
