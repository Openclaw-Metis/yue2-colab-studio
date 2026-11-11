# 升級上游 YuE2 版本

上游以 commit SHA 釘死。上游 main 變動頻繁，升級請當成一次獨立變更，不要和功能修改混在一起。

## 步驟

1. **選定目標 commit**，讀它與目前釘死版本之間的差異，重點看這三個檔案：

   ```bash
   git clone https://github.com/multimodal-art-projection/YuE.git && cd YuE
   git diff 1116bea76032bee5668e5f097294d082fa0b84f0..<新的 SHA> -- src/yue2/pipeline.py src/yue2/protocol.py pyproject.toml
   ```

2. **對照 `src/yue2_studio/engine.py` 檔頭註解**列出的假設，逐條確認是否仍成立：
   - `from_pretrained` 與 `__call__`、`plan` 的參數名稱
   - `on_token(phase, token)` 的 phase 值（`"abc"`、`"semantic"`）
   - `on_progress(stage, completed, total)` 的 stage 值（`"nar"`、`"vae"`）
   - 取消時拋出 `InterruptedError`
   - `SongResult` 的 `audio`、`sample_rate`、`truncated`、`timing`、`save`、`save_artifacts`

3. **更新釘死的版本**，四個地方要一致：
   - `requirements-colab.txt` 的 SHA
   - `src/yue2_studio/__init__.py` 的 `YUE2_COMMIT`
   - `docs/colab-baseline.md` 的「已釘死的版本」
   - 若上游的 `pyproject.toml` 改了 torch、numpy 或 huggingface-hub 的版本，重新確認 Gradio 相容性：

     ```bash
     pip install --dry-run --ignore-installed gradio "huggingface-hub==<新版本>" "numpy==<新版本>"
     ```

4. **只修改 `engine.py`**（以及必要時的 `stand_in_pipeline.py`，讓替身維持與真實管線相同的呼叫形式）。若需要改到其他模組，代表上游的行為模型變了，先回頭更新規格。

5. **本機檢查**：

   ```bash
   ruff check .
   pytest -q
   ```

6. **L4 實測**：執行 `docs/colab-manual-checklist.md` 的 A、C 兩段，至少包含 `scripts/colab_smoke.py --repeat 5`。

7. **更新紀錄**：`docs/colab-baseline.md` 的數字與日期、`CHANGELOG.md`。

## 模型權重的 revision

`MODEL_REVISION` 與 `VAE_REVISION` 也是釘死的。查目前最新的 revision：

```bash
curl -s https://huggingface.co/api/models/m-a-p/YuE2-3B | python -c "import json,sys; print(json.load(sys.stdin)['sha'])"
curl -s https://huggingface.co/api/models/m-a-p/YuE2-Vae | python -c "import json,sys; print(json.load(sys.stdin)['sha'])"
```

換 revision 之後同樣要重跑 L4 實測。

## 回滾

把上述四處改回前一個 SHA，還原 `engine.py`。歌曲庫的資料格式與上游版本無關，不受影響。
