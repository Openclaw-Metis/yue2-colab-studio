"""Every user-facing string, in Traditional Chinese.

Kept in one module so wording can be reviewed without reading UI code.
"""

from __future__ import annotations

APP_TITLE = "YuE2 Colab 寫歌工作室"

# --- Stages -----------------------------------------------------------------

STAGE_LABELS = {
    "idle": "就緒",
    "loading": "正在載入作曲引擎（第一次需要下載，會比較久）",
    "planning": "作曲規劃中",
    "composing": "譜寫內容中",
    "rendering": "聲音合成中",
    "decoding": "音訊解碼中",
    "saving": "保存中",
    "score_ready": "樂譜完成，請到「2 樂譜」確認",
    "done": "歌曲完成",
    "failed": "發生問題",
    "cancelled": "已取消",
}

RUNNING_STATES = ("loading", "planning", "composing", "rendering", "decoding", "saving")

# --- Errors -----------------------------------------------------------------

ERRORS = {
    "E_ENV_GPU": (
        "這個執行階段不是 L4。請到「執行階段 → 變更執行階段類型」選擇 L4 GPU 後重新執行。"
    ),
    "E_ENV_INSTALL": "安裝套件失敗。請選「執行階段 → 中斷並刪除執行階段」後重新執行。",
    "E_MODEL_DOWNLOAD": "下載作曲引擎失敗，請檢查網路後按重試。",
    "E_VALIDATION": "有欄位需要修正。",
    "E_ABC_INVALID": "樂譜格式有問題。可以按「清除樂譜」改回由引擎規劃。",
    "E_OOM": "顯示卡記憶體不足。請縮短歌詞後重試，或到「環境資訊」按「釋放引擎」後再試一次。",
    "E_CANCELLED": "已取消",
    "E_BUSY": "目前有歌曲正在生成，請等它完成或先取消。",
    "E_STORAGE": "無法保存歌曲。成品已暫存在執行階段內，請先下載。",
    "E_TIMEOUT": "生成時間過長，已自動停止。",
    "E_UNKNOWN": "發生未預期的錯誤。",
}

ERROR_NEXT_STEP = {
    "E_MODEL_DOWNLOAD": "確認 Colab 仍在連線後再按一次主要按鈕。",
    "E_ABC_INVALID": "回到「2 樂譜」修正，或清除樂譜後重新產生。",
    "E_OOM": "縮短歌詞，或釋放引擎後重試。",
    "E_STORAGE": "到「歌曲庫」下方的救援資料夾說明取得檔案，並確認儲存空間。",
    "E_TIMEOUT": "縮短歌詞後重試。",
    "E_UNKNOWN": "展開頁面下方的「環境資訊」，複製診斷資訊後回報。",
}

# --- Field validation -------------------------------------------------------

STYLE_EMPTY = "曲風不能是空的"
STYLE_TOO_LONG = "曲風最多 {limit} 字，目前 {count} 字"
LYRICS_TOO_LONG = "歌詞最多 {limit} 字，目前 {count} 字"
COT_INVALID = "規劃方式不正確"
SEED_INVALID = "隨機種子必須是 0 到 2147483647 之間的整數"
CFG_INVALID = "文字引導強度必須在 1.0 到 2.0 之間"
ABC_NEEDS_PLANNING = "使用樂譜時，規劃方式不能選「不規劃」"
ABC_TOO_LARGE = "樂譜最多 200 KB"
ABC_WRONG_TYPE = "只接受 .abc 或 .txt 檔"
ABC_NOT_TEXT = "這個檔案不是文字格式的樂譜"
ABC_EMPTY = "這個檔案沒有內容"

FIELD_NAMES = {
    "style": "曲風",
    "lyrics": "歌詞",
    "cot": "規劃方式",
    "seed": "隨機種子",
    "cfg_scale": "文字引導強度",
    "abc": "樂譜",
}

# --- Compose tab ------------------------------------------------------------

TAB_COMPOSE = "1 寫歌"
TAB_SCORE = "2 樂譜"
TAB_RESULT = "3 成品"
TAB_LIBRARY = "歌曲庫"

