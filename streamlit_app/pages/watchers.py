"""Watcher list, detail, route preview, and control helpers."""

from __future__ import annotations

import re
from typing import Any, Mapping
from uuid import uuid4

from streamlit_app.api_client import StreamLiteApiError
from streamlit_app.commands import build_command_status_display, submit_and_track_command
from streamlit_app.theme import get_status_token

JsonDict = dict[str, Any]

_ROUTE_TAG_PATTERN = re.compile(r"^[A-Z0-9_-]{1,32}$")
_MVP_ROUTE_POLICY = "tag_match_all_destinations"
_FUTURE_ROUTE_POLICIES = ("direct", "fanout", "rule_based")
_WATCHER_ACTIONS = ("start", "pause", "resume", "stop")
_ACTION_ALLOWED_STATES = {
    "start": {"CREATED", "STOPPED", "ERROR"},
    "pause": {"ACTIVE"},
    "resume": {"PAUSED"},
    "stop": {"CREATED", "ACTIVE", "PAUSED", "ERROR"},
}


def build_watchers_view_model(client: Any, config: Mapping[str, Any] | Any, params: Mapping[str, Any] | None = None) -> JsonDict:
    """Build the watcher list from the FastAPI watcher list endpoint."""

    payload = _dict_or_empty(client.list_watchers(params=params))
    rows: list[JsonDict] = []
    for item in _items(payload.get("items")):
        operational_status = item.get("operational_status")
        rows.append(
            {
                "watcher_id": item.get("watcher_id"),
                "name": item.get("name"),
                "lifecycle_state": item.get("lifecycle_state"),
                "operational_status": operational_status,
                "status_token": get_status_token(config, _status_key(operational_status)),
                "source_count": item.get("source_count"),
                "destination_count": item.get("destination_count"),
                "updated_at": item.get("updated_at"),
            }
        )
    return {
        "rows": rows,
        "total": int(payload.get("total", len(rows)) or 0),
        "limit": payload.get("limit"),
        "offset": payload.get("offset"),
        "empty_message": "No watchers found." if not rows else None,
        "refresh_interval_seconds": int(getattr(config, "refresh_interval_seconds", 2)),
        "correlation_id": payload.get("correlation_id"),
    }


def build_watcher_detail_view_model(client: Any, config: Mapping[str, Any] | Any, watcher_id: str) -> JsonDict:
    """Build a read-only watcher detail and route-preview summary."""

    payload = _dict_or_empty(client.get_watcher(watcher_id))
    route_preview = _dict_or_empty(payload.get("route_preview"))
    preview_status = route_preview.get("status")
    lifecycle_state = payload.get("lifecycle_state")
    return {
        "watcher_id": payload.get("watcher_id"),
        "name": payload.get("name"),
        "lifecycle_state": lifecycle_state,
        "operational_status": payload.get("operational_status"),
        "operational_status_token": get_status_token(config, _status_key(payload.get("operational_status"))),
        "route_policy": payload.get("route_policy"),
        "created_at": payload.get("created_at"),
        "updated_at": payload.get("updated_at"),
        "sources": [_folder_detail_row(config, item) for item in _items(payload.get("sources"))],
        "destinations": [_folder_detail_row(config, item) for item in _items(payload.get("destinations"))],
        "route_preview": {
            "status": preview_status,
            "status_token": get_status_token(config, _status_key(preview_status)),
            "matched_destination_count": route_preview.get("matched_destination_count"),
            "unmatched_source_count": route_preview.get("unmatched_source_count"),
            "unmatched_destination_count": route_preview.get("unmatched_destination_count"),
            "generated_at": route_preview.get("generated_at"),
        },
        "can_start_readonly": lifecycle_state in {"CREATED", "STOPPED", "ERROR"} and preview_status == "green",
        "correlation_id": payload.get("correlation_id"),
    }


def normalize_route_tags_text(route_tags_text: str) -> list[str]:
    """Normalize semicolon-delimited route tags for display and API payloads."""

    normalized: list[str] = []
    seen: set[str] = set()
    for raw_segment in str(route_tags_text).split(";"):
        tag = raw_segment.strip().upper()
        if not tag:
            raise ValueError("Route tags must not be empty.")
        if not _ROUTE_TAG_PATTERN.fullmatch(tag):
            raise ValueError("Route tags must match ^[A-Z0-9_-]{1,32}$.")
        if tag not in seen:
            normalized.append(tag)
            seen.add(tag)
    return normalized


