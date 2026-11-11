import shutil
import subprocess
import zipfile
from pathlib import Path

import pytest
from test_app_flows import build, form, last

from yue2_studio import audio_export, ui_text
from yue2_studio.audio_export import ConversionFailed
from yue2_studio.request_rules import StudioRequest
from yue2_studio.song_store import SongNotFound, SongStore, StorageError
from yue2_studio.stand_in_pipeline import STAND_IN_ABC, StandInResult

REQUEST = StudioRequest("piano pop", "[Verse]\nhello", "full", 7, None, None)


def completed(returncode=0, stderr=""):
    return subprocess.CompletedProcess([], returncode, "", stderr)


# --- command and error handling -------------------------------------------------


def test_command_encodes_a_320k_mp3_with_a_title_tag():
    command = audio_export.mp3_command("ffmpeg", Path("in.flac"), Path(".x.mp3.tmp"), "夜車")
    assert command[0] == "ffmpeg"
    assert command[command.index("-c:a") + 1] == "libmp3lame"
    assert command[command.index("-b:a") + 1] == "320k"
    assert command[command.index("-metadata") + 1] == "title=夜車"
    assert command[-3:] == ["-f", "mp3", ".x.mp3.tmp"]
    assert "-vn" in command


def test_title_is_optional():
    assert "-metadata" not in audio_export.mp3_command("ff", Path("a"), Path("b"), None)


def test_missing_ffmpeg_is_reported(tmp_path):
    with pytest.raises(ConversionFailed, match="ffmpeg not found"):
        audio_export.flac_to_mp3(tmp_path / "a.flac", tmp_path / "b", which=lambda name: None)


def test_ffmpeg_error_keeps_its_last_line(tmp_path):
    with pytest.raises(ConversionFailed, match="Unknown encoder"):
        audio_export.flac_to_mp3(
            tmp_path / "a.flac",
            tmp_path / "b",
            which=lambda name: "ffmpeg",
            run=lambda args: completed(1, "noise\nUnknown encoder 'libmp3lame'\n"),
        )


def test_empty_output_is_a_failure(tmp_path):
    with pytest.raises(ConversionFailed, match="no output"):
        audio_export.flac_to_mp3(
            tmp_path / "a.flac",
            tmp_path / "b",
            which=lambda name: "ffmpeg",
            run=lambda args: completed(0),
        )


def test_ffmpeg_that_cannot_start_is_a_failure(tmp_path):
    def broken(args):
        raise FileNotFoundError("ffmpeg")

    with pytest.raises(ConversionFailed, match="FileNotFoundError"):
        audio_export.flac_to_mp3(
            tmp_path / "a.flac", tmp_path / "b", which=lambda name: "ffmpeg", run=broken
        )


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg is not installed")
def test_real_ffmpeg_turns_a_song_into_an_mp3(tmp_path):
    result = StandInResult(REQUEST.to_dict(), STAND_IN_ABC, 1.5, {})
    flac = Path(result.save(tmp_path / "audio.flac"))
    target = tmp_path / ".song.mp3.tmp"
    audio_export.flac_to_mp3(flac, target, title="霓虹 test")
    assert target.read_bytes()[:3] == b"ID3"
    probe = shutil.which("ffprobe")
    if probe:
        found = subprocess.run(
            [
                probe, "-v", "error", "-select_streams", "a:0",
                "-show_entries", "stream=codec_name,sample_rate,channels:format_tags=title",
                "-of", "csv=p=0", str(target),
            ],
            capture_output=True, text=True, encoding="utf-8", check=True,
        ).stdout.split()
        assert found[0] == "mp3,48000,2"
        assert "霓虹" in " ".join(found[1:])


# --- song store -------------------------------------------------------------------


def store_with(tmp_path, converter):
    store = SongStore(tmp_path, mp3_converter=converter)
    record = store.create(StandInResult(REQUEST.to_dict(), STAND_IN_ABC, 1.5, {}), REQUEST)
    return store, record


def test_store_writes_the_mp3_once_beside_the_record(tmp_path):
    calls = []

    def fake(source, target, *, title=None):
        calls.append((Path(source).name, Path(target).name, title))
        Path(target).write_bytes(b"mp3")

    store, record = store_with(tmp_path, fake)
    path = store.make_mp3(record.song_id)
    assert path == tmp_path / "songs" / record.song_id / f"{record.song_id}.mp3"
    assert path.read_bytes() == b"mp3"
    assert calls == [("audio.flac", f".{record.song_id}.mp3.tmp", "piano pop")]
    assert store.make_mp3(record.song_id) == path
    assert len(calls) == 1
    assert store.has_mp3(record.song_id)


