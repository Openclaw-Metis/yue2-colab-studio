"""A GPU-free stand-in for YuE2Pipeline.

It mirrors the calls engine.py makes, so tests and a local UI preview can run
the whole studio without torch, weights or a GPU. The audio it writes is a
quiet tone, not music.
"""

from __future__ import annotations

import json
import math
import time
from pathlib import Path

SAMPLE_RATE = 48000

STAND_IN_ABC = (
    "X:1\n"
    "T:Stand-in score\n"
    "M:4/4\n"
    "L:1/8\n"
    "Q:1/4=88\n"
    "K:C\n"
    'V:Vocal\n"C" C2 E2 G2 E2 | "F" F2 A2 c2 A2 | "G" G2 B2 d2 B2 | "C" c4 z4 |\n'
    "V:Ins\nz8 | z8 | z8 | z8 |\n"
)


class StandInPlan:
    def __init__(self, abc, truncated=False):
        self.abc = abc
        self.truncated = truncated
        self.timing = {}


class StandInResult:
    def __init__(self, request, abc, seconds, truncated):
        self.request = request
        self.abc = abc
        self.sample_rate = SAMPLE_RATE
        self.audio_seconds = seconds
        self.truncated = truncated
        self.timing = {
            "abc": {"seconds": 0.1},
            "semantic": {"seconds": 0.2},
            "nar_seconds": 0.3,
            "vae_seconds": 0.1,
            "e2e_seconds": 0.7,
        }
        self.weights = {"mot": "stand-in", "vae": "stand-in"}

    @property
    def audio(self):
        import numpy as np

        samples = int(self.audio_seconds * SAMPLE_RATE)
        t = np.arange(samples, dtype=np.float32) / SAMPLE_RATE
        tone = 0.1 * np.sin(2 * math.pi * 440.0 * t)
        return np.stack([tone, tone], axis=1)

    def save(self, path):
        import soundfile as sf

        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        sf.write(path, self.audio, SAMPLE_RATE, subtype="PCM_24")
        return str(path)

    def save_artifacts(self, directory):
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)
        self.save(directory / "audio.flac")
        if self.abc is not None:
            (directory / "score.abc").write_bytes(self.abc.encode("utf-8"))
        result = {
            "status": "complete",
            "truncated": self.truncated,
            "sample_rate": SAMPLE_RATE,
            "audio_seconds": self.audio_seconds,
            "timing": self.timing,
        }
        for name, payload in (("request.json", self.request), ("result.json", result)):
            (directory / name).write_text(
                json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        return result


class StandInPipeline:
    """Configurable double: step delay, failure injection, call recording."""

    def __init__(
        self,
        *,
        step_delay=0.0,
        abc_tokens=60,
        semantic_tokens=120,
        nar_steps=4,
        vae_tiles=2,
        audio_seconds=2.0,
        fail_at=None,
        error=None,
        truncated=None,
        save_error=None,
        on_stage_entered=None,
    ):
        self.step_delay = step_delay
        self.abc_tokens = abc_tokens
        self.semantic_tokens = semantic_tokens
        self.nar_steps = nar_steps
        self.vae_tiles = vae_tiles
        self.audio_seconds = audio_seconds
        self.fail_at = fail_at
        self.error = error
        self.truncated = truncated or {"abc": False, "semantic": False}
        self.save_error = save_error
        self.on_stage_entered = on_stage_entered
        self.calls = []
        self.closed = False

    def _enter(self, stage):
        if self.on_stage_entered is not None:
            self.on_stage_entered(stage)
        if self.fail_at == stage:
            raise self.error or RuntimeError(f"stand-in failure at {stage}")

    def _pause(self):
        if self.step_delay:
            time.sleep(self.step_delay)

    def _tokens(self, phase, count, cancelled, on_token):
        self._enter(phase)
        for index in range(count):
            if cancelled is not None and cancelled():
                raise InterruptedError(f"Cancelled during {phase}")
            if on_token is not None:
                on_token(phase, index)
            if index % 20 == 0:
                self._pause()

    def plan(self, style=None, lyrics=None, *, cancelled=None, on_token=None, **kwargs):
        self.calls.append(("plan", {"style": style, "lyrics": lyrics, **kwargs}))
        if kwargs.get("cot") == "off":
            return StandInPlan(None)
        if kwargs.get("abc") is not None:
            return StandInPlan(kwargs["abc"])
        self._tokens("abc", self.abc_tokens, cancelled, on_token)
        return StandInPlan(STAND_IN_ABC, self.truncated["abc"])

    def __call__(
        self,
        style=None,
        lyrics=None,
        *,
        cancelled=None,
        on_token=None,
        on_progress=None,
        **kwargs,
    ):
        self.calls.append(("call", {"style": style, "lyrics": lyrics, **kwargs}))
        cot = kwargs.get("cot", "full")
        abc = kwargs.get("abc")
        if abc is not None and cot == "off":
            raise ValueError("External ABC requires nonempty text and cot=melody/full")
        if cot == "off":
            abc = None
        elif abc is None:
            self._tokens("abc", self.abc_tokens, cancelled, on_token)
            abc = STAND_IN_ABC
        self._tokens("semantic", self.semantic_tokens, cancelled, on_token)

        self._enter("nar")
        for step in range(1, self.nar_steps + 1):
            if cancelled is not None and cancelled():
                raise InterruptedError("Cancelled during acoustic flow matching")
            self._pause()
            if on_progress is not None:
                on_progress("nar", step, self.nar_steps)
        if cancelled is not None and cancelled():
            raise InterruptedError("Cancelled before VAE")

        self._enter("vae")
        for tile in range(1, self.vae_tiles + 1):
            self._pause()
            if on_progress is not None:
                on_progress("vae", tile, self.vae_tiles)

        request = {"style": style, "lyrics": lyrics, **kwargs}
        result = StandInResult(request, abc, self.audio_seconds, dict(self.truncated))
        if self.save_error is not None:
            error = self.save_error

            def failing_save_artifacts(directory):
                raise error

            result.save_artifacts = failing_save_artifacts
        return result

    def close(self):
        self.closed = True
