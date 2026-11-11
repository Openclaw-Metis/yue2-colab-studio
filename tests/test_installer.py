import ast
from pathlib import Path

import pytest

from yue2_studio import installer
from yue2_studio.installer import CommandResult

SRC = Path(__file__).resolve().parents[1] / "src" / "yue2_studio"


def recording_runner(failing_step=None, output="line\n" * 50):
    calls = []

    def run(args):
        calls.append(args)
        failed = failing_step is not None and failing_step in args
        return CommandResult(1 if failed else 0, output)

    return run, calls


def test_install_runs_three_steps_in_order():
    run, calls = recording_runner()
    timings = installer.install("requirements-colab.txt", run=run, clock=lambda: 0.0)
    assert [timing.name for timing in timings] == ["uninstall", "install", "check"]
    assert calls[0][-3:] == ["-y", "torchvision", "torchaudio"]
    assert calls[1][-2:] == ["-r", "requirements-colab.txt"]
    assert calls[2][-1] == "check"


def test_install_stops_at_first_failure_and_keeps_the_tail():
    run, calls = recording_runner(failing_step="install")
    with pytest.raises(installer.InstallFailed) as caught:
        installer.install("requirements-colab.txt", run=run)
    assert caught.value.step == "install"
    assert len(caught.value.tail.splitlines()) == installer.TAIL_LINES
    assert len(calls) == 2


def test_pip_check_failure_is_reported():
    run, _ = recording_runner(failing_step="check")
    with pytest.raises(installer.InstallFailed) as caught:
        installer.install("requirements-colab.txt", run=run)
    assert caught.value.step == "check"


def test_verify_imports_returns_versions():
    run, calls = recording_runner(output="torch 2.10.0\nyue2 0.1.6\n")
    assert installer.verify_imports(run=run) == "torch 2.10.0\nyue2 0.1.6"
    assert "import torch, yue2, gradio" in calls[0][-1]


def test_verify_imports_failure():
    run, _ = recording_runner(failing_step="-c")
    with pytest.raises(installer.InstallFailed):
        installer.verify_imports(run=run)


def _top_level_imports(path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names = set()
    for node in tree.body:
        if isinstance(node, ast.Import):
            names.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0:
            names.add(node.module.split(".")[0])
    return names


@pytest.mark.parametrize(
    "module", ["__init__", "environment", "installer", "notebook_steps", "ui_text"]
)
def test_cell_one_modules_never_import_heavy_packages(module):
    """Cell 1 imports these before anything is installed."""
    forbidden = {"torch", "numpy", "gradio", "yue2", "soundfile"}
    assert not _top_level_imports(SRC / f"{module}.py") & forbidden


def test_only_engine_imports_yue2():
    for path in SRC.glob("*.py"):
        if path.name == "engine.py":
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                assert all(alias.name.split(".")[0] != "yue2" for alias in node.names), path
            elif isinstance(node, ast.ImportFrom) and node.level == 0:
                assert node.module.split(".")[0] != "yue2", path
