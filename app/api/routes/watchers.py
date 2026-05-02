"""Watcher configuration and lifecycle command routes."""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from datetime import datetime, timezone
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

from app import generate_uuid, generate_uuid_str
from app._schema_types import ROUTE_TAG_PATTERN
from app.api.dependencies import (
    PaginationParams,
    get_command_repository,
    get_idempotency_key,
    get_operational_log_repository,
    get_or_create_correlation_id,
    get_pagination,
    get_path_policy,
    get_watcher_repository,
)
from app.api.errors import ApiError
from app.api.schemas.api_models import (
    CommandAcceptedResponse,
    LifecycleCommandRequest,
    RoutePreviewMatch,
    RoutePreviewRequest,
    RoutePreviewResponse,
    RouteTaggedFolderSpec,
    WatcherCreateRequest,
    WatcherDetailResponse,
    WatcherListItem,
    WatcherListResponse,
    WatcherPatchRequest,
    WatcherRoutePreviewSummary,
)
from app.config.path_policy import PathPolicy
from app.repositories.commands import CommandRepository
from app.repositories.observability import OperationalLogRepository
from app.repositories.watchers import WatcherRepository

router = APIRouter(prefix="/watchers")


@router.get("", response_model=WatcherListResponse)
def list_watchers(
    pagination: Annotated[PaginationParams, Depends(get_pagination)],
    repository: Annotated[WatcherRepository, Depends(get_watcher_repository)],
    correlation_id: Annotated[str, Depends(get_or_create_correlation_id)],
) -> WatcherListResponse:
    watchers = repository.list_watchers()
    items = [
        WatcherListItem(
            watcher_id=watcher.watcher_id,
            name=watcher.name,
            lifecycle_state=watcher.lifecycle_state,
            operational_status=watcher.operational_status,
            source_count=len(repository.list_sources(watcher.watcher_id)),
            destination_count=len(repository.list_destinations(watcher.watcher_id)),
            updated_at=_format_datetime(watcher.updated_at),
        )
        for watcher in watchers[pagination.offset : pagination.offset + pagination.limit]
    ]
    return WatcherListResponse(
        items=items,
        limit=pagination.limit,
        offset=pagination.offset,
        total=len(watchers),
        correlation_id=correlation_id,
    )


@router.post("", response_model=WatcherDetailResponse, status_code=201)
def create_watcher(
    payload: WatcherCreateRequest,
    repository: Annotated[WatcherRepository, Depends(get_watcher_repository)],
    path_policy: Annotated[PathPolicy, Depends(get_path_policy)],
    log_repository: Annotated[OperationalLogRepository, Depends(get_operational_log_repository)],
    correlation_id: Annotated[str, Depends(get_or_create_correlation_id)],
) -> WatcherDetailResponse:
    resolved_correlation_id = str(payload.correlation_id or correlation_id)
    prepared_sources = _prepare_folder_specs(
        payload.sources,
        purpose="source",
        record_id_field="source_folder_id",
        path_policy=path_policy,
        correlation_id=resolved_correlation_id,
    )
    prepared_destinations = _prepare_folder_specs(
        payload.destinations,
        purpose="destination",
        record_id_field="destination_folder_id",
        path_policy=path_policy,
        correlation_id=resolved_correlation_id,
    )
    preview = _compute_preview(
        prepared_sources,
        prepared_destinations,
        route_policy=payload.route_policy,
        correlation_id=resolved_correlation_id,
    )

    try:
        watcher = repository.create_watcher(
            watcher_id=generate_uuid(),
            name=payload.name,
            lifecycle_state="CREATED",
            operational_status=preview["status"],
            route_policy=payload.route_policy,
            enabled=payload.enabled,
            latest_route_preview_at=_now(),
        )
        repository.replace_sources(watcher.watcher_id, sources=prepared_sources)
        repository.replace_destinations(watcher.watcher_id, destinations=prepared_destinations)
        repository.save_route_preview(
            watcher.watcher_id,
            route_matches=preview["route_matches"],
            previewed_at=_now(),
        )
        log_repository.write_summary(
            event_name="watcher.create_requested",
            sanitized_message=f"Watcher {payload.name} was created.",
            watcher_id=watcher.watcher_id,
            correlation_id=resolved_correlation_id,
        )
        repository.session.commit()
    except IntegrityError as exc:
        repository.session.rollback()
        raise ApiError(
            409,
            error_code="WATCHER_NAME_CONFLICT",
            message=f"Watcher name {payload.name} already exists.",
            field="name",
            correlation_id=resolved_correlation_id,
        ) from exc

    return _build_watcher_detail_response(repository, watcher.watcher_id, resolved_correlation_id)


