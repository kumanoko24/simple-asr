# 2026-03-15 Project Init — Qwen3-ASR Voice-to-Text CLI

## 完成的目標
- uv init --python 3.13 初始化專案
- 撰寫 app.py：純 terminal CLI（棄用 Textual TUI）
- 麥克風權限檢測（錄 0.1s 測試是否靜音）
- 音量檢測（peak/rms 日誌，靜音警告）
- 自動複製結果到剪貼簿（pbcopy）
- 中英混合語音辨識（language=None + context 提示）

## 架構變更
- v1: Textual TUI → 棄用（tqdm/multiprocessing fd 問題 + 無法選取文字）
- v2: 純 terminal CLI（print 輸出，text 可選取，Enter 控制錄音）

## 遇到的錯誤及解法
### tqdm multiprocessing.RLock ValueError (已不適用，Textual 已棄用)
- Textual worker thread 中 tqdm 建立 multiprocessing lock 時 fd=-1

### 麥克風權限 — 音頻全是零
- macOS 未授權終端機存取麥克風 → 錄到的全是 0.0
- 解法：啟動時錄 0.1s 測試，若 peak < 1e-6 則提示用戶去 System Settings 開權限

### Rich markup 吞語言標籤
- `[en]` 被 RichLog(markup=True) 當成 tag → 需要 `\[en]` 跳脫
- 純 terminal 版本不用 Rich，無此問題

## 啟動方式
```bash
uv run python app.py
```

## 使用方式
- Enter 開始錄音
- Enter 停止錄音 → 自動轉錄
- 結果自動複製到剪貼簿
- q 退出
