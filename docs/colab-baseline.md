# Colab L4 實測基準

這份文件只記錄在 Colab L4 上實際量到的數字。沒有量測的欄位保持「尚未量測」，不填估計值。

量測方式：依序執行 notebook 三格，然後在 Colab 終端機執行

```bash
cd /content/yue2-colab-studio && PYTHONPATH=src python scripts/colab_smoke.py --repeat 5
```

把輸出表格貼到下方對應欄位，並填上日期。

## 環境

| 項目 | 數值 | 量測日期 |
|---|---|---|
| GPU 名稱 | 尚未量測 | |
| GPU 記憶體（GiB） | 尚未量測 | |
| 主機記憶體（GiB） | 尚未量測 | |
| Python 版本 | 尚未量測 | |
| torch / yue2 / gradio 版本 | 尚未量測 | |
| `pip check` 結果 | 尚未量測 | |

## 啟動耗時

| 項目 | 秒數 | 量測日期 |
|---|---|---|
| 第一格：卸載 torchvision、torchaudio | 尚未量測 | |
| 第一格：安裝 requirements-colab.txt | 尚未量測 | |
| 權重下載（YuE2-3B 與 YuE2-Vae） | 尚未量測 | |
| 引擎載入（權重已快取） | 尚未量測 | |

## 生成（官方範例 examples/song.json，cot=full）

| 次數 | 規劃（秒） | 譜寫（秒） | 聲音合成（秒） | 解碼（秒） | 總計（秒） | 音訊長度（秒） | 峰值 VRAM（GiB） | 是否截斷 |
|---|---|---|---|---|---|---|---|---|
| 1 | 尚未量測 | | | | | | | |
| 2 | 尚未量測 | | | | | | | |
| 3 | 尚未量測 | | | | | | | |
| 4 | 尚未量測 | | | | | | | |
| 5 | 尚未量測 | | | | | | | |

## 已釘死的版本

| 項目 | 版本 |
|---|---|
| YuE（yue2-infer 0.1.6）commit | `1116bea76032bee5668e5f097294d082fa0b84f0` |
| m-a-p/YuE2-3B revision | `8f24312f187763b9854adeec87e437e2b03bbff1` |
| m-a-p/YuE2-Vae revision | `152733a19ad43aa67e367f9b5503ef8075bb5126` |
| gradio | 6.17.3 |

模型 revision 取自 2026-11-11 的 Hugging Face API。Gradio 版本是在 Windows、Python 3.13 上以
`pip install --dry-run` 對 `huggingface-hub==0.36.2`、`numpy==2.2.6` 解析得到，尚未在 Colab 上確認。
