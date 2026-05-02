from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect


def _alembic_config(repo_root: Path, database_url: str) -> Config:
    config = Config(str(repo_root / "alembic.ini"))
    config.set_main_option("script_location", str(repo_root / "app" / "db" / "migrations"))
    config.set_main_option("sqlalchemy.url", database_url)
    config.set_main_option("prepend_sys_path", str(repo_root))
    return config


def test_initial_migration_upgrade_downgrade(sqlite_database_url: str) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    config = _alembic_config(repo_root, sqlite_database_url)

    command.upgrade(config, "head")

    engine = __import__("app.db", fromlist=["create_sqlalchemy_engine"]).create_sqlalchemy_engine(sqlite_database_url)
    try:
        upgraded_tables = set(inspect(engine).get_table_names())
        assert "jobs" in upgraded_tables
        assert "event_outbox" in upgraded_tables

        command.downgrade(config, "base")
        downgraded_tables = set(inspect(engine).get_table_names())
        assert "jobs" not in downgraded_tables
        assert "event_outbox" not in downgraded_tables
    finally:
        engine.dispose()


def test_application_owned_uuid_insert(db_session) -> None:
    from app import generate_uuid
    from app.db.models import WatcherModel

    watcher_id = generate_uuid()
    record = WatcherModel(
        watcher_id=watcher_id,
        name="watcher-alpha",
        lifecycle_state="CREATED",
        operational_status="green",
        route_policy="tag_match_all_destinations",
        enabled=False,
    )

    db_session.add(record)
    db_session.flush()

    column = WatcherModel.__table__.c.watcher_id
    assert column.default is None
    assert column.server_default is None
    assert record.watcher_id == watcher_id
