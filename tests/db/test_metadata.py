from __future__ import annotations

from app.db import Base
from app.db.models import ALL_TABLE_NAMES


def test_metadata_contains_all_documented_tables() -> None:
    assert set(Base.metadata.tables) == set(ALL_TABLE_NAMES)