def build_route_tagged_folder_spec(
    *,
    folder_id: str,
    display_path: str,
    route_tags_text: str,
    health_status: str | None = None,
    reason_code: str | None = None,
) -> JsonDict:
    """Return a RouteTaggedFolderSpec-shaped payload."""

    return {
        "folder_id": folder_id,
        "display_path": display_path,
        "route_tags": normalize_route_tags_text(route_tags_text),
        "route_tags_text": route_tags_text,
        "health_status": health_status,
        "reason_code": reason_code,
    }


def validate_folder_input(client: Any, config: Mapping[str, Any] | Any, *, purpose: str, path: str) -> JsonDict:
    """Validate a source or destination path through the API."""

    try:
        payload = _dict_or_empty(client.validate_path({"purpose": purpose, "path": path}))
    except StreamLiteApiError as exc:
        payload = _dict_or_empty(exc.payload)
        return {
            "purpose": purpose,
            "path": path,
            "normalized_path": None,
            "display_path": None,
            "status": "red",
            "reason_code": exc.error_code,
            "message": exc.message,
            "status_token": get_status_token(config, exc.error_code or "red"),
            "correlation_id": payload.get("correlation_id") or _dict_or_empty(payload.get("error")).get("correlation_id"),
        }

    status = payload.get("status")
    return {
        "purpose": payload.get("purpose", purpose),
        "path": payload.get("path", path),
        "normalized_path": payload.get("normalized_path"),
        "display_path": payload.get("display_path"),
        "status": status,
        "reason_code": payload.get("reason_code"),
        "message": payload.get("message"),
        "status_token": get_status_token(config, _status_key(status)),
        "correlation_id": payload.get("correlation_id"),
    }


def build_folder_browse_view_model(
    client: Any,
    config: Mapping[str, Any] | Any,
    *,
    purpose: str,
    root: str | None = None,
) -> JsonDict:
    """Build an allowlisted folder browse view model."""

    params = {"purpose": purpose}
    if root is not None:
        params["root"] = root
    try:
        payload = _dict_or_empty(client.browse_files(params))
    except StreamLiteApiError as exc:
        error_payload = _dict_or_empty(exc.payload)
        return {
            "purpose": purpose,
            "root": root,
            "items": [],
            "error_code": exc.error_code,
            "message": exc.message,
            "status_token": get_status_token(config, "red"),
            "correlation_id": error_payload.get("correlation_id") or _dict_or_empty(error_payload.get("error")).get("correlation_id"),
        }

    items = []
    for item in _items(payload.get("items")):
        reason_code = item.get("reason_code")
        items.append(
            {
                "name": item.get("name"),
                "display_path": item.get("display_path"),
                "is_directory": item.get("is_directory"),
                "is_selectable": item.get("is_selectable"),
                "reason_code": reason_code,
                "status_token": get_status_token(config, reason_code or ("green" if item.get("is_selectable") else "yellow")),
            }
        )
    return {
        "purpose": payload.get("purpose", purpose),
        "root": payload.get("root", root),
        "items": items,
        "correlation_id": payload.get("correlation_id"),
    }


