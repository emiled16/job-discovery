import { Suspense } from "react";

import { CompaniesScreen } from "src/components/companies/companies-screen";
import { AppShell } from "src/components/ui/app-shell";

export default function CompaniesPage() {
  return (
    <Suspense
      fallback={
        <AppShell
          eyebrow="Companies"
          title="Track the companies behind the pipeline."
          description="Loading the companies route."
        >
          <section className="empty-panel">
            <p className="eyebrow">Loading</p>
            <h2>Preparing tracked companies.</h2>
            <p>The company registry is initializing its query state and API fetches.</p>
          </section>
        </AppShell>
      }
    >
      <CompaniesScreen />
    </Suspense>
  );
}
