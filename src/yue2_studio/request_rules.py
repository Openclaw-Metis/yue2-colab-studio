"""Turn raw form values into a validated request, or say what is wrong.

The length limits are this studio's own guard rails, not YuE2 limits.
"""

from __future__ import annotations

import math
import secrets
from dataclasses import asdict, dataclass
from pathlib import Path

from . import ui_text

STYLE_LIMIT = 1000
LYRICS_LIMIT = 5000
ABC_BYTES_LIMIT = 200 * 1024
SEED_MAX = 2**31 - 1
CFG_MIN, CFG_MAX = 1.0, 2.0
COT_MODES = ("full", "melody", "off")
ABC_SUFFIXES = (".abc", ".txt")


@dataclass(frozen=True)
class StudioRequest:
    style: str
    lyrics: str
    cot: str = "full"
    seed: int = 0
    cfg_scale: float | None = None
    abc: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> StudioRequest:
        return cls(
            style=str(data.get("style", "")),
            lyrics=str(data.get("lyrics", "")),
            cot=data.get("cot", "full"),
            seed=int(data.get("seed", 0)),
            cfg_scale=data.get("cfg_scale"),
            abc=data.get("abc"),
        )


@dataclass(frozen=True)
class FieldError:
    field: str
    message: str


class ValidationFailed(Exception):
    def __init__(self, errors: list[FieldError]):
        self.errors = errors
        super().__init__("; ".join(f"{error.field}: {error.message}" for error in errors))

    @property
    def fields(self) -> list[str]:
        return [error.field for error in self.errors]


class AbcFileRejected(Exception):
    pass


def _parse_seed(value) -> int | None:
    """Return a seed, None for "pick one", or raise ValueError."""
    if value is None or (isinstance(value, str) and not value.strip()):
        return None
    if isinstance(value, bool):
        raise ValueError
    number = float(value)
    if not math.isfinite(number) or number != int(number):
        raise ValueError
    seed = int(number)
    if not 0 <= seed <= SEED_MAX:
        raise ValueError
    return seed


def _parse_cfg(value) -> float | None:
    if value is None or (isinstance(value, str) and not value.strip()):
        return None
    if isinstance(value, bool):
        raise ValueError
    number = float(value)
    if not math.isfinite(number) or not CFG_MIN <= number <= CFG_MAX:
        raise ValueError
    return number


def validate(raw: dict) -> StudioRequest:
    errors: list[FieldError] = []

    style = str(raw.get("style") or "").strip()
    if not style:
        errors.append(FieldError("style", ui_text.STYLE_EMPTY))
    elif len(style) > STYLE_LIMIT:
        errors.append(
            FieldError("style", ui_text.STYLE_TOO_LONG.format(limit=STYLE_LIMIT, count=len(style)))
        )

    lyrics = str(raw.get("lyrics") or "").strip()
    if len(lyrics) > LYRICS_LIMIT:
        errors.append(
            FieldError(
                "lyrics", ui_text.LYRICS_TOO_LONG.format(limit=LYRICS_LIMIT, count=len(lyrics))
            )
        )

    cot = raw.get("cot") or "full"
    if cot not in COT_MODES:
        errors.append(FieldError("cot", ui_text.COT_INVALID))

    seed = None
    try:
        seed = _parse_seed(raw.get("seed"))
    except (TypeError, ValueError):
        errors.append(FieldError("seed", ui_text.SEED_INVALID))

    cfg_scale = None
    try:
        cfg_scale = _parse_cfg(raw.get("cfg_scale"))
    except (TypeError, ValueError):
        errors.append(FieldError("cfg_scale", ui_text.CFG_INVALID))

    abc = raw.get("abc")
    abc = abc.strip() if isinstance(abc, str) else None
    abc = abc or None
    if abc is not None:
        if cot == "off":
            errors.append(FieldError("abc", ui_text.ABC_NEEDS_PLANNING))
        elif len(abc.encode("utf-8")) > ABC_BYTES_LIMIT:
            errors.append(FieldError("abc", ui_text.ABC_TOO_LARGE))

    if errors:
        raise ValidationFailed(errors)
    if seed is None:
        # Recorded with the song so a result can be traced back to its seed.
        seed = secrets.randbelow(SEED_MAX + 1)
    return StudioRequest(style, lyrics, cot, seed, cfg_scale, abc)


def read_abc_file(path: str | Path) -> str:
    """Read an uploaded score as text; uploads are never executed or parsed."""
    path = Path(path)
    if path.suffix.lower() not in ABC_SUFFIXES:
        raise AbcFileRejected(ui_text.ABC_WRONG_TYPE)
    if path.stat().st_size > ABC_BYTES_LIMIT:
        raise AbcFileRejected(ui_text.ABC_TOO_LARGE)
    data = path.read_bytes()
    if b"\x00" in data:
        raise AbcFileRejected(ui_text.ABC_NOT_TEXT)
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise AbcFileRejected(ui_text.ABC_NOT_TEXT) from error
    if not text.strip():
        raise AbcFileRejected(ui_text.ABC_EMPTY)
    return text.replace("\r\n", "\n")
