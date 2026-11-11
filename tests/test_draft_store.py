import json

from yue2_studio.draft_store import Draft, DraftStore


def test_missing_draft_is_empty(tmp_path):
    draft = DraftStore(tmp_path).load()
    assert draft == Draft() and draft.is_empty


def test_save_and_load(tmp_path):
    store = DraftStore(tmp_path)
    store.save(
        Draft(
            style="國語抒情",
            lyrics="[Verse]\n霓虹",
            cot="melody",
            seed=5,
            cfg_scale=1.2,
            score_first=True,
            abc_text="X:1\nK:C\nC",
            abc_source="edited",
        )
    )
    loaded = store.load()
    assert loaded.style == "國語抒情" and loaded.abc_source == "edited"
    assert loaded.seed == 5 and loaded.score_first is True
    assert loaded.updated_at
    assert not loaded.is_empty
    assert not (tmp_path / "draft.json.tmp").exists()


def test_older_draft_gets_defaults_for_new_fields(tmp_path):
    (tmp_path / "draft.json").write_text(
        json.dumps({"schema_version": 0, "style": "old", "retired_field": 1}), encoding="utf-8"
    )
    loaded = DraftStore(tmp_path).load()
    assert loaded.style == "old" and loaded.cot == "full" and loaded.schema_version == 1


def test_corrupt_draft_is_treated_as_empty(tmp_path):
    (tmp_path / "draft.json").write_text("{oops", encoding="utf-8")
    assert DraftStore(tmp_path).load().is_empty
    (tmp_path / "draft.json").write_text("[1, 2]", encoding="utf-8")
    assert DraftStore(tmp_path).load().is_empty


def test_unknown_score_source_is_reset(tmp_path):
    (tmp_path / "draft.json").write_text(json.dumps({"abc_source": "stolen"}), encoding="utf-8")
    assert DraftStore(tmp_path).load().abc_source == "none"


def test_clear_removes_the_file_and_is_repeatable(tmp_path):
    store = DraftStore(tmp_path)
    store.save(Draft(style="x"))
    store.clear()
    store.clear()
    assert store.load().is_empty
