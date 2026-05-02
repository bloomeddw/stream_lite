"""Dashboard presentation configuration routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from pydantic import ValidationError

from app.api.dependencies import get_or_create_correlation_id
from app.api.errors import ApiError
from app.api.schemas.api_models import DashboardPresentationResponse

router = APIRouter()

_EMBEDDED_PRESENTATION_DEFAULTS = {
    "schema_version": "1.0.0",
    "theme_name": "default_light",
    "color_tokens": {},
    "status_dot_tokens": {},
    "layout_profile": "operator_default",
    "layout_sections": [
        {
            "section_id": "demo",
            "visible": True,
            "order": 1,
        },
    ],
    "refresh_interval_seconds": 2,
}


@router.get("/config/dashboard-presentation", response_model=DashboardPresentationResponse)
def get_dashboard_presentation(
    request: Request,
    correlation_id: Annotated[str, Depends(get_or_create_correlation_id)],
) -> DashboardPresentationResponse:
    payload = getattr(request.app.state, "dashboard_presentation", _EMBEDDED_PRESENTATION_DEFAULTS)
    try:
        return DashboardPresentationResponse(
            **payload,
            correlation_id=correlation_id,
        )
    except ValidationError as exc:
        raise ApiError(
            500,
            error_code="PRESENTATION_CONFIG_INVALID",
            message="Dashboard presentation configuration is invalid.",
            correlation_id=correlation_id,
        ) from exc


__all__ = ["router"]
