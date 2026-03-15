# Simple ASR

在 macOS (Apple Silicon) 上用 [Qwen3-ASR](https://huggingface.co/Qwen/Qwen3-ASR-1.7B) 做語音轉文字的 CLI 工具。

按 Enter 開始錄音，再按 Enter 停止，辨識結果會自動複製到剪貼簿。

## 功能

- 使用 Qwen3-ASR-1.7B 模型，支援中文（普通話）與英文混合辨識
- 自動偵測 MPS (Metal Performance Shaders) 加速，無 MPS 則退回 CPU
- 辨識結果自動透過 OpenCC 轉換為繁體中文（台灣正體）
- 結果自動複製到系統剪貼簿

## 系統需求

- macOS（Apple Silicon 建議）
- Python >= 3.13
- 麥克風權限

## 安裝

使用 [uv](https://docs.astral.sh/uv/) 管理相依套件：

```bash
uv sync
```

## 使用方式

```bash
uv run python app.py
```

啟動後：

1. 按 **Enter** 開始錄音
2. 再按 **Enter** 停止錄音並開始辨識
3. 辨識結果會顯示在終端機並自動複製到剪貼簿
4. 輸入 **q** 離開程式

## 相依套件

| 套件          | 用途                 |
| ------------- | -------------------- |
| `qwen-asr`    | Qwen3-ASR 模型推論   |
| `torch`       | PyTorch 深度學習框架 |
| `sounddevice` | 麥克風錄音           |
| `numpy`       | 音訊資料處理         |
| `opencc`      | 簡體轉繁體中文       |

## 授權

MIT
