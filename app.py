"""Qwen3-ASR Voice-to-Text CLI — press Enter to start/stop recording."""

from __future__ import annotations

import os
import platform
import subprocess
import sys
import threading
import time

import numpy as np
import sounddevice as sd

os.environ["PYTORCH_ENABLE_MPS_FALLBACK"] = "1"
os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"

SAMPLE_RATE = 16_000  # 16 kHz mono, required by Qwen3-ASR

# ── Colors ────────────────────────────────────────────────────────

RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
DIM = "\033[2m"
BOLD = "\033[1m"
RESET = "\033[0m"


# ── Audio Recorder ────────────────────────────────────────────────


class AudioRecorder:
    def __init__(self, samplerate: int = SAMPLE_RATE) -> None:
        self._samplerate = samplerate
        self._lock = threading.Lock()
        self._chunks: list[np.ndarray] = []
        self._stream: sd.InputStream | None = None

    def _callback(self, indata: np.ndarray, frames, time_info, status) -> None:
        with self._lock:
            self._chunks.append(indata.copy())

    def start(self) -> None:
        with self._lock:
            self._chunks.clear()
        self._stream = sd.InputStream(
            samplerate=self._samplerate,
            channels=1,
            dtype="float32",
            callback=self._callback,
        )
        self._stream.start()

    def stop(self) -> np.ndarray:
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        with self._lock:
            if not self._chunks:
                return np.array([], dtype=np.float32)
            audio = np.concatenate(self._chunks, axis=0).squeeze()
            self._chunks.clear()
        return audio


# ── Clipboard ─────────────────────────────────────────────────────


def copy_to_clipboard(text: str) -> bool:
    try:
        subprocess.run(["pbcopy"], input=text.encode(), check=True)
        return True
    except Exception:
        return False


# ── Main ──────────────────────────────────────────────────────────