def build_route_preview_view_model(
    client: Any,
    config: Mapping[str, Any] | Any,
    *,
    watcher_id: str,
    sources: list[Mapping[str, Any]],
    destinations: list[Mapping[str, Any]],
    route_policy: str = _MVP_ROUTE_POLICY,
) -> JsonDict:
    """Preview route matches and map API IDs back to display rows."""

    payload = {
        "sources": [dict(item) for item in sources],
        "destinations": [dict(item) for item in destinations],
        "route_policy": route_policy,
    }
    try:
        response = _dict_or_empty(client.preview_routes(watcher_id, payload))
    except StreamLiteApiError as exc:
        error_payload = _dict_or_empty(exc.payload)
        return {
            "watcher_id": watcher_id,
            "route_policy": route_policy,
            "status": "red",
            "status_token": get_status_token(config, exc.error_code or "red"),
            "source_rows": [],
            "unmatched_destinations": [],
            "can_enable": False,
            "error_code": exc.error_code,
            "message": exc.message,
            "correlation_id": error_payload.get("correlation_id") or _dict_or_empty(error_payload.get("error")).get("correlation_id"),
        }

    source_by_id = {_folder_id(source): dict(source) for source in sources}
    destination_by_id = {_folder_id(destination): dict(destination) for destination in destinations}
    matches_by_source = {
        str(match.get("source_folder_id")): [str(destination_id) for destination_id in _list_or_empty(match.get("matched_destination_ids"))]
        for match in _items(response.get("source_matches"))
    }
    unmatched_sources = {str(item) for item in _list_or_empty(response.get("unmatched_sources"))}
    unmatched_destination_ids = [str(item) for item in _list_or_empty(response.get("unmatched_destinations"))]

    source_rows = []
    for source_id, source in source_by_id.items():
        matched_destinations = []
        for destination_id in matches_by_source.get(source_id, []):
            destination = destination_by_id.get(destination_id, {})
            destination_status = destination.get("health_status") or "green"
            matched_destinations.append(
                {
                    "destination_folder_id": destination_id,
                    "display_path": destination.get("display_path"),
                    "health_status": destination.get("health_status"),
                    "status_token": get_status_token(config, _status_key(destination_status)),
                    "matched_route_tags": _matched_route_tags(source, destination),
                }
            )
        unmatched = source_id in unmatched_sources
        row_status = "NO_MATCHING_DESTINATION" if unmatched else (source.get("health_status") or "green")
        source_rows.append(
            {
                "source_folder_id": source_id,
                "source_display_path": source.get("display_path"),
                "source_route_tags": _string_list(source.get("route_tags")),
                "matched_destinations": matched_destinations,
                "unmatched": unmatched,
                "reason_code": "NO_MATCHING_DESTINATION" if unmatched else None,
                "status_token": get_status_token(config, row_status),
            }
        )

    unmatched_destinations = []
    for destination_id in unmatched_destination_ids:
        destination = destination_by_id.get(destination_id, {})
        unmatched_destinations.append(
            {
                "destination_folder_id": destination_id,
                "display_path": destination.get("display_path"),
                "health_status": destination.get("health_status"),
                "reason_code": "NO_MATCHING_SOURCE",
                "status_token": get_status_token(config, "NO_MATCHING_SOURCE"),
            }
        )

    status = response.get("status")
    return {
        "watcher_id": watcher_id,
        "route_policy": response.get("route_policy", route_policy),
        "status": status,
        "status_token": get_status_token(config, _status_key(status)),
        "source_rows": source_rows,
        "unmatched_destinations": unmatched_destinations,
        "can_enable": status == "green" and not _has_red_folder(sources, destinations) and _all_have_valid_tags(sources, destinations),
        "correlation_id": response.get("correlation_id"),
    }


def build_lifecycle_request_payload(*, requested_by: str, reason: str | None = None) -> JsonDict:
    """Build a watcher lifecycle command payload."""

    operator = str(requested_by or "").strip()
    if not operator:
        raise ValueError("Operator is required.")
    clean_reason = None if reason is None or not str(reason).strip() else str(reason).strip()
    return {"requested_by": operator, "reason": clean_reason}


def submit_watcher_lifecycle_command(
    client: Any,
    config: Mapping[str, Any] | Any,
    *,
    watcher_id: str,
    action: str,
    requested_by: str,
    reason: str | None = None,
    idempotency_key: str | None = None,
    sleep_fn: Any = None,
) -> JsonDict:
    """Submit a watcher lifecycle command through the API client."""

    if action not in _WATCHER_ACTIONS:
        return {
            "accepted": False,
            "status": "failed",
            "error_code": "DASHBOARD_WATCHER_ACTION_INVALID",
            "message": "Unsupported watcher action.",
        }
    try:
        payload = build_lifecycle_request_payload(requested_by=requested_by, reason=reason)
    except ValueError as exc:
        return {
            "accepted": False,
            "status": "failed",
            "error_code": "DASHBOARD_WATCHER_INPUT_INVALID",
            "message": str(exc),
        }

    def submit(payload_to_submit: Mapping[str, Any], *, idempotency_key: str | None = None) -> Mapping[str, Any]:
        return client.watcher_command(watcher_id, action, payload_to_submit, idempotency_key=idempotency_key)

    return submit_and_track_command(
        submit_fn=submit,
        submit_payload=payload,
        client=client,
        config=config,
        idempotency_key=idempotency_key,
        sleep_fn=sleep_fn,
    )


