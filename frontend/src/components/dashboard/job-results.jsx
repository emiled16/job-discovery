import Link from "next/link";

import { formatPostedDate } from "src/lib/dashboard";

import { ApplicationToggle } from "./application-toggle";

function QueryLink({ search, children, className }) {
  return (
    <Link href={search ? `/jobs?${search}` : "/jobs"} className={className}>
      {children}
    </Link>
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

  return (
    <JobTable
      jobs={jobs}
      selectedJobId={selectedJobId}
      buildSelectSearch={buildSelectSearch}
    />
  );
}