STYLE_LABEL = "曲風"
STYLE_INFO = "寫下語言、音樂類型、樂器、歌聲特色、速度，例如 88 BPM。最多 1000 字。"
LYRICS_LABEL = "歌詞"
LYRICS_INFO = "用 [Verse]、[Chorus] 分段。留空可嘗試純音樂，但不保證沒有人聲。最多 5000 字。"
FILL_EXAMPLE = "填入範例"
SCORE_FIRST_LABEL = "先看樂譜再生成"
SCORE_FIRST_DISABLED = "選擇「不規劃」時沒有樂譜可看"
BTN_GENERATE = "生成歌曲"
BTN_PLAN = "產生樂譜"
BTN_CANCEL = "取消"
BTN_RESTART = "重新開始"
BTN_RESTART_CONFIRM = "確定清空"
BTN_BACK = "先不要"
RESTART_WARNING = "會清空目前的曲風、歌詞與樂譜。已完成的歌曲不受影響。"
NEED_STYLE = "請先填寫曲風"
COUNTER = "曲風 {style} / {style_limit} 字　歌詞 {lyrics} / {lyrics_limit} 字"

ADVANCED_LABEL = "進階設定（多數時候不需要打開）"
COT_LABEL = "規劃方式"
COT_CHOICES = [
    ("旋律加和弦（建議）", "full"),
    ("只規劃旋律", "melody"),
    ("不規劃", "off"),
]
SEED_LABEL = "隨機種子"
SEED_INFO = "留空表示每次隨機。相同的隨機種子不保證做出完全相同的歌。"
CFG_AUTO_LABEL = "文字引導強度使用預設值"
CFG_LABEL = "文字引導強度"
CFG_INFO = "數值越高越貼近曲風描述，但可能影響品質。"

# --- Score tab --------------------------------------------------------------

SCORE_EMPTY = "還沒有樂譜。回到「1 寫歌」，勾選「先看樂譜再生成」後按「產生樂譜」，或在下方上傳自己的樂譜。"
SCORE_VOICES_NOTE = "樂譜使用 ABC 文字格式，只支援 Vocal 與 Ins 兩個聲部。改樂譜會重做整首歌。"
SCORE_LABEL = "樂譜"
SCORE_SOURCE = {
    "none": "",
    "planned": "樂譜來源：引擎規劃",
    "edited": "樂譜來源：你修改過",
    "uploaded": "樂譜來源：你上傳的",
}
BTN_RENDER_FROM_SCORE = "用這份樂譜生成"
BTN_CLEAR_SCORE = "清除樂譜"
UPLOAD_LABEL = "上傳自己的樂譜（.abc 或 .txt，最多 200 KB）"
UPLOAD_LOADED = "樂譜已載入，請確認內容"

# --- Result tab -------------------------------------------------------------

RESULT_EMPTY = "還沒有成品。回到「1 寫歌」填好內容後按「生成歌曲」。"
RESULT_AUDIO_LABEL = "成品"
TRUNCATED_NOTICE = "**請留意：** 長度達上限，歌曲可能提前結束。"
BTN_DOWNLOAD_AUDIO = "下載音訊（FLAC）"
BTN_PACK = "打包完整產物"
PACK_LABEL = "完整產物（壓縮檔）"
RESULT_SCORE_LABEL = "這首歌的樂譜"
BTN_REMIX = "以此為基礎再做一版"
SONG_DONE_TOAST = "歌曲完成"

# --- Library tab ------------------------------------------------------------

LIBRARY_EMPTY = "還沒有歌曲。做好的歌會出現在這裡。"
LIBRARY_PICK = "選一首歌來播放與管理"
BTN_REFRESH = "重新整理清單"
TITLE_LABEL = "名稱"
NOTE_LABEL = "備註"
BTN_SAVE_META = "儲存名稱與備註"
BTN_LOAD_TO_FORM = "載回表單再做一版"
BTN_DELETE = "刪除這首歌"
BTN_DELETE_CONFIRM = "確定刪除，無法復原"
SAVED_TOAST = "已保存"
DELETED_TOAST = "已刪除"
SONG_UNREADABLE = "（無法讀取）"
SONG_INCOMPLETE = "（檔案不完整）"
PARENT_DELETED = "來源已刪除"
TITLE_INVALID = "名稱需為 1 到 80 字"
NOTE_INVALID = "備註最多 500 字"

