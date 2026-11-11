"""Generate YuE2_Colab_Studio.ipynb.

The notebook is a build product: edit this script, run it, commit both. Cell
logic lives in yue2_studio.notebook_steps so it can be unit tested.

    python scripts/build_notebook.py
"""

from __future__ import annotations

import json
from pathlib import Path

REPO_URL = "https://github.com/Openclaw-Metis/yue2-colab-studio"
OUTPUT = Path(__file__).resolve().parents[1] / "YuE2_Colab_Studio.ipynb"

INTRO = """\
# YuE2 Colab 寫歌工作室

用 [YuE2](https://github.com/multimodal-art-projection/YuE) 把曲風與歌詞變成一首完整的歌。本專案為非官方工具。

**開始之前**

1. 上方選單「執行階段」→「變更執行階段類型」，硬體加速器選 **L4 GPU**。免費的 T4 無法使用。
2. 由上往下依序執行三格。
3. 用完之後，請到「執行階段」→「中斷並刪除執行階段」，否則運算單元會繼續被扣。

YuE2 的權重採 CC BY-NC 4.0 加創作者條款，詳見[上游授權](https://github.com/multimodal-art-projection/YuE/blob/main/MODEL_LICENSE)。
"""

CELL_ONE_NOTE = """\
## 第一格：檢查環境並安裝

確認執行階段是 L4，然後安裝 YuE2 與介面需要的套件。首次需要幾分鐘。
成功時最後一行會顯示「環境檢查通過」。
"""

CELL_ONE = f"""\
#@title 1. 檢查環境並安裝 {{ display-mode: "form" }}
REVISION = "main"  #@param {{type:"string"}}

import os, subprocess, sys

REPO_URL = "{REPO_URL}"
REPO_DIR = "/content/yue2-colab-studio"
if os.path.isdir(REPO_DIR):
    # Rerunning this cell picks up fixes published since the first run.
    subprocess.run(["git", "-C", REPO_DIR, "fetch", "--depth", "1", "origin", REVISION], check=True)
    subprocess.run(["git", "-C", REPO_DIR, "reset", "--hard", "-q", "FETCH_HEAD"], check=True)
else:
    subprocess.run(
        ["git", "clone", "--depth", "1", "--branch", REVISION, REPO_URL, REPO_DIR], check=True
    )
if REPO_DIR + "/src" not in sys.path:
    sys.path.insert(0, REPO_DIR + "/src")
for _name in [n for n in sys.modules if n == "yue2_studio" or n.startswith("yue2_studio.")]:
    del sys.modules[_name]
subprocess.run(["git", "-C", REPO_DIR, "log", "-1", "--format=版本 %h %cd", "--date=short"])

from yue2_studio import notebook_steps

notebook_steps.cell_one(REPO_DIR)
"""

CELL_TWO_NOTE = """\
## 第二格：選擇保存位置

勾選 `USE_DRIVE` 會把歌曲存到你的 Google 雲端硬碟（`我的雲端硬碟/YuE2-Studio`），
下次開新的執行階段還找得到。不勾選的話，歌曲只存在這次的執行階段。

這一格會顯示本次專用的通行碼，登入介面時需要。
"""

CELL_TWO = """\
#@title 2. 選擇保存位置 { display-mode: "form" }
USE_DRIVE = False  #@param {type:"boolean"}

session = notebook_steps.cell_two(USE_DRIVE)
"""

CELL_THREE_NOTE = """\
## 第三格：啟動介面

出現 `https://....gradio.live` 的連結後點開，帳號輸入 `studio`，密碼輸入第二格顯示的通行碼。
這一格會一直執行，直到你中斷它。第一次生成歌曲時會下載作曲引擎，需要多等一段時間。
"""

CELL_THREE = """\
#@title 3. 啟動介面 { display-mode: "form" }
notebook_steps.cell_three(REPO_DIR)
"""


def markdown(cell_id: str, text: str) -> dict:
    return {
        "cell_type": "markdown",
        "id": cell_id,
        "metadata": {},
        "source": text.splitlines(keepends=True),
    }


def code(cell_id: str, text: str) -> dict:
    return {
        "cell_type": "code",
        "id": cell_id,
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": text.splitlines(keepends=True),
    }


def build() -> dict:
    return {
        "cells": [
            markdown("intro", INTRO),
            markdown("cell-one-note", CELL_ONE_NOTE),
            code("cell-one", CELL_ONE),
            markdown("cell-two-note", CELL_TWO_NOTE),
            code("cell-two", CELL_TWO),
            markdown("cell-three-note", CELL_THREE_NOTE),
            code("cell-three", CELL_THREE),
        ],
        "metadata": {
            "accelerator": "GPU",
            "colab": {"gpuType": "L4", "provenance": []},
            "kernelspec": {"display_name": "Python 3", "name": "python3"},
            "language_info": {"name": "python"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }


def main() -> None:
    OUTPUT.write_text(
        json.dumps(build(), ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n"
    )
    print(f"wrote {OUTPUT}")


if __name__ == "__main__":
    main()
