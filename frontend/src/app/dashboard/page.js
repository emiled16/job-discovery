import { redirect } from "next/navigation";

export default async function DashboardPage({ searchParams }) {
  const resolvedSearchParams = await searchParams;
  const query = new URLSearchParams();

  for (const [key, value] of Object.entries(resolvedSearchParams ?? {})) {
    if (Array.isArray(value)) {
      value.forEach((item) => query.append(key, item));
      continue;
    }
    if (value) {
      query.set(key, value);
    }
  }

  const search = query.toString();

  redirect(search ? `/jobs?${search}` : "/jobs");
}
