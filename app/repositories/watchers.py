"""Watcher configuration persistence primitives."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime
from uuid import UUID

import sqlalchemy as sa

from app.db.models import (
    WatcherDestinationModel,
    WatcherModel,
    WatcherRouteMatchModel,
    WatcherSourceModel,
)

from .base import RepositoryBase


class WatcherRepository(RepositoryBase):
    def create_watcher(
        self,
        *,
        watcher_id: UUID | str | None = None,
        name: str,
        lifecycle_state: str,
        operational_status: str,
        route_policy: str,
        enabled: bool = False,
        latest_route_preview_at: datetime | None = None,
    ) -> WatcherModel:
        record = WatcherModel(
            watcher_id=self._ensure_uuid(watcher_id),
            name=name,
            lifecycle_state=lifecycle_state,
            operational_status=operational_status,
            route_policy=route_policy,
            enabled=enabled,
            latest_route_preview_at=latest_route_preview_at,
        )
        self.session.add(record)
        self.session.flush()
        return record

    def get_watcher(self, watcher_id: UUID | str) -> WatcherModel | None:
        return self.session.get(WatcherModel, self._ensure_uuid(watcher_id))

    def list_watchers(self) -> list[WatcherModel]:
        statement = sa.select(WatcherModel).order_by(WatcherModel.created_at.asc(), WatcherModel.name.asc())
        return list(self.session.scalars(statement))

    def update_lifecycle_state(
        self,
        watcher_id: UUID | str,
        *,
        lifecycle_state: str,
        operational_status: str | None = None,
        enabled: bool | None = None,
    ) -> WatcherModel:
        watcher = self.get_watcher(watcher_id)
        if watcher is None:
            raise ValueError("watcher not found")
        watcher.lifecycle_state = lifecycle_state
        if operational_status is not None:
            watcher.operational_status = operational_status
        if enabled is not None:
            watcher.enabled = enabled
        watcher.updated_at = self._now()
        self.session.flush()
        return watcher

    def update_watcher_state(self, watcher_id: UUID | str, **kwargs: object) -> WatcherModel:
        return self.update_lifecycle_state(watcher_id, **kwargs)

    def replace_sources(
        self,
        watcher_id: UUID | str,
        *,
        sources: Sequence[Mapping[str, object]],
    ) -> list[WatcherSourceModel]:
        normalized_watcher_id = self._ensure_uuid(watcher_id)
        self.session.execute(
            sa.delete(WatcherSourceModel).where(WatcherSourceModel.watcher_id == normalized_watcher_id),
        )
        created: list[WatcherSourceModel] = []
        for source in sources:
            record = WatcherSourceModel(
                source_folder_id=self._ensure_uuid(source.get("source_folder_id")),
                watcher_id=normalized_watcher_id,
                display_path=str(source["display_path"]),
                normalized_path=str(source["normalized_path"]),
                route_tags=[str(tag) for tag in source.get("route_tags", [])],
                route_tags_text=str(source["route_tags_text"]),
                health_status=str(source["health_status"]),
                reason_code=None if source.get("reason_code") is None else str(source["reason_code"]),
                enabled=bool(source.get("enabled", True)),
            )
            self.session.add(record)
            created.append(record)
        self.session.flush()
        return created

    def list_sources(self, watcher_id: UUID | str) -> list[WatcherSourceModel]:
        statement = (
            sa.select(WatcherSourceModel)
            .where(WatcherSourceModel.watcher_id == self._ensure_uuid(watcher_id))
            .order_by(WatcherSourceModel.created_at.asc(), WatcherSourceModel.display_path.asc())
        )
        return list(self.session.scalars(statement))

    def replace_destinations(
        self,
        watcher_id: UUID | str,
        *,
        destinations: Sequence[Mapping[str, object]],
    ) -> list[WatcherDestinationModel]:
        normalized_watcher_id = self._ensure_uuid(watcher_id)
        self.session.execute(
            sa.delete(WatcherDestinationModel).where(
                WatcherDestinationModel.watcher_id == normalized_watcher_id,
            ),
        )
        created: list[WatcherDestinationModel] = []
        for destination in destinations:
            record = WatcherDestinationModel(
                destination_folder_id=self._ensure_uuid(destination.get("destination_folder_id")),
                watcher_id=normalized_watcher_id,
                display_path=str(destination["display_path"]),
                normalized_path=str(destination["normalized_path"]),
                route_tags=[str(tag) for tag in destination.get("route_tags", [])],
                route_tags_text=str(destination["route_tags_text"]),
                health_status=str(destination["health_status"]),
                reason_code=None if destination.get("reason_code") is None else str(destination["reason_code"]),
                enabled=bool(destination.get("enabled", True)),
            )
            self.session.add(record)
            created.append(record)
        self.session.flush()
        return created

    def list_destinations(self, watcher_id: UUID | str) -> list[WatcherDestinationModel]:
        statement = (
            sa.select(WatcherDestinationModel)
            .where(WatcherDestinationModel.watcher_id == self._ensure_uuid(watcher_id))
            .order_by(WatcherDestinationModel.created_at.asc(), WatcherDestinationModel.display_path.asc())
        )
        return list(self.session.scalars(statement))

    def save_route_preview(
        self,
        watcher_id: UUID | str,
        *,
        route_matches: Sequence[Mapping[str, object]],
        previewed_at: datetime | None = None,
    ) -> list[WatcherRouteMatchModel]:
        normalized_watcher_id = self._ensure_uuid(watcher_id)
        self.session.execute(
            sa.delete(WatcherRouteMatchModel).where(
                WatcherRouteMatchModel.watcher_id == normalized_watcher_id,
            ),
        )
        created: list[WatcherRouteMatchModel] = []
        for route_match in route_matches:
            record = WatcherRouteMatchModel(
                route_match_id=self._ensure_uuid(route_match.get("route_match_id")),
                watcher_id=normalized_watcher_id,
                source_folder_id=self._ensure_uuid(route_match.get("source_folder_id")),
                destination_folder_id=None
                if route_match.get("destination_folder_id") is None
                else self._ensure_uuid(route_match["destination_folder_id"]),
                route_policy=str(route_match["route_policy"]),
                matched_route_tags=[str(tag) for tag in route_match.get("matched_route_tags", [])],
                unmatched_reason_code=None
                if route_match.get("unmatched_reason_code") is None
                else str(route_match["unmatched_reason_code"]),
            )
            self.session.add(record)
            created.append(record)

        watcher = self.get_watcher(normalized_watcher_id)
        if watcher is None:
            raise ValueError("watcher not found")
        watcher.latest_route_preview_at = previewed_at or self._now()
        watcher.updated_at = self._now()
        self.session.flush()
        return created

    def list_route_matches(self, watcher_id: UUID | str) -> list[WatcherRouteMatchModel]:
        statement = (
            sa.select(WatcherRouteMatchModel)
            .where(WatcherRouteMatchModel.watcher_id == self._ensure_uuid(watcher_id))
            .order_by(WatcherRouteMatchModel.created_at.asc(), WatcherRouteMatchModel.route_match_id.asc())
        )
        return list(self.session.scalars(statement))


__all__ = ["WatcherRepository"]
