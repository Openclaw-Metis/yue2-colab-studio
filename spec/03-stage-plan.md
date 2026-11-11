## Codex / Claude Code 分階段開發計畫

專案代號：`yue2-colab-studio`｜日期：2026-11-11｜共 7 個 Stage（Stage 0 至 Stage 6）

### 使用方式

- 開始前把 `spec/01-technical-spec.md` 複製到新 repo 的 `docs/spec/technical-spec.md`。每個 Stage 的 instructions 都以該檔案的章節名稱作為依據。
- 每個 Stage 各有一個 Codex 版與一個 Claude Code 版，內容等價，擇一使用。
- 本專案沒有大型語言模型的文字輸出，Streaming 準則不適用；對應要求是「生成進度必須分階段即時更新」，已寫入相關 Stage。
- 需要真實 GPU 的驗證（標示「Colab 手動」）無法由代理人在本機完成，由你在 Colab L4 執行後把結果貼回。

| Stage | 名稱 | 交付的使用者價值 | 需要 Colab L4 驗證 |
|---|---|---|---|
| 0 | 建立專案骨架與環境閘門 | 開啟 notebook 就知道環境能不能用 | 是 |
| 1 | 打通最小生成流程 | 填表單就能得到一首可播放的歌 | 是 |
| 2 | 加上進度、取消與錯誤處理 | 等待時看得到進度，可以中止，出錯看得懂 | 是 |
| 3 | 實作樂譜檢視與編輯 | 先看樂譜、改樂譜、上傳樂譜再生成 | 是 |
| 4 | 實作歌曲庫與狀態保存 | 舊歌找得回來，草稿不會消失 | 是 |
| 5 | 補齊整合、回歸與邊界測試 | 行為有測試保護 | 否（煙霧測試除外） |
| 6 | 完成文件與交付 | 別人照著 README 就能用 | 是（最終走查） |

### 專案共通規則（Stage 0 寫入 AGENTS.md 與 CLAUDE.md）

```text
# yue2-colab-studio 專案規則

- 規格來源：docs/spec/technical-spec.md。與本檔衝突時以規格為準，並回報衝突。
- 目標環境只有 Google Colab L4。不加入 T4 相容補丁、不修改 yue2 套件原始碼、不做量化。
- 只有 src/yue2_studio/engine.py 可以 import yue2。其他模組一律透過 Engine 介面。
- 只有 song_store.py、draft_store.py、event_log.py 可以寫入工作目錄。
- installer.py 與 notebook 的 Cell 1 不可 import torch；安裝一律用子行程執行 pip。
- 上游版本以 commit SHA 釘死在 requirements-colab.txt，不可改成分支名稱。
- 所有介面字串放在 ui_text.py，使用繁體中文，不使用 emoji。
- 模組名稱要描述職責，不新增 utils、helpers、common、service 這類名稱。
- 測試不得需要 GPU 或網路；用 tests/fake_pipeline.py 取代真實管線。
- 每次變更後執行：ruff check . 與 pytest -q，兩者都要通過。
- 不主動 commit、push 或發布；完成後回報變更檔案清單與測試結果。
- 不猜測 yue2 的參數名稱；不確定時讀取已安裝套件的原始碼確認，並在回報中註明依據。
```

---

### Stage 0：建立專案骨架與環境閘門

- **目標**：建立 repo 結構、開發工具與 notebook 的 Cell 1。在 L4 上能完成安裝並印出環境報告；在 T4 上會被擋下。同時取得後續 Stage 需要的實測事實。
- **前置條件**：一個空的 Git repo；`docs/spec/technical-spec.md` 已放入。

**Codex Instructions**

```text
[建議貼用方式]
直接貼給 Codex。先把「專案共通規則」整段寫入 repo 根目錄的 AGENTS.md，再執行以下任務。

[任務範圍]
做：專案骨架、開發工具設定、環境檢查、安裝器、notebook 的 Cell 1、對應單元測試。
不做：任何 Gradio 介面、任何 yue2 呼叫、歌曲庫、Cell 2 與 Cell 3 的實作（只留標題與「尚未實作」說明）。

[需修改/新增的檔案清單]
新增 AGENTS.md、README.md（只含專案一句話說明與「開發中」）、LICENSE（Apache-2.0）、.gitignore、
pyproject.toml、requirements-colab.txt、YuE2_Colab_Studio.ipynb、
src/yue2_studio/__init__.py、environment.py、installer.py、ui_text.py、event_log.py、
tests/test_environment.py、tests/test_installer.py、tests/test_event_log.py、
docs/colab-baseline.md（含待填表格）。

[具體步驟]
1. 讀 docs/spec/technical-spec.md 的「假設與前提」「專案目錄規劃」「API 設計」「錯誤處理 / 回退策略 / 可觀測性」。
2. pyproject.toml：套件名 yue2-studio，src layout，requires-python >=3.10；設定 ruff（line-length 100）與 pytest（testpaths=tests）。
   執行期相依不寫進 pyproject，統一由 requirements-colab.txt 管理。
3. requirements-colab.txt：
   yue2-infer @ git+https://github.com/multimodal-art-projection/YuE.git@1116bea76032bee5668e5f097294d082fa0b84f0
   gradio 先不寫版本，加註解「版本由 Stage 0 的 Colab 驗證決定後釘死」。
4. environment.py：實作 EnvironmentReport 與 probe()。GPU 資訊以子行程呼叫
   nvidia-smi --query-gpu=name,memory.total --format=csv,noheader,nounits 取得；運算能力以
   nvidia-smi --query-gpu=compute_cap 取得，失敗時回報為未知並視為不通過。不 import torch。
   門檻：compute_capability >= (8, 0) 且 vram_total_gib >= 20.0。把指令執行抽成可注入的函式以便測試。
5. installer.py：install(requirements_path) 依序以子行程執行
   (a) pip uninstall -y torchvision torchaudio
   (b) pip install -r requirements-colab.txt
   (c) pip check
   任一步非零結束即拋出 InstallFailed，附最後 30 行輸出。不 import torch。
6. event_log.py：JSON Lines 寫入、5 MB 輪替保留 3 份、diagnostics() 回傳最近 20 筆事件文字。
7. ui_text.py：放入 E_ENV_GPU、E_ENV_INSTALL 的訊息與「環境檢查通過」。
8. Notebook Cell 1：git clone 本 repo（或使用已存在的目錄）→ probe() → 不通過則印出訊息並 raise SystemExit
   → 通過則 install() → 以子行程執行 python -c "import yue2, gradio; print(yue2.__version__, gradio.__version__)"
   與 yue2 doctor → 印出環境報告表與各步驟耗時。
9. 測試：以注入的假指令模擬 T4（7.5、15 GiB）、L4（8.9、22.5 GiB）、無 GPU、nvidia-smi 不存在。

[輸出格式要求]
回報：新增檔案清單、ruff 與 pytest 的實際輸出摘要、需要我在 Colab 執行並回填的項目清單。

[測試要求]
ruff check . 零錯誤；pytest -q 全數通過；測試不需 GPU 與網路。

[驗收標準 DoD]
- 本機 ruff 與 pytest 通過。
- Colab 手動：T4 runtime 執行 Cell 1 會停止並顯示 E_ENV_GPU 訊息。
- Colab 手動：L4 runtime 執行 Cell 1 完成，印出 Python 版本、GPU 名稱、VRAM、主機記憶體、yue2 與 gradio 版本。
- 我回填 Colab 結果後：requirements-colab.txt 的 gradio 已釘死為實測可共存的版本，docs/colab-baseline.md 已填入安裝耗時。
```

