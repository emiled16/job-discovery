"""Deterministic local seed records."""

from datetime import UTC, datetime

LOCAL_USER = {
    "id": "11111111-1111-1111-1111-111111111111",
    "seed_key": "local_user",
    "display_name": "Local User",
    "email": None,
}

STARTER_COMPANIES = (
    {
        "company": {
            "id": "22222222-2222-2222-2222-222222222221",
            "slug": "openai",
            "name": "OpenAI",
            "website_url": "https://openai.com",
            "description": "AI research and product company.",
            "lifecycle_status": "active",
        },
        "source": {
            "id": "33333333-3333-3333-3333-333333333331",
            "source_type": "greenhouse",
            "external_key": "openai",
            "base_url": "https://boards.greenhouse.io/openai",
            "configuration": {},
            "is_enabled": True,
        },
    },
    {
        "company": {
            "id": "22222222-2222-2222-2222-222222222222",
            "slug": "vercel",
            "name": "Vercel",
            "website_url": "https://vercel.com",
            "description": "Frontend cloud platform.",
            "lifecycle_status": "active",
        },
        "source": {
            "id": "33333333-3333-3333-3333-333333333332",
            "source_type": "lever",
            "external_key": "vercel",
            "base_url": "https://jobs.lever.co/vercel",
            "configuration": {},
            "is_enabled": True,
        },
    },
    {
        "company": {
            "id": "22222222-2222-2222-2222-222222222223",
            "slug": "acme-demo",
            "name": "Acme Demo",
            "website_url": "https://example.com",
            "description": "Manual starter company used for local admin workflows.",
            "lifecycle_status": "paused",
        },
        "source": {
            "id": "33333333-3333-3333-3333-333333333333",
            "source_type": "manual",
            "external_key": "acme-demo",
            "base_url": "https://example.com/careers",
            "configuration": {},
            "is_enabled": False,
        },
    },
)

STARTER_JOBS = (
    {
        "id": "44444444-4444-4444-4444-444444444441",
        "company_slug": "openai",
        "source_type": "greenhouse",
        "source_job_key": "seed-openai-ml",
        "source_identity": "greenhouse:openai:seed-openai-ml",
        "title": "ML Engineer",
        "location_text": "Toronto, ON",
        "work_mode": "remote",
        "employment_type": "Full-time",
        "status": "active",
        "posted_at": datetime(2026, 3, 20, 12, 0, tzinfo=UTC),
        "apply_url": "https://openai.com/careers/ml-engineer",
        "description_text": "Seeded platform role for dashboard and apply flows.",
        "last_seen_at": datetime(2026, 3, 28, 12, 0, tzinfo=UTC),
        "missed_sync_count": 0,
    },
    {
        "id": "44444444-4444-4444-4444-444444444442",
        "company_slug": "vercel",
        "source_type": "lever",
        "source_job_key": "seed-vercel-platform",
        "source_identity": "lever:vercel:seed-vercel-platform",
        "title": "Platform Engineer",
        "location_text": "Remote",
        "work_mode": "remote",
        "employment_type": "Full-time",
        "status": "active",
        "posted_at": datetime(2026, 3, 21, 12, 0, tzinfo=UTC),
        "apply_url": "https://vercel.com/careers/platform-engineer",
        "description_text": "Seeded infrastructure role for summary and admin flows.",
        "last_seen_at": datetime(2026, 3, 28, 12, 0, tzinfo=UTC),
        "missed_sync_count": 0,
    },
)
