"""Event outbox and offset persistence primitives."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

import sqlalchemy as sa

from app.db.models import EventOffsetModel, EventOutboxModel

from .base import RepositoryBase


class EventOutboxRepository(RepositoryBase):
    def enqueue_event(
        self,
        *,
        outbox_id: UUID | str | None = None,
        event_id: UUID | str,
        schema_version: str,
        event_type: str,
        stream_name: str,
        producer: str,
        correlation_id: UUID | str,
        idempotency_key: str,
        occurred_at: datetime,
        payload_json: dict[str, object],
        status: str = "pending",
        job_id: UUID | str | None = None,
        watcher_id: UUID | str | None = None,
        attempt_number: int | None = None,
        next_publish_at: datetime | None = None,
    ) -> EventOutboxModel:
        record = EventOutboxModel(
            outbox_id=self._ensure_uuid(outbox_id),
            event_id=self._ensure_uuid(event_id),
            schema_version=schema_version,
            event_type=event_type,
            stream_name=stream_name,
            producer=producer,
            job_id=None if job_id is None else self._ensure_uuid(job_id),
            watcher_id=None if watcher_id is None else self._ensure_uuid(watcher_id),
            correlation_id=self._ensure_uuid(correlation_id),
            idempotency_key=idempotency_key,
            attempt_number=attempt_number,
            occurred_at=occurred_at,
            payload_json=payload_json,
            status=status,
            publish_attempts=0,
            next_publish_at=next_publish_at,
        )
        self.session.add(record)
        self.session.flush()
        return record

    def list_pending_events(
        self,
        *,
        as_of: datetime | None = None,
        limit: int = 100,
    ) -> list[EventOutboxModel]:
        boundary = as_of or self._now()
        statement = (
            sa.select(EventOutboxModel)
            .where(EventOutboxModel.status.in_(("pending", "publish_failed")))
            .where(
                sa.or_(
                    EventOutboxModel.next_publish_at.is_(None),
                    EventOutboxModel.next_publish_at <= boundary,
                ),
            )
            .order_by(EventOutboxModel.occurred_at.asc(), EventOutboxModel.outbox_id.asc())
            .limit(limit)
        )
        return list(self.session.scalars(statement))

    def claim_due_events(self, *, as_of: datetime | None = None, limit: int = 100) -> list[EventOutboxModel]:
        return self.list_pending_events(as_of=as_of, limit=limit)

    def mark_dispatched(
        self,
        outbox_id: UUID | str,
        *,
        published_stream_id: str,
        published_at: datetime | None = None,
    ) -> EventOutboxModel:
        record = self.session.get(EventOutboxModel, self._ensure_uuid(outbox_id))
        if record is None:
            raise ValueError("event outbox row not found")
        record.status = "published"
        record.published_stream_id = published_stream_id
        record.published_at = published_at or self._now()
        record.next_publish_at = None
        record.last_error_code = None
        record.updated_at = self._now()
        self.session.flush()
        return record

    def mark_published(self, outbox_id: UUID | str, **kwargs: object) -> EventOutboxModel:
        return self.mark_dispatched(outbox_id, **kwargs)

    def mark_publish_failed(
        self,
        outbox_id: UUID | str,
        *,
        last_error_code: str,
        next_publish_at: datetime,
    ) -> EventOutboxModel:
        record = self.session.get(EventOutboxModel, self._ensure_uuid(outbox_id))
        if record is None:
            raise ValueError("event outbox row not found")
        record.status = "publish_failed"
        record.last_error_code = last_error_code
        record.next_publish_at = next_publish_at
        record.publish_attempts += 1
        record.updated_at = self._now()
        self.session.flush()
        return record

    def mark_dead_letter(
        self,
        outbox_id: UUID | str,
        *,
        last_error_code: str,
        next_publish_at: datetime | None = None,
    ) -> EventOutboxModel:
        record = self.session.get(EventOutboxModel, self._ensure_uuid(outbox_id))
        if record is None:
            raise ValueError("event outbox row not found")
        record.status = "dead_lettered"
        record.last_error_code = last_error_code
        record.next_publish_at = next_publish_at
        record.publish_attempts += 1
        record.updated_at = self._now()
        self.session.flush()
        return record

    def mark_dead_lettered(self, outbox_id: UUID | str, **kwargs: object) -> EventOutboxModel:
        return self.mark_dead_letter(outbox_id, **kwargs)

    def get_event_by_id(self, event_id: UUID | str) -> EventOutboxModel | None:
        statement = sa.select(EventOutboxModel).where(
            EventOutboxModel.event_id == self._ensure_uuid(event_id),
        )
        return self.session.scalar(statement)

    def list_events(
        self,
        *,
        watcher_id: UUID | str | None = None,
        job_id: UUID | str | None = None,
        event_type: str | None = None,
        from_occurred_at: datetime | None = None,
        to_occurred_at: datetime | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[EventOutboxModel], int]:
        filters: list[sa.ColumnElement[bool]] = []
        if watcher_id is not None:
            filters.append(EventOutboxModel.watcher_id == self._ensure_uuid(watcher_id))
        if job_id is not None:
            filters.append(EventOutboxModel.job_id == self._ensure_uuid(job_id))
        if event_type is not None:
            filters.append(EventOutboxModel.event_type == event_type)
        if from_occurred_at is not None:
            filters.append(EventOutboxModel.occurred_at >= from_occurred_at)
        if to_occurred_at is not None:
            filters.append(EventOutboxModel.occurred_at <= to_occurred_at)

        statement = (
            sa.select(EventOutboxModel)
            .where(*filters)
            .order_by(EventOutboxModel.occurred_at.desc(), EventOutboxModel.event_id.asc())
            .limit(limit)
            .offset(offset)
        )
        count_statement = sa.select(sa.func.count()).select_from(EventOutboxModel).where(*filters)
        records = list(self.session.scalars(statement))
        total = int(self.session.scalar(count_statement) or 0)
        return records, total


class EventOffsetRepository(RepositoryBase):
    def get_offset(self, consumer_group: str, stream_name: str) -> EventOffsetModel | None:
        statement = sa.select(EventOffsetModel).where(
            EventOffsetModel.consumer_group == consumer_group,
            EventOffsetModel.stream_name == stream_name,
        )
        return self.session.scalar(statement)

    def upsert_offset(
        self,
        *,
        event_offset_id: UUID | str | None = None,
        consumer_group: str,
        stream_name: str,
        redis_stream_id: str,
        last_processed_event_id: UUID | str | None = None,
    ) -> EventOffsetModel:
        record = self.get_offset(consumer_group, stream_name)
        if record is None:
            record = EventOffsetModel(
                event_offset_id=self._ensure_uuid(event_offset_id),
                consumer_group=consumer_group,
                stream_name=stream_name,
                redis_stream_id=redis_stream_id,
                last_processed_event_id=None
                if last_processed_event_id is None
                else self._ensure_uuid(last_processed_event_id),
            )
            self.session.add(record)
        else:
            record.redis_stream_id = redis_stream_id
            record.last_processed_event_id = (
                None if last_processed_event_id is None else self._ensure_uuid(last_processed_event_id)
            )
            record.updated_at = self._now()
        self.session.flush()
        return record


__all__ = ["EventOffsetRepository", "EventOutboxRepository"]
