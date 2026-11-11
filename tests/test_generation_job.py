import threading

from conftest import FORM

from yue2_studio import ui_text
from yue2_studio.engine import StageEvent
from yue2_studio.stand_in_pipeline import STAND_IN_ABC, StandInPipeline


def states(updates):
    seen = []
    for update in updates:
        if not seen or seen[-1] != update.state:
            seen.append(update.state)
    return seen


def run_in_background(generator):
    updates = []
    thread = threading.Thread(target=lambda: updates.extend(generator), daemon=True)
    thread.start()
    return thread, updates


def test_render_ends_with_a_saved_song(studio):
    updates = list(studio.runner.run_render(FORM))
    final = updates[-1]
    assert final.state == "done"
    assert final.song_id is not None
    record = studio.store.get(final.song_id)
    assert record.request["seed"] == 7
    assert record.abc_source == "planned"
    assert record.peak_vram_gib == 11.5
    assert record.versions == {"studio": "test"}
    assert final.elapsed > 0


def test_stage_log_follows_the_pipeline(studio):
    list(studio.runner.run_render(FORM))
    stages = [event["stage"] for event in studio.events("job_stage")]
    assert stages == ["planning", "composing", "rendering", "decoding", "saving"]
    assert len(studio.events("job_completed")) == 1


def test_log_never_contains_the_lyrics(studio):
    list(studio.runner.run_render({**FORM, "lyrics": "[Verse]\nsecret words"}))
    text = (studio.root / "logs" / "app.log").read_text(encoding="utf-8")
    assert "secret words" not in text and "piano pop" not in text
    assert studio.events("job_submitted")[0]["lyrics_chars"] == len("[Verse]\nsecret words")


def test_plan_ends_with_a_score_and_no_song(studio):
    final = list(studio.runner.run_plan(FORM))[-1]
    assert final.state == "score_ready"
    assert final.abc == STAND_IN_ABC
    assert studio.store.list_songs() == []


def test_render_with_an_edited_score(studio):
    edited = STAND_IN_ABC.replace("C2 E2", "D2 F2")
    final = list(studio.runner.run_render(FORM, abc=edited, abc_source="edited"))[-1]
    assert final.state == "done"
    assert studio.pipe.calls[-1][1]["abc"] == edited.strip()
    record = studio.store.get(final.song_id)
    assert record.abc_source == "edited"
    assert studio.store.score_text(final.song_id) == edited.strip()
    assert len(studio.events("score_edited")) == 1


def test_cot_off_has_no_score_source(studio):
    final = list(studio.runner.run_render({**FORM, "cot": "off"}))[-1]
    assert studio.store.get(final.song_id).abc_source == "none"
    assert "planning" not in [event["stage"] for event in studio.events("job_stage")]


def test_validation_failure_does_not_start_a_job(studio):
    updates = list(studio.runner.run_render({**FORM, "style": " "}))
    assert len(updates) == 1
    assert updates[0].error_code == "E_VALIDATION"
    assert updates[0].field_errors[0].field == "style"
    assert studio.pipes == []
    assert list(studio.runner.run_render(FORM))[-1].state == "done"


def test_cancel_during_composing(make_studio, gate):
    hold = gate("semantic")
    studio = make_studio(StandInPipeline(on_stage_entered=hold))
    thread, updates = run_in_background(studio.runner.run_render(FORM))
    assert hold.reached.wait(5)
    assert studio.runner.cancel() == "requested"
    assert studio.runner.snapshot().notice == ui_text.CANCEL_REQUESTED
    hold.release.set()
    thread.join(5)
    assert updates[-1].state == "cancelled"
    assert studio.store.list_songs() == []
    assert len(studio.events("job_cancelled")) == 1
    assert list(studio.runner.run_render(FORM))[-1].state == "done"


def test_cancel_is_ignored_once_decoding_started(make_studio, gate):
    hold = gate("vae")
    studio = make_studio(StandInPipeline(on_stage_entered=hold))
    thread, updates = run_in_background(studio.runner.run_render(FORM))
    assert hold.reached.wait(5)
    # The stand-in enters "vae" just before its first decode progress event.
    studio.runner._advance(StageEvent("decoding", 0, 2))
    assert studio.runner.cancel() == "too_late"
    assert studio.runner.snapshot().notice == ui_text.CANCEL_TOO_LATE
    hold.release.set()
    thread.join(5)
    assert updates[-1].state == "done"



