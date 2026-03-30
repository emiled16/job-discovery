"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV_ITEMS = [
  { href: "/jobs", label: "Jobs", aliases: ["/dashboard"] },
  { href: "/companies", label: "Companies" },
  { href: "/views", label: "Views" },
  { href: "/summary", label: "Summary" },
  { href: "/admin", label: "Admin" },
];

function isNavItemActive(pathname, item) {
  const candidates = [item.href, ...(item.aliases ?? [])];
  return candidates.some(
    (candidate) => pathname === candidate || pathname.startsWith(`${candidate}/`),
  );
}

export function AppShell({ children, eyebrow, title, description, actions }) {
  const pathname = usePathname();

  return (
    <div className="app-shell">
      <aside className="app-sidebar">
        <Link className="brand-mark" href="/jobs">
          <span className="brand-kicker">Job Discovery</span>
          <strong>Field Console</strong>
        </Link>
        <nav className="app-nav" aria-label="Primary">
          {NAV_ITEMS.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className={isNavItemActive(pathname, item) ? "nav-link is-active" : "nav-link"}
            >
              {item.label}
            </Link>
          ))}
        </nav>
      </aside>
      <main className="app-main">
        <header className="page-header">
          <div>
            <p className="eyebrow">{eyebrow}</p>
            <h1>{title}</h1>
            <p className="page-description">{description}</p>
          </div>
          {actions ? <div className="page-actions">{actions}</div> : null}
        </header>
        {children}
      </main>
    </div>
  );
}