@router.get("/{watcher_id}", response_model=WatcherDetailResponse)
def get_watcher(
    watcher_id: UUID,
    repository: Annotated[WatcherRepository, Depends(get_watcher_repository)],
    correlation_id: Annotated[str, Depends(get_or_create_correlation_id)],
) -> WatcherDetailResponse:
    return _build_watcher_detail_response(repository, watcher_id, correlation_id)


@router.patch("/{watcher_id}", response_model=WatcherDetailResponse)
def patch_watcher(
    watcher_id: UUID,
    payload: WatcherPatchRequest,
    repository: Annotated[WatcherRepository, Depends(get_watcher_repository)],
    path_policy: Annotated[PathPolicy, Depends(get_path_policy)],
    log_repository: Annotated[OperationalLogRepository, Depends(get_operational_log_repository)],
    correlation_id: Annotated[str, Depends(get_or_create_correlation_id)],
) -> WatcherDetailResponse:
    resolved_correlation_id = str(payload.correlation_id or correlation_id)
    changes = payload.model_dump(exclude_none=True)
    if not changes:
        raise ApiError(
            422,
            error_code="EMPTY_PATCH",
            message="Watcher patch payload must include at least one field.",
            correlation_id=resolved_correlation_id,
        )

    watcher = repository.get_watcher(watcher_id)
    if watcher is None:
        raise ApiError(
            404,
            error_code="WATCHER_NOT_FOUND",
            message=f"Watcher {watcher_id} was not found.",
            resource_id=str(watcher_id),
            correlation_id=resolved_correlation_id,
        )
    if watcher.lifecycle_state == "ACTIVE":
        raise ApiError(
            409,
            error_code="WATCHER_STATE_CONFLICT",
            message="Active watchers cannot be patched.",
            resource_id=str(watcher_id),
            current_state=watcher.lifecycle_state,
            correlation_id=resolved_correlation_id,
        )

    if payload.name is not None:
        watcher.name = payload.name

    prepared_sources = None
    if payload.sources is not None:
        prepared_sources = _prepare_folder_specs(
            payload.sources,
            purpose="source",
            record_id_field="source_folder_id",
            path_policy=path_policy,
            correlation_id=resolved_correlation_id,
        )
        repository.replace_sources(watcher_id, sources=prepared_sources)

    prepared_destinations = None
    if payload.destinations is not None:
        prepared_destinations = _prepare_folder_specs(
            payload.destinations,
            purpose="destination",
            record_id_field="destination_folder_id",
            path_policy=path_policy,
            correlation_id=resolved_correlation_id,
        )
        repository.replace_destinations(watcher_id, destinations=prepared_destinations)

    sources_for_preview = prepared_sources or _source_records(repository, watcher_id)
    destinations_for_preview = prepared_destinations or _destination_records(repository, watcher_id)
    route_policy = payload.route_policy or watcher.route_policy
    preview = _compute_preview(
        sources_for_preview,
        destinations_for_preview,
        route_policy=route_policy,
        correlation_id=resolved_correlation_id,
    )

    watcher.route_policy = route_policy
    watcher.enabled = watcher.enabled if payload.enabled is None else payload.enabled
    watcher.operational_status = preview["status"]
    watcher.updated_at = _now()

    try:
        repository.session.flush()
        repository.save_route_preview(
            watcher_id,
            route_matches=preview["route_matches"],
            previewed_at=_now(),
        )
        log_repository.write_summary(
            event_name="watcher.patch_requested",
            sanitized_message=f"Watcher {watcher_id} was updated.",
            watcher_id=watcher_id,
            correlation_id=resolved_correlation_id,
        )
        repository.session.commit()
    except IntegrityError as exc:
        repository.session.rollback()
        raise ApiError(
            409,
            error_code="WATCHER_NAME_CONFLICT",
            message=f"Watcher name {payload.name} already exists.",
            field="name",
            resource_id=str(watcher_id),
            correlation_id=resolved_correlation_id,
        ) from exc

    return _build_watcher_detail_response(repository, watcher_id, resolved_correlation_id)


