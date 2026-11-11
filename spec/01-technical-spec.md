# 規格整理 v 1.2.0

專案代號：`yue2-colab-studio`｜規格日期：2026-11-11｜目標硬體：Google Colab L4

## 技術規格文件

### 假設與前提

已確認（使用者決策）：

- 只支援 Colab L4 路線，不做 T4 免費版相容補丁。

採用的合理假設（未經使用者逐項確認，可在開發前推翻）：

| 編號 | 假設 | 推翻時的影響 |
|---|---|---|
| A1 | 首版功能為「寫歌生成」加「樂譜檢視、編輯後再生成」加「歌曲庫」，不含翻唱 | 加翻唱需另建 Python 3.11 + torch 2.8 的 SheetSage2 環境，新增一個 Stage |
| A2 | 歌曲保存位置預設在 runtime 磁碟，可選擇掛載 Google Drive | 若強制 Drive，Stage 4 的掛載流程改為必要步驟 |
| A3 | 交付形式為 GitHub repo 加一本 notebook | 若只要單一 notebook，需把套件程式碼內嵌，維護成本上升 |
| A4 | 單人自用工具，一次只處理一首 | 多人共用需排隊公平性與帳號隔離，超出本規格 |

已查證事實（查證日 2026-11-11）：

| 事實 | 來源 |
|---|---|
| YuE2 官方需求：Linux、Python 3.12、支援 BF16 的 NVIDIA GPU、24 GB VRAM；一次一首；輸出 48 kHz 立體聲 | github.com/multimodal-art-projection/YuE README 與 docs/generation.md |
| RTX 4090 實測峰值 VRAM 11.18 GiB，最長情境 14.08 GiB；建議主機記憶體 24 GB | huggingface.co/m-a-p/YuE2-3B「Speed and resources」 |
| 套件 `yue2-infer` 0.1.6，`requires-python >=3.10`，釘死 `torch==2.10.0`、`transformers==4.57.6`、`huggingface-hub==0.36.2`、`numpy==2.2.6` | repo `pyproject.toml` |
| 上游 main 最新 commit `1116bea76032bee5668e5f097294d082fa0b84f0`（2026-11-01） | repo 首頁 |
| 分段介面 `plan()`、`generate_semantic()`、`synthesize()`、`decode()`；`__call__` 接受 `cancelled`、`on_token`、`on_progress` | repo `src/yue2/pipeline.py` |
| `on_progress(stage, completed, total)`，stage 為 `"nar"` 或 `"vae"` | docs/generation.md |
| 權重授權 CC BY-NC 4.0 加創作者條款；程式碼 Apache-2.0 | repo `MODEL_LICENSE`、`LICENSE` |
| L4 為 Ada Lovelace 架構，約 22.5 GB VRAM，約 1.71 運算單元／小時（第三方量測，非 Google 官方數字） | thundercompute.com 引用 mccormickml.com 2026-03 量測 |
| Colab 預裝的 torchvision 與 torch 2.10 不相容，降版後 transformers 匯入會失敗，需卸載 torchvision、torchaudio | github.com/GLZ-gaoxiaoling/yue2-t4-colab README（社群實測，2026-10） |

未查證風險（由 Stage 0 探測腳本實測後回填）：

- Colab 目前預設 Python 版本與 L4 runtime 的主機記憶體大小。
- 目前 Gradio 版本與 `huggingface-hub==0.36.2`、`numpy==2.2.6` 是否可共存。
- L4 上的實際生成速度；官方沒有 L4 數據，本規格不設未經量測的時間門檻。
- `on_token` callback 的參數形式、請求前置檢查的 Python 函式名稱（只知道 CLI 為 `yue2 validate`）。
- L4 回報的 VRAM 約 22.5 GB，低於官方寫的 24 GB；依實測峰值 14.08 GiB 推斷可行，但需實測確認。

### 背景

YuE2 是 M-A-P 於 2026-09 發布的開源歌曲生成模型，品質與商用服務相近，且會先產出可編輯的旋律與和弦樂譜。官方只提供命令列與 Python 介面，並要求 24 GB 等級的 NVIDIA GPU，沒有這類硬體的人無法使用。

社群已有本機 Gradio 介面（多為 Windows 或 WSL）以及 T4 免費版的補丁方案，但沒有一個專案同時滿足：官方推論程式碼、零補丁、Colab 一鍵啟動、Gradio 操作介面。本專案填補這個空缺，並選擇官方支援範圍內的 L4 作為唯一目標，換取穩定性與低維護成本。

### 目標

| 編號 | 目標 | 可量化成功標準 |
|---|---|---|
| G1 | 在 Colab L4 上用官方未修改的 `yue2-infer` 生成完整歌曲 | 官方範例 `examples/song.json` 在全新 L4 runtime 上生成成功，全程無 OOM，峰值 VRAM 低於 20 GiB |
| G2 | 從開啟 notebook 到看到操作介面，不需要改任何程式碼 | 使用者只需執行 3 個 cell；每個 cell 失敗時都有中文原因與處理方式 |
| G3 | 生成過程可觀察、可取消 | 介面階段文字與進度至少每 2 秒更新一次；按下取消後 30 秒內回到可操作狀態 |
| G4 | 樂譜可檢視、可編輯後再生成 | 編輯過的 ABC 送出後，產物中的 `score.abc` 與送出內容一致 |
| G5 | 成品不因重新整理頁面而遺失 | 重新整理瀏覽器後，歌曲庫與未送出的草稿內容都還在 |

### 範圍

- Colab notebook：環境檢查與安裝、資料位置設定、啟動介面，共 3 個 cell。
- Gradio 介面：寫歌表單、樂譜檢視與編輯、成品播放與下載、歌曲庫。
- 生成模式：`cot="full"`、`"melody"`、`"off"`；可自帶 ABC（貼上或上傳）。
- 歌曲庫：列出、重新命名、刪除、載回表單、打包下載。
- 可選的 Google Drive 保存。
- 不需 GPU 即可執行的單元測試，以及在 Colab 上執行的煙霧測試。

### 不做什麼

- 不支援 T4 與其他不符合 BF16 與 VRAM 門檻的 GPU；偵測到時直接擋下並說明。
- 不做翻唱（SheetSage2 轉譜）、不做器樂專用流程、不做代理人對話式編輯。
- 不修改或打補丁到上游程式碼；不做量化（FP8、GGUF、int8）。
- 不做多人帳號、排隊公平性、計費。
- 不做五線譜或鋼琴捲簾的視覺化編輯器；樂譜以 ABC 文字呈現。
- 不做 MP3 轉檔與混音後製。
- 本專案沒有任何大型語言模型的文字輸出，Streaming 準則不適用；對應的作法是「分階段即時更新進度」。
- 本專案沒有任何圖片縮放功能，等比縮放準則不適用。

### Persona

| Persona | 描述 | 關鍵痛點 | 本專案提供 |
|---|---|---|---|
| 主要使用者：創作者小安 | 會寫歌詞、懂基本曲風詞彙，有 Colab 付費額度，不寫程式 | 沒有 24 GB 顯示卡；命令列安裝會卡在版本衝突 | 三個 cell 啟動、表單操作、看得懂的錯誤訊息 |
| 次要使用者：資料分析師 Oberon | 熟 Python 與 notebook，想比較不同 seed 與樂譜版本 | 官方產物散落各處，難以回頭比對 | 歌曲庫保留完整官方產物與設定，可載回表單重跑 |
| 利害關係人：維護者 | 負責跟上上游改版 | 上游每週都有 commit，介面可能變動 | 釘死 commit、單一轉接模組、假管線測試 |

### 系統說明

系統分成四層。Notebook 層負責安裝與啟動；介面層是 Gradio Blocks 應用；服務層包含環境檢查、生成引擎轉接、歌曲庫與草稿保存；最底層是官方 `yue2-infer` 套件與 Hugging Face 上的權重。

所有對 `yue2` 套件的呼叫集中在 `engine.py` 一個模組，介面層不直接匯入 `yue2`。這樣上游介面變動時只需改一個檔案，測試時也能用假管線替換。歌曲庫以資料夾為單位保存，每首歌一個資料夾，內含官方 `save_artifacts()` 的全部產物與本專案的中繼資料檔，不使用資料庫。

### 核心流程設計

**流程 A：直接生成（預設）**

1. 使用者在「寫歌」分頁填曲風與歌詞，按「生成歌曲」。
2. `request_rules.validate()` 檢查欄位；不通過則在欄位旁顯示原因，不進入生成。
3. 引擎未載入時先載入管線（首次會下載權重）。
4. 呼叫 `engine.render(request, abc=None)`，內部以 `pipe(style, lyrics, cot, seed, ..., cancelled, on_token, on_progress)` 一次完成。
5. 介面依回報依序顯示：作曲規劃、譜寫內容、聲音合成、音訊解碼、保存。
6. `song_store.create()` 建立歌曲資料夾並寫入產物與中繼資料。
7. 自動切到「成品」分頁，顯示播放器、樂譜與下載。

**流程 B：先看樂譜再生成**

1. 使用者勾選「先看樂譜再生成」後按主按鈕（此時按鈕文字為「產生樂譜」）。
2. 呼叫 `engine.plan(request)`，取得 `plan.abc`。
3. 自動切到「樂譜」分頁，ABC 顯示在可編輯文字框。
4. 使用者可直接採用、修改，或上傳自己的 `.abc` 檔取代。
5. 按「用這份樂譜生成」，呼叫 `engine.render(request, abc=編輯後內容)`。依官方指引，編輯後的樂譜以新的 `abc` 輸入送出，不就地修改已保存的 plan。
6. 之後同流程 A 的步驟 5 至 7。

**關鍵分支**

