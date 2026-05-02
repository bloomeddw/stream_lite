from __future__ import annotations

from app.watcher.stability import capture_file_snapshot, is_file_stable, sha256_file


def test_file_stability_requires_unchanged_size_and_mtime_for_window(tmp_path) -> None:
    path = tmp_path / "input.csv"
    path.write_text("a,b\n1,2\n", encoding="utf-8")

    first = capture_file_snapshot(path, observed_at_monotonic=10.0)
    second = capture_file_snapshot(path, observed_at_monotonic=11.0)

    assert not is_file_stable(first, second, now_monotonic=11.0, stability_seconds=2)
    assert is_file_stable(first, second, now_monotonic=12.0, stability_seconds=2)

    path.write_text("a,b\n1,2\n3,4\n", encoding="utf-8")
    changed = capture_file_snapshot(path, observed_at_monotonic=13.0)
    assert not is_file_stable(second, changed, now_monotonic=20.0, stability_seconds=2)


def test_sha256_file_is_deterministic_lower_case_hex(tmp_path) -> None:
    path = tmp_path / "input.txt"
    path.write_text("hello", encoding="utf-8")

    digest = sha256_file(path)

    assert digest == sha256_file(path)
    assert digest == "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"
    assert digest == digest.lower()
    assert len(digest) == 64