@router.post("/{watcher_id}/preview-routes", response_model=RoutePreviewResponse)
def preview_routes(
    watcher_id: UUID,
    payload: RoutePreviewRequest,
    repository: Annotated[WatcherRepository, Depends(get_watcher_repository)],
    path_policy: Annotated[PathPolicy, Depends(get_path_policy)],
    log_repository: Annotated[OperationalLogRepository, Depends(get_operational_log_repository)],
    correlation_id: Annotated[str, Depends(get_or_create_correlation_id)],
) -> RoutePreviewResponse:
    resolved_correlation_id = str(payload.correlation_id or correlation_id)
    if repository.get_watcher(watcher_id) is None:
        raise ApiError(
            404,
            error_code="WATCHER_NOT_FOUND",
            message=f"Watcher {watcher_id} was not found.",
            resource_id=str(watcher_id),
            correlation_id=resolved_correlation_id,
        )
    prepared_sources = _prepare_folder_specs(
        payload.sources,
        purpose="source",
        record_id_field="source_folder_id",
        path_policy=path_policy,
        correlation_id=resolved_correlation_id,
    )
    prepared_destinations = _prepare_folder_specs(
        payload.destinations,
        purpose="destination",
        record_id_field="destination_folder_id",
        path_policy=path_policy,
        correlation_id=resolved_correlation_id,
    )
    preview = _compute_preview(
        prepared_sources,
        prepared_destinations,
        route_policy=payload.route_policy,
        correlation_id=resolved_correlation_id,
    )
    log_repository.write_summary(
        event_name="route.preview_requested",
        sanitized_message=f"Route preview requested for watcher {watcher_id}.",
        watcher_id=watcher_id,
        correlation_id=resolved_correlation_id,
    )
    repository.session.commit()
    return RoutePreviewResponse(
        route_policy=payload.route_policy,
        source_matches=preview["source_matches"],
        unmatched_sources=preview["unmatched_sources"],
        unmatched_destinations=preview["unmatched_destinations"],
        status=preview["status"],
        correlation_id=resolved_correlation_id,
    )


@router.post("/{watcher_id}/start", response_model=CommandAcceptedResponse, status_code=202)
def start_watcher(
    watcher_id: UUID,
    payload: LifecycleCommandRequest,
    repository: Annotated[WatcherRepository, Depends(get_watcher_repository)],
    command_repository: Annotated[CommandRepository, Depends(get_command_repository)],
    log_repository: Annotated[OperationalLogRepository, Depends(get_operational_log_repository)],
    idempotency_key: Annotated[str | None, Depends(get_idempotency_key)],
    correlation_id: Annotated[str, Depends(get_or_create_correlation_id)],
):
    return _request_lifecycle_command(
        watcher_id=watcher_id,
        payload=payload,
        action="start",
        allowed_states={"CREATED", "STOPPED", "ERROR"},
        repository=repository,
        command_repository=command_repository,
        log_repository=log_repository,
        idempotency_key=idempotency_key,
        correlation_id=correlation_id,
        require_green_preview=True,
    )


@router.post("/{watcher_id}/pause", response_model=CommandAcceptedResponse, status_code=202)
def pause_watcher(
    watcher_id: UUID,
    payload: LifecycleCommandRequest,
    repository: Annotated[WatcherRepository, Depends(get_watcher_repository)],
    command_repository: Annotated[CommandRepository, Depends(get_command_repository)],
    log_repository: Annotated[OperationalLogRepository, Depends(get_operational_log_repository)],
    idempotency_key: Annotated[str | None, Depends(get_idempotency_key)],
    correlation_id: Annotated[str, Depends(get_or_create_correlation_id)],
):
    return _request_lifecycle_command(
        watcher_id=watcher_id,
        payload=payload,
        action="pause",
        allowed_states={"ACTIVE"},
        repository=repository,
        command_repository=command_repository,
        log_repository=log_repository,
        idempotency_key=idempotency_key,
        correlation_id=correlation_id,
        require_green_preview=False,
    )