| 分支 | 條件 | 行為 |
|---|---|---|
| 環境不符 | GPU 運算能力低於 8.0 或 VRAM 低於 20 GiB | 第 1 個 cell 即停止，介面不啟動 |
| 取消 | 使用者按「取消」 | 設定取消旗標；引擎於下一個檢查點停止；不建立歌曲；表單內容保留 |
| 截斷 | `result.truncated` 為真 | 仍保存並可播放，成品頁顯示「長度達上限，歌曲可能提前結束」 |
| `cot="off"` 且勾選先看樂譜 | 無樂譜可看 | 勾選框停用並說明原因 |
| 自帶 ABC 但 `cot="off"` | 上游不接受 | 驗證階段擋下，提示改選 full 或 melody |

### 開發應注意重點以及應避開誤區

1. **安裝 cell 不可匯入 torch。** Colab 預先載入的 torch 版本與 YuE2 釘死的 2.10.0 不同，一旦在同一行程匯入舊版再安裝新版，就必須重啟 runtime。安裝一律用子行程執行 `pip`，安裝後才在下一個 cell 匯入。
2. **必須卸載 torchvision 與 torchaudio。** 降版 torch 後不相容的 torchvision 會讓 transformers 匯入時拋出 `RuntimeError`，YuE2 本身不需要這兩個套件。
3. **釘死上游 commit，不追 main。** 上游在 2026-10 下旬到 11 月初每週都有介面層變動。安裝來源固定為 `git+https://github.com/multimodal-art-projection/YuE.git@1116bea76032bee5668e5f097294d082fa0b84f0`，升級時走獨立變更並重跑煙霧測試。
4. **不要用 Gradio 的 `cancels=` 來中止生成。** 那只會丟棄事件，GPU 上的運算仍在跑，下一次請求會撞上「一次一首」的限制。取消一律透過上游的 `cancelled` 可呼叫物件。
5. **管線只載入一次並重複使用。** 每次請求重新 `from_pretrained` 會浪費數十秒並有 VRAM 殘留風險。行程結束或使用者按「釋放引擎」時才呼叫 `close()`。
6. **不要把權重快取放到 Google Drive。** 權重約 8 GB 以上（4B 參數 BF16 的估算值，未實測），免費 Drive 額度 15 GB，而且 Drive 掛載的讀取速度會拖慢載入。Drive 只放歌曲產物。
7. **分享連結是公開網址。** 任何拿到連結的人都能消耗使用者的運算單元並寫入其 Drive，因此預設啟用通行碼。
8. **不要在介面顯示沒有實際作用的控制項。** 上游請求沒有「歌曲長度」「調性」「BPM」的獨立欄位，這些要寫在曲風文字或樂譜裡；介面不提供假的滑桿。
9. **同一個 seed 不保證重現。** 上游文件明示不同 GPU、執行環境、注意力核心都會改變結果；介面文案不可承諾「相同 seed 得到相同歌曲」。

### 任務模型與資訊優先級

#### 任務模型表

| 層級 | 內容 | 為何屬於這一層 | 是否必須首屏支援 |
|---|---|---|---|
| 唯一主目標 | 把曲風與歌詞變成一首可播放的歌 | 所有使用者每次開啟都會做 | 是 |
| 次目標 | 生成前檢視或修改樂譜；聽完後調整再生成 | 是 YuE2 的差異化能力，但不是每次都用 | 否，在第 2 步出現 |
| 低頻目標 | 回頭找舊歌、重新命名、刪除、打包下載 | 累積多首之後才需要 | 否，獨立分頁 |
| 罕見目標 | 調整 seed 與文字引導強度、查看環境與版本、釋放引擎 | 多數人用預設值即可 | 否，收合 |

#### 資訊分類表

| 資訊項目 | 分類 | 使用頻率 | 是否首屏必須 | 不顯示的風險 |
|---|---|---|---|---|
| 曲風輸入框 | action-critical | 高 | 是 | 無法開始 |
| 歌詞輸入框 | action-critical | 高 | 是 | 無法開始 |
| 主按鈕（生成歌曲／產生樂譜） | action-critical | 高 | 是 | 無法開始 |
| 目前階段與進度 | status-feedback | 高 | 是 | 使用者以為當機而關閉頁面 |
| 取消按鈕 | action-critical | 中 | 只在生成中 | 無法止損，浪費運算單元 |
| 「先看樂譜再生成」勾選 | decision-supporting | 中 | 是，緊鄰主按鈕 | 次目標無入口 |
| 規劃方式（cot） | decision-supporting | 低 | 否 | 預設 full 已足夠 |
| seed、文字引導強度 | reference | 低 | 否 | 無 |
| 歌詞段落標記說明 | reference | 低 | 否，欄位旁一行提示 | 新手不知道 `[Verse]` 寫法 |
| 範例曲風與歌詞 | reference | 低 | 否 | 新手空白頁焦慮，以「填入範例」連結緩解 |
| ABC 樂譜文字框 | action-critical | 中 | 只在第 2 步 | 無法編輯樂譜 |
| 播放器與下載 | action-critical | 高 | 只在第 3 步 | 拿不到成品 |
| 截斷警告 | exception-handling | 低 | 只在發生時 | 使用者誤以為歌曲完整 |
| 錯誤訊息與處理建議 | exception-handling | 低 | 只在發生時 | 無法自救 |
| GPU、版本、VRAM 峰值 | reference | 低 | 否 | 回報問題時缺資訊 |
| 歌曲庫清單 | audit-history | 中 | 否 | 找不到舊作 |
| 各階段耗時 | audit-history | 低 | 否 | 無 |

#### 資訊架構表

| 資訊項目 | 使用頻率 | 是否首屏必須 | 所屬任務階段 | 顯示條件 | 建議容器 | 是否可收合 |
|---|---|---|---|---|---|---|
| 曲風、歌詞 | 高 | 是 | empty、drafting | 永遠 | 「寫歌」分頁主區 inline | 否 |
| 主按鈕 | 高 | 是 | drafting | 非生成中 | 主區底部 | 否 |
| 先看樂譜勾選 | 中 | 是 | drafting | cot 不為 off | 主按鈕旁 inline | 否 |
| 狀態列 | 高 | 是 | 全部 | 永遠（空閒時顯示「就緒」） | 頁面頂部單行 | 否 |
| 取消按鈕 | 中 | 否 | generating | 生成中 | 狀態列右側 | 否 |
| 進階設定 | 低 | 否 | drafting | 使用者展開 | accordion | 是，預設收合 |
| 範例 | 低 | 否 | empty | 表單為空時顯示連結 | inline 連結 | 不適用 |
| ABC 編輯框 | 中 | 否 | score_review | 已產生或已上傳樂譜 | 「樂譜」分頁 | 否 |
| 上傳 ABC | 低 | 否 | drafting、score_review | 使用者展開 | 「樂譜」分頁內 accordion | 是 |
| 播放器、下載、成品樂譜 | 高 | 否 | done | 有成品 | 「成品」分頁 | 樂譜可收合 |
| 截斷警告 | 低 | 否 | done | `truncated` 為真 | 成品頁播放器上方 inline | 否 |
| 錯誤面板 | 低 | 否 | failed | 有錯誤 | 狀態列下方 inline | 否 |
| 環境資訊 | 低 | 否 | 任意 | 使用者展開 | 頁尾 accordion | 是，預設收合 |
| 歌曲庫 | 中 | 否 | 任意 | 切換分頁 | 「歌曲庫」分頁 | 否 |

#### Content audit

| 類別 | 內容 |
|---|---|
| must-see-now | 曲風、歌詞、主按鈕、先看樂譜勾選、狀態列 |
| next-step-only | ABC 編輯框與「用這份樂譜生成」；播放器、下載與成品樂譜 |
| error-only | 錯誤面板、截斷警告、欄位驗證訊息 |
| on-demand-reference | 進階設定、環境資訊、各階段耗時、上傳 ABC、歌詞寫法說明 |
| keep-off-first-viewport | 歌曲庫、打包下載、釋放引擎、授權說明全文 |

延後揭露區塊：

| 區塊 | hidden_now_because | reveal_trigger | container |
|---|---|---|---|
| ABC 編輯框 | 還沒有樂譜，空白編輯框會誤導 | `engine.plan` 完成或使用者上傳 ABC | 「樂譜」分頁，完成時自動切換 |
| 播放器與下載 | 還沒有成品 | `song_store.create` 完成 | 「成品」分頁，完成時自動切換 |
| 進階設定 | 預設值對多數人已足夠，露出會增加決策負擔 | 使用者點開 | accordion |
| 上傳 ABC | 罕見用途，且需要懂 ABC | 使用者點開 | accordion |
| 環境資訊 | 只有回報問題時需要 | 使用者點開，或發生錯誤時自動展開 | 頁尾 accordion |
| 取消按鈕 | 空閒時沒有可取消的事 | 進入 generating | 狀態列右側 |
| 錯誤面板 | 沒有錯誤時不佔空間 | 進入 failed | 狀態列下方 |
| 歌曲庫 | 與當下「做一首歌」無關 | 使用者切換分頁 | 獨立分頁 |

### 狀態模型與揭露策略

#### 狀態矩陣