**Claude Code Instructions**

```text
[建議貼用方式]
直接貼給 Claude Code。先把「專案共通規則」整段寫入 repo 根目錄的 CLAUDE.md，再執行以下任務。
Colab 驗證步驟可另存為 .claude/commands/colab-check.md，內容為「列出目前 Stage 需要我在 Colab L4 手動執行的步驟與要貼回的輸出」。

[任務範圍]
做：專案骨架、開發工具設定、環境檢查、安裝器、notebook 的 Cell 1、對應單元測試。
不做：任何 Gradio 介面、任何 yue2 呼叫、歌曲庫、Cell 2 與 Cell 3 的實作（只留標題與「尚未實作」說明）。

[需修改/新增的檔案清單]
新增 CLAUDE.md、README.md、LICENSE（Apache-2.0）、.gitignore、pyproject.toml、requirements-colab.txt、
YuE2_Colab_Studio.ipynb、src/yue2_studio/{__init__,environment,installer,ui_text,event_log}.py、
tests/test_{environment,installer,event_log}.py、docs/colab-baseline.md。

[具體步驟]
1. 先讀 docs/spec/technical-spec.md 的「假設與前提」「專案目錄規劃」「API 設計」「錯誤處理 / 回退策略 / 可觀測性」。
2. pyproject.toml：套件名 yue2-studio，src layout，requires-python >=3.10，ruff（line-length 100）與 pytest 設定。
3. requirements-colab.txt 釘死
   yue2-infer @ git+https://github.com/multimodal-art-projection/YuE.git@1116bea76032bee5668e5f097294d082fa0b84f0
   gradio 版本留待 Colab 驗證後釘死，以註解標明。
4. environment.py：EnvironmentReport 與 probe()，資料來自 nvidia-smi 子行程（name、memory.total、compute_cap），
   指令執行函式可注入。門檻 compute_capability >= (8, 0) 且 vram_total_gib >= 20.0。不 import torch。
5. installer.py：子行程依序執行 pip uninstall -y torchvision torchaudio、pip install -r、pip check；
   失敗拋出 InstallFailed 並附最後 30 行輸出。不 import torch。
6. event_log.py：JSON Lines、5 MB 輪替保留 3 份、diagnostics()。
7. ui_text.py：E_ENV_GPU、E_ENV_INSTALL 訊息與成功訊息。
8. Notebook Cell 1：probe → 不通過則印訊息並 raise SystemExit → install → 子行程驗證 import yue2 與 gradio、執行 yue2 doctor
   → 印出環境報告與耗時。
9. 測試涵蓋 T4、L4、無 GPU、nvidia-smi 不存在四種情境。

[輸出格式要求]
結束時回報：變更檔案清單、ruff 與 pytest 的實際結果、待我在 Colab 回填的項目。不要 commit。

[測試要求]
ruff check . 零錯誤；pytest -q 全數通過；不需 GPU 與網路。

[驗收標準 DoD]
- 本機 ruff 與 pytest 通過。
- Colab 手動：T4 被擋下並顯示 E_ENV_GPU；L4 完成安裝並印出完整環境報告。
- 回填後 gradio 版本已釘死，docs/colab-baseline.md 有安裝耗時、Python 版本、主機記憶體。
```

- **風險與回滾方式**：最大風險是 Gradio 與 YuE2 釘死的 `huggingface-hub`、`numpy` 無法共存。若 `pip check` 失敗，先嘗試較舊的 Gradio 主版本；仍失敗則停在此 Stage，回到規格的「風險與未決事項」改採獨立虛擬環境方案。回滾方式為刪除本 Stage 的 commit，沒有外部狀態。

---

### Stage 1：打通最小生成流程

- **目標**：在 L4 上從 Gradio 表單送出曲風與歌詞，得到可播放的音訊。這是第一個端到端的垂直切片，並取得效能基準。
- **前置條件**：Stage 0 完成；`requirements-colab.txt` 的 Gradio 版本已釘死；已知 Colab 的 Python 版本與主機記憶體。

**Codex Instructions**