@router.post("/{watcher_id}/resume", response_model=CommandAcceptedResponse, status_code=202)
def resume_watcher(
    watcher_id: UUID,
    payload: LifecycleCommandRequest,
    repository: Annotated[WatcherRepository, Depends(get_watcher_repository)],
    command_repository: Annotated[CommandRepository, Depends(get_command_repository)],
    log_repository: Annotated[OperationalLogRepository, Depends(get_operational_log_repository)],
    idempotency_key: Annotated[str | None, Depends(get_idempotency_key)],
    correlation_id: Annotated[str, Depends(get_or_create_correlation_id)],
):
    return _request_lifecycle_command(
        watcher_id=watcher_id,
        payload=payload,
        action="resume",
        allowed_states={"PAUSED"},
        repository=repository,
        command_repository=command_repository,
        log_repository=log_repository,
        idempotency_key=idempotency_key,
        correlation_id=correlation_id,
        require_green_preview=False,
    )


@router.post("/{watcher_id}/stop", response_model=CommandAcceptedResponse, status_code=202)
def stop_watcher(
    watcher_id: UUID,
    payload: LifecycleCommandRequest,
    repository: Annotated[WatcherRepository, Depends(get_watcher_repository)],
    command_repository: Annotated[CommandRepository, Depends(get_command_repository)],
    log_repository: Annotated[OperationalLogRepository, Depends(get_operational_log_repository)],
    idempotency_key: Annotated[str | None, Depends(get_idempotency_key)],
    correlation_id: Annotated[str, Depends(get_or_create_correlation_id)],
):
    return _request_lifecycle_command(
        watcher_id=watcher_id,
        payload=payload,
        action="stop",
        allowed_states={"CREATED", "ACTIVE", "PAUSED", "ERROR"},
        repository=repository,
        command_repository=command_repository,
        log_repository=log_repository,
        idempotency_key=idempotency_key,
        correlation_id=correlation_id,
        require_green_preview=False,
    )


