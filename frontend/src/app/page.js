export default function HomePage() {
  return (
    <main className="shell">
      <section className="hero">
        <p className="eyebrow">Phase 1 bootstrap</p>
        <h1>Job discovery starts with a stable platform.</h1>
        <p>
          The frontend scaffold is online and ready for dashboard, saved views,
          summary, and admin workflows in later phases.
        </p>
        <div className="status-row" aria-label="bootstrap status">
          <span className="status-chip">Next.js app router</span>
          <span className="status-chip">Container-ready</span>
          <span className="status-chip">Waiting for API integration</span>
        </div>
      </section>
    </main>
  );
}