```text
[建議貼用方式]
直接貼給 Codex。AGENTS.md 的專案規則持續適用。

[任務範圍]
做：欄位驗證、引擎轉接、最小 Gradio 介面（曲風、歌詞、主按鈕、播放器）、Cell 2 與 Cell 3、煙霧測試腳本、假管線。
不做：分階段進度、取消、樂譜分頁、歌曲庫、草稿保存、Drive 掛載。此階段成品只寫到 /content/yue2_studio_data/_stage1/<時間戳>/。

[需修改/新增的檔案清單]
新增 src/yue2_studio/request_rules.py、engine.py、theme.py、app.py、scripts/colab_smoke.py、
tests/fake_pipeline.py、tests/test_request_rules.py、tests/test_engine.py。
修改 YuE2_Colab_Studio.ipynb、src/yue2_studio/ui_text.py、docs/colab-baseline.md。

[具體步驟]
1. 讀規格的「核心流程設計」流程 A、「核心資料模型」的 SongRequest、「API 設計」、「UI 風格定調與色彩策略」。
2. 先讀取已安裝的 yue2 套件原始碼（pipeline.py 與 protocol.py），確認 from_pretrained 與 __call__ 實際接受的參數名稱
   （cot、seed、cfg_scale、abc、memory_budget_gib、cache_dir、progress），在回報中列出確認結果。與規格不符時以原始碼為準並回報。
3. request_rules.py：SongRequest dataclass 與 validate(raw)；規則依規格表格。seed 為 None 時產生隨機值並寫回請求。
4. engine.py：Engine 類別，load() 以 YuE2Pipeline.from_pretrained("m-a-p/YuE2-3B", device="cuda",
   cache_dir="/content/hf_cache", progress=False) 載入並保存為單例；render() 呼叫 pipe(...) 回傳 RenderOutcome，
   並以 torch.cuda.max_memory_allocated 計算 peak_vram_gib；close() 呼叫 pipe.close()。
   管線建立函式可注入，測試時換成假管線。此階段 cancelled 傳入永遠回 False 的函式，on_stage 可先不接。
5. tests/fake_pipeline.py：FakePipeline 模擬 __call__、plan、close，回傳帶 audio（numpy 靜音陣列）、sample_rate=48000、
   abc、truncated、timing、save_artifacts(dir) 的假結果；可設定要拋出的例外。
6. theme.py：依規格色碼建立 Gradio 主題。
7. app.py：build_app(engine, workdir) 回傳 gr.Blocks。元件：style_box、lyrics_box、primary_btn、result_audio、
   一個簡單的狀態文字。按下主按鈕 → validate → engine.load（若未載入）→ engine.render → save_artifacts → 回傳 audio.flac 路徑。
   demo.queue 設定生成事件 concurrency_limit=1。
8. Notebook Cell 2：建立 /content/yue2_studio_data，產生 12 字元隨機通行碼並印出。
   Cell 3：build_app(...).launch(share=True, auth=("studio", 通行碼), show_api=False)。
9. scripts/colab_smoke.py：不經介面，直接用 Engine 以官方 examples/song.json 的內容生成，
   參數 --repeat N；輸出每次的各階段耗時、音訊長度、峰值 VRAM、是否截斷的表格。

[輸出格式要求]
回報：變更檔案清單、步驟 2 的參數確認結果、ruff 與 pytest 結果、我需要在 Colab 執行的指令。

[測試要求]
test_request_rules 覆蓋規格測試案例 T-01 至 T-04；test_engine 以假管線驗證 load 只呼叫一次、render 傳入的參數正確、close 會釋放。
ruff 與 pytest 通過。

[驗收標準 DoD]
- 本機測試通過。
- Colab 手動：三個 cell 依序執行後可登入介面，以官方範例生成並在頁面播放（規格 AC-02、AC-03）。
- Colab 手動：python scripts/colab_smoke.py --repeat 5 全部成功，峰值 VRAM 低於 20 GiB（AC-04）。
- docs/colab-baseline.md 已填入權重下載時間、引擎載入時間、各階段耗時、峰值 VRAM。
- 模型與 VAE 的 revision 已釘死為常數並記錄於 docs/colab-baseline.md。
```

**Claude Code Instructions**

```text
[建議貼用方式]
直接貼給 Claude Code。CLAUDE.md 的專案規則持續適用。

[任務範圍]
做：欄位驗證、引擎轉接、最小 Gradio 介面（曲風、歌詞、主按鈕、播放器）、Cell 2 與 Cell 3、煙霧測試腳本、假管線。
不做：分階段進度、取消、樂譜分頁、歌曲庫、草稿保存、Drive 掛載。成品暫寫到 /content/yue2_studio_data/_stage1/<時間戳>/。

[需修改/新增的檔案清單]
新增 src/yue2_studio/{request_rules,engine,theme,app}.py、scripts/colab_smoke.py、
tests/{fake_pipeline,test_request_rules,test_engine}.py。
修改 YuE2_Colab_Studio.ipynb、src/yue2_studio/ui_text.py、docs/colab-baseline.md。

[具體步驟]
1. 讀規格的「核心流程設計」流程 A、「核心資料模型」、「API 設計」、「UI 風格定調與色彩策略」。
2. 讀取已安裝 yue2 套件的 pipeline.py 與 protocol.py，確認 from_pretrained 與 __call__ 的實際參數名稱；
   若本機未安裝，從 requirements-colab.txt 釘死的 commit 讀取原始碼。結果寫進回報，與規格不符時以原始碼為準。
3. request_rules.py：SongRequest 與 validate(raw)，規則依規格；seed 為 None 時產生並記錄隨機值。
4. engine.py：Engine.load / render / close；管線為單例；建立函式可注入；回傳 RenderOutcome 含 peak_vram_gib。
   權重快取固定在 /content/hf_cache。
5. tests/fake_pipeline.py：可設定結果與例外的假管線，介面與 YuE2Pipeline 用到的部分一致。
6. theme.py 與 app.py：build_app(engine, workdir)；最小表單與播放器；生成事件 concurrency_limit=1；show_api=False。
7. Notebook Cell 2（工作目錄與通行碼）與 Cell 3（launch(share=True, auth=...)）。
8. scripts/colab_smoke.py：--repeat N，輸出量測表。

[輸出格式要求]
結束時回報：變更檔案清單、參數確認結果、測試結果、Colab 待執行指令。不要 commit。

[測試要求]
涵蓋規格 T-01 至 T-04 與引擎單例行為；ruff 與 pytest 通過。

[驗收標準 DoD]
- 本機測試通過。
- Colab 手動：AC-02、AC-03、AC-04 通過。
- docs/colab-baseline.md 填入實測數字與釘死的 revision。
```

- **風險與回滾方式**：若 L4 出現 OOM，先在 `from_pretrained` 傳入較低的 `memory_budget_gib`，仍不行再啟用 `low_vram=True` 並在基準文件記錄速度影響。若上游參數名稱與規格不符，只修改 `engine.py`。回滾方式為還原本 Stage 的 commit；`/content/hf_cache` 的權重可保留供重試。

---

### Stage 2：加上進度、取消與錯誤處理

- **目標**：生成期間狀態列分階段即時更新，使用者可以取消，所有失敗都轉成看得懂的訊息並回到可操作狀態。
- **前置條件**：Stage 1 完成且有 L4 基準數字。

**Codex Instructions**

