"""Deterministic local seed records."""

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
