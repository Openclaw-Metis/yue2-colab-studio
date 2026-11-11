import threading

import pytest

from yue2_studio.engine import Engine
from yue2_studio.event_log import EventLog
from yue2_studio.generation_job import JobRunner
from yue2_studio.song_store import SongStore
from yue2_studio.stand_in_pipeline import StandInPipeline

FORM = {"style": "piano pop", "lyrics": "[Verse]\nhello", "cot": "full", "seed": 7}


class Studio:
    """A fully wired studio on the stand-in pipeline, rooted in a temp folder."""

    def __init__(self, root, pipe=None, **runner_kwargs):
        self.root = root
        self.pipe = pipe or StandInPipeline()
        self.pipes = []

        def factory(cache_dir):
            created = self.pipe if not self.pipes else StandInPipeline()
            self.pipes.append(created)
            return created

        self.engine = Engine(
            factory,
            sleep=lambda seconds: None,
            reset_peak_vram=lambda: None,
            read_peak_vram_gib=lambda: 11.5,
            empty_cache=lambda: None,
        )
        self.mp3_calls = []
        self.store = SongStore(root, mp3_converter=self._fake_mp3)
        self.log = EventLog(root / "logs" / "app.log")
        runner_kwargs.setdefault("poll_seconds", 0.005)
        self.runner = JobRunner(
            self.engine, self.store, self.log, versions={"studio": "test"}, **runner_kwargs
        )

    # Set to an exception to make MP3 encoding fail.
    mp3_error = None

    def _fake_mp3(self, source, target, *, title=None):
        """Stands in for ffmpeg so the suite stays fast; test_audio_export runs the real one."""
        self.mp3_calls.append((source, target, title))
        if self.mp3_error is not None:
            raise self.mp3_error
        target.write_bytes(b"ID3\x03\x00\x00\x00\x00\x00\x00stand-in")

    def events(self, name=None):
        records = self.log.recent(200)
        return [r for r in records if name is None or r["event"] == name]


@pytest.fixture
def studio(tmp_path):
    return Studio(tmp_path)


@pytest.fixture
def make_studio(tmp_path):
    def build(pipe=None, **runner_kwargs):
        return Studio(tmp_path, pipe, **runner_kwargs)

    return build


class Gate:
    """Lets a test hold the stand-in pipeline at a chosen stage."""

    def __init__(self, stage):
        self.stage = stage
        self.reached = threading.Event()
        self.release = threading.Event()

    def __call__(self, stage):
        if stage == self.stage:
            self.reached.set()
            assert self.release.wait(5), "test never released the gate"


@pytest.fixture
def gate():
    return Gate
