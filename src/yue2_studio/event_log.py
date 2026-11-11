"""Append-only JSON Lines event log with size-based rotation.

Callers pass counts and identifiers only. Lyrics and style text never reach
this module, so a diagnostics dump is safe to paste into a bug report.
"""

from __future__ import annotations

import json
import threading
import time
from collections.abc import Callable
from pathlib import Path

MAX_BYTES = 5 * 2**20
BACKUPS = 3
DIAGNOSTIC_EVENTS = 20


class EventLog:
    def __init__(
        self,
        path: str | Path,
        *,
        max_bytes: int = MAX_BYTES,
        backups: int = BACKUPS,
        clock: Callable[[], float] = time.time,
    ):
        self.path = Path(path)
        self.max_bytes = max_bytes
        self.backups = backups
        self._clock = clock
        self._lock = threading.Lock()

    def write(self, event: str, **fields) -> None:
        record = {"ts": round(self._clock(), 3), "event": event, **fields}
        line = json.dumps(record, ensure_ascii=False, default=str) + "\n"
        with self._lock:
            try:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                self._rotate_if_needed(len(line.encode("utf-8")))
                with self.path.open("a", encoding="utf-8") as handle:
                    handle.write(line)
            except OSError:
                # Logging must never take a generation down with it.
                pass

    def _rotate_if_needed(self, incoming: int) -> None:
        if not self.path.exists() or self.path.stat().st_size + incoming <= self.max_bytes:
            return
        oldest = self.path.with_name(f"{self.path.name}.{self.backups}")
        oldest.unlink(missing_ok=True)
        for index in range(self.backups - 1, 0, -1):
            source = self.path.with_name(f"{self.path.name}.{index}")
            if source.exists():
                source.replace(self.path.with_name(f"{self.path.name}.{index + 1}"))
        self.path.replace(self.path.with_name(f"{self.path.name}.1"))

    def recent(self, count: int = DIAGNOSTIC_EVENTS) -> list[dict]:
        with self._lock:
            try:
                lines = self.path.read_text(encoding="utf-8").splitlines()
            except OSError:
                return []
        records = []
        for line in lines[-count:]:
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return records

    def diagnostics(self, header: dict | None = None) -> str:
        parts = []
        if header:
            parts.append(json.dumps(header, ensure_ascii=False, indent=2, default=str))
        parts.extend(json.dumps(record, ensure_ascii=False) for record in self.recent())
        return "\n".join(parts)
