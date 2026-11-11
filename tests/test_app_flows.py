"""Drive the UI logic end to end on the stand-in pipeline, without a browser."""

import pytest
from conftest import Studio as Wiring

from yue2_studio import ui_text
from yue2_studio.draft_store import DraftStore
from yue2_studio.stand_in_pipeline import STAND_IN_ABC, StandInPipeline
from yue2_studio.studio import Studio, as_form, render_error, render_status


def form(**overrides):
    values = {
        "style": "piano pop",
        "lyrics": "[Verse]\nhello",
        "cot": "full",
        "seed": 7,
        "cfg_auto": True,
        "cfg": 1.0,
        "score_first": False,
        "abc_text": "",
        "abc_source": "none",
    }
    values.update(overrides)
    return values


def build(tmp_path, pipe=None, persistent=False):
    wiring = Wiring(tmp_path, pipe)
    studio = Studio(
        wiring.engine,
        wiring.store,
        DraftStore(tmp_path),
        wiring.runner,
        wiring.log,
        environment_info={"report": {"gpu_name": "NVIDIA L4", "vram_total_gib": 22.5}},
        persistent=persistent,
    )
    return studio, wiring


@pytest.fixture
def studio(tmp_path):
    return build(tmp_path)[0]


def last(generator):
    patches = list(generator)
    assert patches, "handler produced no update"
    return patches[-1], patches


# --- flow A: straight to a song ---------------------------------------------------


def test_generate_ends_on_the_result_tab(studio):
    final, patches = last(studio.submit(form()))
    assert final["tabs"] == {"selected": "result"}
    assert final["_toast"] == ("info", ui_text.SONG_DONE_TOAST)
    assert final["result_group"] == {"visible": True}
    assert final["result_audio"]["value"].endswith("audio.flac")
    assert final["download_btn"]["value"] == final["result_audio"]["value"]
    assert final["result_score"]["value"] == STAND_IN_ABC
    assert final["truncated_md"] == {"visible": False}
    assert final["cancel_btn"] == {"visible": False}
    assert final["primary_btn"]["interactive"] is True
    assert len(final["library_radio"]["choices"]) == 1
    # While running, the primary button is locked and cancel is offered.
    assert patches[0]["primary_btn"] == {"interactive": False}
    assert patches[0]["cancel_btn"] == {"visible": True}


def test_status_bar_shows_each_stage(tmp_path):
    # Slow enough for the 5 ms poll to observe every stage.
    studio, _ = build(tmp_path, StandInPipeline(step_delay=0.03))
    _, patches = last(studio.submit(form()))
    text = " ".join(patch["status_html"]["value"] for patch in patches if "status_html" in patch)
    for stage in ("composing", "rendering", "decoding", "done"):
        assert ui_text.STAGE_LABELS[stage] in text


def test_truncated_song_shows_the_notice(tmp_path):
    pipe = StandInPipeline(truncated={"abc": False, "semantic": True})
    studio, _ = build(tmp_path, pipe)
    final, _ = last(studio.submit(form()))
    assert final["truncated_md"] == {"visible": True}


def test_validation_error_stays_on_the_form(studio):
    final, patches = last(studio.submit(form(style="  ")))
    assert len(patches) == 2
    assert final["error_html"]["visible"] is True
    assert ui_text.STYLE_EMPTY in final["error_html"]["value"]
    assert "E_VALIDATION" in final["error_html"]["value"]
    assert "tabs" not in final and "env_acc" not in final


def test_unexpected_failure_opens_environment_info(tmp_path):
    studio, _ = build(tmp_path, StandInPipeline(fail_at="semantic", error=KeyError("boom")))
    final, _ = last(studio.submit(form()))
    assert final["env_acc"] == {"open": True}
    assert "E_UNKNOWN" in final["error_html"]["value"]
    assert final["primary_btn"]["interactive"] is True


def test_cfg_is_only_sent_when_not_automatic(tmp_path):
    studio, wiring = build(tmp_path)
    last(studio.submit(form(cfg_auto=False, cfg=1.4)))
    assert wiring.pipe.calls[-1][1]["cfg_scale"] == 1.4
    last(studio.submit(form(cfg_auto=True, cfg=1.4)))
    assert wiring.pipe.calls[-1][1]["cfg_scale"] is None


# --- flow B: score first ----------------------------------------------------------


def test_score_first_ends_on_the_score_tab(studio):
    final, _ = last(studio.submit(form(score_first=True)))
    assert final["tabs"] == {"selected": "score"}
    assert final["abc_editor"] == {"value": STAND_IN_ABC}
    assert final["abc_source_state"] == {"value": "planned"}
    assert final["abc_source_md"]["value"] == ui_text.SCORE_SOURCE["planned"]
    assert final["render_btn"]["visible"] is True
    assert studio.store.list_songs() == []
    assert studio.drafts.load().abc_source == "planned"


