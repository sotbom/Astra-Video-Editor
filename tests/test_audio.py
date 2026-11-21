"""Decode actual output samples to verify audio processing and multitrack mixing."""

import math
import subprocess
from array import array
from threading import Event

import pytest

from app.audio.analysis import analyze_audio
from app.audio.effects import AudioMaster, AudioSettings
from app.core.command_manager import ProjectSession
from app.core.media_probe import probe_media
from app.core.project_manager import load_project, save_project
from app.core.render_engine import RenderCancelled, render_project
from app.core.timeline_engine import TimelineEngine
from app.export.ffmpeg_builder import ExportSettings
from app.media.waveform import waveform
from app.utils.paths import find_tool


def pcm(path):
    result = subprocess.run(
        [
            find_tool("ffmpeg"),
            "-v",
            "error",
            "-i",
            str(path),
            "-vn",
            "-ar",
            "48000",
            "-ac",
            "2",
            "-f",
            "f32le",
            "pipe:1",
        ],
        capture_output=True,
        check=True,
        timeout=30,
    )
    return array("f", result.stdout)


def rms(values, start=0.2, end=0.8, channel=0):
    selected = values[int(start * 48000) * 2 + channel : int(end * 48000) * 2 : 2]
    return math.sqrt(sum(v * v for v in selected) / len(selected))


@pytest.fixture
def audio_edit(media_files):
    session = ProjectSession()
    engine = TimelineEngine(session)
    media = engine.import_media(probe_media(media_files["audio"]))
    clip = engine.add_clip(media, session.project.tracks[1].id, 0)
    return session, engine, clip


def output(project, tmp_path, name="audio.wav"):
    path = tmp_path / name
    render_project(project, ExportSettings(audio_only=True), path)
    return path


def test_gain_pan_fades_and_stereo_wav(audio_edit, tmp_path):
    session, engine, clip_id = audio_edit
    track = session.project.clip_by_id(clip_id).track_id
    base = pcm(output(session.project, tmp_path, "base.wav"))
    engine.set_audio(track, AudioSettings(gain_db=-6, pan=-1), clip_id, 500, 500)
    path = output(session.project, tmp_path)
    info = probe_media(path)
    assert (info.audio_codec, info.sample_rate, info.channels, info.duration_ms) == (
        "pcm_s24le",
        48000,
        2,
        3000,
    )
    processed = pcm(path)
    assert abs(rms(processed, 1, 2) / rms(base, 1, 2) - 10 ** (-6 / 20)) < 0.01
    assert rms(processed, 1, 2, 1) < 0.00001
    assert rms(processed, 0, 0.05) < rms(processed, 1, 2) * 0.15
    assert rms(processed, 2.95, 3) < rms(processed, 1, 2) * 0.15
    saved = tmp_path / "audio.astra"
    save_project(session.project, saved)
    assert load_project(saved) == session.project
    session.undo()
    assert session.project.tracks[1].audio == AudioSettings()
    assert session.project.clips[0].fade_in_ms == 0


def test_multitrack_delay_mute_and_mixing(audio_edit, tmp_path):
    session, engine, clip = audio_edit
    first = session.project.clip_by_id(clip)
    second = engine.add_track("audio")
    engine.add_clip(first.media_id, second, 30)
    mixed = pcm(output(session.project, tmp_path))
    assert rms(mixed, 1.2, 1.8) > rms(mixed, 0.2, 0.8) * 1.9
    engine.set_track(second, muted=True)
    muted = pcm(output(session.project, tmp_path, "muted.wav"))
    assert rms(muted, 3.2, 3.8) < 0.00001
    assert abs(rms(muted, 1.2, 1.8) - rms(muted, 0.2, 0.8)) < 0.001


def test_eq_and_compression_change_samples(audio_edit, tmp_path):
    session, engine, clip = audio_edit
    track = session.project.clip_by_id(clip).track_id
    base = pcm(output(session.project, tmp_path, "base.wav"))
    engine.set_audio(track, AudioSettings(eq=True, highpass=2000))
    filtered = pcm(output(session.project, tmp_path, "eq.wav"))
    assert rms(filtered, 1, 2) < rms(base, 1, 2) * 0.25
    engine.set_audio(
        track,
        AudioSettings(compressor=True, threshold_db=-40, ratio=10, attack_ms=1, release_ms=50),
    )
    compressed = pcm(output(session.project, tmp_path, "compressed.wav"))
    assert rms(compressed, 1, 2) < rms(base, 1, 2) * 0.3


def test_noise_reduction_attenuates_generated_noise(tmp_path):
    source = tmp_path / "noise.wav"
    subprocess.run(
        [
            find_tool("ffmpeg"),
            "-v",
            "error",
            "-f",
            "lavfi",
            "-i",
            "anoisesrc=color=white:amplitude=0.02:seed=42:duration=3",
            "-ar",
            "48000",
            str(source),
        ],
        check=True,
        timeout=30,
    )
    session = ProjectSession()
    engine = TimelineEngine(session)
    media = engine.import_media(probe_media(source))
    engine.add_clip(media, session.project.tracks[1].id, 0)
    baseline = pcm(output(session.project, tmp_path, "before.wav"))
    engine.set_audio(
        session.project.tracks[1].id,
        AudioSettings(denoise=True, noise_floor=-25, noise_reduction=30),
    )
    cleaned = pcm(output(session.project, tmp_path, "after.wav"))
    assert rms(cleaned, 1, 2) < rms(baseline, 1, 2) * 0.5


def test_loudness_normalization_and_peak(audio_edit, tmp_path):
    session, engine, clip = audio_edit
    # Use six seconds so EBU gating has sufficient blocks for a meaningful result.
    first = session.project.clip_by_id(clip)
    engine.add_clip(first.media_id, first.track_id, 90)
    engine.set_audio(first.track_id, AudioSettings(), master=AudioMaster(True, -16, -1))
    path = output(session.project, tmp_path)
    measured = analyze_audio(path)
    assert abs(float(measured["input_i"]) + 16) < 1
    assert float(measured["input_tp"]) <= -0.8


def test_waveform_cache_and_cancellation(media_files, tmp_path):
    info = probe_media(media_files["audio"])
    data = waveform(info, tmp_path)
    assert 0 < len(data["peaks"]) <= 8001
    assert max(data["peaks"]) > 0.05
    cached = next(tmp_path.glob("*.json"))
    before = cached.stat().st_mtime_ns
    assert waveform(info, tmp_path) == data
    assert cached.stat().st_mtime_ns == before
    cancelled = Event()
    cancelled.set()
    with pytest.raises(InterruptedError):
        waveform(info, tmp_path / "new", cancelled)


def test_invalid_audio_and_protected_outputs(audio_edit, tmp_path):
    session, engine, clip = audio_edit
    before = session.project
    with pytest.raises(ValueError):
        engine.set_audio(before.tracks[1].id, AudioSettings(pan=2))
    with pytest.raises(ValueError):
        engine.set_audio(before.tracks[1].id, AudioSettings(gain_db=float("nan")))
    assert session.project == before
    original = before.media[0].info.path.read_bytes()
    with pytest.raises(ValueError, match="source"):
        render_project(
            before, ExportSettings(audio_only=True), before.media[0].info.path, overwrite=True
        )
    assert before.media[0].info.path.read_bytes() == original
    cancelled = Event()
    cancelled.set()
    with pytest.raises(RenderCancelled):
        render_project(before, ExportSettings(audio_only=True), tmp_path / "cancel.wav", cancelled)
