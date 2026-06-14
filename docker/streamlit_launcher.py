"""Docker Streamlit entrypoint for the Stream Lite dashboard.

The application shell defaults to localhost for direct developer execution.
Inside Docker Compose, the dashboard reaches the FastAPI service through the
stable compose service name `api` without adding a dashboard-only env var.
"""

from __future__ import annotations

from streamlit_app.api_client import StreamLiteApiClient
from streamlit_app.main import render_app

render_app(StreamLiteApiClient("http://api:8000"))
