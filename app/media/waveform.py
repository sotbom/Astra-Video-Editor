"""Bounded, cached source peaks decoded off the UI thread."""

import hashlib
import json
import math
import subprocess
import time
from array import array
from pathlib import Path
from threading import Event, Thread

from PySide6.QtCore import QThread, Signal

from app.core.project_manager import atomic_write
from app.utils.paths import find_tool


def waveform(info, cache: Path, cancelled=None):
    cancelled = cancelled or Event()
    if cancelled.is_set():
        raise InterruptedError("Waveform cancelled.")
    stat = info.path.stat()
    key = hashlib.sha256(
        f"v1|{info.path}|{stat.st_size}|{stat.st_mtime_ns}|{info.duration_ms}".encode()
    ).hexdigest()
    path = cache / f"{key}.json"
    if path.exists() and path.stat().st_size < 300000:
        try:
            data = json.loads(path.read_text())
            if (
                not isinstance(data.get("bin_ms"), (int, float))
                or not math.isfinite(data["bin_ms"])
                or data["bin_ms"] <= 0
                or data.get("duration_ms") != info.duration_ms
            ):
                raise ValueError("Invalid waveform cache metadata.")
            if 0 < len(data["peaks"]) <= 8001 and all(
                isinstance(p, (int, float)) and math.isfinite(p) and 0 <= p <= 1
                for p in data["peaks"]
            ):
                return data
        except (ValueError, KeyError, TypeError):
            pass
    samples = max(160, math.ceil(info.duration_ms * 8 / 8000))
    command = [
        find_tool("ffmpeg"),
        "-v",
        "error",
        "-nostdin",
        "-protocol_whitelist",
        "file,pipe",
        "-i",
        str(info.path),
        "-vn",
        "-ac",
        "1",
        "-ar",
        "8000",
        "-f",
        "s16le",
        "pipe:1",
    ]
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    done = Event()
    started = time.monotonic()

    def watch():
        while not done.wait(0.1):
            if cancelled.is_set() or time.monotonic() - started > 3600:
                if process.poll() is None:
                    process.terminate()
                return

    watchdog = Thread(target=watch, daemon=True)
    watchdog.start()
    peaks = []
    try:
        while chunk := process.stdout.read(samples * 2):
            values = array("h", chunk[: len(chunk) // 2 * 2])
            peaks.append(max((abs(v) for v in values), default=0) / 32768)
            if len(peaks) > 8001:
                raise ValueError("Waveform duration differs from source metadata; reimport media.")
        process.wait(timeout=5)
        if cancelled.is_set():
            raise InterruptedError("Waveform cancelled.")
        if process.returncode or not peaks:
            raise ValueError("Waveform decoding failed or timed out.")
        data = {"peaks": peaks, "bin_ms": samples / 8, "duration_ms": info.duration_ms}
        atomic_write(path, json.dumps(data).encode())
        return data
    finally:
        done.set()
        if process.poll() is None:
            process.kill()
            process.wait(timeout=5)
        process.stdout.close()
        watchdog.join(timeout=2)


class WaveformWorker(QThread):
    ready = Signal(object, object)
    failed = Signal(str)
    progress = Signal(int)

    def __init__(self, media, cache, parent=None):
        super().__init__(parent)
        self.media, self.cache = media, cache
        self.cancelled = Event()

    def run(self):
        for index, info in enumerate(self.media):
            if self.cancelled.is_set():
                break
            try:
                self.ready.emit(info.path, waveform(info, self.cache, self.cancelled))
            except (ValueError, OSError, subprocess.SubprocessError) as exc:
                self.failed.emit(str(exc))
            self.progress.emit(round((index + 1) * 100 / len(self.media)))