def test_cancel_when_idle(studio):
    assert studio.runner.cancel() == "idle"


def test_second_request_is_rejected_while_one_runs(make_studio, gate):
    hold = gate("semantic")
    studio = make_studio(StandInPipeline(on_stage_entered=hold))
    thread, updates = run_in_background(studio.runner.run_render(FORM))
    assert hold.reached.wait(5)

    second = list(studio.runner.run_render(FORM))
    assert len(second) == 1 and second[0].rejected
    assert second[0].running
    assert list(studio.runner.run_plan(FORM))[0].rejected

    hold.release.set()
    thread.join(5)
    assert updates[-1].state == "done"
    assert len(studio.store.list_songs()) == 1


def test_out_of_memory_fails_and_the_next_job_reloads(make_studio):
    class OutOfMemoryError(RuntimeError):
        pass

    studio = make_studio(StandInPipeline(fail_at="nar", error=OutOfMemoryError("out of memory")))
    final = list(studio.runner.run_render(FORM))[-1]
    assert final.state == "failed" and final.error_code == "E_OOM"
    assert studio.events("job_failed")[0]["stage"] == "composing"
    assert studio.store.list_songs() == []

    assert list(studio.runner.run_render(FORM))[-1].state == "done"
    assert len(studio.pipes) == 2


def test_unexpected_error_is_reported_and_the_lock_released(make_studio):
    studio = make_studio(StandInPipeline(fail_at="semantic", error=KeyError("boom")))
    final = list(studio.runner.run_render(FORM))[-1]
    assert final.error_code == "E_UNKNOWN"
    assert "KeyError" in final.error_detail
    assert not studio.runner.snapshot().running
    assert studio.runner.cancel() == "idle"


def test_storage_failure_keeps_a_rescue_copy(make_studio):
    studio = make_studio(StandInPipeline(save_error=OSError("No space left on device")))
    final = list(studio.runner.run_render(FORM))[-1]
    assert final.error_code == "E_STORAGE"
    assert final.rescue_path is not None
    assert (studio.root / "_rescue").is_dir()
    assert studio.store.list_songs() == []
    assert not any(path.name.startswith(".tmp-") for path in (studio.root / "songs").iterdir())


def test_timeout_stops_the_job(make_studio):
    ticks = iter(range(0, 10_000_000, 400))
    studio = make_studio(clock=lambda: float(next(ticks)), timeout_seconds=1000)
    final = list(studio.runner.run_render(FORM))[-1]
    assert final.state == "failed" and final.error_code == "E_TIMEOUT"
    assert studio.store.list_songs() == []


def test_download_retry_is_surfaced_as_a_notice(make_studio):
    studio = make_studio()
    attempts = []
    notices = []

    def factory(cache_dir):
        attempts.append(1)
        if len(attempts) == 1:
            raise ConnectionError("reset")
        notices.append(studio.runner.snapshot().notice)
        return StandInPipeline()

    studio.engine._factory = factory
    assert list(studio.runner.run_render(FORM))[-1].state == "done"
    assert notices == [ui_text.DOWNLOAD_RETRY.format(attempt=1)]


def test_download_failure_after_retries(make_studio):
    studio = make_studio()

    def factory(cache_dir):
        raise ConnectionError("down")

    studio.engine._factory = factory
    final = list(studio.runner.run_render(FORM))[-1]
    assert final.error_code == "E_MODEL_DOWNLOAD"
    assert states([final]) == ["failed"]


def test_job_survives_an_abandoned_generator(make_studio, gate):
    """Closing the browser tab drops the generator; the song must still be saved."""
    hold = gate("semantic")
    studio = make_studio(StandInPipeline(on_stage_entered=hold))
    generator = studio.runner.run_render(FORM)
    next(generator)
    assert hold.reached.wait(5)
    generator.close()
    hold.release.set()
    studio.runner.wait(5)
    assert studio.runner.snapshot().state == "done"
    assert len(studio.store.list_songs()) == 1


def test_snapshot_reports_elapsed_while_running(make_studio, gate):
    hold = gate("semantic")
    studio = make_studio(StandInPipeline(on_stage_entered=hold))
    thread, _ = run_in_background(studio.runner.run_render(FORM))
    assert hold.reached.wait(5)
    snapshot = studio.runner.snapshot()
    # The gate holds the pipeline on entry to the semantic phase, before its first token.
    assert snapshot.running and snapshot.state == "planning" and snapshot.elapsed >= 0
    hold.release.set()
    thread.join(5)