| State | 進入條件 | 使用者此刻目標 | 必顯資訊 | 隱藏資訊 | 主 CTA | 離開條件 |
|---|---|---|---|---|---|---|
| empty | 首次開啟且無草稿，或按了「重新開始」 | 知道要填什麼 | 空白表單、填入範例連結、狀態「就緒」 | 樂譜與成品內容、取消、錯誤 | 生成歌曲（停用，直到曲風有內容） | 任一欄位有輸入 |
| drafting | 表單有內容 | 寫好曲風與歌詞 | 表單、先看樂譜勾選 | 取消、錯誤 | 生成歌曲／產生樂譜 | 按主按鈕 |
| generating | 驗證通過並開始執行 | 等待並確認有在進行 | 階段名稱、進度、已耗時、取消 | 主按鈕（停用）、進階設定鎖定 | 取消 | 完成、失敗或取消 |
| score_review | `engine.plan` 完成，或使用者上傳了 ABC | 決定樂譜要不要改 | ABC 編輯框、樂譜來源標示 | 成品內容 | 用這份樂譜生成 | 按 CTA，或回「寫歌」修改 |
| done | 歌曲已保存 | 聽歌、下載、決定是否再做一版 | 播放器、下載、截斷警告（若有） | 取消 | 以此為基礎再做一版 | 按「再做一版」或「重新開始」 |
| failed | 驗證失敗以外的任何錯誤 | 知道原因並重試 | 錯誤面板（原因、處理建議、錯誤代碼）、表單保留 | 進度 | 重試 | 按重試或修改表單 |

狀態對應到範本的等價關係：`generating` 等同 validating，`score_review` 等同 resolved，`failed` 等同 blocked，`done` 等同 submitted。

#### Progressive disclosure 規則

- 首屏只有三個視覺群組：頂部狀態列、表單主區、主按鈕列。
- 首屏只有一個主 CTA；取消是次要樣式，且只在生成中出現。
- 進階設定與環境資訊預設收合。
- 錯誤面板與截斷警告只在對應狀態出現，離開該狀態即消失。
- 欄位說明寫在欄位標籤下方一行，不另做說明卡。
- 分頁標題帶步驟編號（1 寫歌、2 樂譜、3 成品），歌曲庫不編號，表示它不屬於主流程。

#### 容器策略

| 容器 | 放什麼 | 理由 |
|---|---|---|
| tab | 寫歌、樂譜、成品、歌曲庫 | 流程有明顯三階段，分頁避免單頁過長 |
| accordion | 進階設定、上傳 ABC、環境資訊、成品頁的樂譜全文 | 低頻參考資訊 |
| inline helper | 欄位說明、驗證訊息、截斷警告 | 緊貼相關元件 |
| modal（瀏覽器確認框） | 刪除歌曲確認、重新開始確認 | 不可復原的動作 |
| toast（`gr.Info`、`gr.Warning`） | 已保存、已取消、已複製 | 不需要停留的回饋 |

### UI 風格定調與色彩策略

風格走向：**專業工具感，安靜、可靠**。這是在付費運算資源上執行的長時間任務，介面要讓人放心等待，不走娛樂化視覺。淺色模式。

| 角色 | 色碼 | 負責場景 | 使用規則 |
|---|---|---|---|
| 主色 深藍 | `#2F5D8C` | 主 CTA、目前分頁標示、連結 | 每個畫面只用在一個按鈕上 |
| 輔色 淺藍灰 | `#E8EEF5` | 狀態列底色、面板底色、收合區標題列 | 只作底色，不承載文字以外的意義 |
| 中性色 墨灰 | `#1F2933` 文字，`#6B7785` 次要文字，`#FFFFFF` 頁面底 | 內文與說明 | 對比度至少 4.5:1 |
| 強調色 琥珀 | `#E07A1F` | 生成中的階段標示、進度條、截斷警告 | 只表示「進行中」或「需要留意」，不用在按鈕 |
| 錯誤色 | `#B42318` | 錯誤面板邊框與標題、欄位驗證訊息 | 只在 failed 與驗證失敗出現 |

實作方式：以 `gr.themes.Base` 衍生主題，設定 `primary_hue` 與上表色碼；自訂 CSS 控制在 60 行以內，只處理狀態列與錯誤面板。

### 專案目錄規劃

```text
yue2-colab-studio/
├── YuE2_Colab_Studio.ipynb        # 唯一入口，3 個 cell
├── pyproject.toml                 # 套件定義、ruff 與 pytest 設定
├── requirements-colab.txt         # 釘死版本：yue2-infer 的 commit、gradio
├── README.md
├── LICENSE                        # Apache-2.0
├── THIRD_PARTY_NOTICES.md         # YuE2 程式碼與權重授權
├── src/yue2_studio/
│   ├── __init__.py                # 版本字串
│   ├── environment.py             # GPU 門檻檢查、環境報告
│   ├── installer.py               # 以子行程安裝與卸載套件，不匯入 torch
│   ├── request_rules.py           # 表單欄位驗證與正規化
│   ├── engine.py                  # 唯一匯入 yue2 的模組；載入、plan、render、close
│   ├── generation_job.py          # 單一工作狀態、取消旗標、階段事件
│   ├── song_store.py              # 歌曲資料夾的建立、列出、改名、刪除、打包
│   ├── draft_store.py             # 表單草稿的讀寫與清除
│   ├── event_log.py               # JSON Lines 事件記錄
│   ├── ui_text.py                 # 所有繁體中文介面字串與錯誤訊息
│   ├── theme.py                   # Gradio 主題與 CSS
│   └── app.py                     # Gradio Blocks 組裝與事件綁定
├── tests/
│   ├── fake_pipeline.py           # 模擬 YuE2Pipeline 的假管線
│   ├── test_environment.py
│   ├── test_request_rules.py
│   ├── test_engine.py
│   ├── test_generation_job.py
│   ├── test_song_store.py
│   ├── test_draft_store.py
│   └── test_app_flows.py          # 以假管線驅動介面事件函式
├── scripts/
│   └── colab_smoke.py             # 在 L4 上跑官方範例並輸出量測結果
└── docs/
    ├── colab-baseline.md          # L4 實測基準（Stage 0、Stage 1 回填）
    └── upgrading-yue2.md          # 升級上游 commit 的步驟
```

| 目錄 | 責任 | 命名原則 |
|---|---|---|
| 根目錄 | 入口 notebook 與套件設定 | notebook 用專案名；不放其他 notebook |
| `src/yue2_studio/` | 所有執行期程式碼 | 模組名描述職責（`song_store`、`request_rules`），不用 `utils`、`helpers`、`common` |
| `tests/` | 不需 GPU 的測試 | `test_<模組名>.py`，一個模組一個檔 |
| `scripts/` | 需要真實 GPU 的手動腳本 | 動詞或用途開頭 |
| `docs/` | 實測基準與維護步驟 | 小寫連字號 |

切分理由：`engine.py` 是唯一接觸上游的邊界；`song_store.py` 與 `draft_store.py` 是唯一接觸磁碟的邊界；`app.py` 只做組裝，不含商業規則。三個邊界都能用假物件替換，因此測試不需要 GPU。

### 前後端模組

本專案沒有獨立的前端工程；介面由 Gradio 產生。模組分層如下。

| 層 | 模組 | 輸入 | 輸出 | 依賴 |
|---|---|---|---|---|
| 介面層 | `app.py`、`theme.py`、`ui_text.py` | 使用者操作 | 元件更新 | 服務層全部 |
| 服務層 | `request_rules.py` | 原始表單值 | `SongRequest` 或 `ValidationError` 清單 | 無 |
| 服務層 | `generation_job.py` | 請求、引擎 | 階段事件的產生器 | `engine` |
| 服務層 | `song_store.py`、`draft_store.py` | 請求、結果、工作目錄 | 歌曲紀錄、草稿 | 檔案系統 |
| 服務層 | `environment.py`、`installer.py` | 無 | `EnvironmentReport` | `nvidia-smi`、`pip` 子行程 |
| 轉接層 | `engine.py` | `SongRequest`、ABC 文字 | `PlanDraft`、`SongResult` | `yue2` |
| 外部 | `yue2-infer`、Hugging Face Hub、Google Drive | | | |

### 模組架構圖（SVG）

