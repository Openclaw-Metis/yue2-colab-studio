"""Install runtime dependencies in child processes.

This module must never import torch: Colab preloads a newer torch than the
one YuE2 pins, and importing it in the kernel before the downgrade would force
a runtime restart.
"""

from __future__ import annotations

import importlib
import re
import subprocess
import sys
import time
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from importlib import metadata

TAIL_LINES = 30
# Everything the studio runs is reachable from these two distributions.
ROOT_PACKAGES = ("yue2-infer", "gradio")


@dataclass(frozen=True)
class CommandResult:
    returncode: int
    output: str


@dataclass(frozen=True)
class StepTiming:
    name: str
    seconds: float


@dataclass(frozen=True)
class InstallReport:
    timings: list[StepTiming]
    # pip check lines about packages the studio never imports, such as the
    # many libraries Colab preinstalls. Shown as a notice, never fatal.
    unrelated_conflicts: list[str] = field(default_factory=list)


class InstallFailed(Exception):
    def __init__(self, step: str, output: str):
        self.step = step
        self.tail = "\n".join(output.splitlines()[-TAIL_LINES:])
        super().__init__(f"{step} failed\n{self.tail}")


RunCommand = Callable[[list[str]], CommandResult]
RequiresOf = Callable[[str], list[str]]


def _run_command(args: list[str]) -> CommandResult:
    completed = subprocess.run(
        args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, check=False
    )
    return CommandResult(completed.returncode, completed.stdout)


def _pip(*args: str) -> list[str]:
    return [sys.executable, "-m", "pip", *args]


def normalize(name: str) -> str:
    """PEP 503 name normalisation, so "Huggingface_Hub" matches "huggingface-hub"."""
    return re.sub(r"[-_.]+", "-", name).lower()


def _requirement_name(line: str) -> str | None:
    """Name of a Requires-Dist entry, or None when its marker excludes it here."""
    try:
        from packaging.requirements import Requirement

        requirement = Requirement(line)
        if requirement.marker is not None and not requirement.marker.evaluate({"extra": ""}):
            return None
        return normalize(requirement.name)
    except Exception:
        name, _, marker = line.partition(";")
        if "extra" in marker:
            return None
        match = re.match(r"\s*([A-Za-z0-9][A-Za-z0-9._-]*)", name)
        return normalize(match.group(1)) if match else None


def installed_requires(name: str) -> list[str]:
    try:
        lines = metadata.requires(name) or []
    except metadata.PackageNotFoundError:
        return []
    names = (_requirement_name(line) for line in lines)
    return [found for found in names if found]


def dependency_closure(
    roots: Iterable[str] = ROOT_PACKAGES, requires: RequiresOf = installed_requires
) -> set[str]:
    """Every installed distribution the roots depend on, directly or not."""
    seen: set[str] = set()
    pending = [normalize(root) for root in roots]
    while pending:
        name = pending.pop()
        if name in seen:
            continue
        seen.add(name)
        pending.extend(requires(name))
    return seen


def split_check_output(output: str, closure: set[str]) -> tuple[list[str], list[str]]:
    """Separate pip check lines that affect the studio from the rest.

    Every pip check line starts with the distribution whose requirement is
    broken ("X 1.0 requires Y, which is not installed.", "X 1.0 has
    requirement Y>=2, but you have Y 1.0."). A broken requirement only
    matters here when X itself is something the studio runs.
    """
    blocking, unrelated = [], []
    for raw in output.splitlines():
        line = raw.strip()
        if not line or line.lower().startswith("no broken requirements"):
            continue
        owner = normalize(line.split()[0])
        (blocking if owner in closure else unrelated).append(line)
    return blocking, unrelated


def install(
    requirements_path: str,
    run: RunCommand = _run_command,
    clock: Callable[[], float] = time.perf_counter,
    closure: Callable[[], set[str]] | None = None,
) -> InstallReport:
    """Uninstall the conflicting vision/audio wheels, install pins, verify.

    torchvision and torchaudio are removed first: Colab ships builds for a
    newer torch, and after the downgrade transformers fails on
    ``import torchvision`` with a RuntimeError it does not catch. YuE2 needs
    neither package.
    """
    timings = []
    for name, command in (
        ("uninstall", _pip("uninstall", "-y", "torchvision", "torchaudio")),
        ("install", _pip("install", "-r", requirements_path)),
    ):
        start = clock()
        result = run(command)
        if result.returncode != 0:
            raise InstallFailed(name, result.output)
        timings.append(StepTiming(name, clock() - start))

    start = clock()
    result = run(_pip("check"))
    unrelated: list[str] = []
    if result.returncode != 0:
        # Colab preinstalls hundreds of packages, and pinning YuE2's stack
        # always breaks some of them (fastai and timm need torchvision,
        # diffusers needs a newer huggingface-hub). Only conflicts inside the
        # studio's own dependency tree are fatal.
        if closure is None:
            importlib.invalidate_caches()
            closure = dependency_closure
        blocking, unrelated = split_check_output(result.output, closure())
        if blocking or not unrelated:
            raise InstallFailed("check", "\n".join(blocking) or result.output)
    timings.append(StepTiming("check", clock() - start))
    return InstallReport(timings, unrelated)


def verify_imports(run: RunCommand = _run_command) -> str:
    """Import the installed stack in a fresh interpreter and report versions."""
    code = (
        "import torch, yue2, gradio;"
        "print('torch', torch.__version__);"
        "print('yue2', yue2.__version__);"
        "print('gradio', gradio.__version__);"
        "print('cuda', torch.cuda.is_available());"
        "import shutil;"
        "print('ffmpeg', shutil.which('ffmpeg') or 'missing (MP3 export unavailable)')"
    )
    result = run([sys.executable, "-c", code])
    if result.returncode != 0:
        raise InstallFailed("verify", result.output)
    return result.output.strip()
