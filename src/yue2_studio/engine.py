"""The only module that touches the yue2 package.

Checked against yue2-infer at commit 1116bea (src/yue2/pipeline.py and
protocol.py):

- ``YuE2Pipeline.from_pretrained(model, vae=, revision=, vae_revision=,
  cache_dir=, progress=, **kwargs)``; device and memory budget are
  constructor kwargs. The default 24 GiB budget is clamped to
  ``total - 2 GiB``, so an L4 needs no override.
- ``pipe(style, lyrics, cot=, seed=, abc=, cfg_scale=, cancelled=, on_token=,
  on_progress=)`` and ``pipe.plan(...)`` with the same request fields.
- ``on_token(phase, token)`` with phase ``"abc"`` or ``"semantic"``.
- ``on_progress(stage, completed, total)`` with stage ``"nar"`` or ``"vae"``.
- ``cancelled()`` is polled during token generation and flow matching and
  raises ``InterruptedError``. Nothing polls it once VAE decoding starts.
- ``SongResult.truncated`` is ``{"abc": bool, "semantic": bool}``.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from . import MODEL_ID, MODEL_REVISION, VAE_ID, VAE_REVISION
from .request_rules import StudioRequest

CACHE_DIR = "/content/hf_cache"
DOWNLOAD_RETRY_DELAYS = (5, 15, 45)
# on_token fires per token; forwarding every one would flood the UI queue.
TOKEN_REPORT_INTERVAL = 25

_TOKEN_PHASE_TO_STAGE = {"abc": "planning", "semantic": "composing"}
_PROGRESS_TO_STAGE = {"nar": "rendering", "vae": "decoding"}


@dataclass(frozen=True)
class StageEvent:
    stage: str
    completed: int | None = None
    total: int | None = None
    note: str | None = None


@dataclass(frozen=True)
class PlanDraft:
    abc: str
    truncated: bool
    seconds: float


@dataclass(frozen=True)
class RenderOutcome:
    result: Any
    peak_vram_gib: float
    seconds: float


class EngineError(Exception):
    def __init__(self, code: str, detail: str = ""):
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}" if detail else code)


class Cancelled(Exception):
    pass


def _default_factory(cache_dir: str):  # pragma: no cover - needs a GPU and the weights
    from yue2 import YuE2Pipeline

    return YuE2Pipeline.from_pretrained(
        MODEL_ID,
        vae=VAE_ID,
        revision=MODEL_REVISION,
        vae_revision=VAE_REVISION,
        cache_dir=cache_dir,
        progress=False,
        device="cuda",
    )


def _reset_peak_vram() -> None:  # pragma: no cover - needs torch with CUDA
    try:
        import torch

        if torch.cuda.is_available():
            torch.cuda.reset_peak_memory_stats()
    except ImportError:
        pass


def _read_peak_vram_gib() -> float:  # pragma: no cover - needs torch with CUDA
    try:
        import torch

        if torch.cuda.is_available():
            return torch.cuda.max_memory_allocated() / 2**30
    except ImportError:
        pass
    return 0.0


def _empty_cuda_cache() -> None:  # pragma: no cover - needs torch with CUDA
    try:
        import torch

        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except ImportError:
        pass


def is_out_of_memory(error: BaseException) -> bool:
    return type(error).__name__ == "OutOfMemoryError" or "out of memory" in str(error).lower()


def _is_network_error(error: BaseException) -> bool:
    # huggingface_hub and requests errors derive from OSError; so do plain
    # socket failures. A missing local file is not worth retrying.
    return isinstance(error, OSError) and not isinstance(error, FileNotFoundError)


class Engine:
    """Loads one pipeline, keeps it, and translates its callbacks and errors."""

    def __init__(
        self,
        pipeline_factory: Callable[[str], Any] | None = None,
        *,
        cache_dir: str = CACHE_DIR,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.perf_counter,
        reset_peak_vram: Callable[[], None] = _reset_peak_vram,
        read_peak_vram_gib: Callable[[], float] = _read_peak_vram_gib,
        empty_cache: Callable[[], None] = _empty_cuda_cache,
    ):
        self._factory = pipeline_factory or _default_factory
        self._cache_dir = cache_dir
        self._sleep = sleep
        self._clock = clock
        self._reset_peak_vram = reset_peak_vram
        self._read_peak_vram_gib = read_peak_vram_gib
        self._empty_cache = empty_cache
        self._pipe = None
        self._lock = threading.Lock()
        self.state = "unloaded"
        self.load_seconds: float | None = None

    @property
    def ready(self) -> bool:
        return self._pipe is not None and self.state == "ready"

    def load(self, on_status: Callable[[StageEvent], None] | None = None) -> None:
        with self._lock:
            if self.ready:
                return
            if self._pipe is not None:
                self._discard()
            self.state = "loading"
            start = self._clock()
            for attempt in range(len(DOWNLOAD_RETRY_DELAYS) + 1):
                try:
                    self._pipe = self._factory(self._cache_dir)
                    break
                except Exception as error:
                    if is_out_of_memory(error):
                        self.state = "error"
                        raise EngineError("E_OOM", str(error)) from error
                    if not _is_network_error(error):
                        self.state = "error"
                        code = "E_ENV_GPU" if "BF16" in str(error) else "E_UNKNOWN"
                        raise EngineError(code, f"{type(error).__name__}: {error}") from error
                    if attempt == len(DOWNLOAD_RETRY_DELAYS):
                        self.state = "error"
                        raise EngineError("E_MODEL_DOWNLOAD", str(error)) from error
                    if on_status is not None:
                        on_status(StageEvent("loading", note=f"retry:{attempt + 1}"))
                    self._sleep(DOWNLOAD_RETRY_DELAYS[attempt])
            self.load_seconds = self._clock() - start
            self.state = "ready"

    def plan(self, request: StudioRequest, *, cancelled: Callable[[], bool]) -> PlanDraft:
        self.load()
        start = self._clock()
        try:
            plan = self._pipe.plan(
                style=request.style,
                lyrics=request.lyrics,
                cot=request.cot,
                seed=request.seed,
                cfg_scale=request.cfg_scale,
                cancelled=cancelled,
            )
        except BaseException as error:
            raise self._translate(error, has_abc=False) from error
        return PlanDraft(plan.abc or "", bool(plan.truncated), self._clock() - start)

    def render(
        self,
        request: StudioRequest,
        *,
        abc: str | None,
        cancelled: Callable[[], bool],
        on_stage: Callable[[StageEvent], None],
    ) -> RenderOutcome:
        self.load()
        counts = {"abc": 0, "semantic": 0}

        def on_token(phase, token):
            if phase not in counts:
                return
            counts[phase] += 1
            if counts[phase] == 1 or counts[phase] % TOKEN_REPORT_INTERVAL == 0:
                on_stage(StageEvent(_TOKEN_PHASE_TO_STAGE[phase], counts[phase], None))

        def on_progress(stage, completed, total):
            if stage in _PROGRESS_TO_STAGE:
                on_stage(StageEvent(_PROGRESS_TO_STAGE[stage], int(completed), int(total)))

        self._reset_peak_vram()
        start = self._clock()
        try:
            result = self._pipe(
                style=request.style,
                lyrics=request.lyrics,
                cot=request.cot,
                seed=request.seed,
                abc=abc,
                cfg_scale=request.cfg_scale,
                cancelled=cancelled,
                on_token=on_token,
                on_progress=on_progress,
            )
        except BaseException as error:
            raise self._translate(error, has_abc=abc is not None) from error
        return RenderOutcome(result, self._read_peak_vram_gib(), self._clock() - start)

    def _translate(self, error: BaseException, *, has_abc: bool) -> Exception:
        if isinstance(error, InterruptedError):
            return Cancelled()
        if isinstance(error, (KeyboardInterrupt, SystemExit)):
            raise error
        if is_out_of_memory(error):
            # Allocations from the failed run can leave the pipeline unusable.
            self.state = "error"
            self._empty_cache()
            return EngineError("E_OOM", str(error))
        detail = f"{type(error).__name__}: {error}"
        if has_abc and isinstance(error, (ValueError, TypeError)):
            return EngineError("E_ABC_INVALID", detail)
        return EngineError("E_UNKNOWN", detail)

    def _discard(self) -> None:
        pipe, self._pipe = self._pipe, None
        try:
            if pipe is not None:
                pipe.close()
        finally:
            self._empty_cache()

    def close(self) -> None:
        with self._lock:
            self._discard()
            self.state = "unloaded"