```text
[建議貼用方式]
直接貼給 Codex。AGENTS.md 的專案規則持續適用。

[任務範圍]
做：generation_job.py、引擎的階段事件與取消、狀態列、取消按鈕、錯誤面板、完整錯誤代碼對應、工作逾時。
不做：樂譜分頁、歌曲庫、草稿。沒有 LLM 文字輸出，不需 Streaming；必須做到的是進度分階段即時更新。

[需修改/新增的檔案清單]
新增 src/yue2_studio/generation_job.py、tests/test_generation_job.py。
修改 src/yue2_studio/engine.py、app.py、ui_text.py、theme.py、tests/fake_pipeline.py、tests/test_engine.py。

[具體步驟]
1. 讀規格的「狀態機」「通知與背景執行」「錯誤處理 / 回退策略 / 可觀測性」「狀態模型與揭露策略」。
2. 讀取 yue2 原始碼確認 on_token 的呼叫參數形式與 cancelled 被檢查的位置；把結果寫進 engine.py 的模組註解與回報。
3. engine.py：render() 接上 cancelled、on_token、on_progress，轉成 StageEvent：
   尚未收到任何進度時為 planning（cot 為 off 或有 ABC 時直接 composing）；on_token 計數用於 composing 的活動指示；
   on_progress("nar", done, total) 為 rendering；("vae", done, total) 為 decoding。
   on_stage 由引擎執行緒呼叫，只做放入 queue.Queue 的動作。
4. generation_job.py：模組層級單一工作。run_render(raw_form, abc) 為產生器：
   取得工作鎖（失敗回 E_BUSY）→ validate → 於背景執行緒呼叫 engine → 每 0.5 秒輪詢事件佇列並 yield JobUpdate
   → 完成後 yield done。cancel() 設定 threading.Event；decoding 與 saving 階段忽略取消並回報「即將完成，無法取消」。
   current() 回傳最新 JobUpdate 供頁面重整後接續。超過 45 分鐘自動設定取消並以 E_UNKNOWN 結束。
   任何例外都要釋放工作鎖並轉成 failed 與對應錯誤代碼；torch.cuda.OutOfMemoryError 轉 E_OOM，
   並呼叫 torch.cuda.empty_cache() 與標記引擎需重新載入。
5. app.py：新增 status_bar（階段名稱、進度條、已耗時）、cancel_btn（僅生成中可見）、error_panel（僅 failed 可見，含重試）。
   主按鈕事件改為串接 generation_job.run_render 的產生器。加入每 2 秒的 gr.Timer，僅在生成中啟用，呼叫 current()。
   不使用 Gradio 的 cancels= 參數。
6. ui_text.py：補齊規格錯誤代碼表的全部訊息與各階段名稱。
7. event_log：寫入 job_submitted、job_stage、job_completed、job_cancelled、job_failed、validation_failed。不記錄歌詞與曲風全文。
8. fake_pipeline：支援逐步回報進度、可在指定階段等待取消、可在指定階段拋出例外。

[輸出格式要求]
回報：變更檔案清單、on_token 與 cancelled 的確認結果、測試結果、Colab 手動驗證步驟。

[測試要求]
涵蓋規格 T-10 至 T-13：階段順序、composing 時取消、OOM、執行中重複送出。
另加：decoding 時取消被忽略；例外後工作鎖已釋放可再次送出；逾時觸發（以可注入的時鐘測試）。
ruff 與 pytest 通過。

[驗收標準 DoD]
- 本機測試通過。
- Colab 手動：AC-05（三個階段都出現、更新間隔不超過 2 秒）與 AC-06（取消後 30 秒內恢復）通過。
- Colab 手動：生成中重新整理頁面，狀態列接續顯示。
- 任何失敗後介面都不會停在生成中狀態。
```

**Claude Code Instructions**

```text
[建議貼用方式]
直接貼給 Claude Code。CLAUDE.md 的專案規則持續適用。

[任務範圍]
做：generation_job.py、引擎的階段事件與取消、狀態列、取消按鈕、錯誤面板、完整錯誤代碼對應、工作逾時。
不做：樂譜分頁、歌曲庫、草稿。沒有 LLM 文字輸出，不需 Streaming；必須做到進度分階段即時更新。

[需修改/新增的檔案清單]
新增 src/yue2_studio/generation_job.py、tests/test_generation_job.py。
修改 src/yue2_studio/{engine,app,ui_text,theme}.py、tests/fake_pipeline.py、tests/test_engine.py。

[具體步驟]
1. 讀規格的「狀態機」「通知與背景執行」「錯誤處理 / 回退策略 / 可觀測性」「狀態模型與揭露策略」。
2. 從 yue2 原始碼確認 on_token 的參數形式與 cancelled 的檢查點，寫入 engine.py 註解與回報。
3. engine.render() 接上 cancelled、on_token、on_progress 並轉成 StageEvent（planning、composing、rendering、decoding）；
   回呼只把事件放入執行緒安全佇列。
4. generation_job.py：單一工作鎖、run_render 產生器（0.5 秒輪詢）、cancel()、current()、45 分鐘逾時、
   例外一律轉 failed 並釋放鎖；OOM 時清空 CUDA 快取並標記引擎需重新載入。
   decoding 與 saving 階段不可取消。
5. app.py：status_bar、cancel_btn、error_panel、每 2 秒的 gr.Timer（僅生成中）。不使用 cancels=。
6. ui_text.py 補齊所有錯誤訊息與階段名稱；event_log 寫入工作相關事件且不含歌詞全文。
7. fake_pipeline 支援逐步進度、等待取消、指定階段拋例外。

[輸出格式要求]
結束時回報：變更檔案清單、原始碼確認結果、測試結果、Colab 手動步驟。不要 commit。

[測試要求]
涵蓋規格 T-10 至 T-13，以及解碼時取消被忽略、例外後可再次送出、逾時。ruff 與 pytest 通過。

[驗收標準 DoD]
- 本機測試通過。
- Colab 手動：AC-05、AC-06 通過；重新整理後狀態接續；失敗後不會卡在生成中。
```

- **風險與回滾方式**：若上游在取消時不是拋出例外而是回傳不完整結果，需在 `engine.py` 判斷取消旗標後丟棄結果。若 `gr.Timer` 在釘死的 Gradio 版本不可用，改用 `demo.load(every=2)`。回滾方式為還原本 Stage 的 commit，Stage 1 的最小流程仍可用。

---

### Stage 3：實作樂譜檢視與編輯

- **目標**：使用者可以先取得樂譜、編輯或上傳 ABC，再用該樂譜生成；介面改為正式的分頁結構。
- **前置條件**：Stage 2 完成。

**Codex Instructions**