def render_watchers_page(client: Any, config: Mapping[str, Any] | Any) -> None:
    """Render the watcher page when Streamlit runtime is available."""

    import streamlit as st

    view_model = build_watchers_view_model(client, config)
    st.header("Watchers")
    if view_model["rows"]:
        st.table(view_model["rows"])
    else:
        st.info(view_model["empty_message"])

    selected_watcher_id = None
    if view_model["rows"]:
        selected_watcher_id = st.selectbox(
            "Watcher",
            [str(row["watcher_id"]) for row in view_model["rows"] if row.get("watcher_id")],
            key="watchers_selected_watcher_id",
        )
        if selected_watcher_id:
            _render_watcher_detail(client, config, selected_watcher_id)

    _render_create_watcher_form(client, config)
    if selected_watcher_id:
        _render_edit_watcher_form(client, config, selected_watcher_id)


def _render_watcher_detail(client: Any, config: Mapping[str, Any] | Any, watcher_id: str) -> None:
    import streamlit as st

    detail = build_watcher_detail_view_model(client, config, watcher_id)
    st.subheader("Watcher detail")
    st.json(
        {
            "watcher_id": detail["watcher_id"],
            "name": detail["name"],
            "lifecycle_state": detail["lifecycle_state"],
            "operational_status": detail["operational_status"],
            "route_policy": detail["route_policy"],
            "route_preview": detail["route_preview"],
            "can_start_readonly": detail["can_start_readonly"],
        }
    )
    st.subheader("Sources")
    st.table(detail["sources"])
    st.subheader("Destinations")
    st.table(detail["destinations"])
    _render_route_preview_control(client, config, watcher_id, detail)
    _render_lifecycle_controls(client, config, watcher_id, detail)


def _render_route_preview_control(client: Any, config: Mapping[str, Any] | Any, watcher_id: str, detail: Mapping[str, Any]) -> None:
    import streamlit as st

    if st.button("Preview routes", key=f"preview_{watcher_id}"):
        preview = build_route_preview_view_model(
            client,
            config,
            watcher_id=watcher_id,
            sources=list(detail.get("sources", [])),
            destinations=list(detail.get("destinations", [])),
            route_policy=str(detail.get("route_policy") or _MVP_ROUTE_POLICY),
        )
        st.session_state[f"preview_result_{watcher_id}"] = preview
    preview_result = st.session_state.get(f"preview_result_{watcher_id}")
    if preview_result:
        st.subheader("Route preview")
        st.json(preview_result)


def _render_lifecycle_controls(client: Any, config: Mapping[str, Any] | Any, watcher_id: str, detail: Mapping[str, Any]) -> None:
    import streamlit as st

    st.subheader("Lifecycle")
    requested_by = st.text_input("Operator", key=f"watcher_operator_{watcher_id}")
    reason = st.text_input("Reason", key=f"watcher_reason_{watcher_id}")
    lifecycle_state = str(detail.get("lifecycle_state") or "")
    route_preview = _dict_or_empty(detail.get("route_preview"))
    can_start = lifecycle_state in _ACTION_ALLOWED_STATES["start"] and route_preview.get("status") == "green"
    for action in _WATCHER_ACTIONS:
        allowed = can_start if action == "start" else lifecycle_state in _ACTION_ALLOWED_STATES[action]
        if st.button(action.title(), disabled=not allowed, key=f"{action}_{watcher_id}"):
            card = submit_watcher_lifecycle_command(
                client,
                config,
                watcher_id=watcher_id,
                action=action,
                requested_by=requested_by,
                reason=reason,
                idempotency_key=f"watcher-{action}-{watcher_id}-{uuid4()}",
            )
            st.session_state[f"watcher_command_{watcher_id}"] = card
    command_card = st.session_state.get(f"watcher_command_{watcher_id}")
    if command_card:
        st.json(build_command_status_display(command_card))


