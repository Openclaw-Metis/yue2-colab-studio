# YuE2 Colab 寫歌工作室

在 Google Colab L4 上，用瀏覽器介面操作 [YuE2](https://github.com/multimodal-art-projection/YuE)：輸入曲風與歌詞，得到一首有人聲與伴奏的完整歌曲。可以先看樂譜、改樂譜，再照著改過的版本生成。

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/Openclaw-Metis/yue2-colab-studio/blob/main/YuE2_Colab_Studio.ipynb)

**本專案為非官方工具**，與 YuE2 的作者 M-A-P 沒有從屬關係。使用的是官方未修改的 `yue2-infer` 推論程式。

## 目前狀態：程式完成，尚未在 Colab L4 上實測

請先讀這一段。

- 已完成並通過：211 個不需 GPU 的自動測試（覆蓋率 96%）、`ruff` 檢查，以及用「替身引擎」在瀏覽器中實際操作過的介面流程。
- **尚未做過**：在 Colab L4 上安裝、載入真正的 YuE2、生成任何一首歌。
- 最可能出問題的地方是第一格的安裝。待驗證項目列在 [docs/colab-manual-checklist.md](docs/colab-manual-checklist.md)，已知風險在 [docs/known-issues.md](docs/known-issues.md)。
- 因此本文件沒有任何生成速度或等待時間的數字。實測後會填入 [docs/colab-baseline.md](docs/colab-baseline.md)。

## 需求

- Google Colab，並能選用 **L4 GPU**（需要運算單元；Colab 不保證每次都分配得到）。A100 等更高階的 GPU 會放行，但不在驗收範圍。
- 免費的 **T4 無法使用**：它不支援 YuE2 需要的 BF16 運算，記憶體也不足。第一格會直接擋下並說明。
- 選用：Google 雲端硬碟，用來跨執行階段保存歌曲。

## 啟動

1. 點上方的 Open in Colab 徽章開啟筆記本。
2. 上方選單「執行階段」→「變更執行階段類型」，硬體加速器選 **L4 GPU**。
3. 由上往下執行三格：

   | 格 | 做什麼 | 成功時會看到 |
   |---|---|---|
   | 第一格 | 確認是 L4，安裝 YuE2 與介面套件 | 最後一行「環境檢查通過」 |
   | 第二格 | 選擇歌曲保存位置，產生本次的通行碼 | 保存路徑與通行碼 |
   | 第三格 | 啟動介面 | 一個 `gradio.live` 連結 |

4. 點開連結，帳號輸入 `studio`，密碼輸入第二格顯示的通行碼。
5. 用完之後，回到 Colab 選「執行階段」→「中斷並刪除執行階段」，否則運算單元會繼續被扣。

第二格的 `USE_DRIVE` 勾選後，歌曲會存到 `我的雲端硬碟/YuE2-Studio`，下次開新的執行階段還在。不勾選則只存在這次的執行階段。

## 做一首歌

1. 在「1 寫歌」填**曲風**：語言、音樂類型、樂器、歌聲特色、速度。例如「國語、溫暖的鋼琴流行、女聲、木吉他與輕鼓、88 BPM」。
2. 填**歌詞**，用 `[Verse]`、`[Chorus]` 分段。不知道怎麼開始可以按「填入範例」。
3. 按「生成歌曲」。最上方的狀態列會顯示目前階段。第一次生成要先下載作曲引擎。
4. 完成後自動跳到「3 成品」，可以播放、下載 FLAC，或「打包完整產物」取得包含樂譜與所有設定的壓縮檔。

生成途中可以按「取消」。進入「音訊解碼中」之後就無法取消了。

## 先看樂譜再生成

1. 勾選「先看樂譜再生成」，主按鈕會變成「產生樂譜」。
2. 樂譜寫好後跳到「2 樂譜」，內容是 ABC 文字樂譜。可以直接修改，也可以上傳自己的 `.abc` 或 `.txt` 檔（最多 200 KB）。
3. 按「用這份樂譜生成」。

樂譜上方會標示來源：引擎規劃、你修改過、你上傳的。

## 歌曲庫

每首歌存成一個資料夾，內含官方的完整產物與本工具的紀錄。在「歌曲庫」可以播放、改名稱、寫備註、刪除、打包下載，或「載回表單再做一版」。

