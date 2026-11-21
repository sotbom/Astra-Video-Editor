"""Bounded FFprobe inspection of local media."""

import json
import math
import os
import subprocess
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path

from app.utils.paths import find_tool


class MediaError(ValueError):
    """An actionable media import error."""


@dataclass(frozen=True)
class MediaInfo:
    path: Path
    duration_ms: int
    width: int
    height: int
    fps: Fraction
    video_codec: str
    audio_codec: str
    sample_rate: int
    channels: int
    is_image: bool

    @property
    def name(self) -> str:
        return self.path.name


def probe_media(path: str | Path) -> MediaInfo:
    """Inspect one local file with a timeout and no shell interpolation."""
    source = Path(path).resolve()
    if not source.is_file():
        raise MediaError("The selected file is missing or is not a regular file.")
    try:
        result = subprocess.run(
            [
                find_tool("ffprobe"),
                "-v",
                "error",
                "-protocol_whitelist",
                "file,pipe",
                "-show_entries",
                "stream=codec_type,codec_name,width,height,avg_frame_rate,duration,"
                "sample_rate,channels:stream_disposition=attached_pic:format=duration",
                "-of",
                "json",
                str(source),
            ],
            capture_output=True,
            timeout=20,
            check=False,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
    except subprocess.TimeoutExpired as exc:
        raise MediaError("Media inspection timed out after 20 seconds.") from exc
    except OSError as exc:
        raise MediaError(str(exc)) from exc
    if result.returncode:
        raise MediaError("FFprobe could not read this file. It may be corrupt or unsupported.")
    if len(result.stdout) > 4_000_000:
        raise MediaError("Media metadata exceeds the supported size.")
    try:
        data = json.loads(result.stdout)
        streams = data.get("streams", [])
        video = next(
            (
                s
                for s in streams
                if s.get("codec_type") == "video"
                and not s.get("disposition", {}).get("attached_pic")
            ),
            {},
        )
        audio = next((s for s in streams if s.get("codec_type") == "audio"), {})
        if not video and not audio:
            raise MediaError("No playable video, audio, or image stream was found.")
        duration = float(
            data.get("format", {}).get("duration")
            or video.get("duration")
            or audio.get("duration")
            or 0
        )
        if not math.isfinite(duration) or duration < 0:
            raise MediaError("Invalid media duration.")
        try:
            fps = Fraction(video.get("avg_frame_rate", "0/1"))
        except (ValueError, ZeroDivisionError):
            fps = Fraction(0)
        return MediaInfo(
            source,
            round(duration * 1000),
            int(video.get("width", 0)),
            int(video.get("height", 0)),
            fps,
            video.get("codec_name", ""),
            audio.get("codec_name", ""),
            int(audio.get("sample_rate", 0)),
            int(audio.get("channels", 0)),
            bool(video) and source.suffix.lower() in {".png", ".jpg", ".jpeg", ".bmp", ".webp"},
        )
    except (ValueError, TypeError, KeyError, AttributeError) as exc:
        raise MediaError(f"Invalid or unsupported media metadata: {exc}") from exc
