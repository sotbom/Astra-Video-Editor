"""Cancellable process-isolated jobs with CPU fallback after CUDA failure."""

import json
import os
import subprocess
import tempfile
import time
from pathlib import Path
from threading import Event

from PySide6.QtCore import QThread, Signal

from app.ai.model_manager import ai_python
from app.utils.paths import ROOT, find_tool


class AICancelled(Exception):
    pass


def run_process(command, cancelled, timeout, *, status=None, progress=None, log=None):
    with open(log or os.devnull, "wb") as errors:
        process = subprocess.Popen(
            command,
            cwd=ROOT,
            stdin=subprocess.DEVNULL,
            stdout=errors,
            stderr=errors,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        started = time.monotonic()
        previous = None
        try:
            while process.poll() is None:
                if cancelled.wait(0.1):
                    raise AICancelled()
                if time.monotonic() - started > timeout:
                    raise TimeoutError("AI job timed out.")
                if status and status.exists() and progress:
                    try:
                        value = json.loads(status.read_text(encoding="utf-8"))
                        if value != previous:
                            progress(value["progress"], value["message"])
                            previous = value
                    except (ValueError, OSError):
                        pass
            if cancelled.is_set():
                raise AICancelled()
            return process.returncode
        finally:
            if process.poll() is None:
                if os.name == "nt":
                    # A Windows venv launcher owns a child interpreter. Terminate the
                    # tree so cancellation cannot leave inference and log handles alive.
                    subprocess.run(
                        ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        timeout=10,
                        creationflags=subprocess.CREATE_NO_WINDOW,
                    )
                else:
                    process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)


def run_ai(request, cancelled=None, progress=None):
    cancelled = cancelled or Event()
    interpreter = ai_python()
    request = dict(request)
    with tempfile.TemporaryDirectory(prefix="astra-ai-") as folder:
        work = Path(folder)
        if request["task"] == "transcribe":
            source = Path(request.pop("source")).resolve()
            if not source.is_file():
                raise FileNotFoundError("Transcription source is missing.")
            start, duration = request.pop("start_ms"), request.pop("duration_ms")
            if (
                type(start) is not int
                or type(duration) is not int
                or start < 0
                or not 0 < duration <= 604800000
            ):
                raise ValueError("Invalid transcription range.")
            if progress:
                progress(-1, "Extracting selected clip audio locally…")
            audio = work / "audio.wav"
            command = [
                find_tool("ffmpeg"),
                "-v",
                "error",
                "-nostdin",
                "-y",
                "-protocol_whitelist",
                "file,pipe",
                "-ss",
                str(start / 1000),
                "-i",
                str(source),
                "-t",
                str(duration / 1000),
                "-vn",
                "-ac",
                "1",
                "-ar",
                "16000",
                str(audio),
            ]
            if run_process(command, cancelled, 3600, log=work / "extract.log"):
                raise RuntimeError("Audio extraction failed. Select a valid clip containing audio.")
            request["audio"] = str(audio)
        original_device = request.get("device")
        fallback = ""
        for attempt in range(2):
            config, result, status = (
                work / "request.json",
                work / "result.json",
                work / "status.json",
            )
            config.write_text(json.dumps(request), encoding="utf-8")
            result.unlink(missing_ok=True)
            status.unlink(missing_ok=True)
            code = run_process(
                [str(interpreter), "-m", "app.ai.backend", str(config), str(result), str(status)],
                cancelled,
                43200,
                status=status,
                progress=progress,
                log=work / "backend.log",
            )
            response = json.loads(result.read_text(encoding="utf-8")) if result.exists() else {}
            if code == 0 and "result" in response:
                value = response["result"]
                if original_device == "cuda" and attempt:
                    value["fallback"] = fallback
                return value
            message = response.get(
                "error",
                f"AI subprocess exited with code {code}. Check the optional AI installation.",
            )
            if request.get("device") == "cuda" and request["task"] == "transcribe" and attempt == 0:
                fallback = message
                if progress:
                    progress(0, "CUDA failed; retrying locally on CPU (int8)…")
                request.update(device="cpu", compute="int8")
                continue
            raise RuntimeError(message)


class AIWorker(QThread):
    progress = Signal(int, str)
    succeeded = Signal(object)
    failed = Signal(str)
    cancelled = Signal()

    def __init__(self, request, parent=None):
        super().__init__(parent)
        self.request = request
        self.cancel_event = Event()

    def run(self):
        try:
            self.succeeded.emit(run_ai(self.request, self.cancel_event, self.progress.emit))
        except AICancelled:
            self.cancelled.emit()
        except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
            self.failed.emit(str(exc))
