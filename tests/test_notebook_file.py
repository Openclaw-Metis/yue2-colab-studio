"""The committed notebook must match its generator and stay valid."""

import importlib.util
import json
import warnings
from pathlib import Path

import nbformat

ROOT = Path(__file__).resolve().parents[1]


def _builder():
    path = ROOT / "scripts" / "build_notebook.py"
    spec = importlib.util.spec_from_file_location("build_notebook", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_notebook_matches_the_generator():
    committed = json.loads((ROOT / "YuE2_Colab_Studio.ipynb").read_text(encoding="utf-8"))
    assert committed == _builder().build()


def test_notebook_is_valid_and_has_three_code_cells():
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        notebook = nbformat.read(ROOT / "YuE2_Colab_Studio.ipynb", as_version=4)
        nbformat.validate(notebook)
    code = [cell for cell in notebook.cells if cell.cell_type == "code"]
    assert len(code) == 3
    assert "notebook_steps.cell_one(" in code[0].source
    assert "notebook_steps.cell_two(" in code[1].source
    assert "notebook_steps.cell_three(" in code[2].source
    # Cell 1 runs before anything is installed.
    assert "import torch" not in code[0].source


def test_requirements_pin_the_same_commit_as_the_package():
    from yue2_studio import YUE2_COMMIT

    requirements = (ROOT / "requirements-colab.txt").read_text(encoding="utf-8")
    assert f"YuE.git@{YUE2_COMMIT}" in requirements
    assert "gradio==" in requirements
