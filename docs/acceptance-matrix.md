# 驗收對照表

狀態分三種，不混用：

- **自動測試通過**：有不需 GPU 的測試覆蓋，本機與 CI 都會執行。
- **本機瀏覽器實測**：2026-11-11 以替身引擎（不是真的 YuE2）在瀏覽器中操作確認過。
- **待 L4 實測**：只有在 Colab L4 上才能確認，目前沒有任何證據。完成後請在 `colab-manual-checklist.md` 勾選並填日期。

## 驗收條件

| 編號 | 條件摘要 | 自動測試 | 狀態 |
|---|---|---|---|
| AC-01 | T4 在第一格被擋下 | `test_notebook_steps.py::test_cell_one_stops_before_installing_on_t4`、`test_environment.py::test_t4_fails_on_capability_and_memory`、`test_regression_flows.py::test_scenario_unsupported_runtime` | 邏輯自動測試通過；待 L4／T4 實測 |
| AC-02 | 全新 L4 依序執行三格即可開啟介面 | 無 | 使用者回報通過（2026-11-12，0.1.1） |
| AC-03 | 官方範例生成可播放的 48 kHz 立體聲 FLAC | 無 | 使用者回報生成成功（2026-11-12，0.1.1）；取樣率與聲道未由檔案確認 |
| AC-04 | 峰值 VRAM 低於 20 GiB，連續 5 次無 OOM | 無 | 待 L4 實測 |
| AC-05 | 狀態列出現三個階段，更新間隔不超過 2 秒 | `test_app_flows.py::test_status_bar_shows_each_stage`、`test_engine.py::test_stage_events_follow_the_pipeline_order` | 階段順序自動測試通過；本機瀏覽器實測；真實間隔待 L4 實測 |
| AC-06 | 取消後 30 秒內恢復，歌曲庫無新增 | `test_generation_job.py::test_cancel_during_composing`、`test_regression_flows.py::test_scenario_cancel_while_composing` | 自動測試通過；本機瀏覽器實測；真實模型的取消延遲待 L4 實測 |
| AC-07 | 修改後的樂譜與成品 `score.abc` 相同 | `test_generation_job.py::test_render_with_an_edited_score`、`test_regression_flows.py::test_scenario_edit_the_score_then_generate` | 自動測試通過；待 L4 實測 |
| AC-08 | 重新整理後歌曲與表單仍在 | `test_app_flows.py::test_draft_survives_a_reload`、`test_page_load_after_a_finished_job_shows_the_song`、`test_edge_cases.py::test_reload_during_a_job_picks_up_the_status` | 自動測試通過；本機瀏覽器實測（含重啟伺服器） |
| AC-09 | 改名立即更新；刪除後資料夾不存在 | `test_song_store.py::test_update_title_and_note`、`test_delete_removes_the_folder`、`test_app_flows.py::test_select_and_rename`、`test_delete_is_two_steps` | 自動測試通過 |
| AC-10 | 上傳規則 | `test_request_rules.py::test_bad_uploads_are_rejected`、`test_app_flows.py::test_upload_shows_the_file_as_a_preview`、`test_rejected_upload_leaves_the_editor_alone` | 自動測試通過 |
| AC-11 | 生成中再次送出收到 E_BUSY | `test_generation_job.py::test_second_request_is_rejected_while_one_runs`、`test_edge_cases.py::test_double_click_starts_only_one_job` | 自動測試通過 |
| AC-12 | 勾選 `USE_PASSCODE` 時，沒有通行碼無法進入（0.2.0 起通行碼為選用，預設關閉，使用者決定） | `test_notebook_steps.py::test_cell_two_with_passcode_prints_it`、`test_launch_command_*`、`test_launch_refuses_a_public_link_without_a_choice` | 指令組成自動測試通過；登入畫面待 L4 實測 |
| AC-16 | 每首歌可下載 320 kbps MP3；舊歌第一次顯示時補轉；轉檔失敗不影響保存（0.2.0 新增） | `test_audio_export.py`（含真實 ffmpeg 轉檔與 ffprobe 檢查） | 自動測試通過；本機瀏覽器實測（替身引擎）；待 L4 實測 |
| AC-17 | 不勾選 `USE_PASSCODE` 時打開連結即可使用（0.2.0 新增） | `test_notebook_steps.py::test_launch_command_without_passcode_opts_out_explicitly` | 待 L4 實測 |
| AC-13 | 使用 Drive 重開後恢復 | `test_notebook_steps.py::test_cell_two_drive_mounts_and_uses_drive_folder`（只驗路徑選擇） | 待 L4 實測 |
| AC-14 | 測試全過、覆蓋率 80% 以上、ruff 零錯誤 | 全部 | 通過：211 個測試、覆蓋率 96%（2026-11-11，本機 Python 3.13）。CI 結果見 GitHub Actions |
| AC-15 | `colab-baseline.md` 數字完整 | 無 | 待 L4 實測，目前全部為「尚未量測」 |

## 測試案例