def test_failed_encode_leaves_no_partial_file(tmp_path):
    def fake(source, target, *, title=None):
        Path(target).write_bytes(b"half")
        raise ConversionFailed("boom")

    store, record = store_with(tmp_path, fake)
    with pytest.raises(ConversionFailed):
        store.make_mp3(record.song_id)
    assert list((tmp_path / "songs" / record.song_id).glob("*.mp3*")) == []


def test_disk_error_while_encoding_is_a_storage_error(tmp_path):
    def fake(source, target, *, title=None):
        raise OSError("disk full")

    store, record = store_with(tmp_path, fake)
    with pytest.raises(StorageError):
        store.make_mp3(record.song_id)


def test_song_without_audio_cannot_be_encoded(tmp_path):
    store, record = store_with(tmp_path, lambda *a, **k: None)
    store.audio_path(record.song_id).unlink()
    with pytest.raises(SongNotFound):
        store.make_mp3(record.song_id)


def test_mp3_is_included_in_the_zip_and_removed_with_the_song(tmp_path):
    store, record = store_with(tmp_path, lambda s, t, **k: Path(t).write_bytes(b"mp3"))
    store.make_mp3(record.song_id)
    with zipfile.ZipFile(store.export_zip(record.song_id)) as bundle:
        assert f"{record.song_id}/{record.song_id}.mp3" in bundle.namelist()
    store.delete(record.song_id)
    assert not store.mp3_path(record.song_id).exists()


# --- job and interface ---------------------------------------------------------------


def test_finished_song_offers_an_mp3_download(tmp_path):
    studio, wiring = build(tmp_path)
    final, _ = last(studio.submit(form()))
    song = studio.store.list_songs()[0]
    assert final["download_mp3_btn"] == {
        "value": str(studio.store.mp3_path(song.song_id)),
        "interactive": True,
        "label": ui_text.BTN_DOWNLOAD_MP3,
    }
    # Encoded once by the job; showing the song again reuses the file.
    assert len(wiring.mp3_calls) == 1 and wiring.mp3_calls[0][2] == "piano pop"
    detail = studio.select_song(song.song_id)
    assert detail["detail_mp3_btn"]["interactive"] is True
    assert detail["detail_audio_btn"]["value"].endswith("audio.flac")
    assert len(wiring.mp3_calls) == 1


def test_older_song_is_encoded_the_first_time_it_is_shown(tmp_path):
    studio, wiring = build(tmp_path)
    last(studio.submit(form()))
    song = studio.store.list_songs()[0]
    studio.store.mp3_path(song.song_id).unlink()

    detail = studio.select_song(song.song_id)
    assert detail["detail_mp3_btn"]["value"] == str(studio.store.mp3_path(song.song_id))
    assert studio.store.has_mp3(song.song_id)
    assert len(wiring.mp3_calls) == 2


def test_failed_encode_saves_the_song_and_disables_the_button(tmp_path):
    studio, wiring = build(tmp_path)
    wiring.mp3_error = ConversionFailed("ffmpeg not found")
    final, _ = last(studio.submit(form()))
    assert final["tabs"] == {"selected": "result"}
    assert final["download_mp3_btn"] == {
        "value": None,
        "interactive": False,
        "label": ui_text.MP3_UNAVAILABLE,
    }
    assert wiring.events("mp3_failed")[0]["detail"].startswith("ConversionFailed")

    # Once encoding works again, the next time the song is shown it gets an MP3.
    wiring.mp3_error = None
    song = studio.store.list_songs()[0]
    detail = studio.select_song(song.song_id)
    assert detail["detail_mp3_btn"]["interactive"] is True


def test_unplayable_song_has_no_mp3(tmp_path):
    studio, _ = build(tmp_path)
    last(studio.submit(form()))
    song = studio.store.list_songs()[0]
    studio.store.audio_path(song.song_id).unlink()
    studio.store.mp3_path(song.song_id).unlink()
    detail = studio.select_song(song.song_id)
    assert detail["detail_mp3_btn"]["interactive"] is False
    assert detail["detail_audio_btn"]["interactive"] is False
