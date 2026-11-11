import json

from yue2_studio.event_log import EventLog


def test_write_and_read_back(tmp_path):
    log = EventLog(tmp_path / "logs" / "app.log", clock=lambda: 12.3456)
    log.write("job_submitted", job_id="j1", lyrics_chars=42)
    assert log.recent() == [
        {"ts": 12.346, "event": "job_submitted", "job_id": "j1", "lyrics_chars": 42}
    ]


def test_non_ascii_is_kept_readable(tmp_path):
    log = EventLog(tmp_path / "app.log")
    log.write("song_updated", title="霓虹")
    assert "霓虹" in (tmp_path / "app.log").read_text(encoding="utf-8")


def test_rotation_keeps_a_bounded_number_of_files(tmp_path):
    log = EventLog(tmp_path / "app.log", max_bytes=200, backups=2)
    for index in range(60):
        log.write("tick", index=index)
    names = sorted(path.name for path in tmp_path.iterdir())
    assert names == ["app.log", "app.log.1", "app.log.2"]
    assert log.recent(1)[0]["index"] == 59


def test_recent_skips_corrupt_lines(tmp_path):
    path = tmp_path / "app.log"
    path.write_text('{"event": "ok"}\nnot json\n', encoding="utf-8")
    assert EventLog(path).recent() == [{"event": "ok"}]


def test_recent_on_missing_file(tmp_path):
    assert EventLog(tmp_path / "missing.log").recent() == []


def test_diagnostics_contains_header_and_events(tmp_path):
    log = EventLog(tmp_path / "app.log")
    for index in range(30):
        log.write("tick", index=index)
    text = log.diagnostics({"gpu": "NVIDIA L4"})
    assert '"gpu": "NVIDIA L4"' in text
    events = [json.loads(line) for line in text.splitlines() if line.startswith('{"ts"')]
    assert [event["index"] for event in events] == list(range(10, 30))


def test_write_survives_an_unwritable_path(tmp_path):
    blocker = tmp_path / "blocker"
    blocker.write_text("x", encoding="utf-8")
    EventLog(blocker / "app.log").write("tick")
