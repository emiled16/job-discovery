"""Shared schema constants for ORM code and seed data."""

COMPANY_LIFECYCLE_STATES = ("draft", "active", "paused", "archived")
COMPANY_SOURCE_TYPES = ("applytojob", "ashby", "greenhouse", "lever", "manual", "smartrecruiters", "workday")
JOB_STATUSES = ("active", "closed")
JOB_WORK_MODES = ("remote", "hybrid", "onsite", "unknown")
APPLICATION_STATUSES = (
    "saved",
    "applied",
    "interviewing",
    "offered",
    "rejected",
    "withdrawn",
)
PIPELINE_RUN_TRIGGER_TYPES = ("manual", "scheduled")
PIPELINE_RUN_STATUSES = ("queued", "running", "succeeded", "failed", "partial")
PIPELINE_EVENT_LEVELS = ("info", "warning", "error")
