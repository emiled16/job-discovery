import { Suspense } from "react";

import { DashboardScreen } from "src/components/dashboard/dashboard-screen";
import { AppShell } from "src/components/ui/app-shell";

export default function DashboardPage() {
  return (
    <Suspense
      fallback={
        <AppShell
          eyebrow="Dashboard"
          title="Search the live pipeline."
          description="Loading the dashboard route."
        >
          <section className="empty-panel">
            <p className="eyebrow">Loading</p>
            <h2>Preparing live job results.</h2>
            <p>The dashboard is initializing its query state and API fetches.</p>
          </section>
        </AppShell>
      }
    >
      <DashboardScreen />
    </Suspense>
  );
}
