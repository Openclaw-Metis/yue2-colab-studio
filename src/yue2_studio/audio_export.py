"""Convert a song's FLAC into an MP3 with ffmpeg.

The FLAC from YuE2 stays the master copy; the MP3 is a smaller file for
sharing and players that do not open FLAC. The caller (song_store) chooses the
target path; this module only encodes.
"""

from __future__ import annotations

import shutil
import subprocess
from collections.abc import Callable
from pathlib import Path

MP3_BITRATE = "320k"
SAMPLE_RATE = "48000"
TIMEOUT_SECONDS = 300


class ConversionFailed(Exception):
    pass


Run = Callable[[list[str]], subprocess.CompletedProcess]


def _run(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        args, capture_output=True, text=True, timeout=TIMEOUT_SECONDS, check=False
    )


def mp3_command(ffmpeg: str, source: Path, target: Path, title: str | None) -> list[str]:
    command = [
        ffmpeg,
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        str(source),
        "-vn",
        "-map_metadata",
        "-1",
        "-c:a",
        "libmp3lame",
        "-b:a",
        MP3_BITRATE,
        "-ar",
        SAMPLE_RATE,
        "-id3v2_version",
        "3",
    ]
    if title:
        command += ["-metadata", f"title={title}"]
    # The target may be a temporary name without the .mp3 suffix, so the
    # format is named explicitly instead of inferred from the extension.
    return [*command, "-f", "mp3", str(target)]


def flac_to_mp3(
    source: Path,
    target: Path,
    *,
    title: str | None = None,
    run: Run = _run,
    which: Callable[[str], str | None] = shutil.which,
) -> None:
    ffmpeg = which("ffmpeg")
    if ffmpeg is None:
        raise ConversionFailed("ffmpeg not found")
    try:
        completed = run(mp3_command(ffmpeg, Path(source), Path(target), title))
    except (OSError, subprocess.TimeoutExpired) as error:
        raise ConversionFailed(f"{type(error).__name__}: {error}") from error
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "").strip().splitlines()
        raise ConversionFailed(detail[-1] if detail else f"ffmpeg exit {completed.returncode}")
    if not Path(target).is_file() or Path(target).stat().st_size == 0:
        raise ConversionFailed("ffmpeg produced no output")
