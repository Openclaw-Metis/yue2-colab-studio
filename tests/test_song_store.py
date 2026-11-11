import json
import zipfile
from datetime import datetime, timedelta, timezone

import pytest

from yue2_studio import ui_text
from yue2_studio.request_rules import StudioRequest
from yue2_studio.song_store import (
    InvalidMetadata,
    InvalidSongId,
    SongNotFound,
    SongRecord,
    SongStore,
    StorageError,
)
from yue2_studio.stand_in_pipeline import STAND_IN_ABC, StandInResult

STYLE = "國語、溫暖的鋼琴流行、女聲"
REQUEST = StudioRequest(STYLE, "[Verse]\n霓虹漸漸淡去", "full", 7, None, None)


def result(truncated=None, abc=STAND_IN_ABC):
    return StandInResult(
        REQUEST.to_dict(), abc, 1.5, truncated or {"abc": False, "semantic": False}
    )


class Clock:
    def __init__(self):
        self.now = datetime(2026, 11, 11, 14, 30, 5, tzinfo=timezone.utc)

    def __call__(self):
        self.now += timedelta(seconds=1)
        return self.now


@pytest.fixture
def store(tmp_path):
    return SongStore(tmp_path, now=Clock())


def test_create_writes_artifacts_and_a_record(store, tmp_path):
    record = store.create(result(), REQUEST, abc_source="planned", peak_vram_gib=11.234)
    folder = tmp_path / "songs" / record.song_id
    assert (folder / "artifacts" / "audio.flac").is_file()
    assert (folder / "artifacts" / "score.abc").is_file()
    saved = json.loads((folder / "studio.json").read_text(encoding="utf-8"))
    assert saved["schema_version"] == 1
    assert saved["request"]["lyrics"] == "[Verse]\n霓虹漸漸淡去"
    assert saved["duration_sec"] == 1.5
    assert saved["peak_vram_gib"] == 11.23
    assert saved["timing"]["nar_seconds"] == 0.3
    assert "problem" not in saved and "extra" not in saved
    assert record.title == "國語、溫暖的鋼琴流行、女聲"
    assert not any(path.name.startswith(".tmp-") for path in (tmp_path / "songs").iterdir())


def test_song_id_format(store):
    record = store.create(result(), REQUEST)
    stamp, clock, suffix = record.song_id.split("-")
    assert (stamp, clock) == ("20261111", "143006")
    assert len(suffix) == 4 and suffix.isalnum() and suffix.islower()


def test_non_ascii_survives_the_round_trip(store):
    record = store.create(result(), REQUEST)
    assert store.get(record.song_id).request["style"] == REQUEST.style


def test_truncated_dict_is_flattened(store):
    record = store.create(result({"abc": False, "semantic": True}), REQUEST)
    assert store.get(record.song_id).truncated is True


def test_failed_create_leaves_no_folder_and_rescues_audio(store, tmp_path):
    broken = result()

    def explode(directory):
        (directory / "partial.bin").parent.mkdir(parents=True, exist_ok=True)
        raise OSError("disk full")

    broken.save_artifacts = explode
    with pytest.raises(StorageError) as caught:
        store.create(broken, REQUEST)
    assert "disk full" in caught.value.detail
    assert list((tmp_path / "songs").iterdir()) == []
    assert caught.value.rescue_path.endswith(".flac")
    assert len(list((tmp_path / "_rescue").glob("*.flac"))) == 1
    assert store.list_songs() == []


def test_list_is_newest_first(store):
    first = store.create(result(), REQUEST)
    second = store.create(result(), REQUEST)
    assert [record.song_id for record in store.list_songs()] == [second.song_id, first.song_id]


def test_list_on_an_empty_library(store):
    assert store.list_songs() == []


@pytest.mark.parametrize(
    "bad", ["../x", "..", "a/b", "a\\b", "ABC", "", "song id", ".tmp-1", "a--b", "-a", None, 5]
)
def test_unsafe_ids_are_refused_before_touching_disk(store, bad):
    for action in (store.get, store.delete, store.export_zip, store.audio_path):
        with pytest.raises(InvalidSongId):
            action(bad)


