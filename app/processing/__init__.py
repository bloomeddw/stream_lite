"""Processing package exports for WP-08."""

from .engine import ProcessingBatchResult, ProcessingExecutionResult, ProcessingWorker
from .spark_adapter import ProcessingAdapterInput, ProcessingAdapterResult, SparkDemoAdapter

__all__ = [
    "ProcessingAdapterInput",
    "ProcessingAdapterResult",
    "ProcessingBatchResult",
    "ProcessingExecutionResult",
    "ProcessingWorker",
    "SparkDemoAdapter",
]
