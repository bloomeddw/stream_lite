from __future__ import annotations

from app.db import Base
from app.db.models import ALL_TABLE_NAMES


def test_metadata_contains_all_documented_tables() -> None:
    assert set(Base.metadata.tables) == set(ALL_TABLE_NAMES)


def test_metadata_constraint_names_are_unique_per_table() -> None:
    """Catch duplicate generated CHECK names before PostgreSQL migration runtime."""

    for table in Base.metadata.tables.values():
        named_constraints = [constraint.name for constraint in table.constraints if constraint.name]
        assert len(named_constraints) == len(set(named_constraints)), table.name
