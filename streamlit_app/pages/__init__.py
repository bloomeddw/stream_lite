"""Read-only Streamlit dashboard page helpers for WP11-B1.

Page modules expose pure view-model builders plus optional render functions. The
builders use the API client contract only and must not import persistence, broker,
or worker internals.
"""

__all__ = ["config", "events", "health", "jobs", "logs", "outputs", "quarantine", "watchers"]
