"""Edge and abuse cases from the spec that are not covered by a module's own tests."""

import json
import threading

from conftest import Gate
from test_app_flows import build, form, last

from yue2_studio import ui_text
from yue2_studio.stand_in_pipeline import StandInPipeline


def test_very_long_lyrics_are_refused_and_the_draft_keeps_them(tmp_path):
    studio, wiring = build(tmp_path)
    lyrics = "啦" * 50_000
    final, _ = last(studio.submit(form(lyrics=lyrics)))
    assert "50000" in final["error_html"]["value"]
    assert wiring.pipes == []
    assert studio.drafts.load().lyrics == lyrics


def test_markup_in_lyrics_is_stored_verbatim_and_escaped_in_errors(tmp_path):
    studio, _ = build(tmp_path)
    lyrics = "[Verse]\n<img src=x onerror=alert(1)>"
    last(studio.submit(form(lyrics=lyrics)))
    song = studio.store.list_songs()[0]
    assert song.request["lyrics"] == lyrics


def test_double_click_starts_only_one_job(tmp_path):
    hold = Gate("semantic")
    studio, wiring = build(tmp_path, StandInPipeline(on_stage_entered=hold))
    patches = []
    thread = threading.Thread(target=lambda: patches.extend(studio.submit(form())), daemon=True)
    thread.start()
    assert hold.reached.wait(5)

    second, all_second = last(studio.submit(form()))
    assert all_second == [{"_toast": ("warning", ui_text.ERRORS["E_BUSY"])}]
    assert studio.restart_ask()["_toast"][0] == "warning"
    assert studio.restart_confirm()["_toast"][0] == "warning"
    assert studio.release_engine()["_toast"] == ("warning", ui_text.ENGINE_BUSY)
    assert studio.load_to_form("20261111-000000-zzzz")["_toast"][0] == "warning"

    hold.release.set()
    thread.join(5)
    assert len(studio.store.list_songs()) == 1
    assert sum(1 for name, _ in wiring.pipe.calls if name == "call") == 1


def test_reload_during_a_job_picks_up_the_status(tmp_path):
    hold = Gate("nar")
    studio, _ = build(tmp_path, StandInPipeline(on_stage_entered=hold))
    thread = threading.Thread(target=lambda: list(studio.submit(form())), daemon=True)
    thread.start()
    assert hold.reached.wait(5)

    patch = studio.page_load()
    assert ui_text.STAGE_LABELS["composing"] in patch["status_html"]["value"]
    assert patch["cancel_btn"] == {"visible": True}
    assert patch["primary_btn"]["interactive"] is False
    assert studio.tick()["cancel_btn"] == {"visible": True}

    hold.release.set()
    thread.join(5)
    assert ui_text.STAGE_LABELS["done"] in studio.tick()["status_html"]["value"]


def test_binary_file_renamed_to_abc_is_refused(tmp_path):
    studio, _ = build(tmp_path)
    path = tmp_path / "fake.abc"
    path.write_bytes(bytes(range(256)))
    patch = studio.abc_uploaded(str(path), form(abc_text="keep"))
    assert patch["_toast"] == ("warning", ui_text.ABC_NOT_TEXT)
    assert "abc_editor" not in patch


def test_cancel_during_decoding_reports_too_late(tmp_path):
    hold = Gate("vae")
    studio, _ = build(tmp_path, StandInPipeline(on_stage_entered=hold))
    thread = threading.Thread(target=lambda: list(studio.submit(form())), daemon=True)
    thread.start()
    assert hold.reached.wait(5)
    from yue2_studio.engine import StageEvent

    studio.runner._advance(StageEvent("decoding", 0, 2))
    assert studio.cancel()["_toast"] == ("warning", ui_text.CANCEL_TOO_LATE)
    hold.release.set()
    thread.join(5)
    assert len(studio.store.list_songs()) == 1


def test_full_storage_shows_the_rescue_path(tmp_path):
    studio, _ = build(tmp_path, StandInPipeline(save_error=OSError("No space left on device")))
    final, _ = last(studio.submit(form()))
    html = final["error_html"]["value"]
    assert "E_STORAGE" in html and "_rescue" in html
    assert studio.store.list_songs() == []


def test_song_with_missing_audio_is_listed_as_incomplete(tmp_path):
    studio, _ = build(tmp_path)
    last(studio.submit(form()))
    song = studio.store.list_songs()[0]
    studio.store.audio_path(song.song_id).unlink()
    choices = studio.refresh_library()["library_radio"]["choices"]
    assert ui_text.SONG_INCOMPLETE in choices[0][0]
    assert studio.page_load()["result_group"] == {"visible": False}
    studio.delete_confirm(song.song_id)
    assert studio.store.list_songs() == []


def test_chinese_request_is_stored_readably(tmp_path):
    studio, _ = build(tmp_path)
    last(studio.submit(form(style="國語、鋼琴抒情、女聲", lyrics="[主歌]\n霓虹漸漸淡去的巷口")))
    song = studio.store.list_songs()[0]
    raw = (tmp_path / "songs" / song.song_id / "studio.json").read_text(encoding="utf-8")
    assert "霓虹漸漸淡去的巷口" in raw
    assert json.loads(raw)["title"] == "國語、鋼琴抒情、女聲"


def test_extra_voice_in_a_score_is_passed_through(tmp_path):
    """Upstream ignores extra voices; the studio must not second-guess the score."""
    studio, wiring = build(tmp_path)
    score = "X:1\nK:C\nV:Vocal\nC D E F|\nV:Ins\nz4|\nV:Third\nG4|"
    last(studio.render_from_score(form(abc_text=score, abc_source="uploaded")))
    assert wiring.pipe.calls[-1][1]["abc"] == score
    assert studio.store.list_songs()[0].abc_source == "uploaded"


def test_rejected_score_keeps_the_user_on_the_score(tmp_path):
    studio, _ = build(tmp_path, StandInPipeline(fail_at="semantic", error=ValueError("ABC IDs")))
    final, _ = last(studio.render_from_score(form(abc_text="X:1\nK:C\nC", abc_source="edited")))
    assert "E_ABC_INVALID" in final["error_html"]["value"]
    assert "env_acc" not in final and "tabs" not in final


def test_two_workdirs_never_share_song_ids(tmp_path):
    first, _ = build(tmp_path / "a")
    second, _ = build(tmp_path / "b")
    last(first.submit(form()))
    last(second.submit(form()))
    assert first.store.list_songs()[0].song_id != second.store.list_songs()[0].song_id


def test_draft_write_failure_does_not_block_generation(tmp_path, monkeypatch):
    studio, _ = build(tmp_path)

    def refuse(draft):
        raise OSError("read-only")

    monkeypatch.setattr(studio.drafts, "save", refuse)
    final, _ = last(studio.submit(form()))
    assert final["tabs"] == {"selected": "result"}
