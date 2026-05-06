from __future__ import annotations

from streamlit_app.api_client import poll_command_until_terminal


class _FakeClient:
    def __init__(self, statuses: list[str]) -> None:
        self.statuses = list(statuses)
        self.calls = 0

    def get_command_status(self, command_id: str) -> dict[str, object]:
        index = min(self.calls, len(self.statuses) - 1)
        self.calls += 1
        status = self.statuses[index]
        payload: dict[str, object] = {
            "command_id": command_id,
            "status": status,
            "result": {"done": True} if status == "succeeded" else None,
            "error": {"error_code": "COMMAND_FAILED"} if status == "failed" else None,
        }
        return payload


def test_accepted_is_not_treated_as_success() -> None:
    sleeps: list[float] = []
    client = _FakeClient(["accepted", "succeeded"])

    result = poll_command_until_terminal(client, "cmd-1", interval_seconds=0.25, sleep_fn=sleeps.append)

    assert result.status == "succeeded"
    assert result.attempts == 2
    assert sleeps == [0.25]


def test_polling_stops_on_succeeded_without_extra_sleep() -> None:
    sleeps: list[float] = []
    result = poll_command_until_terminal(_FakeClient(["succeeded"]), "cmd-1", sleep_fn=sleeps.append)

    assert result.status == "succeeded"
    assert result.attempts == 1
    assert sleeps == []


def test_polling_stops_on_failed() -> None:
    result = poll_command_until_terminal(_FakeClient(["running", "failed"]), "cmd-1", sleep_fn=lambda _: None)

    assert result.status == "failed"
    assert result.error == {"error_code": "COMMAND_FAILED"}


def test_polling_stops_on_expired() -> None:
    result = poll_command_until_terminal(_FakeClient(["accepted", "expired"]), "cmd-1", sleep_fn=lambda _: None)

    assert result.status == "expired"
    assert result.attempts == 2


def test_max_attempts_returns_last_non_terminal_status() -> None:
    sleeps: list[float] = []
    result = poll_command_until_terminal(
        _FakeClient(["accepted", "running", "running"]),
        "cmd-1",
        max_attempts=3,
        sleep_fn=sleeps.append,
    )

    assert result.status == "running"
    assert result.attempts == 3
    assert sleeps == [1.0, 1.0]
