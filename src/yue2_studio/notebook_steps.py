"""What each notebook cell does, kept out of the .ipynb so it can be tested.

Cell 1 runs before dependencies exist, so this module imports nothing beyond
the standard library and the two dependency-free siblings.
"""

from __future__ import annotations

import json
import os
import secrets
import string
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

from . import environment, installer, ui_text

ENV_MARKER = Path("/content/yue2_studio_env.json")
SESSION_FILE = Path("/content/yue2_studio_session.json")
LOCAL_WORKDIR = "/content/yue2_studio_data"
DRIVE_MOUNT = "/content/drive"
DRIVE_WORKDIR = "/content/drive/MyDrive/YuE2-Studio"
PASSCODE_ALPHABET = string.ascii_lowercase + string.digits
PASSCODE_LENGTH = 12


def cell_one(
    repo_dir: str,
    *,
    probe: Callable[[], environment.EnvironmentReport] = environment.probe,
    install: Callable[[str], list[installer.StepTiming]] = installer.install,
    verify: Callable[[], str] = installer.verify_imports,
    marker: Path = ENV_MARKER,
    out: Callable[[str], None] = print,
) -> environment.EnvironmentReport:
    """Gate on the GPU, then install and verify the pinned stack."""
    report = probe()
    out(environment.format_report(report))
    if not report.ok:
        out("")
        for problem in report.problems:
            out(problem)
        out(ui_text.ERRORS["E_ENV_GPU"])
        raise SystemExit("E_ENV_GPU")

    out("\n正在安裝套件，需要幾分鐘……")
    try:
        timings = install(str(Path(repo_dir) / "requirements-colab.txt"))
        versions = verify()
    except installer.InstallFailed as failure:
        out(ui_text.ERRORS["E_ENV_INSTALL"])
        out(failure.tail)
        raise SystemExit("E_ENV_INSTALL") from failure

    for timing in timings:
        out(f"{timing.name:<10} {timing.seconds:6.1f} 秒")
    out(versions)
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text(
        json.dumps({"report": report.to_dict(), "versions": versions}, ensure_ascii=False),
        encoding="utf-8",
    )
    out("\n" + ui_text.ENV_OK)
    return report


def make_passcode() -> str:
    return "".join(secrets.choice(PASSCODE_ALPHABET) for _ in range(PASSCODE_LENGTH))


def cell_two(
    use_drive: bool,
    *,
    mount_drive: Callable[[str], None] | None = None,
    marker: Path = ENV_MARKER,
    session_file: Path = SESSION_FILE,
    local_workdir: str = LOCAL_WORKDIR,
    drive_workdir: str = DRIVE_WORKDIR,
    out: Callable[[str], None] = print,
) -> dict:
    """Pick where songs are kept and mint this session's passcode."""
    if not marker.exists():
        out(ui_text.CELL_ONE_FIRST)
        raise SystemExit("E_ENV_GPU")

    if use_drive:
        if mount_drive is None:  # pragma: no cover - only reachable on Colab
            from google.colab import drive

            mount_drive = drive.mount
        mount_drive(DRIVE_MOUNT)
        workdir = drive_workdir
    else:
        workdir = local_workdir
    Path(workdir).mkdir(parents=True, exist_ok=True)

    session = {"workdir": workdir, "use_drive": bool(use_drive), "passcode": make_passcode()}
    session_file.write_text(json.dumps(session, ensure_ascii=False), encoding="utf-8")
    out(ui_text.WORKDIR_NOTICE.format(workdir=workdir))
    if not use_drive:
        out(ui_text.EPHEMERAL_WARNING)
    out(ui_text.PASSCODE_NOTICE.format(passcode=session["passcode"]))
    return session


def cell_three(
    repo_dir: str,
    *,
    session_file: Path = SESSION_FILE,
    out: Callable[[str], None] = print,
) -> int:  # pragma: no cover - starts a long-running server process
    """Run the studio in a child process and relay its output.

    A child process starts from the freshly installed packages. The notebook
    kernel may still hold modules that were imported before cell 1 replaced
    them, which is exactly the mismatch that breaks torch and numpy.
    """
    if not session_file.exists():
        out(ui_text.CELL_TWO_FIRST)
        raise SystemExit("E_ENV_GPU")
    session = json.loads(session_file.read_text(encoding="utf-8"))

    env = dict(os.environ)
    source = str(Path(repo_dir) / "src")
    env["PYTHONPATH"] = source + os.pathsep + env.get("PYTHONPATH", "")
    env["YUE2_STUDIO_PASSCODE"] = session["passcode"]
    env["PYTHONUNBUFFERED"] = "1"
    command = [sys.executable, "-m", "yue2_studio.launch", "--share"]
    command += ["--workdir", session["workdir"]]
    if session.get("use_drive"):
        command.append("--persistent")

    out(ui_text.LAUNCHING)
    process = subprocess.Popen(
        command, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
    )
    try:
        for line in process.stdout:
            out(line.rstrip("\n"))
    except KeyboardInterrupt:
        process.terminate()
        try:
            process.wait(timeout=20)
        except subprocess.TimeoutExpired:
            process.kill()
    return process.wait()


def read_env_marker(marker: Path = ENV_MARKER) -> dict:
    try:
        return json.loads(marker.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}

