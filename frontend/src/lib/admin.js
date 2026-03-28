export function createEmptyCompanyDraft() {
  return {
    id: "",
    slug: "",
    name: "",
    websiteUrl: "",
    description: "",
    lifecycleStatus: "draft",
    sourceType: "greenhouse",
    externalKey: "",
    baseUrl: "",
    isEnabled: true,
  };
}

export function companyDraftFromRecord(company) {
  if (!company) {
    return createEmptyCompanyDraft();
  }

  const primarySource = company.sources?.[0] ?? {};
  return {
    id: company.id,
    slug: company.slug ?? "",
    name: company.name ?? "",
    websiteUrl: company.website_url ?? "",
    description: company.description ?? "",
    lifecycleStatus: company.lifecycle_status ?? "draft",
    sourceType: primarySource.source_type ?? "greenhouse",
    externalKey: primarySource.external_key ?? "",
    baseUrl: primarySource.base_url ?? "",
    isEnabled:
      primarySource.is_enabled === undefined ? true : Boolean(primarySource.is_enabled),
  };
}

export function buildCompanyCreatePayload(draft) {
  return {
    slug: draft.slug.trim(),
    name: draft.name.trim(),
    website_url: draft.websiteUrl.trim() || null,
    description: draft.description.trim() || null,
    lifecycle_status: draft.lifecycleStatus,
    source: {
      source_type: draft.sourceType,
      external_key: draft.externalKey.trim() || null,
      base_url: draft.baseUrl.trim() || null,
      configuration: {},
      is_enabled: Boolean(draft.isEnabled),
    },
  };
}

export function buildCompanyPatchPayload(draft) {
  return buildCompanyCreatePayload(draft);
}

export function buildPipelineRunQuery(filters) {
  return {
    company_id: filters.companyId || undefined,
    statuses: filters.status ? [filters.status] : undefined,
    started_after: filters.startedAfter || undefined,
    started_before: filters.startedBefore || undefined,
    page: 1,
    per_page: 20,
  };
}
