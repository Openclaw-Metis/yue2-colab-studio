"""Install runtime dependencies in child processes.

This module must never import torch: Colab preloads a newer torch than the
one YuE2 pins, and importing it in the kernel before the downgrade would force
a runtime restart.
"""

from __future__ import annotations

import subprocess
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass

TAIL_LINES = 30


@dataclass(frozen=True)
class CommandResult:
    returncode: int
    output: str


@dataclass(frozen=True)
class StepTiming:
    name: str
    seconds: float


class InstallFailed(Exception):
    def __init__(self, step: str, output: str):
        self.step = step
        self.tail = "\n".join(output.splitlines()[-TAIL_LINES:])
        super().__init__(f"{step} failed\n{self.tail}")


RunCommand = Callable[[list[str]], CommandResult]


def _run_command(args: list[str]) -> CommandResult:
    completed = subprocess.run(
        args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, check=False
    )
    return CommandResult(completed.returncode, completed.stdout)


def _pip(*args: str) -> list[str]:
    return [sys.executable, "-m", "pip", *args]


def install(
    requirements_path: str,
    run: RunCommand = _run_command,
    clock: Callable[[], float] = time.perf_counter,
) -> list[StepTiming]:
    """Uninstall the conflicting vision/audio wheels, install pins, verify.

    torchvision and torchaudio are removed first: Colab ships builds for a
    newer torch, and after the downgrade transformers fails on
    ``import torchvision`` with a RuntimeError it does not catch. YuE2 needs
    neither package.
    """
    steps = [
        ("uninstall", _pip("uninstall", "-y", "torchvision", "torchaudio")),
        ("install", _pip("install", "-r", requirements_path)),
        ("check", _pip("check")),
    ]
    timings = []
    for name, command in steps:
        start = clock()
        result = run(command)
        if result.returncode != 0:
            raise InstallFailed(name, result.output)
        timings.append(StepTiming(name, clock() - start))
    return timings


def verify_imports(run: RunCommand = _run_command) -> str:
    """Import the installed stack in a fresh interpreter and report versions."""
    code = (
        "import torch, yue2, gradio;"
        "print('torch', torch.__version__);"
        "print('yue2', yue2.__version__);"
        "print('gradio', gradio.__version__);"
        "print('cuda', torch.cuda.is_available())"
    )
    result = run([sys.executable, "-c", code])
    if result.returncode != 0:
        raise InstallFailed("verify", result.output)
    return result.output.strip()