def _render_create_watcher_form(client: Any, config: Mapping[str, Any] | Any) -> None:
    import streamlit as st

    st.subheader("Create watcher")
    _ensure_folder_rows("create_sources")
    _ensure_folder_rows("create_destinations")
    if st.button("Add source", key="create_add_source"):
        st.session_state["create_sources"].append(_blank_folder_row())
    if st.button("Add destination", key="create_add_destination"):
        st.session_state["create_destinations"].append(_blank_folder_row())
    if st.button("Browse source", key="create_browse_source"):
        st.session_state["create_source_browse"] = build_folder_browse_view_model(client, config, purpose="source")
    if st.button("Browse destination", key="create_browse_destination"):
        st.session_state["create_destination_browse"] = build_folder_browse_view_model(client, config, purpose="destination")
    if st.session_state.get("create_source_browse"):
        st.table(st.session_state["create_source_browse"].get("items", []))
    if st.session_state.get("create_destination_browse"):
        st.table(st.session_state["create_destination_browse"].get("items", []))

    with st.form("create_watcher_form"):
        name = st.text_input("Watcher name", key="create_watcher_name")
        st.selectbox("Route policy", [_MVP_ROUTE_POLICY], key="create_route_policy")
        for policy in _FUTURE_ROUTE_POLICIES:
            st.checkbox(policy, value=False, disabled=True, key=f"future_policy_{policy}")
        source_inputs = _folder_form_inputs("source", st.session_state["create_sources"], "create")
        destination_inputs = _folder_form_inputs("destination", st.session_state["create_destinations"], "create")
        validate_clicked = st.form_submit_button("Validate paths")
        save_clicked = st.form_submit_button("Save watcher")

    if validate_clicked or save_clicked:
        sources, source_errors = _validated_specs(client, config, "source", source_inputs)
        destinations, destination_errors = _validated_specs(client, config, "destination", destination_inputs)
        st.session_state["create_validation_results"] = [_validation_display_row(config, spec) for spec in [*sources, *destinations]]
        for error in [*source_errors, *destination_errors]:
            st.error(error)
        if save_clicked and name.strip() and sources and destinations and not source_errors and not destination_errors:
            try:
                created = client.create_watcher(
                    {
                        "name": name.strip(),
                        "sources": sources,
                        "destinations": destinations,
                        "route_policy": _MVP_ROUTE_POLICY,
                        "enabled": False,
                    }
                )
            except StreamLiteApiError as exc:
                st.error(exc.message)
            else:
                st.success("created")
                st.json(created)
    if st.session_state.get("create_validation_results"):
        st.subheader("Validation")
        st.table(st.session_state["create_validation_results"])


def _render_edit_watcher_form(client: Any, config: Mapping[str, Any] | Any, watcher_id: str) -> None:
    import streamlit as st

    detail = build_watcher_detail_view_model(client, config, watcher_id)
    active = detail.get("lifecycle_state") == "ACTIVE"
    st.subheader("Edit watcher")
    with st.form(f"edit_watcher_form_{watcher_id}"):
        name = st.text_input("Watcher name", value=str(detail.get("name") or ""), disabled=active, key=f"edit_name_{watcher_id}")
        st.selectbox("Route policy", [_MVP_ROUTE_POLICY], disabled=active, key=f"edit_policy_{watcher_id}")
        submit = st.form_submit_button("Save edits", disabled=active)
    if submit:
        try:
            updated = client.patch_watcher(watcher_id, {"name": name.strip(), "route_policy": _MVP_ROUTE_POLICY})
        except StreamLiteApiError as exc:
            st.error(exc.message)
        else:
            st.success("updated")
            st.json(updated)


def _folder_form_inputs(purpose: str, rows: list[JsonDict], key_prefix: str) -> list[JsonDict]:
    import streamlit as st

    inputs = []
    for index, row in enumerate(rows):
        st.write(f"{purpose.title()} {index + 1}")
        path = st.text_input("Path", value=str(row.get("path") or ""), key=f"{key_prefix}_{purpose}_{index}_path")
        route_tags_text = st.text_input("Route tags", value=str(row.get("route_tags_text") or ""), key=f"{key_prefix}_{purpose}_{index}_tags")
        try:
            st.write("Normalized tags", normalize_route_tags_text(route_tags_text))
        except ValueError as exc:
            st.warning(str(exc))
        inputs.append({"folder_id": row["folder_id"], "path": path, "route_tags_text": route_tags_text})
    return inputs


