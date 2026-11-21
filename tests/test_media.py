from fractions import Fraction

import pytest

from app.core.media_probe import MediaError, probe_media
from app.utils.paths import find_tool


def test_probe_video(media_files):
    info = probe_media(media_files["video"])
    assert (info.width, info.height) == (640, 360)
    assert info.fps == Fraction(30)
    assert abs(info.duration_ms - 6000) < 100
    assert info.video_codec == "h264"
    assert info.audio_codec == "aac"
    assert info.sample_rate == 48000
    assert not info.is_image


def test_audio_and_image(media_files):
    audio = probe_media(media_files["audio"])
    assert not audio.video_codec
    assert audio.duration_ms == 3000
    assert audio.channels == 1
    image = probe_media(media_files["image"])
    assert image.is_image
    assert (image.width, image.height) == (320, 240)


def test_corrupt_missing_and_directory(tmp_path):
    corrupt = tmp_path / "bad.mp4"
    corrupt.write_bytes(b"This is not a video")
    for path in (corrupt, tmp_path / "missing.mp4", tmp_path):
        with pytest.raises(MediaError):
            probe_media(path)


def test_missing_ffprobe(monkeypatch, media_files, tmp_path):
    monkeypatch.setenv("ASTRA_FFPROBE", str(tmp_path / "missing.exe"))
    with pytest.raises(MediaError, match="ASTRA_FFPROBE"):
        probe_media(media_files["video"])


def test_explicit_tool_override(monkeypatch, media_files):
    real = find_tool("ffprobe")
    monkeypatch.setenv("ASTRA_FFPROBE", real)
    assert probe_media(media_files["video"]).width == 640