```text
[建議貼用方式]
直接貼給 Codex。AGENTS.md 的專案規則持續適用。

[任務範圍]
做：四個分頁的版面（歌曲庫分頁先放空狀態說明）、先看樂譜流程、ABC 編輯與上傳、進階設定、樂譜來源標示、成品頁。
不做：歌曲庫功能、草稿保存、Drive。成品仍寫到暫存資料夾。不做五線譜或鋼琴捲簾顯示。

[需修改/新增的檔案清單]
修改 src/yue2_studio/{engine,generation_job,request_rules,app,ui_text,theme}.py、tests/fake_pipeline.py、
tests/test_engine.py、tests/test_generation_job.py、tests/test_request_rules.py。
新增 tests/test_app_flows.py。

[具體步驟]
1. 讀規格的「核心流程設計」流程 B 與關鍵分支、「任務模型與資訊優先級」全部表格、「狀態模型與揭露策略」、
   「UI 元件清單」、「分步導覽策略」、「UI ↔ API Mapping」。
2. engine.py：新增 plan(request, cancelled) 呼叫 pipe.plan(...) 並回傳 PlanDraft(abc, truncated, seconds)。
   render() 支援 abc 參數。依上游文件，編輯後的樂譜以新的 abc 輸入送出，不修改已保存的 plan 物件。
3. 從 yue2 原始碼找出請求前置檢查的函式（CLI 的 yue2 validate 所呼叫者）。若可直接呼叫，
   在送出前用它檢查 ABC 並把錯誤轉成 E_ABC_INVALID；若找不到穩定入口，改為捕捉 render 時的例外。把採用的作法寫進回報。
4. generation_job.py：新增 run_plan(raw_form) 產生器，終止狀態為 score_ready。
5. request_rules.py：read_abc_file(path) 檢查副檔名（.abc、.txt）、大小（200 KB）、UTF-8 可解碼；
   validate 加入「有 abc 時 cot 不可為 off」。
6. app.py 依規格重排：
   - 頂部 status_bar 與 error_panel 不變。
   - gr.Tabs：「1 寫歌」「2 樂譜」「3 成品」「歌曲庫」。
   - 寫歌：style_box、lyrics_box（含字數）、fill_example_link（表單為空時可見）、score_first_chk、primary_btn、
     advanced_acc（cot_radio、seed_box、cfg_slider 與「使用預設」勾選）。
     cot 為 off 時 score_first_chk 停用並顯示原因；勾選時主按鈕文字為「產生樂譜」。
   - 樂譜：abc_source_label、abc_editor、abc_upload（accordion 內）、abc_clear_btn、render_from_score_btn；
     無樂譜時顯示一行空狀態說明。常駐一行說明「只支援 Vocal 與 Ins 兩個聲部」。
     上傳後內容載入編輯框作為預覽，來源標示「你上傳的」；手動修改引擎規劃的內容後標示「你修改過」。
   - 成品：result_audio、truncated_notice、download_flac、result_score（accordion）、remix_btn（此階段只把請求填回表單）。
   - 階段完成時以程式切換分頁。
7. 首屏檢查：寫歌分頁在 1366x768 不需捲動；每個分頁只有一個 primary 按鈕。
8. event_log：score_edited、abc_uploaded。

[輸出格式要求]
回報：變更檔案清單、ABC 前置檢查採用的作法、測試結果、Colab 手動驗證步驟、一張寫歌分頁的版面文字描述。

[測試要求]
涵蓋規格 T-02、T-14、T-15、T-16 與 AC-10 的上傳規則。
test_app_flows 以假管線直接呼叫事件函式，驗證流程 A 與流程 B 的輸出（分頁切換、ABC 內容、abc_source）。
ruff 與 pytest 通過。

[驗收標準 DoD]
- 本機測試通過。
- Colab 手動：AC-07 通過（修改一個音後，成品資料夾的 score.abc 與送出的文字相同）。
- Colab 手動：上傳合法 .abc 後出現在編輯框；上傳 .mid 被拒絕並顯示原因。
- Colab 手動：cot 選「不規劃」時先看樂譜勾選框停用。
```

**Claude Code Instructions**

```text
[建議貼用方式]
直接貼給 Claude Code。CLAUDE.md 的專案規則持續適用。

[任務範圍]
做：四個分頁的版面（歌曲庫先放空狀態）、先看樂譜流程、ABC 編輯與上傳、進階設定、樂譜來源標示、成品頁。
不做：歌曲庫功能、草稿保存、Drive、五線譜或鋼琴捲簾顯示。

[需修改/新增的檔案清單]
修改 src/yue2_studio/{engine,generation_job,request_rules,app,ui_text,theme}.py、tests/fake_pipeline.py、
tests/test_{engine,generation_job,request_rules}.py。新增 tests/test_app_flows.py。

[具體步驟]
1. 讀規格的流程 B、「任務模型與資訊優先級」、「狀態模型與揭露策略」、「UI 元件清單」、「分步導覽策略」、「UI ↔ API Mapping」。
2. engine.plan() 回傳 PlanDraft；render() 支援 abc。編輯後的樂譜一律以新的 abc 輸入送出。
3. 從 yue2 原始碼找出請求前置檢查入口；可用則送出前檢查 ABC，否則捕捉 render 例外，轉成 E_ABC_INVALID。回報採用作法。
4. generation_job.run_plan()，終止狀態 score_ready。
5. request_rules.read_abc_file()：副檔名、200 KB、UTF-8；validate 加入 abc 與 cot 的相依規則。
6. app.py 依規格元件清單重排為四個分頁；實作勾選框切換主按鈕文字、cot 為 off 時停用勾選框、
   樂譜來源標示、上傳預覽、清除樂譜、階段完成自動切換分頁、成品頁與截斷警告。
7. 確認每個分頁只有一個 primary 按鈕，寫歌分頁在 1366x768 不需捲動。
8. event_log 加入 score_edited、abc_uploaded。

[輸出格式要求]
結束時回報：變更檔案清單、ABC 檢查作法、測試結果、Colab 手動步驟。不要 commit。

[測試要求]
涵蓋規格 T-02、T-14、T-15、T-16 與上傳規則；ruff 與 pytest 通過。

[驗收標準 DoD]
- 本機測試通過。
- Colab 手動：AC-07 通過；上傳規則正確；cot 為 off 時勾選框停用。
```

- **風險與回滾方式**：以相同 seed 先 `plan` 再帶 `abc` 生成，結果可能與一次完成的版本不同，這是預期行為，介面文案不得暗示兩者相同。若 `gr.Code` 對 ABC 的編輯體驗不佳，改用等寬字型的 `gr.Textbox`。回滾方式為還原本 Stage 的 commit，回到 Stage 2 的單頁介面。

---

### Stage 4：實作歌曲庫與狀態保存

- **目標**：每首歌存成獨立資料夾並可在歌曲庫管理；表單與樂譜自動保存；可選擇存到 Google Drive；提供重新開始。
- **前置條件**：Stage 3 完成。

**Codex Instructions**