def _validated_specs(
    client: Any,
    config: Mapping[str, Any] | Any,
    purpose: str,
    inputs: list[Mapping[str, Any]],
) -> tuple[list[JsonDict], list[str]]:
    specs = []
    errors = []
    for item in inputs:
        path = str(item.get("path") or "").strip()
        route_tags_text = str(item.get("route_tags_text") or "").strip()
        if not path:
            errors.append(f"{purpose} path is required.")
            continue
        try:
            route_tags = normalize_route_tags_text(route_tags_text)
        except ValueError as exc:
            errors.append(str(exc))
            continue
        validation = validate_folder_input(client, config, purpose=purpose, path=path)
        if validation.get("status") == "red":
            errors.append(str(validation.get("message") or validation.get("reason_code") or "Path validation failed."))
            continue
        specs.append(
            {
                "folder_id": item.get("folder_id"),
                "display_path": validation.get("display_path") or path,
                "route_tags": route_tags,
                "route_tags_text": route_tags_text,
                "health_status": validation.get("status"),
                "reason_code": validation.get("reason_code"),
            }
        )
    return specs, errors


def _validation_display_row(config: Mapping[str, Any] | Any, spec: Mapping[str, Any]) -> JsonDict:
    return {
        **dict(spec),
        "status_token": get_status_token(config, spec.get("reason_code") or spec.get("health_status") or "unknown"),
    }


def _ensure_folder_rows(key: str) -> None:
    import streamlit as st

    if key not in st.session_state:
        st.session_state[key] = [_blank_folder_row()]


def _blank_folder_row() -> JsonDict:
    return {"folder_id": str(uuid4()), "path": "", "route_tags_text": ""}


def _folder_detail_row(config: Mapping[str, Any] | Any, item: Mapping[str, Any]) -> JsonDict:
    health_status = item.get("health_status")
    reason_code = item.get("reason_code")
    return {
        "folder_id": item.get("folder_id"),
        "display_path": item.get("display_path"),
        "route_tags": _string_list(item.get("route_tags")),
        "route_tags_text": item.get("route_tags_text"),
        "health_status": health_status,
        "reason_code": reason_code,
        "status_token": get_status_token(config, reason_code or _status_key(health_status)),
    }


def _status_key(value: Any) -> str:
    return "unknown" if value is None else str(value)


def _matched_route_tags(source: Mapping[str, Any], destination: Mapping[str, Any]) -> list[str]:
    destination_tags = set(_string_list(destination.get("route_tags")))
    return [tag for tag in _string_list(source.get("route_tags")) if tag in destination_tags]


def _all_have_valid_tags(sources: list[Mapping[str, Any]], destinations: list[Mapping[str, Any]]) -> bool:
    for item in [*sources, *destinations]:
        tags = _string_list(item.get("route_tags"))
        if not tags or any(_ROUTE_TAG_PATTERN.fullmatch(tag) is None for tag in tags):
            return False
    return True


def _has_red_folder(sources: list[Mapping[str, Any]], destinations: list[Mapping[str, Any]]) -> bool:
    return any(str(item.get("health_status") or "").lower() == "red" for item in [*sources, *destinations])


def _folder_id(item: Mapping[str, Any]) -> str:
    return str(item.get("folder_id") or item.get("source_folder_id") or item.get("destination_folder_id") or "")


def _items(value: Any) -> list[JsonDict]:
    if isinstance(value, list):
        return [dict(item) for item in value if isinstance(item, Mapping)]
    return []


def _list_or_empty(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def _string_list(value: Any) -> list[str]:
    return [str(item) for item in value] if isinstance(value, list) else []


def _dict_or_empty(value: Any) -> JsonDict:
    return dict(value) if isinstance(value, Mapping) else {}


__all__ = [
    "build_folder_browse_view_model",
    "build_lifecycle_request_payload",
    "build_route_preview_view_model",
    "build_route_tagged_folder_spec",
    "build_watcher_detail_view_model",
    "build_watchers_view_model",
    "normalize_route_tags_text",
    "render_watchers_page",
    "submit_watcher_lifecycle_command",
    "validate_folder_input",
]