def _request_lifecycle_command(
    *,
    watcher_id: UUID,
    payload: LifecycleCommandRequest,
    action: Literal["start", "pause", "resume", "stop"],
    allowed_states: set[str],
    repository: WatcherRepository,
    command_repository: CommandRepository,
    log_repository: OperationalLogRepository,
    idempotency_key: str | None,
    correlation_id: str,
    require_green_preview: bool,
) -> JSONResponse:
    resolved_correlation_id = str(payload.correlation_id or correlation_id)
    scope = f"watcher.{action}:{watcher_id}"
    payload_hash = _payload_hash(payload.model_dump(mode="json", exclude={"correlation_id": True}))
    if idempotency_key is not None:
        existing_record = command_repository.get_key(scope=scope, idempotency_key=idempotency_key)
        if existing_record is not None:
            if existing_record.payload_hash is not None and existing_record.payload_hash != payload_hash:
                raise ApiError(
                    409,
                    error_code="IDEMPOTENCY_KEY_CONFLICT",
                    message="Idempotency-Key was already used with a different request payload.",
                    resource_id=str(watcher_id),
                    correlation_id=resolved_correlation_id,
                )
            if existing_record.first_response_json is not None:
                response = CommandAcceptedResponse.model_validate(existing_record.first_response_json)
                return JSONResponse(status_code=202, content=response.model_dump(mode="json"))

    watcher = repository.get_watcher(watcher_id)
    if watcher is None:
        raise ApiError(
            404,
            error_code="WATCHER_NOT_FOUND",
            message=f"Watcher {watcher_id} was not found.",
            resource_id=str(watcher_id),
            correlation_id=resolved_correlation_id,
        )
    if watcher.lifecycle_state not in allowed_states:
        raise ApiError(
            409,
            error_code="WATCHER_STATE_CONFLICT",
            message=f"Watcher cannot {action} from {watcher.lifecycle_state}.",
            resource_id=str(watcher_id),
            current_state=watcher.lifecycle_state,
            correlation_id=resolved_correlation_id,
        )

    if require_green_preview:
        preview_summary = _build_preview_summary(
            repository,
            watcher_id,
            watcher.latest_route_preview_at or watcher.updated_at,
        )
        if preview_summary.status != "green":
            raise ApiError(
                409,
                error_code="ROUTE_NOT_ENABLED",
                message="Watcher route preview must be green before start.",
                resource_id=str(watcher_id),
                current_state=watcher.lifecycle_state,
                correlation_id=resolved_correlation_id,
            )

    created = command_repository.create_command(
        command_id=generate_uuid(),
        command_type=f"watcher.{action}",
        target_resource_type="watcher",
        target_resource_id=watcher_id,
        requested_by=payload.requested_by,
        operator_reason=payload.reason or "",
        idempotency_key=idempotency_key or generate_uuid_str(),
        correlation_id=resolved_correlation_id,
    )
    response = CommandAcceptedResponse(
        command_id=created.command_id,
        status="accepted",
        target_resource_type="watcher",
        target_resource_id=watcher_id,
        accepted_at=_format_datetime(created.created_at),
        correlation_id=resolved_correlation_id,
    )
    if idempotency_key is not None:
        command_repository.reserve_idempotency_key(
            idempotency_key_id=generate_uuid(),
            scope=scope,
            idempotency_key=idempotency_key,
            target_type="watcher",
            target_id=watcher_id,
            payload_hash=payload_hash,
            first_response_json=response.model_dump(mode="json"),
        )
    log_repository.write_summary(
        event_name=f"watcher.{action}_requested",
        sanitized_message=f"Watcher {watcher_id} {action} command accepted.",
        watcher_id=watcher_id,
        correlation_id=resolved_correlation_id,
    )
    repository.session.commit()
    return JSONResponse(status_code=202, content=response.model_dump(mode="json"))


def _build_watcher_detail_response(
    repository: WatcherRepository,
    watcher_id: UUID | str,
    correlation_id: str,
) -> WatcherDetailResponse:
    watcher = repository.get_watcher(watcher_id)
    if watcher is None:
        raise ApiError(
            404,
            error_code="WATCHER_NOT_FOUND",
            message=f"Watcher {watcher_id} was not found.",
            resource_id=str(watcher_id),
            correlation_id=correlation_id,
        )
    sources = repository.list_sources(watcher.watcher_id)
    destinations = repository.list_destinations(watcher.watcher_id)
    preview_summary = _build_preview_summary(
        repository,
        watcher.watcher_id,
        watcher.latest_route_preview_at or watcher.updated_at,
    )
    return WatcherDetailResponse(
        watcher_id=watcher.watcher_id,
        name=watcher.name,
        lifecycle_state=watcher.lifecycle_state,
        operational_status=watcher.operational_status,
        sources=[
            RouteTaggedFolderSpec(
                folder_id=source.source_folder_id,
                display_path=source.display_path,
                route_tags=source.route_tags,
                route_tags_text=source.route_tags_text,
                health_status=source.health_status,
                reason_code=source.reason_code,
            )
            for source in sources
        ],
        destinations=[
            RouteTaggedFolderSpec(
                folder_id=destination.destination_folder_id,
                display_path=destination.display_path,
                route_tags=destination.route_tags,
                route_tags_text=destination.route_tags_text,
                health_status=destination.health_status,
                reason_code=destination.reason_code,
            )
            for destination in destinations
        ],
        route_policy=watcher.route_policy,
        route_preview=preview_summary,
        created_at=_format_datetime(watcher.created_at),
        updated_at=_format_datetime(watcher.updated_at),
        correlation_id=correlation_id,
    )


