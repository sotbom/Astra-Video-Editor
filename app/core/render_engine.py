"""Cancellable background FFmpeg rendering with atomic output publication."""

import os
import subprocess
import tempfile
import time
from dataclasses import replace
from pathlib import Path
from threading import Event

from PySide6.QtCore import QThread, Signal

from app.core.media_probe import probe_media
from app.export.ffmpeg_builder import ExportSettings, build_command


class RenderCancelled(Exception):
    pass


def render_project(
    project,
    settings: ExportSettings,
    output: Path,
    cancelled: Event | None = None,
    progress=None,
    *,
    overwrite=False,
    protected=(),
    verified=None,
):
    """Render to a sibling temporary; retain existing output on failure or cancellation."""
    cancelled = cancelled or Event()
    output = output.resolve()
    forbidden = {m.info.path.resolve() for m in project.media} | {
        Path(p).resolve() for p in protected
    }
    if output in forbidden or any(
        output.exists() and p.exists() and output.samefile(p) for p in forbidden
    ):
        raise ValueError("Export must never overwrite source media or the project file.")
    suffix = ".wav" if settings.audio_only else ".mp4"
    if output.suffix.lower() != suffix:
        raise ValueError(f"This export profile requires a {suffix} filename.")
    if output.exists() and not overwrite:
        raise FileExistsError("Output already exists. Choose another name or confirm replacement.")
    if cancelled.is_set():
        raise RenderCancelled()
    with tempfile.TemporaryDirectory(prefix=".astra-render-", dir=output.parent) as folder:
        work = Path(folder)
        temporary, graph, status = (
            work / ("output" + suffix),
            work / "graph.txt",
            work / "progress.txt",
        )
        command = build_command(project, settings, temporary, graph, status)
        if os.name == "nt" and len(subprocess.list2cmdline(command)) > 30000:
            raise ValueError("This timeline exceeds the current Windows export command limit.")
        process = None
        try:
            with (work / "errors.log").open("wb") as errors:
                process = subprocess.Popen(
                    command,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=errors,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
                started = time.monotonic()
                while process.poll() is None:
                    if cancelled.wait(0.1):
                        raise RenderCancelled()
                    if time.monotonic() - started > 43200:
                        raise TimeoutError("Export exceeded the 12-hour processing limit.")
                    if progress and status.exists():
                        lines = status.read_text(encoding="utf-8", errors="replace").splitlines()
                        frames = [
                            int(line[6:])
                            for line in lines
                            if line.startswith("frame=") and line[6:].strip().isdigit()
                        ]
                        if frames:
                            progress(min(99, frames[-1] * 100 // project.end))
                        times = [
                            int(line.split("=", 1)[1])
                            for line in lines
                            if line.startswith("out_time_us=") and line.split("=", 1)[1].isdigit()
                        ]
                        if times:
                            progress(
                                min(99, times[-1] // max(1, project.milliseconds(project.end) * 10))
                            )
                if process.returncode:
                    with (work / "errors.log").open("rb") as log:
                        log.seek(max(0, log.seek(0, 2) - 6000))
                        detail = log.read().decode("utf-8", errors="replace")
                    raise RuntimeError("FFmpeg export failed: " + detail)
            if cancelled.is_set():
                raise RenderCancelled()
            info = probe_media(temporary)
            if settings.audio_only and (
                not info.audio_codec or info.sample_rate != 48000 or info.channels != 2
            ):
                raise RuntimeError("Rendered audio failed media verification.")
            if not settings.audio_only and (
                not info.video_codec
                or (info.width, info.height)
                != (
                    settings.width,
                    settings.height,
                )
            ):
                raise RuntimeError("Rendered output failed media verification.")
            if abs(info.duration_ms - project.milliseconds(project.end)) > max(
                100, project.milliseconds(2)
            ):
                raise RuntimeError("Rendered output duration does not match the timeline.")
            if cancelled.is_set():
                raise RenderCancelled()
            if overwrite:
                os.replace(temporary, output)
            else:
                # On Windows rename fails if a destination appeared during the render.
                if output.exists():
                    raise FileExistsError("Output appeared during rendering; it was preserved.")
                os.rename(temporary, output)
            if progress:
                progress(100)
            if verified:
                verified(replace(info, path=output))
            return output
        finally:
            if process and process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)


class RenderWorker(QThread):
    progress = Signal(int)
    succeeded = Signal(object)
    failed = Signal(str)
    cancelled = Signal()

    def __init__(self, project, settings, output, *, overwrite=False, protected=(), parent=None):
        super().__init__(parent)
        self.project, self.settings, self.output = project, settings, output
        self.overwrite, self.protected = overwrite, protected
        self.cancel_event = Event()

    def run(self):
        try:
            result = render_project(
                self.project,
                self.settings,
                self.output,
                self.cancel_event,
                self.progress.emit,
                overwrite=self.overwrite,
                protected=self.protected,
                verified=lambda info: setattr(self, "media_info", info),
            )
            self.succeeded.emit(result)
        except RenderCancelled:
            self.cancelled.emit()
        except (OSError, ValueError, RuntimeError, TimeoutError, subprocess.SubprocessError) as exc:
            self.failed.emit(str(exc))