```svg
<svg viewBox="0 0 1200 720" xmlns="http://www.w3.org/2000/svg" font-family="sans-serif" font-size="16">
  <rect width="1200" height="720" fill="#FFFFFF"/>
  <defs><marker id="a" markerWidth="10" markerHeight="8" refX="9" refY="4" orient="auto"><path d="M0,0 L10,4 L0,8 z" fill="#1F2933"/></marker></defs>

  <rect x="30" y="30" width="1140" height="110" rx="8" fill="#E8EEF5" stroke="#2F5D8C"/>
  <text x="50" y="60" font-weight="bold" fill="#1F2933">Notebook 層（YuE2_Colab_Studio.ipynb）</text>
  <rect x="60" y="78" width="300" height="46" rx="6" fill="#FFFFFF" stroke="#6B7785"/><text x="80" y="107" fill="#1F2933">Cell 1 檢查與安裝</text>
  <rect x="450" y="78" width="300" height="46" rx="6" fill="#FFFFFF" stroke="#6B7785"/><text x="470" y="107" fill="#1F2933">Cell 2 資料位置與通行碼</text>
  <rect x="840" y="78" width="300" height="46" rx="6" fill="#FFFFFF" stroke="#6B7785"/><text x="860" y="107" fill="#1F2933">Cell 3 啟動介面</text>

  <rect x="30" y="170" width="1140" height="110" rx="8" fill="#FFFFFF" stroke="#2F5D8C" stroke-width="2"/>
  <text x="50" y="200" font-weight="bold" fill="#1F2933">介面層（Gradio）</text>
  <rect x="60" y="216" width="520" height="46" rx="6" fill="#2F5D8C"/><text x="80" y="245" fill="#FFFFFF">app.py：分頁、事件綁定、狀態列</text>
  <rect x="620" y="216" width="250" height="46" rx="6" fill="#E8EEF5" stroke="#6B7785"/><text x="640" y="245" fill="#1F2933">ui_text.py 介面字串</text>
  <rect x="900" y="216" width="240" height="46" rx="6" fill="#E8EEF5" stroke="#6B7785"/><text x="920" y="245" fill="#1F2933">theme.py 主題</text>

  <rect x="30" y="310" width="1140" height="170" rx="8" fill="#FFFFFF" stroke="#2F5D8C"/>
  <text x="50" y="340" font-weight="bold" fill="#1F2933">服務層</text>
  <rect x="60" y="356" width="250" height="46" rx="6" fill="#E8EEF5" stroke="#6B7785"/><text x="76" y="385" fill="#1F2933">request_rules 欄位驗證</text>
  <rect x="340" y="356" width="270" height="46" rx="6" fill="#E8EEF5" stroke="#6B7785"/><text x="356" y="385" fill="#1F2933">generation_job 工作與取消</text>
  <rect x="640" y="356" width="240" height="46" rx="6" fill="#E8EEF5" stroke="#6B7785"/><text x="656" y="385" fill="#1F2933">song_store 歌曲庫</text>
  <rect x="910" y="356" width="230" height="46" rx="6" fill="#E8EEF5" stroke="#6B7785"/><text x="926" y="385" fill="#1F2933">draft_store 草稿</text>
  <rect x="60" y="418" width="250" height="46" rx="6" fill="#E8EEF5" stroke="#6B7785"/><text x="76" y="447" fill="#1F2933">environment 環境檢查</text>
  <rect x="340" y="418" width="270" height="46" rx="6" fill="#E8EEF5" stroke="#6B7785"/><text x="356" y="447" fill="#1F2933">installer 安裝（子行程）</text>
  <rect x="640" y="418" width="500" height="46" rx="6" fill="#E8EEF5" stroke="#6B7785"/><text x="656" y="447" fill="#1F2933">event_log 事件記錄（JSON Lines）</text>

  <rect x="30" y="510" width="560" height="80" rx="8" fill="#FFFFFF" stroke="#E07A1F" stroke-width="2"/>
  <text x="50" y="540" font-weight="bold" fill="#1F2933">轉接層 engine.py</text>
  <text x="50" y="568" fill="#6B7785">唯一匯入 yue2 的模組：load / plan / render / close</text>

  <rect x="30" y="620" width="270" height="70" rx="8" fill="#E8EEF5" stroke="#6B7785"/><text x="50" y="662" fill="#1F2933">yue2-infer（釘死 commit）</text>
  <rect x="320" y="620" width="270" height="70" rx="8" fill="#E8EEF5" stroke="#6B7785"/><text x="340" y="662" fill="#1F2933">Hugging Face 權重</text>
  <rect x="640" y="510" width="530" height="180" rx="8" fill="#FFFFFF" stroke="#6B7785"/>
  <text x="660" y="540" font-weight="bold" fill="#1F2933">儲存</text>
  <text x="660" y="572" fill="#1F2933">工作目錄 /content/yue2_studio_data</text>
  <text x="660" y="600" fill="#1F2933">或 Google Drive：MyDrive/YuE2-Studio</text>
  <text x="660" y="634" fill="#6B7785">songs/&lt;song_id&gt;/、draft.json、logs/app.log</text>
  <text x="660" y="662" fill="#6B7785">權重快取固定在 /content/hf_cache</text>

  <line x1="600" y1="140" x2="600" y2="170" stroke="#1F2933" marker-end="url(#a)"/>
  <line x1="320" y1="262" x2="320" y2="310" stroke="#1F2933" marker-end="url(#a)"/>
  <line x1="475" y1="402" x2="310" y2="510" stroke="#1F2933" marker-end="url(#a)"/>
  <line x1="760" y1="402" x2="760" y2="510" stroke="#1F2933" marker-end="url(#a)"/>
  <line x1="165" y1="590" x2="165" y2="620" stroke="#1F2933" marker-end="url(#a)"/>
  <line x1="455" y1="590" x2="455" y2="620" stroke="#1F2933" marker-end="url(#a)"/>
</svg>
```

### 使用流程

1. 在 Colab 開啟 notebook，於「執行階段」選擇 L4 GPU。
2. 執行 Cell 1。看到環境報告與「環境檢查通過」。首次約需數分鐘安裝套件。
3. 執行 Cell 2。選擇是否保存到 Google Drive；畫面顯示本次通行碼。
4. 執行 Cell 3。點開輸出的連結，輸入通行碼。
5. 在「1 寫歌」填曲風與歌詞，按「生成歌曲」。首次生成會下載權重並載入引擎。
6. 等待狀態列跑完各階段，頁面自動切到「3 成品」。
7. 播放、下載，或按「以此為基礎再做一版」回到表單。
8. 要調整旋律時，勾選「先看樂譜再生成」，在「2 樂譜」修改後再生成。
9. 結束時回到 Colab 中斷執行階段，避免持續消耗運算單元。

### 功能清單（含 CRUD 與 state）

| 編號 | 功能 | 輸入 | 輸出 | 狀態變化 |
|---|---|---|---|---|
| F1 | 環境檢查 | 無 | `EnvironmentReport` | 不通過則停止 |
| F2 | 安裝相依套件 | `requirements-colab.txt` | 安裝紀錄 | 失敗則停止並顯示最後 30 行輸出 |
| F3 | 載入引擎 | 環境報告 | 已載入的管線 | 引擎 `unloaded → loading → ready`；失敗為 `error` |
| F4 | 驗證請求 | 表單值 | `SongRequest` 或錯誤清單 | 失敗時停留在 drafting |
| F5 | 產生樂譜 | `SongRequest` | `PlanDraft`（ABC 文字、是否截斷、耗時） | 工作 `planning → score_ready` |
| F6 | 生成歌曲 | `SongRequest`、可選 ABC | `SongResult` | 工作依階段前進到 `done` |
| F7 | 取消生成 | 無 | 無 | 工作 `→ cancelled` |
| F8 | 歌曲：建立 | 請求、結果 | 歌曲資料夾 | 歌曲 `saved` |
| F9 | 歌曲：列出與檢視 | 無或 `song_id` | 歌曲紀錄清單或單筆 | 無 |
| F10 | 歌曲：修改 | `song_id`、新標題、備註 | 更新後紀錄 | `updated_at` 更新 |
| F11 | 歌曲：刪除 | `song_id`、使用者確認 | 無 | 資料夾移除 |
| F12 | 歌曲：載回表單 | `song_id` | 草稿被該歌曲的請求覆寫 | 介面回到 drafting |
| F13 | 歌曲：打包下載 | `song_id` | zip 檔 | 無 |
| F14 | 草稿：建立與修改 | 表單值 | `draft.json` | 欄位失焦或變動後 1 秒內寫入 |
| F15 | 草稿：刪除（重新開始） | 使用者確認 | 無 | 介面回到 empty |
| F16 | 上傳 ABC | `.abc` 或 `.txt` 檔 | 內容載入編輯框作為預覽 | 介面進入 score_review |
| F17 | 釋放引擎 | 無 | VRAM 釋放 | 引擎 `ready → unloaded` |

物件的 CRUD 覆蓋：

| 物件 | Create | Read | Update | Delete |
|---|---|---|---|---|
| 歌曲 | F8 | F9 | F10 | F11 |
| 草稿 | F14 | 開啟時自動載入 | F14 | F15 |
| 樂譜（編輯中的 ABC） | F5、F16 | 編輯框 | 直接編輯 | 「清除樂譜」按鈕，回到由引擎規劃 |

### G3M

| 項目 | 內容 |
|---|---|
| Goal | 讓沒有 24 GB 顯示卡的人，用 Colab L4 與官方未修改的 YuE2 做出歌曲 |
| Signal | 使用者完成一次從表單到可播放成品的流程；能回頭找到舊作 |
| Metric 1 | 全新 L4 runtime 上官方範例生成成功率：連續 5 次全部成功 |
| Metric 2 | 生成中介面更新間隔不超過 2 秒 |
| Metric 3 | 取消後 30 秒內可再次送出 |
| Metric 4 | 不需 GPU 的測試全數通過，`engine.py` 以外的模組行覆蓋率 80% 以上 |
| Metric 5 | 啟動到介面可用的時間與每首歌耗時，記錄於 `docs/colab-baseline.md`（先量測，不預設門檻） |

### UI 設計

主畫面的視覺重點是表單主區的主按鈕；狀態列是唯一的狀態區，永遠在頂部同一位置。版面密度偏低：寫歌分頁只有兩個輸入框、一個勾選框、一個按鈕與一個收合區，在 1366 x 768 的視窗內不需捲動。

歌詞框預設 12 行，可拉高。曲風框 3 行。兩個輸入框都顯示字數與上限。主按鈕在曲風為空時停用，並在下方顯示一行「請先填寫曲風」。

### UI 元件清單

