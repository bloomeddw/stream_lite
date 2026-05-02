"""Route registration for the Stream Lite FastAPI app."""

from .commands import router as commands_router
from .config import router as config_router
from .events import router as events_router
from .files import router as files_router
from .health import router as health_router
from .jobs import router as jobs_router
from .metrics import router as metrics_router
from .operations import router as operations_router
from .watchers import router as watchers_router

ROUTERS = (
    health_router,
    watchers_router,
    jobs_router,
    commands_router,
    events_router,
    metrics_router,
    files_router,
    config_router,
    operations_router,
)

__all__ = ["ROUTERS"]
