from fastapi import APIRouter

from job_discovery_backend.api.routes.v1.jobs import router as jobs_router

router = APIRouter(prefix="/api/v1")
router.include_router(jobs_router)
