import subprocess

from yue2_studio import environment


def runner(responses):
    """Return a fake nvidia-smi that answers by query string."""

    def run(args):
        query = next(arg for arg in args if arg.startswith("--query-gpu="))
        answer = responses.get(query)
        if isinstance(answer, Exception):
            raise answer
        if answer is None:
            raise subprocess.CalledProcessError(1, args)
        return answer

    return run


FULL = "--query-gpu=name,memory.total,compute_cap"
BASIC = "--query-gpu=name,memory.total"


def probe(responses):
    return environment.probe(run=runner(responses), read_ram_gib=lambda: 51.0)


def test_l4_passes():
    report = probe({FULL: "NVIDIA L4, 23034, 8.9\n"})
    assert report.ok
    assert report.compute_capability == (8, 9)
    assert 22.4 < report.vram_total_gib < 22.6
    assert report.problems == []


def test_t4_fails_on_capability_and_memory():
    report = probe({FULL: "Tesla T4, 15360, 7.5\n"})
    assert not report.ok
    assert len(report.problems) == 2
    assert "Tesla T4" in report.problems[0]


def test_a100_passes():
    assert probe({FULL: "NVIDIA A100-SXM4-40GB, 40960, 8.0\n"}).ok


def test_no_gpu_when_nvidia_smi_is_missing():
    report = probe({FULL: FileNotFoundError(), BASIC: FileNotFoundError()})
    assert not report.ok
    assert report.gpu_name is None
    assert report.vram_total_gib == 0.0


def test_old_driver_falls_back_to_known_model_names():
    assert probe({BASIC: "NVIDIA L4, 23034\n"}).compute_capability == (8, 9)
    assert not probe({BASIC: "Tesla T4, 15360\n"}).ok


def test_unknown_model_without_capability_is_rejected():
    report = probe({BASIC: "Mystery Card 9000, 49152\n"})
    assert not report.ok
    assert report.compute_capability is None


def test_capable_gpu_with_too_little_memory_is_rejected():
    report = probe({FULL: "NVIDIA RTX 4070, 12282, 8.9\n"})
    assert not report.ok
    assert len(report.problems) == 1


def test_format_report_mentions_every_field():
    text = environment.format_report(probe({FULL: "NVIDIA L4, 23034, 8.9\n"}))
    assert "NVIDIA L4" in text and "8.9" in text and "51.0" in text


def test_ram_reader_returns_zero_without_procfs(monkeypatch):
    def missing(*args, **kwargs):
        raise OSError

    monkeypatch.setattr("builtins.open", missing)
    assert environment._read_ram_gib() == 0.0