def main() -> None:
    print(f"{BOLD}Qwen3-ASR Voice-to-Text{RESET}")
    print(f"{DIM}{'─' * 50}{RESET}")

    # System info
    print(f"{DIM}System:  {platform.platform()}{RESET}")
    print(f"{DIM}Python:  {platform.python_version()}{RESET}")

    import torch

    print(f"{DIM}PyTorch: {torch.__version__}{RESET}")

    if torch.backends.mps.is_available():
        print(f"{GREEN}MPS backend: available{RESET}")
    else:
        print(f"{YELLOW}MPS backend: not available — will use CPU{RESET}")

    # Mic detection
    try:
        default_input = sd.query_devices(kind="input")
        print(
            f"{GREEN}Microphone:{RESET} {default_input['name']} "
            f"{DIM}(ch={default_input['max_input_channels']}, "
            f"sr={default_input['default_samplerate']}Hz){RESET}"
        )
    except Exception as e:
        print(f"{RED}Microphone error: {e}{RESET}")
        sys.exit(1)

    # Request microphone permission via AVFoundation (triggers macOS popup)
    print(f"{DIM}Requesting microphone permission…{RESET}", end=" ", flush=True)
    try:
        result = subprocess.run(
            [
                "swift",
                "-e",
                "import AVFoundation;"
                "let s = DispatchSemaphore(value: 0);"
                'AVCaptureDevice.requestAccess(for: .audio) { g in print(g ? "granted" : "denied"); s.signal() };'
                "s.wait();",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        status = result.stdout.strip()
        if status == "denied":
            print(f"{RED}DENIED{RESET}")
            print()
            print(f"{RED}{BOLD}Microphone permission denied!{RESET}")
            print(
                f"Go to: {BOLD}System Settings → Privacy & Security → Microphone{RESET}"
            )
            print(f"Enable access for your terminal app (Terminal / iTerm2 / etc.)")
            print(f"{DIM}Then restart the terminal.{RESET}")
            sys.exit(1)
        print(f"{GREEN}{status}{RESET}")
    except Exception:
        print(f"{YELLOW}skipped (swift not found){RESET}")
    print(f"{GREEN}OK{RESET}")

    print(f"{DIM}{'─' * 50}{RESET}")

    # Load model
    device = "mps" if torch.backends.mps.is_available() else "cpu"
    dtype = torch.float16 if device == "mps" else torch.float32
    print(
        f"Loading model {BOLD}Qwen/Qwen3-ASR-1.7B{RESET} {DIM}(device={device}, dtype={dtype}){RESET}"
    )

    from pathlib import Path

    cache_dir = (
        Path.home() / ".cache" / "huggingface" / "hub" / "models--Qwen--Qwen3-ASR-1.7B"
    )
    if cache_dir.exists():
        print(f"{DIM}  Model found in local cache{RESET}")
    else:
        print(f"{YELLOW}  Model not cached — downloading (~3.4 GB)…{RESET}")

    from qwen_asr import Qwen3ASRModel

    t0 = time.monotonic()
    try:
        model = Qwen3ASRModel.from_pretrained(
            "Qwen/Qwen3-ASR-1.7B",
            dtype=dtype,
            device_map=device,
            max_new_tokens=256,
        )
    except Exception as e:
        print(f"{YELLOW}  {device} failed ({e}), falling back to CPU…{RESET}")
        model = Qwen3ASRModel.from_pretrained(
            "Qwen/Qwen3-ASR-1.7B",
            dtype=torch.float32,
            device_map="cpu",
            max_new_tokens=256,
        )
    print(f"{GREEN}Model loaded{RESET} {DIM}({time.monotonic() - t0:.1f}s){RESET}")
    print(f"{DIM}{'─' * 50}{RESET}")
    print(
        f"Press {BOLD}Enter{RESET} to start recording, {BOLD}Enter{RESET} again to stop."
    )
    print(f"Type {BOLD}q{RESET} to quit. Results are auto-copied to clipboard.")
    print()

    from opencc import OpenCC

    s2tw = OpenCC("s2tw")

    recorder = AudioRecorder()

    while True:
        try:
            cmd = (
                input(f"{DIM}[ready]{RESET} Press Enter to record (q to quit): ")
                .strip()
                .lower()
            )
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if cmd == "q":
            break

        # Start recording
        recorder.start()
        record_start = time.monotonic()
        print(f"  {RED}{BOLD}● RECORDING{RESET} — press Enter to stop…", flush=True)

        try:
            input()
        except (EOFError, KeyboardInterrupt):
            recorder.stop()
            print()
            break

        # Stop recording
        audio = recorder.stop()
        duration = time.monotonic() - record_start
        samples = len(audio)
        rms = float(np.sqrt(np.mean(audio**2))) if samples > 0 else 0
        peak = float(np.max(np.abs(audio))) if samples > 0 else 0

        print(
            f"  {DIM}Recorded {duration:.2f}s, {samples} samples "
            f"(peak={peak:.4f}, rms={rms:.4f}){RESET}"
        )

        if samples < int(SAMPLE_RATE * 0.1):
            print(f"  {YELLOW}Too short — skipped{RESET}")
            print()
            continue

        if peak < 0.001:
            print(f"  {YELLOW}Audio is silent — mic may not have permission{RESET}")
            print()
            continue

        # Transcribe
        print(f"  {DIM}Transcribing…{RESET}", end=" ", flush=True)
        t0 = time.monotonic()
        results = model.transcribe(
            audio=(audio, SAMPLE_RATE),
            language=None,
            context="Mixed 普通話 (Taiwan) and English conversation",
        )
        inference_time = time.monotonic() - t0
        text = s2tw.convert(results[0].text.strip())
        lang = results[0].language

        rtf = inference_time / duration if duration > 0 else 0
        print(f"{DIM}done ({inference_time:.2f}s, RTF={rtf:.2f}){RESET}")

        if text:
            print(f"  {BOLD}[{lang}]{RESET} {DIM}{duration:.1f}s{RESET}  {text}")
            if copy_to_clipboard(text):
                print(f"  {DIM}(copied to clipboard){RESET}")
        else:
            print(f"  {YELLOW}(no speech detected){RESET}")

        print()

    print(f"{DIM}Bye!{RESET}")


if __name__ == "__main__":
    main()