| 元件 id | Gradio 類型 | 用途 | 關鍵屬性 | 互動 |
|---|---|---|---|---|
| `status_bar` | `gr.HTML` | 階段、進度、已耗時 | 內含進度條 | 由生成事件串流更新 |
| `cancel_btn` | `gr.Button`（secondary） | 取消 | 只在生成中可見 | 設定取消旗標 |
| `error_panel` | `gr.HTML` | 錯誤原因、建議、代碼 | 只在 failed 可見 | 內含「重試」 |
| `tabs` | `gr.Tabs` | 四個分頁 | `selected` 可由程式切換 | |
| `style_box` | `gr.Textbox` | 曲風 | 3 行，上限 1000 字 | 變動時存草稿 |
| `lyrics_box` | `gr.Textbox` | 歌詞 | 12 行，上限 5000 字 | 變動時存草稿 |
| `fill_example_link` | `gr.Button`（link 樣式） | 填入範例 | 只在表單為空時可見 | 填入官方範例內容 |
| `score_first_chk` | `gr.Checkbox` | 先看樂譜再生成 | cot 為 off 時停用 | 切換主按鈕文字 |
| `primary_btn` | `gr.Button`（primary） | 生成歌曲／產生樂譜 | 曲風為空時停用 | 觸發 F4、F5 或 F6 |
| `advanced_acc` | `gr.Accordion` | 進階設定 | 預設收合 | |
| `cot_radio` | `gr.Radio` | 規劃方式 | 旋律加和弦（預設）、只規劃旋律、不規劃 | |
| `seed_box` | `gr.Number` | 亂數種子 | 空白表示隨機；0 到 2147483647 | |
| `cfg_slider` | `gr.Slider` | 文字引導強度 | 1.0 到 2.0，步進 0.05；「使用預設」勾選時停用 | |
| `abc_editor` | `gr.Code` 或 `gr.Textbox` | ABC 樂譜 | 等寬字型，20 行 | 直接編輯 |
| `abc_source_label` | `gr.Markdown` | 樂譜來源 | 引擎規劃、你修改過、你上傳的 | |
| `abc_upload` | `gr.File` | 上傳 ABC | 限 `.abc`、`.txt`，200 KB | 內容載入 `abc_editor` 預覽 |
| `abc_clear_btn` | `gr.Button` | 清除樂譜 | | 清空編輯框 |
| `render_from_score_btn` | `gr.Button`（primary） | 用這份樂譜生成 | 編輯框為空時停用 | 觸發 F6 |
| `result_audio` | `gr.Audio` | 播放成品 | `type="filepath"`，不可編輯 | |
| `truncated_notice` | `gr.Markdown` | 截斷警告 | 只在截斷時可見 | |
| `download_flac` | `gr.DownloadButton` | 下載音訊 | | |
| `download_zip` | `gr.DownloadButton` | 下載完整產物 | | 觸發 F13 |
| `result_score` | `gr.Code` 於 accordion | 成品樂譜 | 唯讀 | |
| `remix_btn` | `gr.Button`（primary） | 以此為基礎再做一版 | | 觸發 F12 |
| `restart_btn` | `gr.Button` | 重新開始 | 需確認 | 觸發 F15 |
| `library_table` | `gr.Dataframe` | 歌曲清單 | 標題、建立時間、長度、規劃方式、seed | 選列後顯示詳情 |
| `library_detail` | `gr.Group` | 選中歌曲的播放、改名、刪除、載回 | 未選取時隱藏 | 觸發 F10 至 F13 |
| `env_acc` | `gr.Accordion` | 環境資訊 | 預設收合；錯誤時自動展開 | 內含「釋放引擎」 |

### 分步導覽策略

採用 `gr.Tabs`，前三個分頁對應三個階段並帶編號。理由：三個階段的必顯資訊完全不同，放在同一頁會超過三個視覺群組；分頁讓使用者可以隨時回上一步修改，比線性 wizard 自由。階段完成時由程式自動切換分頁，使用者不需要自己找下一步在哪裡。未達條件的分頁仍可點選，但顯示一行空狀態說明（例如「還沒有樂譜。回到 1 寫歌，勾選先看樂譜再生成」）。

### 主要畫面示意（SVG）

```svg
<svg viewBox="0 0 1440 960" xmlns="http://www.w3.org/2000/svg" font-family="sans-serif" font-size="18">
  <rect width="1440" height="960" fill="#FFFFFF"/>
  <rect x="40" y="30" width="1360" height="64" rx="8" fill="#E8EEF5"/>
  <circle cx="76" cy="62" r="9" fill="#E07A1F"/>
  <text x="100" y="68" fill="#1F2933" font-weight="bold">譜寫內容中</text>
  <rect x="260" y="54" width="700" height="16" rx="8" fill="#FFFFFF" stroke="#6B7785"/>
  <rect x="260" y="54" width="330" height="16" rx="8" fill="#E07A1F"/>
  <text x="980" y="68" fill="#6B7785">已耗時 01:42</text>
  <rect x="1260" y="44" width="120" height="36" rx="6" fill="#FFFFFF" stroke="#6B7785"/><text x="1298" y="68" fill="#1F2933">取消</text>

  <rect x="40" y="120" width="180" height="48" rx="6" fill="#2F5D8C"/><text x="84" y="151" fill="#FFFFFF">1 寫歌</text>
  <rect x="230" y="120" width="180" height="48" rx="6" fill="#FFFFFF" stroke="#6B7785"/><text x="274" y="151" fill="#1F2933">2 樂譜</text>
  <rect x="420" y="120" width="180" height="48" rx="6" fill="#FFFFFF" stroke="#6B7785"/><text x="464" y="151" fill="#1F2933">3 成品</text>
  <rect x="1220" y="120" width="180" height="48" rx="6" fill="#FFFFFF" stroke="#6B7785"/><text x="1272" y="151" fill="#1F2933">歌曲庫</text>

  <rect x="40" y="190" width="1360" height="600" rx="8" fill="#FFFFFF" stroke="#6B7785"/>
  <text x="70" y="232" fill="#1F2933" font-weight="bold">曲風</text>
  <text x="130" y="232" fill="#6B7785" font-size="15">語言、類型、樂器、人聲特色、速度，例如 88 BPM</text>
  <rect x="70" y="246" width="1300" height="90" rx="6" fill="#FFFFFF" stroke="#6B7785"/>
  <text x="1280" y="358" fill="#6B7785" font-size="14">86 / 1000</text>

  <text x="70" y="394" fill="#1F2933" font-weight="bold">歌詞</text>
  <text x="130" y="394" fill="#6B7785" font-size="15">用 [Verse]、[Chorus] 標示段落；留空可嘗試純音樂</text>
  <rect x="70" y="408" width="1300" height="260" rx="6" fill="#FFFFFF" stroke="#6B7785"/>
  <text x="90" y="442" fill="#6B7785">[Verse]</text>
  <text x="1270" y="690" fill="#6B7785" font-size="14">214 / 5000</text>

  <rect x="70" y="712" width="22" height="22" rx="3" fill="#FFFFFF" stroke="#1F2933"/>
  <text x="104" y="730" fill="#1F2933">先看樂譜再生成</text>
  <rect x="1130" y="700" width="240" height="56" rx="8" fill="#2F5D8C"/><text x="1198" y="735" fill="#FFFFFF" font-weight="bold">生成歌曲</text>

  <rect x="40" y="810" width="1360" height="50" rx="8" fill="#E8EEF5"/><text x="70" y="842" fill="#1F2933">進階設定（規劃方式、亂數種子、文字引導強度）</text><text x="1350" y="842" fill="#6B7785">▸</text>
  <rect x="40" y="874" width="1360" height="50" rx="8" fill="#E8EEF5"/><text x="70" y="906" fill="#1F2933">環境資訊</text><text x="1350" y="906" fill="#6B7785">▸</text>
</svg>
```

### 非功能需求

| 類別 | 需求 |
|---|---|
| 效能 | 不重複載入管線；介面更新間隔不超過 2 秒；歌曲庫 200 首以內列出時間低於 1 秒。生成耗時不設門檻，以 `docs/colab-baseline.md` 的實測為準 |
| 資源 | 峰值 VRAM 低於 20 GiB；`memory_budget_gib` 依偵測到的 VRAM 設定，保留上游預設的 2 GiB 餘量；不啟用 `low_vram` |
| 可靠性 | 任何生成失敗都不得讓介面卡在 generating；例外一律轉為 failed 並釋放取消旗標。中途失敗不留下半成品歌曲資料夾（先寫暫存資料夾，成功後改名） |
| 安全性 | 分享連結預設需要通行碼（每次啟動隨機產生 12 字元，顯示在 notebook 輸出）；上傳檔案只接受指定副檔名與大小，以 UTF-8 文字讀取，不執行；`song_id` 只允許 `[a-z0-9-]`，所有路徑組合後必須位於工作目錄內；不記錄歌詞全文到事件記錄 |
| 可用性 | 全繁體中文介面；錯誤訊息包含原因、下一步、錯誤代碼三部分；主要流程在 1366 x 768 內不需捲動 |
| 可維護性 | 只有 `engine.py` 匯入 `yue2`；上游版本以 commit SHA 釘死；ruff 檢查零錯誤 |
| 相容性 | 只保證 Colab L4；A100 等符合門檻的 GPU 會放行但不列入驗收 |
| 授權 | README 與介面頁尾標示權重為 CC BY-NC 4.0 加創作者條款，連結到上游 `MODEL_LICENSE` |

### 核心資料模型

**SongRequest**（記憶體物件，也寫入歌曲中繼資料）

| 欄位 | 型別 | 規則 |
|---|---|---|
| `style` | str | 去頭尾空白後 1 到 1000 字 |
| `lyrics` | str | 0 到 5000 字；可為空 |
| `cot` | `"full"`、`"melody"`、`"off"` | 預設 `"full"` |
| `seed` | int 或 None | 0 到 2147483647；None 表示由本專案產生隨機值並記錄 |
| `cfg_scale` | float 或 None | 1.0 到 2.0；None 表示不傳，使用上游預設 |
| `abc` | str 或 None | 有值時 `cot` 不可為 `"off"`；上限 200 KB |

字數上限是本專案的保護性限制，不是上游限制。

**SongRecord**（`songs/<song_id>/studio.json`）

