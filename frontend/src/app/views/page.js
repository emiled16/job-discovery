import { AppShell } from "src/components/ui/app-shell";

export default function ViewsPage() {
  return (
    <AppShell
      eyebrow="Saved views"
      title="View library is next."
      description="The route is in place so navigation stays stable while the saved-view workflows land in the next task."
    >
      <section className="empty-panel">
        <p className="eyebrow">Queued</p>
        <h2>Saved view create, edit, and apply flows are the next implementation slice.</h2>
        <p>This placeholder keeps the overall product shell intact between commits.</p>
      </section>
    </AppShell>
  );
}
