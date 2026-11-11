"""The Gradio layer: it builds, and it can express every patch studio.py emits."""

import ast
from pathlib import Path

import gradio as gr
import pytest
from conftest import Studio as Wiring

from yue2_studio import theme
from yue2_studio.app import build_app
from yue2_studio.draft_store import DraftStore
from yue2_studio.studio import Studio

SRC = Path(__file__).resolve().parents[1] / "src" / "yue2_studio"


@pytest.fixture
def demo(tmp_path):
    wiring = Wiring(tmp_path)
    studio = Studio(
        wiring.engine, wiring.store, DraftStore(tmp_path), wiring.runner, wiring.log
    )
    return build_app(studio)


def test_app_builds(demo):
    assert isinstance(demo, gr.Blocks)


def test_exactly_one_primary_button_per_tab(demo):
    primaries = [
        block.value
        for block in demo.blocks.values()
        if isinstance(block, gr.Button) and block.variant == "primary"
    ]
    # compose, score, result (remix) and library (load back into the form)
    assert len(primaries) == 4


def test_no_event_is_exposed_as_api(demo):
    visibilities = {fn.api_visibility for fn in demo.fns.values()}
    assert visibilities == {"private"}


def _patch_keys():
    """Every component name studio.py can put in a patch."""
    tree = ast.parse((SRC / "studio.py").read_text(encoding="utf-8"))
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Dict):
            for key, value in zip(node.keys, node.values, strict=True):
                if (
                    isinstance(key, ast.Constant)
                    and isinstance(key.value, str)
                    and isinstance(value, ast.Dict)
                ):
                    names.add(key.value)
        elif isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name):
            if node.value.id == "patch" and isinstance(node.slice, ast.Constant):
                names.add(node.slice.value)
    return names - {"_toast", "report"}


def test_every_patched_name_is_a_real_component():
    from yue2_studio.studio import MP3_BUTTONS

    names = _patch_keys() | set(MP3_BUTTONS.values())
    source = (SRC / "app.py").read_text(encoding="utf-8")
    missing = sorted(name for name in names if f'c["{name}"]' not in source)
    assert missing == []


def test_theme_builds():
    assert theme.build_theme() is not None
    assert theme.PRIMARY in theme.CSS or theme.ACCENT in theme.CSS
    assert "__theme" in theme.FORCE_LIGHT_HEAD