| 欄位 | 型別 | 說明 |
|---|---|---|
| `schema_version` | int | 目前為 1 |
| `song_id` | str | 主鍵。格式 `YYYYMMDD-HHMMSS-<4 位隨機>`，例如 `20261111-143005-k3f9` |
| `title` | str | 預設取曲風前 30 字；可修改，1 到 80 字 |
| `note` | str | 使用者備註，0 到 500 字 |
| `created_at`、`updated_at` | ISO 8601 字串 | UTC |
| `request` | SongRequest | 實際送出的請求，含最終 seed |
| `abc_source` | `"planned"`、`"edited"`、`"uploaded"`、`"none"` | 樂譜來源 |
| `parent_song_id` | str 或 None | 由哪首歌「再做一版」而來 |
| `duration_sec` | float | 由音訊長度計算 |
| `truncated` | bool | 來自 `result.truncated` |
| `timing` | dict | 各階段秒數，來自 `result.timing` |
| `peak_vram_gib` | float | `torch.cuda.max_memory_allocated` 換算 |
| `versions` | dict | 本專案版本、yue2 commit、torch 版本、模型與 VAE 的 revision、GPU 名稱 |

**歌曲資料夾結構**

```text
songs/20261111-143005-k3f9/
├── studio.json          # SongRecord
└── artifacts/           # 官方 save_artifacts() 的完整輸出
    ├── audio.flac
    ├── score.abc        # cot 不為 off 時存在
    ├── plan.json
    ├── latent.npy
    ├── result.json
    └── ...
```

**Draft**（`draft.json`）：`schema_version`、`style`、`lyrics`、`cot`、`seed`、`cfg_scale`、`score_first`、`abc_text`、`abc_source`、`updated_at`。

**關聯與查詢**：歌曲之間只有 `parent_song_id` 的單向關聯，父歌曲被刪除時子歌曲保留該欄位值但介面顯示「來源已刪除」。歌曲庫預設依 `created_at` 由新到舊排序。沒有自動清理；容量由使用者自行管理，環境資訊區顯示工作目錄總大小。

### State 管理與持久化

| 狀態 | 存放位置 | 生命週期 | 恢復方式 |
|---|---|---|---|
| 表單內容、樂譜編輯內容 | `draft.json` | 跨頁面重整；使用 Drive 時跨 runtime | 頁面載入時 `draft_store.load()` 填回 |
| 目前工作（階段、進度、取消旗標） | 行程記憶體，單一 `GenerationJob` 物件 | 行程存活期間 | 頁面重整後由 `demo.load` 讀取並接續顯示 |
| 引擎（已載入的管線） | 行程記憶體，模組層級單例 | 行程存活期間 | 不恢復；runtime 重啟後首次生成重新載入 |
| 歌曲 | `songs/` 資料夾 | 永久，直到使用者刪除或 runtime 磁碟被回收 | 歌曲庫掃描資料夾 |
| 目前分頁、收合狀態 | 瀏覽器 | 該頁面 | 不恢復 |
| 權重快取 | `/content/hf_cache` | runtime 存活期間 | 重新下載 |

「以專案形式開啟並繼續編輯」的對應：工作目錄就是專案。選擇 Google Drive 時，下次開新的 runtime 並掛載同一個資料夾，草稿與歌曲庫完整恢復。沒有選擇 Drive 時，runtime 回收後資料消失，Cell 2 與介面頁尾都明確提示這一點。

衝突處理：單人單頁面使用為前提。若同時開兩個分頁，草稿以最後寫入者為準；生成工作同時只有一個，第二個請求會收到「目前有歌曲正在生成」。

資料升級：`schema_version` 不符時，讀取函式以預設值補齊缺少的欄位並保留未知欄位；無法解析的 `studio.json` 不讓歌曲庫整體失敗，該筆顯示為「無法讀取」並可刪除。

### API 設計

本專案不提供 HTTP API（Gradio 自動產生的端點以 `show_api=False` 關閉）。以下為模組間的 Python 介面，屬於穩定介面，變更需同步更新測試。

```python
# environment.py
@dataclass(frozen=True)
class EnvironmentReport:
    gpu_name: str | None
    compute_capability: tuple[int, int] | None
    vram_total_gib: float
    ram_total_gib: float
    python_version: str
    ok: bool
    problems: list[str]          # ui_text 的訊息鍵

def probe() -> EnvironmentReport: ...
# 門檻：compute_capability >= (8, 0) 且 vram_total_gib >= 20.0

# request_rules.py
def validate(raw: dict) -> SongRequest: ...      # 失敗時拋出 ValidationFailed(errors: list[FieldError])

# engine.py
class Engine:
    def load(self, on_status: Callable[[str], None]) -> None: ...
    def plan(self, request: SongRequest, *, cancelled: Callable[[], bool]) -> PlanDraft: ...
    def render(self, request: SongRequest, *, abc: str | None,
               cancelled: Callable[[], bool],
               on_stage: Callable[[StageEvent], None]) -> RenderOutcome: ...
    def close(self) -> None: ...

@dataclass(frozen=True)
class PlanDraft:
    abc: str
    truncated: bool
    seconds: float

@dataclass(frozen=True)
class StageEvent:
    stage: Literal["loading", "planning", "composing", "rendering", "decoding", "saving"]
    completed: int | None        # 無法得知總量時為 None
    total: int | None

@dataclass(frozen=True)
class RenderOutcome:
    result: Any                  # yue2 的 SongResult
    peak_vram_gib: float

# generation_job.py
def run_plan(raw_form: dict) -> Iterator[JobUpdate]: ...
def run_render(raw_form: dict, abc: str | None) -> Iterator[JobUpdate]: ...
def cancel() -> None: ...
def current() -> JobUpdate: ...

# song_store.py
def create(outcome: RenderOutcome, request: SongRequest, *, abc_source: str,
           parent_song_id: str | None) -> SongRecord: ...
def list_songs() -> list[SongRecord]: ...
def get(song_id: str) -> SongRecord: ...
def update(song_id: str, *, title: str | None = None, note: str | None = None) -> SongRecord: ...
def delete(song_id: str) -> None: ...
def export_zip(song_id: str) -> Path: ...

# draft_store.py
def load() -> Draft: ...
def save(draft: Draft) -> None: ...
def clear() -> None: ...
```

`engine.py` 對上游的對應：

| 本專案 | 上游呼叫 | 備註 |
|---|---|---|
| `Engine.load` | `YuE2Pipeline.from_pretrained("m-a-p/YuE2-3B", device="cuda", cache_dir=..., progress=False, memory_budget_gib=...)` | 模型與 VAE 的 revision 於 Stage 1 釘死並寫入 `requirements-colab.txt` 旁的常數 |
| `Engine.plan` | `pipe.plan(style=, lyrics=, cot=, seed=, cancelled=)` | 取 `plan.abc`、`plan.truncated` |
| `Engine.render` | `pipe(style=, lyrics=, cot=, seed=, abc=, cfg_scale=, cancelled=, on_token=, on_progress=)` | `on_progress("nar", ...)` 對應 rendering，`("vae", ...)` 對應 decoding；`on_token` 只用來計數並區分 planning 與 composing，其參數形式於 Stage 2 依原始碼確認 |
| `Engine.close` | `pipe.close()` | |

同步與非同步：所有引擎呼叫都是同步阻塞。Gradio 事件函式以產生器形式逐步 `yield`；`on_stage` 由引擎執行緒寫入執行緒安全的佇列，事件函式每 0.5 秒輪詢並輸出。生成類事件共用 `concurrency_id="gpu"`、`concurrency_limit=1`。

### 錯誤處理 / 回退策略 / 可觀測性

**錯誤代碼**

| 代碼 | 觸發 | 使用者訊息 | 回退 |
|---|---|---|---|
| `E_ENV_GPU` | 無 GPU、運算能力低於 8.0 或 VRAM 低於 20 GiB | 「這個執行階段不是 L4。請到『執行階段 → 變更執行階段類型』選擇 L4 GPU 後重新執行。」 | 停止，不啟動介面 |
| `E_ENV_INSTALL` | pip 子行程非零結束或 `pip check` 失敗 | 「安裝套件失敗。」加最後 30 行輸出 | 停止；建議「中斷並刪除執行階段」後重試 |
| `E_MODEL_DOWNLOAD` | 權重下載失敗或磁碟不足 | 「下載作曲引擎失敗，請檢查網路後按重試。」 | 已下載部分保留，可續傳 |
| `E_VALIDATION` | 欄位不合規則 | 顯示在欄位旁，例如「曲風不能是空的」 | 停留在 drafting |
| `E_ABC_INVALID` | 上游拒絕 ABC | 「樂譜格式有問題：<上游訊息>。可以改回引擎規劃的版本。」 | 提供「還原為引擎規劃的樂譜」 |
| `E_OOM` | `torch.cuda.OutOfMemoryError` | 「顯示卡記憶體不足。請縮短歌詞後重試，或按『釋放引擎』後再試一次。」 | 清空 CUDA 快取；引擎標記為需重新載入 |
| `E_CANCELLED` | 使用者取消 | 以 toast 顯示「已取消」 | 回到 drafting，不算錯誤 |
| `E_BUSY` | 生成中又送出請求 | 「目前有歌曲正在生成，請等它完成或先取消。」 | 無 |
| `E_STORAGE` | 寫入失敗、Drive 未掛載、容量不足 | 「無法保存歌曲：<原因>。成品暫存在執行階段內，請先下載。」 | 改寫到 `/content/yue2_studio_data/_rescue/` |
| `E_UNKNOWN` | 其他例外 | 「發生未預期的錯誤。」加例外類別名稱 | 記錄完整 traceback；環境資訊區自動展開 |

**重試**：只有 `E_MODEL_DOWNLOAD` 自動重試（最多 3 次，間隔 5、15、45 秒）。生成失敗不自動重試，因為每次嘗試都消耗運算單元，由使用者決定。

**可觀測性**

