"""Bounded background frame previews using the export graph."""

import subprocess
import tempfile
from dataclasses import replace
from pathlib import Path

from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QImage

from app.export.ffmpeg_builder import ExportSettings, build_command


class EffectPreview(QThread):
    ready = Signal(object)
    failed = Signal(str)

    def __init__(self, project, clip_id, effects, offset, parent=None):
        super().__init__(parent)
        clip = project.clip_by_id(clip_id)
        clip = replace(
            clip,
            start=0,
            source_in=clip.source_in + offset,
            source_out=clip.source_in + offset + 1,
            effects=effects,
        )
        self.project = replace(
            project,
            clips=(clip,),
            subtitles=(),
            tracks=tuple(replace(t, muted=True) for t in project.tracks),
        )

    def run(self):
        try:
            with tempfile.TemporaryDirectory(prefix="astra-preview-") as folder:
                root = Path(folder)
                ratio = min(640 / self.project.width, 360 / self.project.height)
                w, h = (
                    max(16, int(self.project.width * ratio) // 2 * 2),
                    max(16, int(self.project.height * ratio) // 2 * 2),
                )
                cmd = build_command(
                    self.project,
                    ExportSettings(w, h),
                    root / "unused.mp4",
                    root / "graph.txt",
                    root / "progress.txt",
                )
                # Replace encoder options with a single PNG, retaining the identical graph.
                cmd = cmd[: cmd.index("-map")] + [
                    "-map",
                    "[vout]",
                    "-frames:v",
                    "1",
                    "-f",
                    "image2",
                    str(root / "frame.png"),
                    "-map",
                    "[aout]",
                    "-f",
                    "null",
                    "-",
                ]
                subprocess.run(
                    cmd,
                    capture_output=True,
                    check=True,
                    timeout=30,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
                image = QImage(str(root / "frame.png"))
                if image.isNull():
                    raise ValueError("Preview produced no image")
                self.ready.emit(image)
        except Exception as exc:
            self.failed.emit(str(exc))
