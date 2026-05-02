from __future__ import annotations

import re
from pathlib import Path

import pytest

from app.config import SettingsError, StreamLiteSettings

REPO_ROOT = Path(__file__).resolve().parents[2]


def _read_env_example() -> dict[str, str]:
    values: dict[str, str] = {}
    for line in (REPO_ROOT / ".env.example").read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key, value = line.split("=", 1)
        values[key] = value
    return values


def _catalog_env_vars() -> set[str]:
    text = (REPO_ROOT / "docs" / "operations" / "environment_variables.md").read_text(
        encoding="utf-8"
    )
    return set(re.findall(r"STREAM_LITE_[A-Z0-9_]+", text))


def test_settings_surface_matches_documented_env_inventory() -> None:
    documented = set(StreamLiteSettings.documented_env_vars())
    assert documented == set(_read_env_example())
    assert documented == _catalog_env_vars()


def test_settings_load_env_example_values() -> None:
    settings = StreamLiteSettings.from_environment(_read_env_example())

    assert settings.api_port == 8000
    assert settings.dashboard_port == 8501
    assert settings.broker_profile == "redis_streams"
    assert settings.processing_engine == "spark"
    assert settings.watch_root == "/data/sources"
    assert settings.output_root == "/data/outputs"
    assert settings.quarantine_root == "/data/quarantine"
    assert settings.debug is False
    assert settings.retry_backoff_multiplier == 2.0
    assert settings.log_level == "INFO"
    assert settings.to_path_policy().source_roots == ("/data/sources",)
    assert settings.as_environ(sanitized=True)["STREAM_LITE_DATABASE_URL"] == "[redacted]"


def test_settings_fail_fast_when_database_url_is_missing() -> None:
    env = _read_env_example()
    env.pop("STREAM_LITE_DATABASE_URL")

    with pytest.raises(SettingsError) as excinfo:
        StreamLiteSettings.from_environment(env)

    assert excinfo.value.env_var == "STREAM_LITE_DATABASE_URL"
    assert excinfo.value.error_code == "CONFIG_MISSING"


def test_settings_reject_invalid_port_range() -> None:
    env = _read_env_example()
    env["STREAM_LITE_API_PORT"] = "70000"

    with pytest.raises(SettingsError) as excinfo:
        StreamLiteSettings.from_environment(env)

    assert excinfo.value.env_var == "STREAM_LITE_API_PORT"
    assert excinfo.value.error_code == "CONFIG_INVALID_ENUM"


def test_settings_reject_deferred_processing_profile() -> None:
    env = _read_env_example()
    env["STREAM_LITE_PROCESSING_ENGINE"] = "flink"

    with pytest.raises(SettingsError) as excinfo:
        StreamLiteSettings.from_environment(env)

    assert excinfo.value.env_var == "STREAM_LITE_PROCESSING_ENGINE"
    assert excinfo.value.error_code == "CONFIG_UNSUPPORTED_DEFERRED_PROFILE"