def test_delete_outside_the_library_is_impossible(store, tmp_path):
    victim = tmp_path / "keep.txt"
    victim.write_text("keep", encoding="utf-8")
    with pytest.raises(InvalidSongId):
        store.delete("../keep.txt")
    assert victim.exists()


def test_corrupt_record_does_not_hide_the_others(store, tmp_path):
    good = store.create(result(), REQUEST)
    bad = store.create(result(), REQUEST)
    (tmp_path / "songs" / bad.song_id / "studio.json").write_text("{not json", encoding="utf-8")
    records = {record.song_id: record for record in store.list_songs()}
    assert records[good.song_id].playable
    assert records[bad.song_id].problem == ui_text.SONG_UNREADABLE
    store.delete(bad.song_id)
    assert [record.song_id for record in store.list_songs()] == [good.song_id]


def test_missing_audio_is_flagged(store):
    record = store.create(result(), REQUEST)
    store.audio_path(record.song_id).unlink()
    assert store.get(record.song_id).problem == ui_text.SONG_INCOMPLETE


def test_stray_folders_are_ignored(store, tmp_path):
    store.create(result(), REQUEST)
    (tmp_path / "songs" / ".tmp-leftover").mkdir()
    (tmp_path / "songs" / "Not A Song").mkdir()
    assert len(store.list_songs()) == 1


def test_update_title_and_note(store):
    record = store.create(result(), REQUEST)
    updated = store.update(record.song_id, title="  夜車  ", note="第二版")
    assert (updated.title, updated.note) == ("夜車", "第二版")
    assert updated.updated_at > record.updated_at
    assert store.get(record.song_id).title == "夜車"


@pytest.mark.parametrize("title", ["", "   ", "x" * 81])
def test_bad_titles_are_refused(store, title):
    record = store.create(result(), REQUEST)
    with pytest.raises(InvalidMetadata):
        store.update(record.song_id, title=title)
    assert store.get(record.song_id).title == record.title


def test_long_note_is_refused(store):
    record = store.create(result(), REQUEST)
    with pytest.raises(InvalidMetadata):
        store.update(record.song_id, note="n" * 501)


def test_delete_removes_the_folder(store, tmp_path):
    record = store.create(result(), REQUEST)
    store.delete(record.song_id)
    assert not (tmp_path / "songs" / record.song_id).exists()
    with pytest.raises(SongNotFound):
        store.get(record.song_id)
    with pytest.raises(SongNotFound):
        store.delete(record.song_id)


def test_export_zip_contains_record_and_artifacts(store):
    record = store.create(result(), REQUEST)
    archive = store.export_zip(record.song_id)
    with zipfile.ZipFile(archive) as bundle:
        names = set(bundle.namelist())
    assert f"{record.song_id}/studio.json" in names
    assert f"{record.song_id}/artifacts/audio.flac" in names
    assert f"{record.song_id}/artifacts/score.abc" in names


def test_older_record_gets_defaults_and_keeps_unknown_fields(store, tmp_path):
    record = store.create(result(), REQUEST)
    path = tmp_path / "songs" / record.song_id / "studio.json"
    path.write_text(
        json.dumps({"title": "old", "request": {"style": "x"}, "from_the_future": 42}),
        encoding="utf-8",
    )
    loaded = store.get(record.song_id)
    assert loaded.title == "old" and loaded.note == "" and loaded.abc_source == "none"
    store.update(record.song_id, note="kept")
    assert json.loads(path.read_text(encoding="utf-8"))["from_the_future"] == 42


def test_score_text_is_none_without_a_score(store):
    record = store.create(result(abc=None), REQUEST)
    assert store.score_text(record.song_id) is None


def test_total_bytes_counts_the_library(store):
    assert store.total_bytes() == 0 or store.total_bytes() >= 0
    store.create(result(), REQUEST)
    assert store.total_bytes() > 1000


def test_record_from_dict_tolerates_minimal_data():
    record = SongRecord.from_dict({"song_id": "20261111-000000-abcd"})
    assert record.title == "20261111-000000-abcd" and record.request == {}