```text
[建議貼用方式]
直接貼給 Codex。AGENTS.md 的專案規則持續適用。

[任務範圍]
做：song_store.py、draft_store.py、歌曲庫分頁、再做一版、重新開始、打包下載、Cell 2 的 Drive 選項、環境資訊區與釋放引擎。
不做：搜尋、標籤、多候選生成、MP3 轉檔。

[需修改/新增的檔案清單]
新增 src/yue2_studio/song_store.py、draft_store.py、tests/test_song_store.py、tests/test_draft_store.py。
修改 src/yue2_studio/{generation_job,app,ui_text,event_log}.py、YuE2_Colab_Studio.ipynb、tests/test_app_flows.py。

[具體步驟]
1. 讀規格的「核心資料模型」「State 管理與持久化」「UI 狀態保存與重新開始」「功能清單」的 F8 至 F17、
   「非功能需求」的安全性、「Edge / Abuse cases」。
2. song_store.py（唯一寫入 songs/ 的模組）：
   - create()：先在 songs/.tmp-<id>/ 呼叫 result.save_artifacts(artifacts/) 並寫入 studio.json，成功後原子改名為 songs/<id>/；
     失敗時刪除暫存資料夾並拋出 E_STORAGE，同時把 audio.flac 寫到 _rescue/。
   - song_id 格式 YYYYMMDD-HHMMSS-<4 位小寫英數>；所有接受 song_id 的函式先以正規表示式 ^[a-z0-9-]+$ 檢查，
     再確認解析後的路徑位於 songs/ 之內。
   - list_songs() 依 created_at 由新到舊；單筆 studio.json 損毀或缺檔時回傳標記為無法讀取的紀錄，不拋例外。
   - update(title, note)、delete()、export_zip()（輸出到工作目錄的 exports/）。
   - schema_version=1；讀取時缺少的欄位以預設值補齊，未知欄位保留。
3. draft_store.py：load()、save()、clear()；寫入採「寫暫存檔後改名」；檔案損毀時回傳空草稿並記錄事件。
4. generation_job.py：render 成功後進入 saving 並呼叫 song_store.create()；記錄 abc_source、parent_song_id、
   timing、peak_vram_gib、versions。移除 Stage 1 的暫存輸出路徑。
5. app.py：
   - demo.load：填回草稿、同步工作狀態、載入歌曲庫。
   - 表單與樂譜欄位變動後以 1 秒防抖呼叫 draft_store.save()。
   - 歌曲庫分頁：library_table 與 library_detail（播放、標題、備註、儲存、刪除、載回表單、下載 zip）。
     刪除與重新開始使用瀏覽器確認框（js 參數）。
   - 成品頁的 remix_btn 寫入 parent_song_id；download_zip 接上 export_zip。
   - restart_btn：確認後 draft_store.clear()，回到空白狀態並切回寫歌分頁；生成中停用。
   - env_acc：環境報告、版本、最近一首的耗時與峰值 VRAM、工作目錄大小、「釋放引擎」、「複製診斷資訊」；發生錯誤時自動展開。
   - 未使用 Drive 時，頁尾常駐一行提醒歌曲只存在本次執行階段。
6. Notebook Cell 2：表單參數 USE_DRIVE（布林）。為真時 google.colab.drive.mount 並使用 /content/drive/MyDrive/YuE2-Studio；
   為假時使用 /content/yue2_studio_data。權重快取永遠在 /content/hf_cache。
7. event_log：song_updated、song_deleted、song_exported、song_reloaded、draft_cleared、engine_released。

[輸出格式要求]
回報：變更檔案清單、測試結果、Colab 手動驗證步驟。

[測試要求]
涵蓋規格 T-06 至 T-09：建立中途失敗不留資料夾、路徑穿越被拒、損毀紀錄不影響清單、草稿讀寫與舊版補齊。
另加：改名與刪除、zip 內容包含 studio.json 與 artifacts、E_STORAGE 時救援檔存在。
測試使用 pytest 的 tmp_path，不寫入真實工作目錄。ruff 與 pytest 通過。

[驗收標準 DoD]
- 本機測試通過。
- Colab 手動：AC-08（重整後歌曲與表單仍在）、AC-09（改名與刪除）、AC-13（Drive 重開後恢復）通過。
- Colab 手動：按重新開始後表單清空，歌曲庫不受影響。
- 歌曲資料夾內有官方完整產物與 studio.json。
```

**Claude Code Instructions**

```text
[建議貼用方式]
直接貼給 Claude Code。CLAUDE.md 的專案規則持續適用。

[任務範圍]
做：song_store.py、draft_store.py、歌曲庫分頁、再做一版、重新開始、打包下載、Cell 2 的 Drive 選項、環境資訊區與釋放引擎。
不做：搜尋、標籤、多候選生成、MP3 轉檔。

[需修改/新增的檔案清單]
新增 src/yue2_studio/{song_store,draft_store}.py、tests/test_{song_store,draft_store}.py。
修改 src/yue2_studio/{generation_job,app,ui_text,event_log}.py、YuE2_Colab_Studio.ipynb、tests/test_app_flows.py。

[具體步驟]
1. 讀規格的「核心資料模型」「State 管理與持久化」「UI 狀態保存與重新開始」、功能 F8 至 F17、安全性需求、Edge cases。
2. song_store.py：暫存資料夾寫入後原子改名；song_id 以 ^[a-z0-9-]+$ 驗證並確認路徑在 songs/ 內；
   list_songs 對損毀紀錄容錯；update、delete、export_zip；schema_version=1 的向前相容讀取；E_STORAGE 時寫入 _rescue/。
3. draft_store.py：load、save（寫暫存檔後改名）、clear；損毀時回傳空草稿。
4. generation_job.py：成功後呼叫 song_store.create() 並記錄 abc_source、parent_song_id、timing、peak_vram_gib、versions。
5. app.py：demo.load 恢復草稿與工作狀態；1 秒防抖自動保存；歌曲庫清單與詳情；刪除與重新開始需確認；
   再做一版、打包下載、環境資訊區（釋放引擎、複製診斷資訊、錯誤時自動展開）；未用 Drive 時常駐提醒。
6. Notebook Cell 2：USE_DRIVE 表單參數與對應工作目錄；權重快取固定在 /content/hf_cache。
7. event_log 加入歌曲庫與草稿相關事件。

[輸出格式要求]
結束時回報：變更檔案清單、測試結果、Colab 手動步驟。不要 commit。

[測試要求]
涵蓋規格 T-06 至 T-09，加上改名刪除、zip 內容、救援檔；一律使用 tmp_path。ruff 與 pytest 通過。

[驗收標準 DoD]
- 本機測試通過。
- Colab 手動：AC-08、AC-09、AC-13 通過；重新開始不影響歌曲庫；歌曲資料夾內容完整。
```

- **風險與回滾方式**：Google Drive 掛載的檔案系統對「改名」的原子性與速度不如本機磁碟，若在 Drive 上出現不完整資料夾，改為先在 `/content` 完成再整個複製過去。刪除是不可復原的動作，必須保留確認步驟。回滾方式為還原本 Stage 的 commit；已建立的歌曲資料夾是獨立檔案，不受程式回滾影響。