- Logs：`logs/app.log`，JSON Lines，每行含 `ts`、`event`、`job_id`、`song_id`、`stage`、`seconds`、`error_code`。單檔上限 5 MB，保留 3 份輪替。不記錄歌詞與曲風全文，只記錄字數。
- Metrics：每首歌的各階段秒數、峰值 VRAM、權重載入秒數，寫入 `studio.json` 的 `timing` 與事件記錄；環境資訊區顯示最近一首的數值。
- Traces：以 `job_id` 串起同一次工作的所有事件，等同輕量追蹤；不導入外部追蹤系統。
- 診斷匯出：環境資訊區的「複製診斷資訊」產生一段文字，含環境報告、版本、最近 20 筆事件，不含歌詞。

### 狀態機

**GenerationJob**

| 目前狀態 | 事件 | 下一狀態 | 條件與動作 |
|---|---|---|---|
| idle | submit_plan | loading 或 planning | 引擎未載入則先 loading |
| idle | submit_render | loading 或 planning 或 composing | 有 ABC 時略過 planning |
| loading | loaded | planning 或 composing | |
| loading | error | failed | `E_MODEL_DOWNLOAD`、`E_OOM` |
| planning | plan_done（僅產生樂譜） | score_ready | 回傳 `PlanDraft` |
| planning | 第一個非樂譜階段的回報 | composing | 一次完成的流程 |
| composing | `on_progress("nar")` 首次出現 | rendering | |
| rendering | `on_progress("vae")` 首次出現 | decoding | |
| decoding | 上游回傳結果 | saving | |
| saving | 寫入完成 | done | 建立 SongRecord |
| saving | 寫入失敗 | failed | `E_STORAGE`，成品寫入救援資料夾 |
| planning、composing、rendering | cancel | cancelled | 上游於檢查點拋出中止 |
| decoding、saving | cancel | 不變 | 忽略取消並提示「即將完成，無法取消」 |
| 任一執行中狀態 | 例外 | failed | 對應錯誤代碼 |
| score_ready、done、failed、cancelled | 新的 submit | 依 idle 規則 | 終止狀態可直接重新開始 |

**Engine**：`unloaded → loading → ready`；`ready → unloaded`（釋放引擎）；`loading → error`；`ready → error`（OOM 後）；`error → loading`（下次請求自動重新載入）。

### 通知與背景執行

| 項目 | 規則 |
|---|---|
| 背景任務 | 只有一種：歌曲生成（含產生樂譜）。執行於 Gradio 的工作執行緒 |
| 觸發 | 使用者按主按鈕或「用這份樂譜生成」 |
| 去重 | 全域單一工作；執行中再送出回 `E_BUSY`。主按鈕於送出瞬間停用，避免連點 |
| 取消 | 取消旗標為 `threading.Event`；上游在 token 生成與聲音合成的檢查點查詢。decoding 之後不可取消 |
| 狀態查詢 | `generation_job.current()`；頁面載入與每 2 秒的計時器呼叫 |
| 瀏覽器關閉 | 工作繼續執行（Colab cell 仍在跑）。重新開啟連結後，狀態列顯示目前階段；若已完成，成品在歌曲庫 |
| 通知 | 只有頁面內通知：完成時切換分頁並以 toast 顯示「歌曲完成」；失敗顯示錯誤面板。不寄信、不推播 |
| 重試 | 僅權重下載自動重試；生成由使用者手動重試 |
| 失敗告警 | 寫入事件記錄 `job_failed`；錯誤面板顯示代碼。沒有外部告警通道 |
| 逾時 | 單一工作超過 45 分鐘視為異常，設定取消旗標並以 `E_UNKNOWN` 結束（門檻於 Stage 2 依實測基準調整） |

### UI 事件回報

事件寫入 `logs/app.log`，用途為追錯與使用統計，不對外傳送。

| 事件名稱 | 觸發時機 | 攜帶欄位 | 用途 |
|---|---|---|---|
| `app_started` | 介面啟動 | 環境報告摘要、版本、是否使用 Drive | 環境追溯 |
| `engine_loaded` | 引擎載入完成 | `seconds` | 載入時間基準 |
| `job_submitted` | 送出生成或產生樂譜 | `job_id`、`kind`、`cot`、`style_chars`、`lyrics_chars`、`has_abc`、`abc_source` | 使用型態 |
| `job_stage` | 階段轉換 | `job_id`、`stage`、`seconds_in_prev_stage` | 找出慢的階段 |
| `job_completed` | 歌曲保存完成 | `job_id`、`song_id`、`total_seconds`、`duration_sec`、`truncated`、`peak_vram_gib` | 成功率與效能 |
| `job_cancelled` | 取消生效 | `job_id`、`stage` | 取消發生在哪 |
| `job_failed` | 任何失敗 | `job_id`、`stage`、`error_code`、`exception_type` | 追錯 |
| `validation_failed` | 欄位驗證不過 | `fields` | 哪個欄位最常出錯 |
| `score_edited` | 送出時 ABC 與引擎規劃不同 | `job_id`、`chars_before`、`chars_after` | 樂譜編輯使用率 |
| `abc_uploaded` | 上傳 ABC | `bytes`、`accepted` | |
| `song_updated`、`song_deleted`、`song_exported`、`song_reloaded` | 歌曲庫操作 | `song_id` | 稽核 |
| `draft_cleared` | 重新開始 | 無 | |
| `engine_released` | 釋放引擎 | 無 | |

### UI ↔ API Mapping

| 畫面與元件 | 事件 | 呼叫 | 預期回應 |
|---|---|---|---|
| 頁面載入 | `demo.load` | `draft_store.load()`、`generation_job.current()`、`song_store.list_songs()` | 表單填回；狀態列同步；歌曲庫填入 |
| `style_box`、`lyrics_box`、進階設定 | `change`（防抖 1 秒） | `draft_store.save()` | 無可見變化 |
| `fill_example_link` | `click` | 無（讀取內建範例） | 表單填入範例 |
| `primary_btn`（未勾選先看樂譜） | `click` | `generation_job.run_render(form, abc=None)` | 串流更新狀態列；完成後切到「3 成品」 |
| `primary_btn`（勾選先看樂譜） | `click` | `generation_job.run_plan(form)` | 串流更新；完成後切到「2 樂譜」並填入 ABC |
| `cancel_btn` | `click` | `generation_job.cancel()` | toast「已取消」；回到 drafting |
| `abc_upload` | `upload` | `request_rules.read_abc_file()` | 內容載入 `abc_editor`；來源標示「你上傳的」 |
| `abc_clear_btn` | `click` | 無 | 編輯框清空；來源標示清除 |
| `render_from_score_btn` | `click` | `generation_job.run_render(form, abc=editor_text)` | 同主按鈕 |
| `remix_btn` | `click` | `song_store.get()` 後 `draft_store.save()` | 表單填入該歌曲請求；切到「1 寫歌」 |
| `restart_btn` | `click`（確認後） | `draft_store.clear()` | 表單清空；回到 empty |
| `download_flac` | `click` | 無（直接提供檔案路徑） | 瀏覽器下載 |
| `download_zip` | `click` | `song_store.export_zip()` | 瀏覽器下載 |
| `library_table` | `select` | `song_store.get()` | 顯示 `library_detail` |
| 歌曲庫「儲存標題與備註」 | `click` | `song_store.update()` | toast「已保存」；清單更新 |
| 歌曲庫「刪除」 | `click`（確認後） | `song_store.delete()` | 清單移除該列 |
| 「釋放引擎」 | `click` | `Engine.close()` | 環境資訊顯示「引擎未載入」 |
| 「複製診斷資訊」 | `click` | `event_log.diagnostics()` | 文字複製到剪貼簿 |
| 計時器（每 2 秒，僅生成中） | `tick` | `generation_job.current()` | 狀態列更新（頁面重整後接續用） |

### UI 狀態保存與重新開始

- 自動保留：曲風、歌詞、規劃方式、seed、文字引導強度、先看樂譜勾選、樂譜編輯內容與來源。
- 恢復時機：頁面載入時。若草稿含樂譜內容，「2 樂譜」分頁直接顯示，但不自動切換過去。
- 不保留：目前分頁、收合狀態、歌曲庫的選取。
- 生成成功後草稿不清除，方便只改一兩個字再做一版。
- 重新開始：「1 寫歌」分頁右上的「重新開始」。確認文字為「會清空目前的曲風、歌詞與樂譜。已完成的歌曲不受影響。」確認後清除草稿、回到 empty、切回「1 寫歌」。
- 生成中「重新開始」停用。

### 建議補充的功能

| 功能 | 優先度 | 原因 |
|---|---|---|
| 翻唱（SheetSage2 轉譜後以 `cot="melody"` 生成） | 高 | 上游主打能力；需獨立 Python 環境，是完整的下一個里程碑 |
| 同一請求連續生成多個 seed 並排試聽 | 高 | 官方基準本身就是多候選挑選；單次生成品質有隨機性 |
| ABC 的 MIDI 試聽 | 中 | 改樂譜後不必花運算單元就能先聽旋律 |
| MP3 下載 | 中 | FLAC 檔案大，分享不便 |
| 用已保存的 latent 換解碼器重新解碼 | 低 | 上游支援，但只對比較研究有用 |
| 歌曲庫搜尋與標籤 | 低 | 超過數十首才有需要 |
| A100 驗收 | 低 | 目前只放行不驗收 |

### 驗收條件

