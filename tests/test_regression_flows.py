"""The three Gherkin scenarios from spec/01-technical-spec.md, as one test each."""

import threading

import pytest
from conftest import Gate
from test_app_flows import build, form, last

from yue2_studio import notebook_steps, ui_text
from yue2_studio.environment import EnvironmentReport
from yue2_studio.stand_in_pipeline import STAND_IN_ABC, StandInPipeline


def test_scenario_edit_the_score_then_generate(tmp_path):
    studio, _ = build(tmp_path, StandInPipeline(step_delay=0.02))

    # Given a filled form with "score first" ticked, when I ask for the score
    planned, patches = last(studio.submit(form(score_first=True)))
    assert any(
        ui_text.STAGE_LABELS["planning"] in patch.get("status_html", {}).get("value", "")
        for patch in patches
    )
    # Then I land on the score tab with the planner's score
    assert planned["tabs"] == {"selected": "score"}
    assert planned["abc_source_md"]["value"] == ui_text.SCORE_SOURCE["planned"]

    # When I change the score text
    edited_text = STAND_IN_ABC.replace("G2 E2", "A2 E2")
    edited = studio.abc_edited(form(abc_text=edited_text, abc_source="planned"))
    assert edited["abc_source_md"]["value"] == ui_text.SCORE_SOURCE["edited"]

    # And generate from it
    final, _ = last(
        studio.render_from_score(
            form(abc_text=edited_text, abc_source=edited["abc_source_state"]["value"])
        )
    )
    # Then I land on the result, and the song's score is exactly what I sent
    assert final["tabs"] == {"selected": "result"}
    assert final["result_score"]["value"] == edited_text.strip()


def test_scenario_cancel_while_composing(tmp_path):
    hold = Gate("nar")
    studio, _ = build(tmp_path, StandInPipeline(on_stage_entered=hold))
    studio.form_changed(form())
    patches = []
    thread = threading.Thread(target=lambda: patches.extend(studio.submit(form())), daemon=True)
    thread.start()
    assert hold.reached.wait(5)
    assert studio.runner.snapshot().state == "composing"

    studio.cancel()
    hold.release.set()
    thread.join(5)

    final = patches[-1]
    assert final["_toast"] == ("info", ui_text.ERRORS["E_CANCELLED"])
    assert final["primary_btn"]["interactive"] is True
    draft = studio.drafts.load()
    assert (draft.style, draft.lyrics) == ("piano pop", "[Verse]\nhello")
    assert studio.store.list_songs() == []


def test_scenario_unsupported_runtime(tmp_path):
    lines = []
    t4 = EnvironmentReport("Tesla T4", (7, 5), 15.0, 12.7, "3.12.0", False, ["too old"])
    with pytest.raises(SystemExit):
        notebook_steps.cell_one(
            str(tmp_path),
            probe=lambda: t4,
            install=lambda path: pytest.fail("must not install"),
            marker=tmp_path / "env.json",
            out=lines.append,
        )
    assert any("不是 L4" in line for line in lines)

    # Cell 2 refuses without cell 1's marker, so cell 3 never gets a session.
    with pytest.raises(SystemExit):
        notebook_steps.cell_two(
            False,
            marker=tmp_path / "env.json",
            session_file=tmp_path / "session.json",
            out=lines.append,
        )
    assert ui_text.CELL_ONE_FIRST in lines
    assert not (tmp_path / "session.json").exists()