def _build_preview_summary(
    repository: WatcherRepository,
    watcher_id: UUID | str,
    generated_at: datetime,
) -> WatcherRoutePreviewSummary:
    sources = repository.list_sources(watcher_id)
    destinations = repository.list_destinations(watcher_id)
    route_matches = repository.list_route_matches(watcher_id)
    matched_destination_ids = {
        row.destination_folder_id
        for row in route_matches
        if row.destination_folder_id is not None
    }
    unmatched_sources = {
        row.source_folder_id
        for row in route_matches
        if row.destination_folder_id is None
    }
    unmatched_destinations = {
        destination.destination_folder_id
        for destination in destinations
        if destination.destination_folder_id not in matched_destination_ids
    }
    status = _preview_status(
        matched_destination_count=len(matched_destination_ids),
        unmatched_source_count=len(unmatched_sources),
        unmatched_destination_count=len(unmatched_destinations),
    )
    return WatcherRoutePreviewSummary(
        status=status,
        matched_destination_count=len(matched_destination_ids),
        unmatched_source_count=len(unmatched_sources),
        unmatched_destination_count=len(unmatched_destinations),
        generated_at=_format_datetime(generated_at),
    )


def _prepare_folder_specs(
    specs: list[RouteTaggedFolderSpec],
    *,
    purpose: Literal["source", "destination"],
    record_id_field: str,
    path_policy: PathPolicy,
    correlation_id: str,
) -> list[dict[str, object]]:
    prepared: list[dict[str, object]] = []
    for index, spec in enumerate(specs):
        expected_tags = _normalize_route_tags_text(
            spec.route_tags_text,
            field=f"{purpose}s[{index}].route_tags_text",
            correlation_id=correlation_id,
        )
        if expected_tags != list(spec.route_tags):
            raise ApiError(
                422,
                error_code="TAG_INVALID",
                message="route_tags must match the normalized route_tags_text value.",
                field=f"{purpose}s[{index}].route_tags_text",
                correlation_id=correlation_id,
            )
        validation = _validate_folder_path(
            purpose=purpose,
            display_path=spec.display_path,
            path_policy=path_policy,
            correlation_id=correlation_id,
        )
        if validation.status != "green":
            raise ApiError(
                422,
                error_code=validation.reason_code or "PATH_INVALID",
                message=validation.message,
                field=f"{purpose}s[{index}].display_path",
                correlation_id=correlation_id,
            )
        prepared.append(
            {
                record_id_field: spec.folder_id,
                "display_path": spec.display_path,
                "normalized_path": validation.normalized_path,
                "route_tags": expected_tags,
                "route_tags_text": spec.route_tags_text,
                "health_status": spec.health_status or "green",
                "reason_code": spec.reason_code,
                "enabled": True,
            }
        )
    return prepared


def _validate_folder_path(
    *,
    purpose: Literal["source", "destination"],
    display_path: str,
    path_policy: PathPolicy,
    correlation_id: str,
):
    direct = path_policy.validate_path(purpose, display_path, correlation_id=correlation_id)
    if direct.status == "green":
        return direct
    roots = path_policy.source_roots if purpose == "source" else path_policy.destination_roots
    for root in roots:
        candidate = root.rstrip("/")
        if display_path != "/":
            candidate = f"{candidate}{display_path}"
        joined = path_policy.validate_path(purpose, candidate, correlation_id=correlation_id)
        if joined.status == "green":
            return joined
    return direct