# --- Environment ------------------------------------------------------------

ENV_LABEL = "環境資訊（出問題時會自動打開）"
BTN_RELEASE_ENGINE = "釋放引擎"
BTN_DIAGNOSTICS = "產生診斷資訊"
DIAGNOSTICS_LABEL = "診斷資訊（不含歌詞，可複製後回報）"
ENGINE_RELEASED_TOAST = "引擎已釋放"
ENGINE_BUSY = "生成中無法釋放引擎"
ENGINE_STATES = {
    "unloaded": "未載入",
    "loading": "載入中",
    "ready": "已就緒",
    "error": "需要重新載入",
}

EPHEMERAL_WARNING = (
    "歌曲目前只存在這次的執行階段，關閉後會消失。請記得下載，"
    "或在筆記本第二格改用 Google 雲端硬碟保存。"
)
LICENSE_FOOTER = (
    "本專案為非官方工具。作曲引擎 YuE2 由 M-A-P 提供，權重採 CC BY-NC 4.0 加創作者條款："
    "個人創作者可使用並從成品獲利，學術研究限非商業用途，公司商業使用需另洽原團隊授權。"
    "[完整條款](https://github.com/multimodal-art-projection/YuE/blob/main/MODEL_LICENSE)"
)

# --- Misc -------------------------------------------------------------------

CANCEL_TOO_LATE = "即將完成，無法取消"
CANCEL_REQUESTED = "正在取消，請稍候"
DOWNLOAD_RETRY = "下載中斷，重試第 {attempt} 次"
ELAPSED = "已經過 {minutes:02d}:{seconds:02d}"
ERROR_CODE = "代碼"
ERROR_NEXT = "下一步"

EXAMPLE_STYLE = (
    "English, warm piano pop, expressive female voice, acoustic piano, "
    "rounded bass and light drums, lyrical memorable melody, unhurried phrasing, 88 BPM"
)
EXAMPLE_LYRICS = (
    "[Verse]\n"
    "Neon fades along the lane\n"
    "Footsteps keep the time of rain\n"
    "Fold the night and leave it here\n"
    "Morning has a sky to clear\n"
    "\n"
    "[Chorus]\n"
    "Let the day come into view\n"
    "Every road begins with you\n"
    "Hold a little room for light\n"
    "We will sing beyond the night"
)

# --- Notebook ---------------------------------------------------------------

ENV_OK = "環境檢查通過"
ENV_NO_GPU = "找不到 NVIDIA GPU。"
ENV_GPU_TOO_OLD = "目前的 GPU 是 {name}，不支援 YuE2 需要的運算格式。"
ENV_VRAM_TOO_SMALL = "目前的 GPU 記憶體是 {vram:.1f} GiB，至少需要 {need:.0f} GiB。"
ENV_GPU_UNKNOWN = "無法判斷 GPU 型號（{name}）。"
INSTALL_FAILED_STEP = "失敗的步驟：{step}"
UNRELATED_CONFLICTS = (
    "以下是 Colab 預裝套件的相依提醒，與本工具無關，可以忽略。"
    "但同一個執行階段內請不要再使用這些套件（例如 fastai、timm、diffusers）："
)
CELL_ONE_FIRST ="請先執行第一格，並確認看到「環境檢查通過」。"
CELL_TWO_FIRST = "請先執行第二格。"
PASSCODE_NOTICE = "這次的登入帳號是 studio，通行碼是：{passcode}"
WORKDIR_NOTICE = "歌曲會保存在：{workdir}"
LAUNCHING = "正在啟動介面，出現連結後點開並輸入通行碼。要結束時請中斷這一格。"
