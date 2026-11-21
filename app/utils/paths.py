"""Locate external tools without modifying the system PATH."""

import os
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def find_tool(name: str) -> str:
    """Find an explicitly configured, local, or PATH FFmpeg tool."""
    configured = os.environ.get(f"ASTRA_{name.upper()}")
    if configured:
        if Path(configured).is_file():
            return str(Path(configured).resolve())
        raise FileNotFoundError(f"ASTRA_{name.upper()} does not point to a file.")
    suffix = ".exe" if os.name == "nt" else ""
    candidates = [ROOT / "tools" / "bin" / f"{name}{suffix}"]
    candidates.extend(sorted((ROOT / "tools").glob(f"ffmpeg-*/bin/{name}{suffix}")))
    for candidate in candidates:
        if candidate.is_file():
            return str(candidate)
    found = shutil.which(name)
    if found:
        return found
    raise FileNotFoundError(
        f"{name} was not found. Run scripts/setup_dev.ps1 or set ASTRA_{name.upper()}."
    )
