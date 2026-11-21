"""Offline voice DSP using the installed FFmpeg Rubber Band backend."""

import subprocess
from functools import lru_cache
from pathlib import Path

from app.utils.paths import find_tool

VOICE_FIELDS = {"voice", "pitch_semitones", "tempo", "preserve_formants", "timbre_db"}
VOICE_PRESETS = {
    "Natural lower": (-3.0, 1.0, True, -1.5),
    "Natural higher": (3.0, 1.0, True, 1.0),
    "Neutral altered": (1.0, 1.0, False, -1.0),
}


@lru_cache(maxsize=8)
def _rubberband_available(executable: str, size: int, modified: int) -> bool:
    result = subprocess.run(
        [executable, "-hide_banner", "-filters"],
        capture_output=True,
        text=True,
        timeout=10,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    return result.returncode == 0 and any(
        len(line.split()) > 1 and line.split()[1] == "rubberband"
        for line in result.stdout.splitlines()
    )


def require_rubberband() -> None:
    """Probe in the render worker; cache only for the same executable metadata."""
    executable = find_tool("ffmpeg")
    stat = Path(executable).stat()
    if not _rubberband_available(executable, stat.st_size, stat.st_mtime_ns):
        raise ValueError(
            "Voice transformation requires an FFmpeg build with librubberband. "
            "Disable Voice transformation or configure a compatible FFmpeg binary."
        )


def voice_filters(settings, duration_ms: int) -> list[str]:
    """Keep a fixed timeline slot; stretch trimmed audio, then pad/trim before fades."""
    if not settings.voice:
        return []
    filters = []
    if settings.pitch_semitones or settings.tempo != 1:
        pitch = 2 ** (settings.pitch_semitones / 12)
        formant = "preserved" if settings.preserve_formants else "shifted"
        filters.append(
            f"rubberband=pitch={pitch:.12f}:tempo={settings.tempo}:formant={formant}:"
            "pitchq=quality:channels=together"
        )
        filters += [
            "aresample=48000",
            "apad",
            f"atrim=duration={duration_ms / 1000}",
            "asetpts=PTS-STARTPTS",
        ]
    if settings.timbre_db:
        filters += [
            f"bass=g={-settings.timbre_db / 2}:f=180",
            f"treble=g={settings.timbre_db}:f=3500",
        ]
    return filters