| 編號 | 條件 | 驗證方式 |
|---|---|---|
| AC-01 | 在 T4 runtime 執行 Cell 1，停止並顯示 `E_ENV_GPU` 的中文訊息，後續 cell 不會啟動介面 | Colab 手動 |
| AC-02 | 在全新 L4 runtime 依序執行 3 個 cell，不修改任何程式碼即可開啟介面 | Colab 手動 |
| AC-03 | 以官方 `examples/song.json` 的曲風與歌詞生成，得到可播放的 48 kHz 立體聲 FLAC | `scripts/colab_smoke.py` |
| AC-04 | AC-03 的峰值 VRAM 低於 20 GiB，連續 5 次無 OOM | `scripts/colab_smoke.py --repeat 5` |
| AC-05 | 生成中狀態列至少出現「譜寫內容」「聲音合成」「音訊解碼」三個階段，更新間隔不超過 2 秒 | Colab 手動加事件記錄 |
| AC-06 | 於譜寫內容階段按取消，30 秒內主按鈕恢復可用，歌曲庫沒有新增項目 | Colab 手動 |
| AC-07 | 勾選先看樂譜，取得 ABC；修改一個音後生成，成品資料夾的 `score.abc` 與送出的文字相同 | Colab 手動加檔案比對 |
| AC-08 | 生成完成後重新整理瀏覽器，歌曲庫仍有該歌曲，表單內容仍在 | Colab 手動 |
| AC-09 | 歌曲改名後清單立即更新；刪除後資料夾不存在 | 單元測試加手動 |
| AC-10 | 上傳 300 KB 的檔案或 `.mid` 檔被拒絕並顯示原因；上傳合法 `.abc` 後內容出現在編輯框 | 單元測試 |
| AC-11 | 生成中再次送出，收到 `E_BUSY` 訊息，原工作不受影響 | 單元測試（假管線） |
| AC-12 | 沒有通行碼無法進入介面 | Colab 手動 |
| AC-13 | 使用 Drive 時，中斷 runtime 後重開並掛載同一資料夾，歌曲庫與草稿恢復 | Colab 手動 |
| AC-14 | `pytest` 在無 GPU 環境全數通過；`engine.py` 以外行覆蓋率 80% 以上；`ruff check` 零錯誤 | CI 或本機 |
| AC-15 | `docs/colab-baseline.md` 記錄 L4 上的安裝時間、權重下載時間、引擎載入時間、範例歌曲各階段耗時與峰值 VRAM | 文件檢查 |

### 測試案例

| 編號 | 類型 | 案例 | 預期 |
|---|---|---|---|
| T-01 | 單元 | `validate`：曲風為空白字元 | `E_VALIDATION`，欄位 `style` |
| T-02 | 單元 | `validate`：`cot="off"` 且帶 ABC | `E_VALIDATION`，欄位 `abc` |
| T-03 | 單元 | `validate`：seed 為 -1、2147483648、非整數 | 皆拒絕 |
| T-04 | 單元 | `validate`：歌詞為空 | 接受 |
| T-05 | 單元 | `probe`：模擬 T4（7.5、15 GiB）、L4（8.9、22.5 GiB）、無 GPU | 不通過、通過、不通過 |
| T-06 | 單元 | `song_store.create` 中途例外 | 不留下歌曲資料夾，暫存資料夾被清除 |
| T-07 | 單元 | `song_store.delete("../x")`、含大寫或斜線的 id | 拒絕，不觸碰檔案系統 |
| T-08 | 單元 | `studio.json` 損毀 | `list_songs` 仍回傳其他歌曲，該筆標記為無法讀取 |
| T-09 | 單元 | `draft_store`：寫入後讀回；`schema_version` 較舊 | 內容一致；缺少欄位以預設值補齊 |
| T-10 | 單元 | `engine.render` 以假管線回報 nar 與 vae 進度 | `StageEvent` 順序為 composing、rendering、decoding |
| T-11 | 單元 | 假管線在 composing 時取消 | 狀態為 cancelled，不呼叫 `song_store.create` |
| T-12 | 單元 | 假管線拋出 OOM | 狀態為 failed，代碼 `E_OOM`，引擎標記需重新載入 |
| T-13 | 單元 | 執行中再次 `run_render` | 第二次回 `E_BUSY` |
| T-14 | 流程 | 以假管線走完流程 A 的事件函式 | 最後輸出包含音訊路徑與分頁切換到成品 |
| T-15 | 流程 | 以假管線走完流程 B，中間修改 ABC | `abc_source` 為 `edited`，送入管線的 ABC 等於修改後文字 |
| T-16 | 流程 | `truncated=True` 的結果 | 成品頁顯示截斷警告 |
| T-17 | Colab | 煙霧測試：官方範例 5 次 | 全部成功，輸出量測表 |
| T-18 | Colab | 中文歌詞加中文曲風描述 | 生成成功，檔名與中繼資料無亂碼 |

### Gherkin / BDD

```gherkin
Feature: 先看樂譜再生成

  Scenario: 修改樂譜後生成
    Given 介面已啟動且引擎可用
    And 我填好曲風與歌詞
    And 我勾選「先看樂譜再生成」
    When 我按下「產生樂譜」
    Then 狀態列顯示「作曲規劃中」
    And 完成後頁面切到「2 樂譜」
    And 樂譜來源顯示「引擎規劃」
    When 我修改樂譜文字
    Then 樂譜來源顯示「你修改過」
    When 我按下「用這份樂譜生成」
    Then 頁面最後切到「3 成品」
    And 成品的樂譜與我送出的文字相同

  Scenario: 生成中取消
    Given 一首歌正在「譜寫內容」階段
    When 我按下「取消」
    Then 30 秒內出現「已取消」
    And 主按鈕恢復可用
    And 我填的曲風與歌詞都還在
    And 歌曲庫沒有新增歌曲

  Scenario: 在不支援的執行階段啟動
    Given Colab 執行階段是 T4
    When 我執行 Cell 1
    Then 我看到「這個執行階段不是 L4」的說明
    And Cell 3 不會啟動介面
```

### Edge / Abuse cases

| 情境 | 處理行為 | 使用者提示 | 回復策略 |
|---|---|---|---|
| 歌詞貼入 5 萬字 | 驗證擋下 | 「歌詞最多 5000 字，目前 50000 字」 | 保留內容讓使用者自行刪減 |
| 歌詞含 HTML 或 script 標籤 | 視為純文字；顯示時經 Gradio 跳脫 | 無 | 無 |
| 連點主按鈕 | 第一次點擊後立即停用；後端再以單一工作保護 | 無，或 `E_BUSY` | 無 |
| 生成中重新整理頁面 | 工作不中斷；頁面載入後接續顯示 | 狀態列顯示目前階段 | 計時器輪詢 |
| 生成中 Colab 斷線或 runtime 被回收 | 工作遺失 | 重新連線後歌曲庫沒有該歌曲；草稿若在 Drive 則保留 | 說明文件提示使用 Drive |
| 分享連結外流 | 需要通行碼 | 登入畫面 | 重新執行 Cell 2 與 Cell 3 產生新通行碼 |
| 上傳二進位檔改名為 `.abc` | UTF-8 解碼失敗即拒絕 | 「這個檔案不是文字格式的樂譜」 | 編輯框內容不變 |
| ABC 加入第三個聲部 | 送交上游；上游文件說明多餘聲部不會成為獨立控制 | 樂譜分頁常駐一行說明「只支援 Vocal 與 Ins 兩個聲部」 | 無 |
| 取消發生在解碼階段 | 忽略 | 「即將完成，無法取消」 | 完成後可刪除 |
| Drive 容量已滿 | `E_STORAGE` | 「無法保存歌曲：Google Drive 空間不足」 | 寫入救援資料夾並提供下載 |
| 權重下載到一半斷線 | 自動重試 3 次 | 狀態列「下載中斷，重試第 2 次」 | 續傳 |
| 同一資料夾被兩個 runtime 同時掛載 | 不支援；歌曲 id 含時間與隨機碼，不會互相覆蓋，草稿以最後寫入為準 | README 說明 | 無 |
| 歌曲資料夾被手動刪掉部分檔案 | 該歌曲顯示「檔案不完整」，可刪除，不可播放 | 清單標示 | 無 |
| 以歌詞要求模仿特定歌手 | 上游沒有歌手身分控制；不額外處理 | 頁尾授權說明含上游的負責任使用條款連結 | 無 |
| 工作超過 45 分鐘 | 自動取消 | 「生成時間過長，已自動停止」 | 記錄 `job_failed` |

### 風險與未決事項

| 風險 | 可能性 | 影響 | 因應 |
|---|---|---|---|
| Gradio 與 `huggingface-hub==0.36.2`、`numpy==2.2.6` 版本衝突 | 中 | 無法安裝 | Stage 0 以 `pip install --dry-run` 與 `pip check` 找出可共存版本並釘死；找不到時把介面放在獨立虛擬環境，以子行程方式呼叫引擎（需另開變更） |
| L4 的 22.5 GB 低於官方寫的 24 GB | 低 | 長歌 OOM | Stage 1 以最長情境實測；必要時設定較低的 `memory_budget_gib` 或啟用 `low_vram` 作為退路 |
| 上游介面變動 | 高（若升級） | `engine.py` 失效 | 釘死 commit；升級流程寫入 `docs/upgrading-yue2.md` |
| Colab 預裝套件版本變動 | 中 | 安裝 cell 失效 | 安裝後執行 `pip check` 與匯入測試；失敗訊息指向 README 的已知問題 |
| L4 配額不保證 | 中 | 使用者拿不到 L4 | 屬於 Colab 限制，README 說明 |
| Gradio 分享連結服務中斷 | 低 | 無法開啟介面 | 說明文件提供改用 Colab 內嵌顯示的參數 |
| 權重授權為非商用加創作者條款 | 確定 | 公司商用需另洽授權 | README 與頁尾標示 |

未決事項：假設 A1 至 A4 是否成立；通行碼是否要改為可由使用者自訂；逾時門檻 45 分鐘是否合理（待基準量測）。
