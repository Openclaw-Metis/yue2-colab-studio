"""Runs one generation at a time and reports where it is.

The work happens on a worker thread that owns the busy lock, so a job keeps
going (and still gets saved) when the browser tab that started it goes away.
UI handlers only read snapshots.
"""

from __future__ import annotations

import secrets
import threading
import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field, replace

from . import ui_text
from .engine import Cancelled, Engine, EngineError, StageEvent
from .request_rules import FieldError, StudioRequest, ValidationFailed, validate
from .song_store import SongStore, StorageError

POLL_SECONDS = 0.5
# Placeholder until an L4 baseline exists; see docs/colab-baseline.md.
TIMEOUT_SECONDS = 45 * 60
_STAGE_ORDER = ("loading", "planning", "composing", "rendering", "decoding", "saving")
_UNCANCELLABLE = ("decoding", "saving")


@dataclass(frozen=True)
class JobUpdate:
    state: str = "idle"
    job_id: str | None = None
    kind: str | None = None
    completed: int | None = None
    total: int | None = None
    elapsed: float = 0.0
    error_code: str | None = None
    error_detail: str = ""
    field_errors: tuple[FieldError, ...] = ()
    song_id: str | None = None
    abc: str | None = None
    abc_truncated: bool = False
    notice: str | None = None
    rescue_path: str | None = None
    # True when this request was refused because another job is running.
    rejected: bool = False

    @property
    def running(self) -> bool:
        return self.state in ui_text.RUNNING_STATES


@dataclass
class _Job:
    job_id: str
    kind: str
    started: float
    deadline: float
    cancel: threading.Event = field(default_factory=threading.Event)
    timed_out: bool = False


class _NullLog:
    def write(self, event: str, **fields) -> None:
        pass


