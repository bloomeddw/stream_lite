"""Engine and session primitives for Stream Lite durable state."""

from __future__ import annotations

import os
import sqlite3
from collections.abc import Iterator, Mapping
from contextlib import contextmanager

import sqlalchemy as sa
from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

STREAM_LITE_DATABASE_URL_ENV = "STREAM_LITE_DATABASE_URL"


def get_database_url(
    database_url: str | None = None,
    *,
    environ: Mapping[str, str] | None = None,
) -> str:
    """Return the configured database URL or raise when it is unavailable."""

    if database_url is not None and database_url.strip():
        return database_url.strip()

    source = os.environ if environ is None else environ
    value = source.get(STREAM_LITE_DATABASE_URL_ENV, "").strip()
    if not value:
        raise ValueError(
            f"{STREAM_LITE_DATABASE_URL_ENV} is required for database access.",
        )
    return value


def create_sqlalchemy_engine(
    database_url: str,
    *,
    echo: bool = False,
) -> Engine:
    """Create a synchronous SQLAlchemy engine for the configured URL."""

    engine_kwargs: dict[str, object] = {"echo": echo}
    if database_url.startswith("sqlite"):
        engine_kwargs["connect_args"] = {"check_same_thread": False}

    engine = sa.create_engine(database_url, **engine_kwargs)

    if database_url.startswith("sqlite"):

        @event.listens_for(engine, "connect")
        def _configure_sqlite(dbapi_connection, _connection_record) -> None:  # type: ignore[no-untyped-def]
            if isinstance(dbapi_connection, sqlite3.Connection):
                cursor = dbapi_connection.cursor()
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.close()

    return engine


def create_session_factory(
    database_url: str | None = None,
    *,
    environ: Mapping[str, str] | None = None,
    echo: bool = False,
    expire_on_commit: bool = False,
) -> sessionmaker[Session]:
    """Return a session factory bound to the configured engine."""

    resolved_url = get_database_url(database_url, environ=environ)
    engine = create_sqlalchemy_engine(resolved_url, echo=echo)
    return sessionmaker(bind=engine, class_=Session, expire_on_commit=expire_on_commit)


@contextmanager
def session_scope(session_factory: sessionmaker[Session]) -> Iterator[Session]:
    """Provide a transaction scope around a series of repository calls."""

    session = session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


__all__ = [
    "STREAM_LITE_DATABASE_URL_ENV",
    "create_session_factory",
    "create_sqlalchemy_engine",
    "get_database_url",
    "session_scope",
]