```text
<保存位置>/
├── songs/<歌曲編號>/
│   ├── studio.json        曲風、歌詞、設定、耗時、版本
│   └── artifacts/         audio.flac、score.abc 與 YuE2 的其他產物
├── exports/               打包出來的壓縮檔
├── draft.json             還沒送出的表單內容
└── logs/app.log           事件記錄（不含歌詞與曲風內容）
```

## 限制

- 一次只能做一首歌，也只設計給一個人使用。
- 沒有「歌曲長度」「調性」的獨立設定。速度與風格寫在曲風描述裡；旋律、和弦與調性要在樂譜裡調整。
- 不能指定特定歌手的聲音。
- 樂譜只有 Vocal 與 Ins 兩個聲部有作用。
- 改樂譜會重做整首歌，沒改到的地方聽起來也可能不同。
- 歌詞留空不保證沒有人聲。
- 相同的隨機種子不保證做出完全相同的歌。
- 分享連結加通行碼等於你的運算額度，不要隨意分享。
- 第一版不含：翻唱、MP3 下載、五線譜顯示、多人共用。

## 常見問題

| 狀況 | 處理 |
|---|---|
| 第一格顯示「不是 L4」 | 變更執行階段類型為 L4 後重新執行 |
| 第一格安裝失敗 | 選「中斷並刪除執行階段」後重來；仍失敗請附上輸出回報 |
| 連結打不開 | 確認第三格仍在執行；必要時重新執行第二、三格 |
| 忘記通行碼 | 看第二格的輸出 |
| 顯示卡記憶體不足 | 縮短歌詞；或在「環境資訊」按「釋放引擎」後再試 |
| 重開 Colab 後歌曲庫是空的 | 上次沒有勾選 `USE_DRIVE`，無法找回 |
| 出現未預期的錯誤 | 展開頁面下方「環境資訊」，按「產生診斷資訊」，複製後回報。內容不含歌詞 |

## 開發

不需要 GPU。測試使用替身管線，不會下載模型。

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -e ".[dev]"    # Linux、macOS 用 .venv/bin/python
.venv/Scripts/python -m ruff check .
.venv/Scripts/python -m pytest -q
```

在本機看介面（替身引擎產生的是測試音，不是音樂）：

```bash
.venv/Scripts/python -m yue2_studio.launch --stand-in --workdir .studio-data
```

筆記本由 `scripts/build_notebook.py` 產生，請修改腳本後重新產生，不要直接編輯 `.ipynb`。

| 文件 | 內容 |
|---|---|
| [spec/](spec/) | 技術規格、白話規格、分階段開發計畫 |
| [docs/acceptance-matrix.md](docs/acceptance-matrix.md) | 每項驗收條件對應的測試與目前狀態，以及實作與規格的差異 |
| [docs/colab-manual-checklist.md](docs/colab-manual-checklist.md) | 必須在 L4 上手動確認的項目 |
| [docs/colab-baseline.md](docs/colab-baseline.md) | L4 實測數字（尚未量測） |
| [docs/known-issues.md](docs/known-issues.md) | 已知問題與限制 |
| [docs/upgrading-yue2.md](docs/upgrading-yue2.md) | 升級上游版本的步驟 |

程式結構的重點：只有 `src/yue2_studio/engine.py` 會匯入 `yue2`；`studio.py` 放所有介面行為且不依賴 Gradio；`app.py` 只負責版面與事件綁定。

## 授權

- 本專案的程式碼與文件：[Apache-2.0](LICENSE)。
- YuE2 推論程式（`yue2-infer`）：Apache-2.0，版權屬於 YuE2 作者。
- **YuE2 模型權重：CC BY-NC 4.0 加創作者條款。** 依上游說明，個人使用者、內容創作者與音樂人可以使用並從成品獲利；學術研究與教育限非商業用途；公司商業使用需另外向原團隊取得授權。完整條款見上游的 [MODEL_LICENSE](https://github.com/multimodal-art-projection/YuE/blob/main/MODEL_LICENSE)，以該文件為準。

本專案不包含也不散布任何模型權重。第三方元件見 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。

## 致謝

YuE2 由 Multimodal Art Projection（M-A-P）與合作單位開發。論文：[YuE2: Unifying Symbolic and Audio Music Generation at Frontier Quality](https://arxiv.org/abs/2609.33757)。
