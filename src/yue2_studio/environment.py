"""Runtime gate: decide whether this machine can run unpatched YuE2.

Reads the GPU through nvidia-smi so the check works before torch is installed
(and so cell 1 never imports the Colab-preinstalled torch it is about to
replace).
"""

from __future__ import annotations

import platform
import subprocess
from collections.abc import Callable
from dataclasses import asdict, dataclass, field

from . import ui_text

# BF16 tensor cores and FlashAttention both start at Ampere (sm_80).
MIN_COMPUTE_CAPABILITY = (8, 0)
# Upstream measured a 14.08 GiB worst-case peak and keeps a 2 GiB reserve.
# 20 GiB admits the L4 (about 22.5 GiB reported) and rejects 16 GiB cards.
MIN_VRAM_GIB = 20.0

# Fallback when an old driver cannot answer --query-gpu=compute_cap.
_KNOWN_CAPABILITIES = {
    "T4": (7, 5),
    "P100": (6, 0),
    "V100": (7, 0),
    "L4": (8, 9),
    "A100": (8, 0),
    "H100": (9, 0),
}

RunCommand = Callable[[list[str]], str]


@dataclass(frozen=True)
class EnvironmentReport:
    gpu_name: str | None
    compute_capability: tuple[int, int] | None
    vram_total_gib: float
    ram_total_gib: float
    python_version: str
    ok: bool
    problems: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def _run_command(args: list[str]) -> str:
    completed = subprocess.run(args, capture_output=True, text=True, timeout=30, check=True)
    return completed.stdout


def _read_ram_gib() -> float:
    try:
        with open("/proc/meminfo", encoding="ascii") as handle:
            for line in handle:
                if line.startswith("MemTotal:"):
                    return int(line.split()[1]) / 2**20
    except OSError:
        pass
    return 0.0


def _parse_capability(text: str) -> tuple[int, int] | None:
    major, _, minor = text.strip().partition(".")
    if major.isdigit() and minor.isdigit():
        return int(major), int(minor)
    return None


def _capability_from_name(name: str) -> tuple[int, int] | None:
    tokens = name.replace("-", " ").split()
    for model, capability in _KNOWN_CAPABILITIES.items():
        if model in tokens:
            return capability
    return None


def _query_gpu(run: RunCommand) -> tuple[str, float, tuple[int, int] | None] | None:
    base = ["nvidia-smi", "--format=csv,noheader,nounits"]
    try:
        first = run([*base, "--query-gpu=name,memory.total,compute_cap"]).strip().splitlines()[0]
        name, memory_mib, capability = (part.strip() for part in first.split(","))
        return name, float(memory_mib) / 1024, _parse_capability(capability)
    except (OSError, subprocess.SubprocessError, ValueError, IndexError):
        pass
    try:
        first = run([*base, "--query-gpu=name,memory.total"]).strip().splitlines()[0]
        name, memory_mib = (part.strip() for part in first.split(","))
        return name, float(memory_mib) / 1024, _capability_from_name(name)
    except (OSError, subprocess.SubprocessError, ValueError, IndexError):
        return None


def probe(
    run: RunCommand = _run_command,
    read_ram_gib: Callable[[], float] = _read_ram_gib,
) -> EnvironmentReport:
    python_version = platform.python_version()
    ram = read_ram_gib()
    gpu = _query_gpu(run)
    if gpu is None:
        return EnvironmentReport(None, None, 0.0, ram, python_version, False, [ui_text.ENV_NO_GPU])

    name, vram, capability = gpu
    problems = []
    if capability is None:
        problems.append(ui_text.ENV_GPU_UNKNOWN.format(name=name))
    elif capability < MIN_COMPUTE_CAPABILITY:
        problems.append(ui_text.ENV_GPU_TOO_OLD.format(name=name))
    if vram < MIN_VRAM_GIB:
        problems.append(ui_text.ENV_VRAM_TOO_SMALL.format(vram=vram, need=MIN_VRAM_GIB))
    return EnvironmentReport(name, capability, vram, ram, python_version, not problems, problems)


def format_report(report: EnvironmentReport) -> str:
    capability = (
        ".".join(str(part) for part in report.compute_capability)
        if report.compute_capability
        else "未知"
    )
    lines = [
        f"GPU            {report.gpu_name or '無'}",
        f"運算能力等級   {capability}",
        f"GPU 記憶體     {report.vram_total_gib:.1f} GiB",
        f"主機記憶體     {report.ram_total_gib:.1f} GiB",
        f"Python         {report.python_version}",
    ]
    return "\n".join(lines)
