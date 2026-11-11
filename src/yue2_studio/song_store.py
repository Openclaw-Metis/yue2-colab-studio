"""The song library: one folder per song, no database.

    songs/<song_id>/studio.json      this studio's record
    songs/<song_id>/artifacts/       everything YuE2's save_artifacts() writes
    songs/<song_id>/<song_id>.mp3    MP3 copy of the audio for easy sharing

A song is written to a hidden temporary folder and renamed into place, so a
failed save never leaves a half-written song in the library.
"""

from __future__ import annotations

import json
import re
import secrets
import shutil
import string
import zipfile
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import audio_export, ui_text
from .request_rules import StudioRequest

SCHEMA_VERSION = 1
TITLE_LIMIT = 80
NOTE_LIMIT = 500
DEFAULT_TITLE_CHARS = 30
_SONG_ID = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
_ID_ALPHABET = string.ascii_lowercase + string.digits


class StorageError(Exception):
    def __init__(self, detail: str, rescue_path: str | None = None):
        self.detail = detail
        self.rescue_path = rescue_path
        super().__init__(detail)


class SongNotFound(KeyError):
    pass


class InvalidSongId(ValueError):
    pass


class InvalidMetadata(ValueError):
    pass


@dataclass
class SongRecord:
    song_id: str
    title: str
    created_at: str
    updated_at: str
    request: dict
    note: str = ""
    abc_source: str = "none"
    parent_song_id: str | None = None
    duration_sec: float = 0.0
    truncated: bool = False
    timing: dict = field(default_factory=dict)
    peak_vram_gib: float = 0.0
    versions: dict = field(default_factory=dict)
    schema_version: int = SCHEMA_VERSION
    # Fields written by a newer version are carried through untouched.
    extra: dict = field(default_factory=dict)
    # Not persisted: set while listing.
    problem: str | None = None

    def to_dict(self) -> dict:
        data = asdict(self)
        data.pop("problem")
        data.update(data.pop("extra"))
        return data

    @classmethod
    def from_dict(cls, data: dict) -> SongRecord:
        known = {name for name in cls.__dataclass_fields__ if name not in ("extra", "problem")}
        values = {key: value for key, value in data.items() if key in known}
        extra = {key: value for key, value in data.items() if key not in known}
        now = _utc_now()
        values.setdefault("title", values.get("song_id", ""))
        values.setdefault("created_at", now)
        values.setdefault("updated_at", values["created_at"])
        values.setdefault("request", {})
        return cls(**values, extra=extra)

    @property
    def playable(self) -> bool:
        return self.problem is None


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def _is_truncated(value: Any) -> bool:
    if isinstance(value, dict):
        return any(bool(flag) for flag in value.values())
    return bool(value)


def _json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, default=str))