def test_filling_the_editor_with_the_planned_score_is_not_an_edit(studio):
    last(studio.submit(form(score_first=True)))
    patch = studio.abc_edited(form(abc_text=STAND_IN_ABC, abc_source="planned"))
    assert patch["abc_source_state"] == {"value": "planned"}


def test_editing_a_planned_score_marks_it_edited(studio):
    last(studio.submit(form(score_first=True)))
    patch = studio.abc_edited(form(abc_text=STAND_IN_ABC + "% tweak", abc_source="planned"))
    assert patch["abc_source_state"] == {"value": "edited"}
    assert patch["abc_source_md"]["value"] == ui_text.SCORE_SOURCE["edited"]
    assert studio.drafts.load().abc_source == "edited"


def test_editing_an_uploaded_score_keeps_its_source(studio):
    patch = studio.abc_edited(form(abc_text="X:1\nK:C\nD", abc_source="uploaded"))
    assert patch["abc_source_state"] == {"value": "uploaded"}


def test_emptying_the_editor_clears_the_source(studio):
    patch = studio.abc_edited(form(abc_text="  ", abc_source="edited"))
    assert patch["abc_source_state"] == {"value": "none"}
    assert patch["render_btn"] == {"visible": False}
    assert patch["score_empty_md"] == {"visible": True}


def test_render_from_an_edited_score(tmp_path):
    studio, wiring = build(tmp_path)
    edited = STAND_IN_ABC.replace("C2 E2", "D2 F2")
    final, _ = last(studio.render_from_score(form(abc_text=edited, abc_source="edited")))
    assert final["tabs"] == {"selected": "result"}
    assert wiring.pipe.calls[-1][1]["abc"] == edited.strip()
    song = studio.store.list_songs()[0]
    assert song.abc_source == "edited"
    assert studio.store.score_text(song.song_id) == edited.strip()


def test_render_from_score_needs_a_score(studio):
    final, patches = last(studio.render_from_score(form()))
    assert len(patches) == 1 and final["_toast"][0] == "warning"


def test_score_with_cot_off_is_a_field_error(studio):
    final, _ = last(studio.render_from_score(form(cot="off", abc_text="X:1", abc_source="edited")))
    assert ui_text.ABC_NEEDS_PLANNING in final["error_html"]["value"]


def test_score_first_is_ignored_when_planning_is_off(studio):
    final, _ = last(studio.submit(form(score_first=True, cot="off")))
    assert final["tabs"] == {"selected": "result"}


def test_upload_shows_the_file_as_a_preview(studio, tmp_path):
    path = tmp_path / "tune.abc"
    path.write_text("X:1\nK:G\nG A B", encoding="utf-8")
    patch = studio.abc_uploaded(str(path), form())
    assert patch["abc_editor"] == {"value": "X:1\nK:G\nG A B"}
    assert patch["abc_source_state"] == {"value": "uploaded"}
    assert patch["_toast"] == ("info", ui_text.UPLOAD_LOADED)
    assert patch["abc_upload"] == {"value": None}


def test_rejected_upload_leaves_the_editor_alone(studio, tmp_path):
    path = tmp_path / "tune.mid"
    path.write_bytes(b"MThd")
    patch = studio.abc_uploaded(str(path), form(abc_text="keep"))
    assert patch["_toast"] == ("warning", ui_text.ABC_WRONG_TYPE)
    assert "abc_editor" not in patch
    assert studio.abc_uploaded(None, form()) == {}


def test_clear_score(studio):
    patch = studio.abc_cleared(form(abc_text="X:1", abc_source="edited"))
    assert patch["abc_editor"] == {"value": ""}
    assert patch["abc_source_state"] == {"value": "none"}
    assert studio.drafts.load().abc_text == ""


# --- form hints and drafts --------------------------------------------------------


def test_form_hints_follow_the_controls(studio):
    patch = studio.form_changed(form(score_first=True))
    assert patch["primary_btn"] == {"value": ui_text.BTN_PLAN}
    assert patch["counter_md"]["value"].startswith("曲風 9 / 1000")
    assert patch["fill_example_btn"] == {"visible": False}

    patch = studio.form_changed(form(score_first=True, cot="off"))
    assert patch["primary_btn"] == {"value": ui_text.BTN_GENERATE}
    assert patch["score_first_chk"] == {
        "interactive": False,
        "info": ui_text.SCORE_FIRST_DISABLED,
    }
    assert studio.form_changed(form(cfg_auto=False))["cfg_slider"] == {"interactive": True}
    assert studio.form_changed(form(style="", lyrics=""))["fill_example_btn"] == {"visible": True}


