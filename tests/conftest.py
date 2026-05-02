"""Pytest path bootstrap for Stream Lite contract tests.

The repository is documentation/contract-first at this stage and has not yet been
packaged as an installable Python distribution. Contract tests import utilities
from top-level folders such as ``tools``. When pytest is launched from some
Windows environments, the repository root is not guaranteed to be present on
``sys.path`` during collection, so this conftest file inserts it explicitly.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from sqlalchemy.orm import Session, sessionmaker

REPO_ROOT = Path(__file__).resolve().parents[1]
repo_root_text = str(REPO_ROOT)

if repo_root_text not in sys.path:
    sys.path.insert(0, repo_root_text)

from app.db import Base, create_sqlalchemy_engine


@pytest.fixture()
def sqlite_database_url(tmp_path: Path) -> str:
    return f"sqlite:///{tmp_path / 'stream_lite.sqlite'}"


@pytest.fixture()
def sqlite_engine() -> object:
    engine = create_sqlalchemy_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    try:
        yield engine
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()


@pytest.fixture()
def db_session(sqlite_engine: object) -> Session:
    session_factory = sessionmaker(bind=sqlite_engine, class_=Session, expire_on_commit=False)
    session = session_factory()
    try:
        yield session
    finally:
        session.rollback()
        session.close()
