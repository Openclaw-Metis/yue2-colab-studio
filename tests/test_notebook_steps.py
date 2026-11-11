import json

import pytest

from yue2_studio import installer, notebook_steps, ui_text
from yue2_studio.environment import EnvironmentReport

L4 = EnvironmentReport("NVIDIA L4", (8, 9), 22.5, 51.0, "3.12.0", True, [])
T4 = EnvironmentReport("Tesla T4", (7, 5), 15.0, 12.7, "3.12.0", False, ["too old"])


def test_cell_one_stops_before_installing_on_t4(tmp_path):
    lines = []
    installed = []
    with pytest.raises(SystemExit) as caught:
        notebook_steps.cell_one(
            str(tmp_path),
            probe=lambda: T4,
            install=installed.append,
            marker=tmp_path / "env.json",
            out=lines.append,
        )
    assert caught.value.code == "E_ENV_GPU"
    assert installed == []
    assert ui_text.ERRORS["E_ENV_GPU"] in lines
    assert not (tmp_path / "env.json").exists()


def test_cell_one_installs_and_writes_marker_on_l4(tmp_path):
    lines = []
    seen = []

    def install(path):
        seen.append(path)
        return installer.InstallReport([installer.StepTiming("install", 1.5)])

    report = notebook_steps.cell_one(
        str(tmp_path),
        probe=lambda: L4,
        install=install,
        verify=lambda: "torch 2.10.0",
        marker=tmp_path / "env.json",
        out=lines.append,
    )
    assert report is L4
    assert seen[0].endswith("requirements-colab.txt")
    assert lines[-1].strip() == ui_text.ENV_OK
    marker = json.loads((tmp_path / "env.json").read_text(encoding="utf-8"))
    assert marker["versions"] == "torch 2.10.0"
    assert marker["report"]["gpu_name"] == "NVIDIA L4"


def test_cell_one_reports_install_failure(tmp_path):
    lines = []

    def install(path):
        raise installer.InstallFailed("install", "boom\n" * 3)

    with pytest.raises(SystemExit) as caught:
        notebook_steps.cell_one(
            str(tmp_path),
            probe=lambda: L4,
            install=install,
            marker=tmp_path / "env.json",
            out=lines.append,
        )
    assert caught.value.code == "E_ENV_INSTALL"
    # Colab's IPython 7.34 on Python 3.13 crashes rendering chained exceptions.
    assert caught.value.__cause__ is None and caught.value.__context__ is None
    assert ui_text.ERRORS["E_ENV_INSTALL"] in lines
    assert ui_text.INSTALL_FAILED_STEP.format(step="install") in lines
    assert not (tmp_path / "env.json").exists()


def test_cell_one_lists_unrelated_conflicts_and_still_passes(tmp_path):
    lines = []

    def install(path):
        return installer.InstallReport(
            [installer.StepTiming("check", 0.5)],
            ["fastai 2.8.12 requires torchvision, which is not installed."],
        )

    notebook_steps.cell_one(
        str(tmp_path),
        probe=lambda: L4,
        install=install,
        verify=lambda: "torch 2.10.0",
        marker=tmp_path / "env.json",
        out=lines.append,
    )
    assert ui_text.UNRELATED_CONFLICTS in "\n".join(lines)
    assert "  fastai 2.8.12 requires torchvision, which is not installed." in lines
    assert lines[-1].strip() == ui_text.ENV_OK


def test_cell_two_requires_cell_one(tmp_path):
    with pytest.raises(SystemExit):
        notebook_steps.cell_two(
            False,
            marker=tmp_path / "missing.json",
            session_file=tmp_path / "session.json",
            out=lambda line: None,
        )


def test_cell_two_local_storage_warns_about_losing_songs(tmp_path):
    marker = tmp_path / "env.json"
    marker.write_text("{}", encoding="utf-8")
    lines = []
    session = notebook_steps.cell_two(
        False,
        marker=marker,
        session_file=tmp_path / "session.json",
        local_workdir=str(tmp_path / "data"),
        out=lines.append,
    )
    assert (tmp_path / "data").is_dir()
    assert ui_text.EPHEMERAL_WARNING in lines
    assert len(session["passcode"]) == notebook_steps.PASSCODE_LENGTH
    assert json.loads((tmp_path / "session.json").read_text(encoding="utf-8")) == session


def test_cell_two_drive_mounts_and_uses_drive_folder(tmp_path):
    marker = tmp_path / "env.json"
    marker.write_text("{}", encoding="utf-8")
    mounted = []
    lines = []
    session = notebook_steps.cell_two(
        True,
        mount_drive=mounted.append,
        marker=marker,
        session_file=tmp_path / "session.json",
        drive_workdir=str(tmp_path / "drive" / "YuE2-Studio"),
        out=lines.append,
    )
    assert mounted == [notebook_steps.DRIVE_MOUNT]
    assert session["use_drive"] is True
    assert ui_text.EPHEMERAL_WARNING not in lines


def test_passcodes_differ():
    assert notebook_steps.make_passcode() != notebook_steps.make_passcode()


def test_read_env_marker_tolerates_missing_and_corrupt(tmp_path):
    assert notebook_steps.read_env_marker(tmp_path / "missing.json") == {}
    broken = tmp_path / "broken.json"
    broken.write_text("{", encoding="utf-8")
    assert notebook_steps.read_env_marker(broken) == {}