def _compute_preview(
    sources: list[dict[str, object]],
    destinations: list[dict[str, object]],
    *,
    route_policy: str,
    correlation_id: str,
) -> dict[str, object]:
    matches_by_source: dict[UUID, list[UUID]] = defaultdict(list)
    matched_tags_by_pair: dict[tuple[UUID, UUID], list[str]] = {}
    matched_destination_ids: set[UUID] = set()
    route_match_rows: list[dict[str, object]] = []

    for source in sources:
        source_id = UUID(str(source["source_folder_id"]))
        source_tags = set(str(tag) for tag in source["route_tags"])
        for destination in destinations:
            destination_id = UUID(str(destination["destination_folder_id"]))
            destination_tags = set(str(tag) for tag in destination["route_tags"])
            matched_tags = sorted(source_tags & destination_tags)
            if not matched_tags:
                continue
            matches_by_source[source_id].append(destination_id)
            matched_tags_by_pair[(source_id, destination_id)] = matched_tags
            matched_destination_ids.add(destination_id)
            route_match_rows.append(
                {
                    "route_match_id": generate_uuid(),
                    "source_folder_id": source_id,
                    "destination_folder_id": destination_id,
                    "route_policy": route_policy,
                    "matched_route_tags": matched_tags,
                    "unmatched_reason_code": None,
                }
            )

    unmatched_sources = [
        UUID(str(source["source_folder_id"]))
        for source in sources
        if UUID(str(source["source_folder_id"])) not in matches_by_source
    ]
    for source_id in unmatched_sources:
        route_match_rows.append(
            {
                "route_match_id": generate_uuid(),
                "source_folder_id": source_id,
                "destination_folder_id": None,
                "route_policy": route_policy,
                "matched_route_tags": [],
                "unmatched_reason_code": "NO_MATCHING_DESTINATION",
            }
        )

    unmatched_destinations = [
        UUID(str(destination["destination_folder_id"]))
        for destination in destinations
        if UUID(str(destination["destination_folder_id"])) not in matched_destination_ids
    ]
    status = _preview_status(
        matched_destination_count=len(matched_destination_ids),
        unmatched_source_count=len(unmatched_sources),
        unmatched_destination_count=len(unmatched_destinations),
    )

    return {
        "status": status,
        "source_matches": [
            RoutePreviewMatch(
                source_folder_id=source_id,
                matched_destination_ids=sorted(
                    destination_ids,
                    key=str,
                ),
            )
            for source_id, destination_ids in sorted(matches_by_source.items(), key=lambda item: str(item[0]))
        ],
        "unmatched_sources": sorted(unmatched_sources, key=str),
        "unmatched_destinations": sorted(unmatched_destinations, key=str),
        "route_matches": route_match_rows,
    }


def _preview_status(
    *,
    matched_destination_count: int,
    unmatched_source_count: int,
    unmatched_destination_count: int,
) -> str:
    if matched_destination_count == 0:
        return "red"
    if unmatched_source_count or unmatched_destination_count:
        return "yellow"
    return "green"


def _normalize_route_tags_text(
    route_tags_text: str,
    *,
    field: str,
    correlation_id: str,
) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for raw_segment in route_tags_text.split(";"):
        tag = raw_segment.strip().upper()
        if not tag:
            raise ApiError(
                422,
                error_code="TAG_INVALID",
                message="route_tags_text must contain non-empty route tags.",
                field=field,
                correlation_id=correlation_id,
            )
        if not ROUTE_TAG_PATTERN.fullmatch(tag):
            raise ApiError(
                422,
                error_code="TAG_INVALID",
                message="Route tags must match ^[A-Z0-9_-]{1,32}$.",
                field=field,
                correlation_id=correlation_id,
            )
        if tag in seen:
            continue
        seen.add(tag)
        normalized.append(tag)
    if not normalized:
        raise ApiError(
            422,
            error_code="TAG_INVALID",
            message="At least one route tag is required.",
            field=field,
            correlation_id=correlation_id,
        )
    return normalized


def _source_records(repository: WatcherRepository, watcher_id: UUID | str) -> list[dict[str, object]]:
    return [
        {
            "source_folder_id": row.source_folder_id,
            "display_path": row.display_path,
            "normalized_path": row.normalized_path,
            "route_tags": row.route_tags,
            "route_tags_text": row.route_tags_text,
            "health_status": row.health_status,
            "reason_code": row.reason_code,
            "enabled": row.enabled,
        }
        for row in repository.list_sources(watcher_id)
    ]


def _destination_records(repository: WatcherRepository, watcher_id: UUID | str) -> list[dict[str, object]]:
    return [
        {
            "destination_folder_id": row.destination_folder_id,
            "display_path": row.display_path,
            "normalized_path": row.normalized_path,
            "route_tags": row.route_tags,
            "route_tags_text": row.route_tags_text,
            "health_status": row.health_status,
            "reason_code": row.reason_code,
            "enabled": row.enabled,
        }
        for row in repository.list_destinations(watcher_id)
    ]


def _payload_hash(payload: dict[str, object]) -> str:
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _format_datetime(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


__all__ = ["router"]