---

### Stage 5：補齊整合、回歸與邊界測試

- **目標**：把規格中的驗收條件、測試案例與邊界情境全部落到自動化測試或明確的手動檢查表，達到覆蓋率門檻。
- **前置條件**：Stage 4 完成，功能凍結。

**Codex Instructions**

```text
[建議貼用方式]
直接貼給 Codex。AGENTS.md 的專案規則持續適用。本階段不得新增功能。

[任務範圍]
做：補測試、修正測試發現的缺陷、建立驗收對照表與 Colab 手動檢查表、設定 CI。
不做：新功能、介面調整、重構（除非是修正缺陷所必需，且需在回報中說明）。

[需修改/新增的檔案清單]
新增 tests/test_edge_cases.py、tests/test_regression_flows.py、docs/acceptance-matrix.md、docs/colab-manual-checklist.md、
.github/workflows/ci.yml。
修改既有 tests/ 檔案與 pyproject.toml（加入 pytest-cov 設定）。必要時修改 src/ 以修正缺陷。

[具體步驟]
1. 讀規格的「驗收條件」「測試案例」「Gherkin / BDD」「Edge / Abuse cases」。
2. docs/acceptance-matrix.md：一張表列出 AC-01 至 AC-15 與 T-01 至 T-18，各自對應到測試函式名稱或手動檢查表項目。
   沒有對應的項目視為缺口，必須補上。
3. tests/test_edge_cases.py 至少涵蓋：5 萬字歌詞被拒且內容保留；歌詞含 HTML 標籤原樣保存；連續兩次送出只有一個工作；
   二進位檔改名為 .abc 被拒；解碼階段取消被忽略；儲存失敗時救援檔存在；權重下載失敗重試 3 次後回報 E_MODEL_DOWNLOAD
   （以可注入的等待函式避免真的等待）；歌曲資料夾缺檔時顯示檔案不完整；工作逾時；含中文的曲風與歌詞在 studio.json 無亂碼。
4. tests/test_regression_flows.py：以假管線完整走過三個 Gherkin 情境。
5. 覆蓋率：pytest --cov=yue2_studio --cov-report=term-missing；engine.py 以外的模組行覆蓋率需達 80%。
   在 pyproject 設定排除 engine.py 中直接呼叫 yue2 的行。
6. CI：GitHub Actions，Python 3.12，安裝開發相依（ruff、pytest、pytest-cov、numpy、gradio 的釘死版本），不安裝 yue2-infer 與 torch；
   執行 ruff check 與 pytest。確認所有測試在沒有 torch 的環境下可執行（engine.py 的 torch 匯入需延後到函式內）。
7. docs/colab-manual-checklist.md：列出必須在 L4 手動執行的項目（AC-01 至 AC-08、AC-12、AC-13、T-17、T-18），
   每項含步驟、預期結果、勾選欄與日期欄。
8. 測試發現的每個缺陷：先寫出會失敗的測試，再修正，並在回報中逐項列出。

[輸出格式要求]
回報：新增測試數量、覆蓋率表、修正的缺陷清單、驗收對照表中仍需手動驗證的項目。

[測試要求]
ruff check . 零錯誤；pytest 全數通過；覆蓋率達標；CI 設定檔語法正確。

[驗收標準 DoD]
- AC-14 通過。
- docs/acceptance-matrix.md 沒有缺口。
- Colab 手動檢查表全部勾選完成並填上日期（由我執行後回填）。
- scripts/colab_smoke.py --repeat 5 在最終程式碼上再次通過。
```

**Claude Code Instructions**

```text
[建議貼用方式]
直接貼給 Claude Code。CLAUDE.md 的專案規則持續適用。本階段不得新增功能。
可把「跑完整檢查」存成 .claude/commands/verify.md，內容為依序執行 ruff check . 與 pytest --cov=yue2_studio 並回報結果。

[任務範圍]
做：補測試、修正測試發現的缺陷、驗收對照表、Colab 手動檢查表、CI。
不做：新功能、介面調整、非必要的重構。

[需修改/新增的檔案清單]
新增 tests/test_edge_cases.py、tests/test_regression_flows.py、docs/acceptance-matrix.md、docs/colab-manual-checklist.md、
.github/workflows/ci.yml。修改既有測試與 pyproject.toml；必要時修改 src/ 修正缺陷。

[具體步驟]
1. 讀規格的「驗收條件」「測試案例」「Gherkin / BDD」「Edge / Abuse cases」。
2. 建立 docs/acceptance-matrix.md，把 AC-01 至 AC-15、T-01 至 T-18 對應到測試函式或手動檢查項目，補齊缺口。
3. test_edge_cases.py：過長歌詞、HTML 標籤、重複送出、偽裝的 .abc、解碼時取消、儲存失敗救援、下載重試、缺檔歌曲、逾時、中文內容。
4. test_regression_flows.py：以假管線走過三個 Gherkin 情境。
5. 覆蓋率設定與門檻（engine.py 以外 80%）。
6. CI：Python 3.12，不安裝 yue2-infer 與 torch；確保測試在沒有 torch 時可執行。
7. docs/colab-manual-checklist.md：L4 手動項目、步驟、預期、勾選與日期欄。
8. 缺陷處理：先寫失敗測試再修正，逐項回報。

[輸出格式要求]
結束時回報：測試數量、覆蓋率表、缺陷清單、仍需手動驗證的項目。不要 commit。

[測試要求]
ruff 零錯誤；pytest 全過；覆蓋率達標。

[驗收標準 DoD]
- AC-14 通過；驗收對照表無缺口。
- Colab 手動檢查表完成並回填；煙霧測試 5 次再次通過。
```

- **風險與回滾方式**：測試可能揭露前面 Stage 的設計缺陷，例如 `engine.py` 在模組層級匯入 torch 導致 CI 無法執行。這類修正限制在最小範圍，並附上對應測試。若為了達到覆蓋率而寫出只為了數字的測試，寧可下修門檻並在驗收對照表說明原因。回滾方式為還原個別缺陷修正的 commit；新增的測試檔本身沒有回滾風險。

---

### Stage 6：完成文件與交付

- **目標**：讓第一次接觸的人只看 README 就能成功做出一首歌，並讓維護者知道如何升級上游版本。
- **前置條件**：Stage 5 完成，Colab 手動檢查表全數通過。

**Codex Instructions**