def test_draft_survives_a_reload(tmp_path):
    studio, _ = build(tmp_path)
    studio.form_changed(form(style="國語抒情", seed=12, cfg_auto=False, cfg=1.3))
    reloaded, _ = build(tmp_path)
    patch = reloaded.page_load()
    assert patch["style_box"] == {"value": "國語抒情"}
    assert patch["seed_box"] == {"value": 12}
    assert patch["cfg_auto_chk"] == {"value": False}
    assert patch["cfg_slider"]["value"] == 1.3
    assert patch["status_html"]["value"].count(ui_text.STAGE_LABELS["idle"]) == 1
    assert patch["footer_warning_md"] == {"visible": True}


def test_page_load_on_a_fresh_workdir(tmp_path):
    studio, _ = build(tmp_path, persistent=True)
    patch = studio.page_load()
    assert patch["result_group"] == {"visible": False}
    assert patch["library_empty_md"] == {"visible": True}
    assert patch["footer_warning_md"] == {"visible": False}
    assert "NVIDIA L4" in patch["env_md"]["value"]


def test_page_load_after_a_finished_job_shows_the_song(studio):
    last(studio.submit(form()))
    patch = studio.page_load()
    assert patch["result_group"] == {"visible": True}


def test_bad_seed_text_does_not_break_autosave(studio):
    studio.form_changed(form(seed="abc"))
    assert studio.drafts.load().seed is None


def test_fill_example(studio):
    patch = studio.fill_example(form(style="", lyrics=""))
    assert patch["style_box"] == {"value": ui_text.EXAMPLE_STYLE}
    assert studio.drafts.load().lyrics == ui_text.EXAMPLE_LYRICS


def test_restart_needs_confirmation_and_keeps_songs(studio):
    last(studio.submit(form()))
    assert studio.restart_ask() == {"restart_confirm_group": {"visible": True}}
    assert studio.restart_back() == {"restart_confirm_group": {"visible": False}}
    assert not studio.drafts.load().is_empty

    patch = studio.restart_confirm()
    assert patch["style_box"] == {"value": ""}
    assert patch["tabs"] == {"selected": "compose"}
    assert studio.drafts.load().is_empty
    assert len(studio.store.list_songs()) == 1


# --- library ----------------------------------------------------------------------


def make_song(studio, **overrides):
    last(studio.submit(form(**overrides)))
    return studio.store.list_songs()[0]


def test_select_and_rename(studio):
    song = make_song(studio)
    choices = studio.refresh_library()["library_radio"]["choices"]
    assert [song_id for _, song_id in choices] == [song.song_id]
    detail = studio.select_song(song.song_id)
    assert detail["selected_song_state"] == {"value": song.song_id}
    assert detail["title_box"] == {"value": "piano pop"}
    assert detail["delete_confirm_btn"] == {"visible": False}

    patch = studio.save_meta(song.song_id, "夜車", "第二版")
    assert patch["_toast"] == ("info", ui_text.SAVED_TOAST)
    assert patch["library_radio"]["choices"][0][0].startswith("夜車")
    assert patch["library_radio"]["value"] == song.song_id
    assert studio.store.get(song.song_id).note == "第二版"


def test_bad_title_is_a_warning(studio):
    song = make_song(studio)
    assert studio.save_meta(song.song_id, " ", "")["_toast"] == ("warning", ui_text.TITLE_INVALID)


def test_unknown_selection_hides_the_detail(studio):
    assert studio.select_song("20261111-000000-zzzz")["detail_group"] == {"visible": False}
    assert studio.select_song("../x")["detail_group"] == {"visible": False}


def test_a_late_reset_of_the_radio_does_not_close_the_open_song(studio):
    """Browser finding (2026-11-12): the reset's .change can arrive after the user's pick."""
    assert studio.select_song(None) == {}
    assert studio.select_song("") == {}


def test_refresh_keeps_the_open_song_open(studio):
    song = make_song(studio)
    patch = studio.refresh_library(song.song_id)
    assert patch["library_radio"]["value"] == song.song_id
    assert patch["detail_group"] == {"visible": True}
    studio.store.delete(song.song_id)
    patch = studio.refresh_library(song.song_id)
    assert patch["library_radio"]["value"] is None
    assert patch["detail_group"] == {"visible": False}


def test_delete_is_two_steps(studio):
    song = make_song(studio)
    assert studio.delete_ask(song.song_id) == {"delete_confirm_btn": {"visible": True}}
    assert len(studio.store.list_songs()) == 1

    patch = studio.delete_confirm(song.song_id, shown_song_id=song.song_id)
    assert patch["_toast"] == ("info", ui_text.DELETED_TOAST)
    assert patch["library_empty_md"] == {"visible": True}
    assert patch["detail_group"] == {"visible": False}
    assert patch["result_group"] == {"visible": False}
    assert studio.store.list_songs() == []