class JobRunner:
    def __init__(
        self,
        engine: Engine,
        store: SongStore,
        log=None,
        *,
        versions: dict | None = None,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
        poll_seconds: float = POLL_SECONDS,
        timeout_seconds: float = TIMEOUT_SECONDS,
    ):
        self.engine = engine
        self.store = store
        self.log = log or _NullLog()
        self.versions = versions or {}
        self._clock = clock
        self._sleep = sleep
        self._poll_seconds = poll_seconds
        self._timeout_seconds = timeout_seconds
        self._busy = threading.Lock()
        self._state_lock = threading.Lock()
        self._latest = JobUpdate()
        self._job: _Job | None = None
        self._thread: threading.Thread | None = None

    # --- reading ----------------------------------------------------------------

    def snapshot(self) -> JobUpdate:
        with self._state_lock:
            update, job = self._latest, self._job
            if update.running and job is not None:
                update = replace(update, elapsed=self._clock() - job.started)
            return update

    def _set(self, **changes) -> None:
        with self._state_lock:
            self._latest = replace(self._latest, **changes)

    def _advance(self, event: StageEvent) -> None:
        """Apply a stage event, ignoring any that would move backwards."""
        with self._state_lock:
            current = self._latest
            if event.stage not in _STAGE_ORDER or current.state not in _STAGE_ORDER:
                return
            before, after = _STAGE_ORDER.index(current.state), _STAGE_ORDER.index(event.stage)
            if after < before:
                return
            notice = current.notice if after == before else None
            if event.note and event.note.startswith("retry:"):
                notice = ui_text.DOWNLOAD_RETRY.format(attempt=event.note.split(":", 1)[1])
            self._latest = replace(
                current,
                state=event.stage,
                completed=event.completed,
                total=event.total,
                notice=notice,
            )
        if after > before:
            self.log.write("job_stage", job_id=current.job_id, stage=event.stage)

    # --- cancelling ---------------------------------------------------------------

    def cancel(self) -> str:
        """Ask the running job to stop. Returns "idle", "too_late" or "requested"."""
        with self._state_lock:
            job, state = self._job, self._latest.state
            if job is None or not self._latest.running:
                return "idle"
            if state in _UNCANCELLABLE:
                self._latest = replace(self._latest, notice=ui_text.CANCEL_TOO_LATE)
                return "too_late"
            job.cancel.set()
            self._latest = replace(self._latest, notice=ui_text.CANCEL_REQUESTED)
            return "requested"

    def _should_stop(self, job: _Job) -> bool:
        if job.cancel.is_set():
            return True
        if self._clock() > job.deadline:
            job.timed_out = True
            return True
        return False

    # --- running ------------------------------------------------------------------

    def run_plan(self, raw_form: dict) -> Iterator[JobUpdate]:
        raw = {**raw_form, "abc": None}
        yield from self._run("plan", raw, lambda job, request: self._plan(job, request))

    def run_render(
        self,
        raw_form: dict,
        *,
        abc: str | None = None,
        abc_source: str = "none",
        parent_song_id: str | None = None,
    ) -> Iterator[JobUpdate]:
        raw = {**raw_form, "abc": abc}
        yield from self._run(
            "render",
            raw,
            lambda job, request: self._render(job, request, abc_source, parent_song_id),
        )

    def _run(self, kind: str, raw: dict, work) -> Iterator[JobUpdate]:
        if not self._busy.acquire(blocking=False):
            yield replace(self.snapshot(), rejected=True)
            return
        try:
            request = validate(raw)
        except ValidationFailed as failure:
            self._busy.release()
            self.log.write("validation_failed", fields=failure.fields)
            with self._state_lock:
                self._job = None
                self._latest = JobUpdate(
                    state="failed",
                    kind=kind,
                    error_code="E_VALIDATION",
                    field_errors=tuple(failure.errors),
                )
                update = self._latest
            yield update
            return

        now = self._clock()
        job = _Job(secrets.token_hex(4), kind, now, now + self._timeout_seconds)
        has_score = request.abc is not None
        with self._state_lock:
            self._job = job
            self._latest = JobUpdate(
                state="planning" if self.engine.ready else "loading",
                job_id=job.job_id,
                kind=kind,
            )
        self.log.write(
            "job_submitted",
            job_id=job.job_id,
            kind=kind,
            cot=request.cot,
            style_chars=len(request.style),
            lyrics_chars=len(request.lyrics),
            has_abc=has_score,
        )
        self._thread = threading.Thread(
            target=self._guarded, args=(job, request, work), daemon=True
        )
        self._thread.start()
        thread = self._thread
        while thread.is_alive():
            yield self.snapshot()
            self._sleep(self._poll_seconds)
        yield self.snapshot()

    def _guarded(self, job: _Job, request: StudioRequest, work) -> None:
        try:
            if not self.engine.ready:
                self.engine.load(self._advance)
            if self._should_stop(job):
                raise Cancelled()
            work(job, request)
        except Cancelled:
            if job.timed_out:
                self._fail(job, "E_TIMEOUT", "")
            else:
                self._set(state="cancelled", completed=None, total=None, notice=None)
                self.log.write("job_cancelled", job_id=job.job_id)
        except EngineError as error:
            self._fail(job, error.code, error.detail)
        except StorageError as error:
            self._fail(job, "E_STORAGE", error.detail, rescue_path=error.rescue_path)
        except Exception as error:  # the UI must never be left stuck in a running state
            self._fail(job, "E_UNKNOWN", f"{type(error).__name__}: {error}")
        finally:
            with self._state_lock:
                elapsed = self._clock() - job.started
                self._latest = replace(self._latest, elapsed=elapsed)
            self._busy.release()

    def _fail(self, job: _Job, code: str, detail: str, **extra) -> None:
        stage = self.snapshot().state
        self._set(
            state="failed",
            error_code=code,
            error_detail=detail,
            completed=None,
            total=None,
            notice=None,
            **extra,
        )
        self.log.write(
            "job_failed", job_id=job.job_id, stage=stage, error_code=code, detail=detail[:300]
        )

    def _plan(self, job: _Job, request: StudioRequest) -> None:
        self._advance(StageEvent("planning"))
        draft = self.engine.plan(request, cancelled=lambda: self._should_stop(job))
        self._set(
            state="score_ready",
            abc=draft.abc,
            abc_truncated=draft.truncated,
            completed=None,
            total=None,
            notice=None,
        )
        self.log.write("plan_completed", job_id=job.job_id, seconds=round(draft.seconds, 2))

    def _render(
        self, job: _Job, request: StudioRequest, abc_source: str, parent_song_id: str | None
    ) -> None:
        if request.abc is None:
            abc_source = "none" if request.cot == "off" else "planned"
            first_stage = "composing" if request.cot == "off" else "planning"
        else:
            first_stage = "composing"
            if abc_source == "edited":
                self.log.write("score_edited", job_id=job.job_id, chars=len(request.abc))
        self._advance(StageEvent(first_stage))

        outcome = self.engine.render(
            request,
            abc=request.abc,
            cancelled=lambda: self._should_stop(job),
            on_stage=self._advance,
        )
        self._advance(StageEvent("saving"))
        record = self.store.create(
            outcome.result,
            request,
            abc_source=abc_source,
            parent_song_id=parent_song_id,
            peak_vram_gib=outcome.peak_vram_gib,
            versions=self.versions,
        )
        try:
            self.store.make_mp3(record.song_id)
        except Exception as error:
            # The song is already saved; the MP3 can be made again from the
            # result or library page, so a failed encode must not fail the job.
            self.log.write(
                "mp3_failed",
                job_id=job.job_id,
                song_id=record.song_id,
                detail=f"{type(error).__name__}: {error}"[:300],
            )
        self._set(state="done", song_id=record.song_id, completed=None, total=None, notice=None)
        self.log.write(
            "job_completed",
            job_id=job.job_id,
            song_id=record.song_id,
            total_seconds=round(outcome.seconds, 2),
            duration_sec=record.duration_sec,
            truncated=record.truncated,
            peak_vram_gib=record.peak_vram_gib,
        )

    def wait(self, timeout: float | None = None) -> None:
        """Block until the current worker finishes (used by tests and shutdown)."""
        thread = self._thread
        if thread is not None:
            thread.join(timeout)
