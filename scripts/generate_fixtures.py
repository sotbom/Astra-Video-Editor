"""Create original synthetic test assets; never access private media."""

import subprocess
from pathlib import Path

from app.utils.paths import ROOT, find_tool


def generate(directory: Path) -> dict[str, Path]:
    """Generate a six-second video, PCM audio, and a still image."""
    directory.mkdir(parents=True, exist_ok=True)
    ffmpeg = find_tool("ffmpeg")
    assets = {
        "video": directory / "Astra test ü space.mp4",
        "audio": directory / "tone.wav",
        "image": directory / "still.png",
    }
    commands = [
        [
            "-f",
            "lavfi",
            "-i",
            "testsrc2=size=640x360:rate=30",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:sample_rate=48000",
            "-t",
            "6",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            str(assets["video"]),
        ],
        [
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=660:sample_rate=48000",
            "-t",
            "3",
            "-c:a",
            "pcm_s16le",
            str(assets["audio"]),
        ],
        [
            "-f",
            "lavfi",
            "-i",
            "color=c=teal:s=320x240",
            "-frames:v",
            "1",
            "-update",
            "1",
            str(assets["image"]),
        ],
    ]
    for args in commands:
        output = Path(args[-1])
        if not output.exists():
            subprocess.run(
                [ffmpeg, "-hide_banner", "-loglevel", "error", "-nostdin", "-n", *args],
                check=True,
                timeout=60,
            )
    return assets


if __name__ == "__main__":
    for name, path in generate(ROOT / "tests/fixtures/generated").items():
        print(f"{name}: {path}")