class SongStore:
    def __init__(
        self,
        root: str | Path,
        *,
        now: Callable[[], datetime] | None = None,
        mp3_converter: Callable[..., None] = audio_export.flac_to_mp3,
    ):
        self.root = Path(root)
        self.songs_dir = self.root / "songs"
        self.exports_dir = self.root / "exports"
        self.rescue_dir = self.root / "_rescue"
        self._now = now or (lambda: datetime.now(timezone.utc))
        self._mp3_converter = mp3_converter

    # --- identifiers and paths ------------------------------------------------

    def new_song_id(self) -> str:
        stamp = self._now().strftime("%Y%m%d-%H%M%S")
        suffix = "".join(secrets.choice(_ID_ALPHABET) for _ in range(4))
        return f"{stamp}-{suffix}"

    def _song_dir(self, song_id: str) -> Path:
        """Resolve a song folder, refusing anything that could leave songs/."""
        if not isinstance(song_id, str) or not _SONG_ID.fullmatch(song_id):
            raise InvalidSongId(str(song_id))
        path = (self.songs_dir / song_id).resolve()
        if path.parent != self.songs_dir.resolve():
            raise InvalidSongId(song_id)
        return path

    def audio_path(self, song_id: str) -> Path:
        return self._song_dir(song_id) / "artifacts" / "audio.flac"

    def mp3_path(self, song_id: str) -> Path:
        """Kept beside studio.json, not in artifacts/: YuE2's receipt hashes cover that folder."""
        return self._song_dir(song_id) / f"{song_id}.mp3"

    def has_mp3(self, song_id: str) -> bool:
        return self.mp3_path(song_id).is_file()

    def make_mp3(self, song_id: str) -> Path:
        """Encode the song's FLAC as MP3 once; later calls reuse the file."""
        record = self.get(song_id)
        if not record.playable:
            raise SongNotFound(song_id)
        target = self.mp3_path(song_id)
        if target.is_file():
            return target
        temporary = target.with_name(f".{target.name}.tmp")
        try:
            self._mp3_converter(self.audio_path(song_id), temporary, title=record.title)
            temporary.replace(target)
        except OSError as error:
            temporary.unlink(missing_ok=True)
            raise StorageError(f"{type(error).__name__}: {error}") from error
        except Exception:
            temporary.unlink(missing_ok=True)
            raise
        return target

    def score_text(self, song_id: str) -> str | None:
        path = self._song_dir(song_id) / "artifacts" / "score.abc"
        try:
            return path.read_text(encoding="utf-8")
        except OSError:
            return None

    # --- create ---------------------------------------------------------------

    def create(
        self,
        result: Any,
        request: StudioRequest,
        *,
        abc_source: str = "none",
        parent_song_id: str | None = None,
        peak_vram_gib: float = 0.0,
        versions: dict | None = None,
    ) -> SongRecord:
        song_id = self.new_song_id()
        temporary = self.songs_dir / f".tmp-{song_id}"
        try:
            temporary.mkdir(parents=True)
            result.save_artifacts(temporary / "artifacts")
            stamp = self._now().isoformat(timespec="milliseconds")
            record = SongRecord(
                song_id=song_id,
                title=request.style[:DEFAULT_TITLE_CHARS].strip() or song_id,
                created_at=stamp,
                updated_at=stamp,
                request=request.to_dict(),
                abc_source=abc_source,
                parent_song_id=parent_song_id,
                duration_sec=round(len(result.audio) / result.sample_rate, 2),
                truncated=_is_truncated(result.truncated),
                timing=_json_safe(result.timing),
                peak_vram_gib=round(peak_vram_gib, 2),
                versions=versions or {},
            )
            self._write_record(temporary, record)
            temporary.replace(self.songs_dir / song_id)
            return record
        except Exception as error:
            shutil.rmtree(temporary, ignore_errors=True)
            raise StorageError(
                f"{type(error).__name__}: {error}", self._rescue(result, song_id)
            ) from error

    def _rescue(self, result: Any, song_id: str) -> str | None:
        """Keep at least the audio when the library itself cannot be written."""
        for directory in (self.rescue_dir, Path.cwd() / "_rescue"):
            try:
                directory.mkdir(parents=True, exist_ok=True)
                return str(result.save(directory / f"{song_id}.flac"))
            except Exception:
                continue
        return None

    @staticmethod
    def _write_record(directory: Path, record: SongRecord) -> None:
        temporary = directory / "studio.json.tmp"
        temporary.write_text(
            json.dumps(record.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8"
        )
        temporary.replace(directory / "studio.json")

    # --- read -----------------------------------------------------------------

    def get(self, song_id: str) -> SongRecord:
        directory = self._song_dir(song_id)
        if not directory.is_dir():
            raise SongNotFound(song_id)
        return self._read(directory)

    def _read(self, directory: Path) -> SongRecord:
        song_id = directory.name
        try:
            data = json.loads((directory / "studio.json").read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                raise ValueError("studio.json is not an object")
            data["song_id"] = song_id
            record = SongRecord.from_dict(data)
        except (OSError, ValueError, TypeError):
            stamp = _utc_now()
            return SongRecord(
                song_id, song_id, stamp, stamp, {}, problem=ui_text.SONG_UNREADABLE
            )
        if not (directory / "artifacts" / "audio.flac").is_file():
            record.problem = ui_text.SONG_INCOMPLETE
        return record

    def list_songs(self) -> list[SongRecord]:
        if not self.songs_dir.is_dir():
            return []
        records = [
            self._read(path)
            for path in self.songs_dir.iterdir()
            if path.is_dir() and _SONG_ID.fullmatch(path.name)
        ]
        # Song ids start with a UTC timestamp to the second, which also places
        # unreadable records sensibly; created_at breaks ties within a second.
        return sorted(
            records,
            key=lambda record: (record.song_id[:15], record.created_at, record.song_id),
            reverse=True,
        )

    # --- update, delete, export -------------------------------------------------

    def update(
        self, song_id: str, *, title: str | None = None, note: str | None = None
    ) -> SongRecord:
        record = self.get(song_id)
        if record.problem == ui_text.SONG_UNREADABLE:
            raise SongNotFound(song_id)
        if title is not None:
            title = title.strip()
            if not 1 <= len(title) <= TITLE_LIMIT:
                raise InvalidMetadata(ui_text.TITLE_INVALID)
            record.title = title
        if note is not None:
            note = note.strip()
            if len(note) > NOTE_LIMIT:
                raise InvalidMetadata(ui_text.NOTE_INVALID)
            record.note = note
        record.updated_at = self._now().isoformat(timespec="milliseconds")
        try:
            self._write_record(self._song_dir(song_id), record)
        except OSError as error:
            raise StorageError(f"{type(error).__name__}: {error}") from error
        return record

    def delete(self, song_id: str) -> None:
        directory = self._song_dir(song_id)
        if not directory.is_dir():
            raise SongNotFound(song_id)
        shutil.rmtree(directory)

    def export_zip(self, song_id: str) -> Path:
        directory = self._song_dir(song_id)
        if not directory.is_dir():
            raise SongNotFound(song_id)
        try:
            self.exports_dir.mkdir(parents=True, exist_ok=True)
            target = self.exports_dir / f"{song_id}.zip"
            temporary = target.with_suffix(".zip.tmp")
            with zipfile.ZipFile(temporary, "w", zipfile.ZIP_DEFLATED) as archive:
                for path in sorted(directory.rglob("*")):
                    if path.is_file():
                        archive.write(path, Path(song_id) / path.relative_to(directory))
            temporary.replace(target)
            return target
        except OSError as error:
            raise StorageError(f"{type(error).__name__}: {error}") from error

    def total_bytes(self) -> int:
        if not self.root.is_dir():
            return 0
        return sum(path.stat().st_size for path in self.root.rglob("*") if path.is_file())
