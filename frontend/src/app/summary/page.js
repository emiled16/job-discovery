import { AppShell } from "src/components/ui/app-shell";

export default function SummaryPage() {
  return (
    <AppShell
      eyebrow="Summary"
      title="Analytics panel is queued."
      description="The route exists now; metric cards and trend rendering land in the next frontend slice."
    >
      <section className="empty-panel">
        <p className="eyebrow">Queued</p>
        <h2>Summary metrics and application trends are the next task.</h2>
        <p>The shell is already wired into the product navigation.</p>
      </section>
    </AppShell>
  );
}
