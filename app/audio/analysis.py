"""EBU R128 loudness and true-peak analysis through the verified FFmpeg build."""

import json
import re
import subprocess
import time
from threading import Event

from PySide6.QtCore import QThread, Signal

from app.utils.paths import find_tool


def analyze_audio(path, cancelled=None):
    cancelled = cancelled or Event()
    command = (
        [
            find_tool("ffmpeg"),
            "-hide_banner",
            "-nostdin",
            "-i",
            str(path),
            "-vn",
            "-af",
            "loudnorm=I=-16:TP=-1:LRA=11:print_format=json",
            "-f",
            "null",
            "-",
        ],
    )
    process = subprocess.Popen(
        command[0],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    started = time.monotonic()
    try:
        while True:
            if cancelled.is_set():
                raise InterruptedError("Loudness analysis cancelled.")
            if time.monotonic() - started > 120:
                raise TimeoutError("Loudness analysis timed out.")
            try:
                _, errors = process.communicate(timeout=0.1)
                break
            except subprocess.TimeoutExpired:
                pass
        if process.returncode:
            raise ValueError("Loudness analysis failed.")
    finally:
        if process.poll() is None:
            process.terminate()
            process.communicate(timeout=5)
    matches = re.findall(r"\{[^{}]*\}", errors.decode(errors="replace"))
    if not matches:
        raise ValueError("FFmpeg returned no loudness measurement.")
    return json.loads(matches[-1])


class AnalysisWorker(QThread):
    ready = Signal(object)
    failed = Signal(str)

    def __init__(self, path, parent=None):
        super().__init__(parent)
        self.path = path
        self.cancelled = Event()

    def run(self):
        try:
            self.ready.emit(analyze_audio(self.path, self.cancelled))
        except (OSError, ValueError, subprocess.SubprocessError) as exc:
            self.failed.emit(str(exc))
