import pytest

from yue2_studio import engine as engine_module
from yue2_studio.engine import Cancelled, Engine, EngineError, StageEvent
from yue2_studio.request_rules import StudioRequest
from yue2_studio.stand_in_pipeline import STAND_IN_ABC, StandInPipeline

REQUEST = StudioRequest("piano pop", "[Verse]\nhello", "full", 7, None, None)


def make_engine(pipe=None, **kwargs):
    pipes = []

    def factory(cache_dir):
        created = pipe if pipe is not None and not pipes else StandInPipeline()
        pipes.append(created)
        return created

    engine = Engine(
        factory,
        sleep=lambda seconds: None,
        reset_peak_vram=lambda: None,
        read_peak_vram_gib=lambda: 11.5,
        empty_cache=lambda: None,
        **kwargs,
    )
    return engine, pipes


def never():
    return False


def render(engine, request=REQUEST, abc=None, cancelled=never):
    events = []
    outcome = engine.render(request, abc=abc, cancelled=cancelled, on_stage=events.append)
    return outcome, events


def test_pipeline_is_created_once_and_reused():
    engine, pipes = make_engine()
    render(engine)
    render(engine)
    assert len(pipes) == 1
    assert engine.state == "ready"
    assert engine.load_seconds is not None


def test_render_forwards_the_request_fields():
    pipe = StandInPipeline()
    engine, _ = make_engine(pipe)
    request = StudioRequest("jazz", "la", "melody", 99, 1.3, None)
    render(engine, request, abc="X:1\nK:C\nC")
    name, kwargs = pipe.calls[-1]
    assert name == "call"
    assert kwargs == {
        "style": "jazz",
        "lyrics": "la",
        "cot": "melody",
        "seed": 99,
        "abc": "X:1\nK:C\nC",
        "cfg_scale": 1.3,
    }


def test_stage_events_follow_the_pipeline_order():
    engine, _ = make_engine()
    outcome, events = render(engine)
    stages = []
    for event in events:
        if not stages or stages[-1] != event.stage:
            stages.append(event.stage)
    assert stages == ["planning", "composing", "rendering", "decoding"]
    assert outcome.peak_vram_gib == 11.5
    assert events[-1] == StageEvent("decoding", 2, 2)


def test_supplied_score_skips_planning():
    engine, _ = make_engine()
    _, events = render(engine, abc=STAND_IN_ABC)
    assert "planning" not in {event.stage for event in events}


def test_token_events_are_throttled():
    engine, _ = make_engine(StandInPipeline(semantic_tokens=100))
    _, events = render(engine, abc=STAND_IN_ABC)
    composing = [event.completed for event in events if event.stage == "composing"]
    assert composing == [1, 25, 50, 75, 100]


def test_plan_returns_the_score():
    pipe = StandInPipeline(truncated={"abc": True, "semantic": False})
    engine, _ = make_engine(pipe)
    draft = engine.plan(REQUEST, cancelled=never)
    assert draft.abc == STAND_IN_ABC
    assert draft.truncated is True
    assert pipe.calls[-1][0] == "plan"
    assert pipe.calls[-1][1]["seed"] == 7


def test_cancel_becomes_cancelled():
    engine, _ = make_engine()
    with pytest.raises(Cancelled):
        render(engine, cancelled=lambda: True)
    assert engine.state == "ready"


def test_out_of_memory_marks_the_engine_for_reload():
    class OutOfMemoryError(RuntimeError):
        pass

    broken = StandInPipeline(fail_at="nar", error=OutOfMemoryError("CUDA out of memory"))
    engine, pipes = make_engine(broken)
    with pytest.raises(EngineError) as caught:
        render(engine)
    assert caught.value.code == "E_OOM"
    assert engine.state == "error"

    render(engine)
    assert broken.closed
    assert len(pipes) == 2
    assert engine.state == "ready"


def test_value_error_with_a_score_is_an_abc_problem():
    engine, _ = make_engine(StandInPipeline(fail_at="semantic", error=ValueError("ABC IDs")))
    with pytest.raises(EngineError) as caught:
        render(engine, abc="X:1")
    assert caught.value.code == "E_ABC_INVALID"


def test_value_error_without_a_score_is_unknown():
    engine, _ = make_engine(StandInPipeline(fail_at="semantic", error=ValueError("odd")))
    with pytest.raises(EngineError) as caught:
        render(engine)
    assert caught.value.code == "E_UNKNOWN"
    assert "ValueError" in caught.value.detail


def test_download_is_retried_three_times_then_reported():
    attempts = []
    sleeps = []
    notes = []

    def factory(cache_dir):
        attempts.append(cache_dir)
        raise ConnectionError("network down")

    engine = Engine(factory, sleep=sleeps.append, empty_cache=lambda: None)
    with pytest.raises(EngineError) as caught:
        engine.load(notes.append)
    assert caught.value.code == "E_MODEL_DOWNLOAD"
    assert len(attempts) == 4
    assert sleeps == list(engine_module.DOWNLOAD_RETRY_DELAYS)
    assert [note.note for note in notes] == ["retry:1", "retry:2", "retry:3"]
    assert engine.state == "error"


def test_download_recovers_after_a_transient_failure():
    attempts = []

    def factory(cache_dir):
        attempts.append(1)
        if len(attempts) < 3:
            raise TimeoutError("slow")
        return StandInPipeline()

    engine = Engine(factory, sleep=lambda seconds: None, empty_cache=lambda: None)
    engine.load()
    assert engine.ready and len(attempts) == 3


def test_missing_bf16_support_is_an_environment_error():
    def factory(cache_dir):
        raise RuntimeError("The unquantized preset requires CUDA BF16 support")

    engine = Engine(factory, empty_cache=lambda: None)
    with pytest.raises(EngineError) as caught:
        engine.load()
    assert caught.value.code == "E_ENV_GPU"


def test_out_of_memory_while_loading():
    def factory(cache_dir):
        raise RuntimeError("CUDA out of memory")

    engine = Engine(factory, empty_cache=lambda: None)
    with pytest.raises(EngineError) as caught:
        engine.load()
    assert caught.value.code == "E_OOM"


def test_close_releases_the_pipeline():
    pipe = StandInPipeline()
    engine, _ = make_engine(pipe)
    engine.load()
    engine.close()
    assert pipe.closed
    assert engine.state == "unloaded" and not engine.ready
