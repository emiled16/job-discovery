"""Engine and session lifecycle helpers."""

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from job_discovery_backend.config import load_settings

_engine_cache: dict[str, Engine] = {}
_session_factory_cache: dict[str, sessionmaker[Session]] = {}


def build_engine(database_url: str) -> Engine:
    """Create a SQLAlchemy engine with conservative defaults."""

    return create_engine(database_url, pool_pre_ping=True)


def get_engine(database_url: str | None = None) -> Engine:
    """Return a cached engine for the requested database URL."""

    resolved_url = database_url or load_settings().database_url
    engine = _engine_cache.get(resolved_url)
    if engine is None:
        engine = build_engine(resolved_url)
        _engine_cache[resolved_url] = engine
    return engine


def get_session_factory(database_url: str | None = None) -> sessionmaker[Session]:
    """Return a cached session factory bound to the requested engine."""

    resolved_url = database_url or load_settings().database_url
    factory = _session_factory_cache.get(resolved_url)
    if factory is None:
        factory = sessionmaker(
            bind=get_engine(resolved_url),
            autoflush=False,
            expire_on_commit=False,
        )
        _session_factory_cache[resolved_url] = factory
    return factory


@contextmanager
def session_scope(database_url: str | None = None) -> Iterator[Session]:
    """Create, commit, and close a session around a unit of work."""

    session = get_session_factory(database_url)()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def reset_database_state() -> None:
    """Dispose cached engines and session factories for tests."""

    for engine in _engine_cache.values():
        engine.dispose()
    _engine_cache.clear()
    _session_factory_cache.clear()
