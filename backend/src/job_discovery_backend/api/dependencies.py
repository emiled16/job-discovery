from __future__ import annotations

from collections.abc import Iterator

from fastapi import Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from job_discovery_backend.api.errors import ApiError
from job_discovery_backend.db.models import User
from job_discovery_backend.db.session import get_session_factory

LOCAL_USER_SEED_KEY = "local_user"


def get_db_session(request: Request) -> Iterator[Session]:
    session = get_session_factory(request.app.state.settings.database_url)()
    try:
        yield session
    finally:
        session.close()


def get_current_user(session: Session = Depends(get_db_session)) -> User:
    user = session.scalar(select(User).where(User.seed_key == LOCAL_USER_SEED_KEY))
    if user is None:
        raise ApiError(503, "user_context_unavailable", "Local user seed is unavailable")
    return user
