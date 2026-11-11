"""The unsent form, saved so a page reload or a new runtime can pick it up."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, fields
from datetime import datetime, timezone
from pathlib import Path

SCHEMA_VERSION = 1
ABC_SOURCES = ("none", "planned", "edited", "uploaded")


@dataclass
class Draft:
    style: str = ""
    lyrics: str = ""
    cot: str = "full"
    seed: int | None = None
    cfg_scale: float | None = None
    score_first: bool = False
    abc_text: str = ""
    abc_source: str = "none"
    parent_song_id: str | None = None
    updated_at: str = ""
    schema_version: int = SCHEMA_VERSION

    @property
    def is_empty(self) -> bool:
        return not (self.style.strip() or self.lyrics.strip() or self.abc_text.strip())


class DraftStore:
    def __init__(self, root: str | Path):
        self.path = Path(root) / "draft.json"

    def load(self) -> Draft:
        """Return the saved draft; a missing or damaged file is an empty one."""
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                return Draft()
            known = {item.name for item in fields(Draft)}
            draft = Draft(**{key: value for key, value in data.items() if key in known})
        except (OSError, ValueError, TypeError):
            return Draft()
        if draft.abc_source not in ABC_SOURCES:
            draft.abc_source = "none"
        draft.schema_version = SCHEMA_VERSION
        return draft

    def save(self, draft: Draft) -> None:
        draft.updated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(asdict(draft), ensure_ascii=False), encoding="utf-8")
        temporary.replace(self.path)

    def clear(self) -> None:
        self.path.unlink(missing_ok=True)
