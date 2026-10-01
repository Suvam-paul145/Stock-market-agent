import json

from stock_agent.report_paths import create_report_directory, refresh_report_index


def save_report(root, moment, kind="screen"):
    report = {"generated_at": moment, "mode": "test_fixture"}
    directory = create_report_directory(root, report, kind, allow_collision=True)
    (directory / "research.json").write_text(json.dumps(report), encoding="utf-8")
    (directory / "index.html").write_text("Test fixture", encoding="utf-8")
    return directory


def test_timestamp_is_converted_to_india_date_before_naming(tmp_path):
    directory = save_report(tmp_path, "2026-09-30T20:15:25Z")
    assert directory.name == "2026-10-01_01-45-25_IST_screen"


def test_two_runs_in_the_same_second_preserve_both_reports(tmp_path):
    first = save_report(tmp_path, "2026-10-01T00:00:00.100000Z")
    second = save_report(tmp_path, "2026-10-01T00:00:00.200000Z")
    assert first != second
    assert second.name.endswith("_0002")
    assert ".100000Z" in (first / "research.json").read_text()
    assert ".200000Z" in (second / "research.json").read_text()


def test_history_uses_original_report_time_not_creation_order(tmp_path):
    latest = save_report(tmp_path, "2026-10-01T00:00:00Z")
    earlier = save_report(tmp_path, "2026-09-01T00:00:00Z", "demo")
    incomplete = tmp_path / "incomplete"
    incomplete.mkdir()
    (incomplete / "index.html").write_text("Incomplete report")
    page = refresh_report_index(tmp_path).read_text(encoding="utf-8")
    assert page.index(latest.name) < page.index(earlier.name)
    assert "Latest" in page and "incomplete" not in page