@pytest.mark.parametrize("song_id", [None, "", "../x", "20261111-000000-zzzz"])
def test_library_actions_ignore_unknown_songs(studio, song_id):
    for action in (studio.delete_ask, studio.delete_confirm, studio.pack, studio.load_to_form):
        assert action(song_id)["_toast"][0] == "warning"
    assert studio.save_meta(song_id, "t", "n")["_toast"][0] == "warning"


def test_pack_offers_a_zip(studio):
    song = make_song(studio)
    patch = studio.pack(song.song_id)
    assert patch["pack_file"]["value"].endswith(f"{song.song_id}.zip")
    assert studio.pack(song.song_id, "detail_pack_file")["detail_pack_file"]["visible"] is True


def test_remix_copies_the_request_and_links_the_parent(studio):
    song = make_song(studio, style="jazz trio", seed=99)
    patch = studio.load_to_form(song.song_id)
    assert patch["tabs"] == {"selected": "compose"}
    assert patch["style_box"] == {"value": "jazz trio"}
    # A new take should not silently reuse the old seed.
    assert patch["seed_box"] == {"value": None}
    assert patch["abc_editor"] == {"value": ""}

    last(studio.submit(form(style="jazz trio")))
    newest = studio.store.list_songs()[0]
    assert newest.parent_song_id == song.song_id
    detail = studio.select_song(newest.song_id)
    assert "jazz trio" in detail["detail_parent_md"]["value"]

    studio.store.delete(song.song_id)
    detail = studio.select_song(newest.song_id)
    assert ui_text.PARENT_DELETED in detail["detail_parent_md"]["value"]


def test_remix_of_an_edited_song_brings_its_score(studio):
    edited = STAND_IN_ABC.replace("C2 E2", "D2 F2")
    last(studio.render_from_score(form(abc_text=edited, abc_source="edited")))
    song = studio.store.list_songs()[0]
    patch = studio.load_to_form(song.song_id)
    assert patch["abc_editor"] == {"value": edited.strip()}
    assert patch["abc_source_state"] == {"value": "edited"}


def test_unreadable_song_is_listed_but_not_playable(studio, tmp_path):
    song = make_song(studio)
    (tmp_path / "songs" / song.song_id / "studio.json").write_text("{", encoding="utf-8")
    patch = studio.refresh_library()
    assert ui_text.SONG_UNREADABLE in patch["library_radio"]["choices"][0][0]
    detail = studio.select_song(song.song_id)
    assert detail["detail_audio"]["visible"] is False
    assert detail["load_btn"] == {"interactive": False}


# --- environment ------------------------------------------------------------------


def test_release_engine(tmp_path):
    studio, wiring = build(tmp_path)
    last(studio.submit(form()))
    patch = studio.release_engine()
    assert patch["_toast"] == ("info", ui_text.ENGINE_RELEASED_TOAST)
    assert wiring.pipe.closed
    assert ui_text.ENGINE_STATES["unloaded"] in patch["env_md"]["value"]


def test_diagnostics_never_include_lyrics(studio):
    last(studio.submit(form(lyrics="[Verse]\nprivate words")))
    text = studio.diagnostics()["diag_box"]["value"]
    assert "job_completed" in text and "NVIDIA L4" in text
    assert "private words" not in text and "piano pop" not in text


def test_environment_summary_mentions_the_latest_song(studio):
    last(studio.submit(form()))
    text = studio.environment_markdown()
    assert "峰值 VRAM 11.50 GiB" in text and "歌曲數：1" in text


def test_cancel_and_tick_when_idle(studio):
    assert studio.cancel()["cancel_btn"] == {"visible": False}
    assert ui_text.STAGE_LABELS["idle"] in studio.tick()["status_html"]["value"]


# --- rendering helpers ------------------------------------------------------------


def test_status_escapes_and_shows_progress():
    from yue2_studio.generation_job import JobUpdate

    running = JobUpdate(state="rendering", completed=8, total=32, elapsed=75, notice="<b>x</b>")
    text = render_status(running)
    assert "width:25%" in text and "01:15" in text and "&lt;b&gt;" in text
    assert "studio-bar-busy" in render_status(JobUpdate(state="composing", completed=40))


def test_error_panel_escapes_details():
    from yue2_studio.generation_job import JobUpdate

    failed = JobUpdate(state="failed", error_code="E_STORAGE", error_detail="<x>", rescue_path="/r")
    text = render_error(failed)
    assert "&lt;x&gt;" in text and "<code>/r</code>" in text and "E_STORAGE" in text
    assert render_error(JobUpdate(state="done")) == ""


def test_as_form_requires_every_field():
    with pytest.raises(ValueError):
        as_form("only", "two")
