# yue2-colab-studio 專案規則

- 規格來源：`spec/01-technical-spec.md`。與本檔衝突時以規格為準，並回報衝突。
- 目標環境只有 Google Colab L4。不加入 T4 相容補丁、不修改 yue2 套件原始碼、不做量化。
- 只有 `src/yue2_studio/engine.py` 可以 import `yue2`。其他模組一律透過 `Engine` 介面。
- 只有 `song_store.py`、`draft_store.py`、`event_log.py` 可以寫入工作目錄。
- `installer.py`、`environment.py`、`notebook_steps.py` 不可 import torch；安裝一律用子行程執行 pip。
- 上游版本以 commit SHA 釘死在 `requirements-colab.txt`，不可改成分支名稱。升級流程見 `docs/upgrading-yue2.md`。
- 所有介面字串放在 `ui_text.py`，使用繁體中文，不使用 emoji。
- 模組名稱要描述職責，不新增 utils、helpers、common、service 這類名稱。
- 測試不得需要 GPU 或網路；用 `yue2_studio.stand_in_pipeline` 取代真實管線。
- notebook 由 `scripts/build_notebook.py` 產生，不要手動編輯 `.ipynb`。
- 每次變更後執行 `ruff check .` 與 `pytest -q`，兩者都要通過。
- 不猜測 yue2 的參數名稱；不確定時讀取釘死 commit 的原始碼確認。
- 「程式完成」與「L4 實測通過」是兩件事。沒有 L4 證據的項目不得標示為通過，見 `docs/colab-manual-checklist.md`。
