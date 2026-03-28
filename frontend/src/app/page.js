import Link from "next/link";

import { AppShell } from "src/components/ui/app-shell";

export default function HomePage() {
  return (
    <AppShell
      eyebrow="Platform"
      title="One place to search, track, and operate the job pipeline."
      description="The product shell is live. Dashboard browsing is wired first, with saved views, summary, and admin workflows following in the next implementation commits."
      actions={
        <Link href="/dashboard" className="primary-link">
          Open dashboard
        </Link>
      }
    >
      <section className="overview-grid">
        <article className="overview-card">
          <p className="eyebrow">Live now</p>
          <h2>Dashboard foundation</h2>
          <p>
            Browse jobs by title, location, company, work mode, date, sort, and page
            while keeping a detail panel in view.
          </p>
        </article>
        <article className="overview-card">
          <p className="eyebrow">Next</p>
          <h2>Views and summary</h2>
          <p>
            Reusable filters and progress analytics are queued as the next frontend slice.
          </p>
        </article>
        <article className="overview-card">
          <p className="eyebrow">Operators</p>
          <h2>Admin control plane</h2>
          <p>
            Company management, manual sync triggering, and pipeline run inspection follow
            after the user-facing flows.
          </p>
        </article>
      </section>
    </AppShell>
  );
}
