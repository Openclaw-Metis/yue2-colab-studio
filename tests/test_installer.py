import ast
import sys
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
    report = installer.install("requirements-colab.txt", run=run, clock=lambda: 0.0)
    assert [timing.name for timing in report.timings] == ["uninstall", "install", "check"]
    assert report.unrelated_conflicts == []
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


def test_unparseable_pip_check_failure_is_reported():
    run, _ = recording_runner(failing_step="check", output="")
    with pytest.raises(installer.InstallFailed) as caught:
        installer.install("requirements-colab.txt", run=run, closure=lambda: {"gradio"})
    assert caught.value.step == "check"


# --- pip check on Colab ---------------------------------------------------------

# pip check output reported from a Colab L4 runtime on 2026-11-12 (Python 3.13.16).
COLAB_CHECK = (
    "fastai 2.8.12 requires torchvision, which is not installed.\n"
    "ipython 7.34.0 requires jedi, which is not installed.\n"
    "timm 1.0.31 requires torchvision, which is not installed.\n"
    "diffusers 0.42.1 has requirement huggingface-hub<3.0,>=1.32.0, "
    "but you have huggingface-hub 0.36.2.\n"
    "diffusers 0.42.1 has requirement safetensors>=0.8.0, but you have safetensors 0.7.0.\n"
    "cuda-python 13.0.3 has requirement cuda-bindings~=13.0.3, "
    "but you have cuda-bindings 12.9.4.\n"
)
STUDIO_CLOSURE = {
    "yue2-infer",
    "torch",
    "transformers",
    "huggingface-hub",
    "safetensors",
    "tiktoken",
    "numpy",
    "soundfile",
    "accelerate",
    "gradio",
    "cuda-bindings",
    "fastapi",
}


def check_runner(check_output):
    def run(args):
        if args[-1] == "check":
            return CommandResult(1, check_output)
        return CommandResult(0, "")

    return run


def test_colab_preinstalled_conflicts_are_only_a_notice():
    report = installer.install(
        "r.txt", run=check_runner(COLAB_CHECK), closure=lambda: STUDIO_CLOSURE
    )
    assert [timing.name for timing in report.timings] == ["uninstall", "install", "check"]
    assert len(report.unrelated_conflicts) == 6
    assert report.unrelated_conflicts[0].startswith("fastai 2.8.12")


def test_conflict_inside_the_studio_stack_is_fatal():
    output = COLAB_CHECK + (
        "Transformers 4.57.6 has requirement huggingface-hub<1.0,>=0.34.0, "
        "but you have huggingface-hub 1.32.0.\n"
    )
    with pytest.raises(installer.InstallFailed) as caught:
        installer.install("r.txt", run=check_runner(output), closure=lambda: STUDIO_CLOSURE)
    assert caught.value.step == "check"
    assert caught.value.tail.startswith("Transformers 4.57.6")
    assert "fastai" not in caught.value.tail


def test_split_check_output_normalises_names():
    blocking, unrelated = installer.split_check_output(
        "Huggingface_Hub 0.36.2 requires tqdm, which is not installed.\n"
        "No broken requirements found.\n",
        {"huggingface-hub"},
    )
    assert blocking == ["Huggingface_Hub 0.36.2 requires tqdm, which is not installed."]
    assert unrelated == []


def test_dependency_closure_follows_transitive_requirements():
    graph = {
        "yue2-infer": ["torch", "transformers"],
        "transformers": ["huggingface-hub", "torch"],
        "gradio": ["fastapi", "huggingface-hub"],
        "fastapi": ["starlette"],
    }
    closure = installer.dependency_closure(requires=lambda name: graph.get(name, []))
    assert closure == {
        "yue2-infer",
        "torch",
        "transformers",
        "huggingface-hub",
        "gradio",
        "fastapi",
        "starlette",
    }


@pytest.mark.parametrize(
    "line, expected",
    [
        ("anyio<5.0,>=3.0", "anyio"),
        ("Huggingface_Hub==0.36.2", "huggingface-hub"),
        ("pytest==9.0.3; extra == 'test'", None),
        ("pywin32; sys_platform == 'nonexistent-os'", None),
    ],
)
def test_requirement_names_respect_markers(line, expected):
    assert installer._requirement_name(line) == expected


def test_python_version_markers_follow_the_running_interpreter():
    line = "audioop-lts<=0.2.2; python_version >= '3.13'"
    expected = "audioop-lts" if sys.version_info >= (3, 13) else None
    assert installer._requirement_name(line) == expected


def test_closure_of_this_environment_contains_gradio_dependencies():
    closure = installer.dependency_closure(["gradio"])
    assert {"gradio", "fastapi", "huggingface-hub", "numpy"} <= closure
    assert installer.installed_requires("no-such-distribution-xyz") == []


# --- verification ---------------------------------------------------------------


def test_verify_imports_returns_versions():
    run, calls = recording_runner(output="torch 2.10.0\nyue2 0.1.6\n")
    assert installer.verify_imports(run=run) == "torch 2.10.0\nyue2 0.1.6"
    assert "import torch, yue2, gradio" in calls[0][-1]


def test_verify_imports_failure():
    run, _ = recording_runner(failing_step="-c")
    with pytest.raises(installer.InstallFailed):
        installer.verify_imports(run=run)


# --- import boundaries ------------------------------------------------------------


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
