import { AppShell } from "src/components/ui/app-shell";

export default function AdminPage() {
  return (
    <AppShell
      eyebrow="Admin"
      title="Operator workflows are queued."
      description="Company management, manual sync, and run monitoring land in the admin implementation slice."
    >
      <section className="empty-panel">
        <p className="eyebrow">Queued</p>
        <h2>The admin surface will be filled in after saved views and summary.</h2>
        <p>This keeps the information architecture stable as the remaining routes arrive.</p>
      </section>
    </AppShell>
  );
}