| 編號 | 對應測試 |
|---|---|
| T-01 | `test_request_rules.py::test_blank_style_is_rejected` |
| T-02 | `test_request_rules.py::test_abc_with_cot_off_is_rejected`、`test_app_flows.py::test_score_with_cot_off_is_a_field_error` |
| T-03 | `test_request_rules.py::test_bad_seeds_are_rejected` |
| T-04 | `test_request_rules.py::test_empty_lyrics_are_accepted` |
| T-05 | `test_environment.py`（T4、L4、A100、無 GPU、舊驅動、未知型號） |
| T-06 | `test_song_store.py::test_failed_create_leaves_no_folder_and_rescues_audio` |
| T-07 | `test_song_store.py::test_unsafe_ids_are_refused_before_touching_disk`、`test_delete_outside_the_library_is_impossible` |
| T-08 | `test_song_store.py::test_corrupt_record_does_not_hide_the_others` |
| T-09 | `test_draft_store.py::test_save_and_load`、`test_older_draft_gets_defaults_for_new_fields` |
| T-10 | `test_engine.py::test_stage_events_follow_the_pipeline_order` |
| T-11 | `test_generation_job.py::test_cancel_during_composing` |
| T-12 | `test_generation_job.py::test_out_of_memory_fails_and_the_next_job_reloads` |
| T-13 | `test_generation_job.py::test_second_request_is_rejected_while_one_runs` |
| T-14 | `test_app_flows.py::test_generate_ends_on_the_result_tab` |
| T-15 | `test_app_flows.py::test_render_from_an_edited_score` |
| T-16 | `test_app_flows.py::test_truncated_song_shows_the_notice` |
| T-17 | 手動：`scripts/colab_smoke.py --repeat 5`。待 L4 實測 |
| T-18 | `test_edge_cases.py::test_chinese_request_is_stored_readably`（保存）；真實生成待 L4 實測 |

## Edge / Abuse cases

| 情境 | 對應測試 |
|---|---|
| 歌詞 5 萬字 | `test_edge_cases.py::test_very_long_lyrics_are_refused_and_the_draft_keeps_them` |
| 歌詞含 HTML | `test_edge_cases.py::test_markup_in_lyrics_is_stored_verbatim_and_escaped_in_errors`、`test_app_flows.py::test_error_panel_escapes_details` |
| 連點主按鈕 | `test_edge_cases.py::test_double_click_starts_only_one_job` |
| 生成中重新整理 | `test_edge_cases.py::test_reload_during_a_job_picks_up_the_status`、`test_generation_job.py::test_job_survives_an_abandoned_generator` |
| 二進位檔改名 | `test_edge_cases.py::test_binary_file_renamed_to_abc_is_refused` |
| 多餘聲部 | `test_edge_cases.py::test_extra_voice_in_a_score_is_passed_through` |
| 解碼階段取消 | `test_edge_cases.py::test_cancel_during_decoding_reports_too_late` |
| 儲存空間不足 | `test_edge_cases.py::test_full_storage_shows_the_rescue_path` |
| 下載中斷 | `test_engine.py::test_download_is_retried_three_times_then_reported`、`test_generation_job.py::test_download_retry_is_surfaced_as_a_notice` |
| 檔案不完整 | `test_edge_cases.py::test_song_with_missing_audio_is_listed_as_incomplete` |
| 工作逾時 | `test_generation_job.py::test_timeout_stops_the_job` |
| 分享連結外流 | 預設不需登入（使用者決定），連結本身即是存取權；需要分享時勾選 `USE_PASSCODE`（AC-12） |
| Colab 斷線、runtime 回收 | 無法自動測試；見 `known-issues.md` |

## 實作與規格的差異

規格（`spec/01-technical-spec.md`）寫於實作之前，以下幾點在實作時調整：

| 規格 | 實作 | 原因 |
|---|---|---|
| 本專案的請求物件叫 `SongRequest` | 改名為 `StudioRequest` | 與上游 `yue2.protocol.SongRequest` 同名會混淆 |
| 測試替身放在 `tests/fake_pipeline.py` | `src/yue2_studio/stand_in_pipeline.py` | 本機預覽（`launch --stand-in`）也要用 |
| 第三格在 notebook 核心內啟動 Gradio | 以子行程啟動 `yue2_studio.launch` | 核心可能還留著第一格換掉之前的 torch、numpy 模組 |
| 歌曲庫用表格點選 | 單選清單 | Gradio 6.17.3 的表格點選事件在瀏覽器實測中沒有觸發 |
| 文字欄位用 `.input` 事件自動保存 | 用 `.change` | 同上，`.input` 在實測中沒有觸發 |
| 刪除與重新開始用瀏覽器確認框 | 二段式按鈕 | 不依賴自訂 JavaScript |
| 曲風為空時主按鈕停用 | 按下後顯示欄位錯誤 | 狀態輪詢會覆寫按鈕狀態，改由驗證訊息處理較單純 |
| 逾時以 `E_UNKNOWN` 回報 | 新增 `E_TIMEOUT` | 訊息與處理建議不同 |
| 介面元件 `library_table`、`library_ids_state` | `library_radio` | 見上 |
| 資料夾 `docs/spec/` | `spec/` | 規格先於 repo 存在，保留原位置 |
| `gr.Blocks(theme=, css=)`、`show_api=False` | `launch(theme=, css=, footer_links=[])`，事件設 `api_visibility="private"` | Gradio 6 的參數位置不同 |
| 不做 MP3 轉檔 | 0.2.0 起自動轉出 320 kbps MP3 | 使用者要求（2026-11-12） |
| 分享連結預設需要通行碼 | 0.2.0 起通行碼為選用，預設關閉 | 使用者要求直接進入（2026-11-12）；連結公開的風險寫在第二格說明與 README |
| 規格未定義下載按鈕的顯示切換 | MP3 按鈕固定顯示，只切換可用狀態 | 瀏覽器實測時 Gradio 6.17.3 對反覆顯示又隱藏的按鈕，之後的可見度更新不再生效 |