```text
[建議貼用方式]
直接貼給 Codex。AGENTS.md 的專案規則持續適用。本階段只動文件與 notebook 的說明文字，不改執行邏輯。

[任務範圍]
做：README、授權與第三方聲明、升級指引、已知問題、notebook 的說明儲存格、版本號與變更紀錄。
不做：功能變更、發布到任何平台、建立 release 或 tag（除非我另外要求）。

[需修改/新增的檔案清單]
修改 README.md、YuE2_Colab_Studio.ipynb（僅 Markdown 儲存格與各 cell 的註解）、src/yue2_studio/__init__.py（版本 0.1.0）、
docs/colab-baseline.md。
新增 THIRD_PARTY_NOTICES.md、docs/upgrading-yue2.md、docs/known-issues.md、CHANGELOG.md。

[具體步驟]
1. 讀規格的「範圍」「不做什麼」「非功能需求」的授權列、「風險與未決事項」，以及 docs/spec/ 下的白話版規格（若已放入）。
2. README.md（繁體中文）依序包含：
   一句話說明；Open in Colab 徽章（連結格式 https://colab.research.google.com/github/<owner>/<repo>/blob/main/YuE2_Colab_Studio.ipynb，
   owner 與 repo 以實際值填入，未知時保留佔位並在回報中提醒）；
   需求（Colab L4、運算單元、可選的 Google Drive）；三步驟啟動；做一首歌；先看樂譜再生成；歌曲庫；
   限制（直接採用白話版規格的「限制與注意事項」內容）；實測基準（引用 docs/colab-baseline.md 的數字與量測日期）；
   常見問題；授權（程式碼 Apache-2.0；YuE2 權重為 CC BY-NC 4.0 加創作者條款，連結上游 MODEL_LICENSE）；致謝；
   明確標示本專案為非官方專案。
   所有數字必須來自 docs/colab-baseline.md，沒有量測的項目寫「尚未量測」，不得估算。
3. THIRD_PARTY_NOTICES.md：列出 yue2-infer（Apache-2.0）、YuE2-3B 與 YuE2-Vae 權重、Gradio 及其授權與來源連結。
4. docs/upgrading-yue2.md：升級上游 commit 的步驟：
   改 requirements-colab.txt 的 SHA → 比對上游 pipeline.py 與 protocol.py 的介面差異 → 只修改 engine.py →
   跑本機測試 → 在 L4 跑 colab_smoke.py --repeat 5 與手動檢查表 → 更新 colab-baseline.md 與 CHANGELOG。
5. docs/known-issues.md：把 Stage 0 至 Stage 5 回報過但未解決的問題、Colab 的限制（L4 不保證分配、閒置斷線）、
   相同 seed 不保證重現等列入，每項含現象、原因、暫時作法。
6. Notebook：最上方加入說明儲存格（用途、需要 L4、結束時要中斷執行階段）；每個程式 cell 前加一句說明這格會做什麼、
   大約要等多久（引用實測數字）、成功時會看到什麼。
7. CHANGELOG.md：0.1.0 的功能清單。
8. 最後檢查：README 的每個步驟都與 notebook 實際行為一致；所有連結可開啟；文件不含 emoji。

[輸出格式要求]
回報：變更檔案清單、README 中仍為佔位或「尚未量測」的項目、需要我做的最終 Colab 走查步驟。

[測試要求]
ruff 與 pytest 仍然通過（確認沒有誤改程式）；notebook 檔案為合法 JSON 且可被 nbformat 讀取；README 內的相對連結指向存在的檔案。

[驗收標準 DoD]
- AC-15 通過：docs/colab-baseline.md 數字完整。
- 我以全新的 L4 runtime 只依照 README 操作，成功做出一首歌並在歌曲庫找到它。
- README 明確標示非官方專案與權重授權條款。
- 沒有任何未經量測的效能數字。
```

**Claude Code Instructions**

```text
[建議貼用方式]
直接貼給 Claude Code。CLAUDE.md 的專案規則持續適用。本階段只動文件與 notebook 的說明文字，不改執行邏輯。
升級流程適合做成可重複使用的指令：把 docs/upgrading-yue2.md 的步驟另存為 .claude/commands/upgrade-yue2.md。

[任務範圍]
做：README、授權與第三方聲明、升級指引、已知問題、notebook 說明儲存格、版本號與變更紀錄。
不做：功能變更、發布、建立 release 或 tag、commit 與 push（除非我另外要求）。

[需修改/新增的檔案清單]
修改 README.md、YuE2_Colab_Studio.ipynb（僅說明文字）、src/yue2_studio/__init__.py（版本 0.1.0）、docs/colab-baseline.md。
新增 THIRD_PARTY_NOTICES.md、docs/upgrading-yue2.md、docs/known-issues.md、CHANGELOG.md、.claude/commands/upgrade-yue2.md。

[具體步驟]
1. 讀規格的「範圍」「不做什麼」、授權需求、「風險與未決事項」與白話版規格。
2. README.md（繁體中文）：一句話說明、Open in Colab 徽章、需求、三步驟啟動、做一首歌、先看樂譜再生成、歌曲庫、限制、
   實測基準（只引用 docs/colab-baseline.md，缺的寫「尚未量測」）、常見問題、授權、致謝、非官方專案聲明。
3. THIRD_PARTY_NOTICES.md：yue2-infer、YuE2-3B 與 YuE2-Vae 權重、Gradio 的授權與來源。
4. docs/upgrading-yue2.md：改 SHA → 比對上游介面 → 只改 engine.py → 本機測試 → L4 煙霧測試與手動檢查表 → 更新基準與 CHANGELOG。
5. docs/known-issues.md：現象、原因、暫時作法。
6. Notebook 加入開頭說明與每個 cell 的用途、等待時間（實測）、成功時的畫面。
7. CHANGELOG.md 寫入 0.1.0。
8. 檢查 README 與 notebook 行為一致、連結有效、文件不含 emoji。

[輸出格式要求]
結束時回報：變更檔案清單、佔位與「尚未量測」項目、最終 Colab 走查步驟。不要 commit。

[測試要求]
ruff 與 pytest 仍通過；notebook 可被 nbformat 讀取；README 相對連結有效。

[驗收標準 DoD]
- AC-15 通過。
- 我只依 README 在全新 L4 runtime 成功做出一首歌。
- README 有非官方聲明與權重授權條款；沒有未經量測的效能數字。
```

- **風險與回滾方式**：文件最常見的問題是與實際行為不一致，因此 DoD 要求由真人在全新 runtime 只照 README 走一遍。若走查失敗，修正的是文件或回到對應 Stage 修正程式，不在本 Stage 臨時改邏輯。回滾方式為還原文件 commit，不影響功能。
