from fastapi import APIRouter

from job_discovery_backend.api.routes.v1.applications import router as applications_router
from job_discovery_backend.api.routes.v1.jobs import router as jobs_router
from job_discovery_backend.api.routes.v1.summary import router as summary_router
from job_discovery_backend.api.routes.v1.views import router as views_router

router = APIRouter(prefix="/api/v1")
router.include_router(applications_router)
router.include_router(jobs_router)
router.include_router(summary_router)
router.include_router(views_router)
