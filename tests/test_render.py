"""Real FFmpeg output verification, including pixels, audio and protected outputs."""

import json
import subprocess
from array import array
from dataclasses import replace
from threading import Event

import pytest

from app.core.command_manager import ProjectSession
from app.core.media_probe import probe_media
from app.core.project_manager import decode, encode, load_project, save_project
from app.core.project_schema import Project
from app.core.render_engine import RenderCancelled, render_project
from app.core.timeline_engine import TimelineEngine
from app.export.ffmpeg_builder import ExportSettings
from app.utils.paths import find_tool
from app.video.filters import VideoEffects


@pytest.fixture
def render_edit(media_files):
    session = ProjectSession()
    engine = TimelineEngine(session)
    media = engine.import_media(probe_media(media_files["video"]))
    clip = engine.add_clip(media, session.project.tracks[0].id, 0)
    engine.edit_clip(clip, start=0, source_in=30, source_out=45)
    return session, engine, clip


def frame(path, index=0):
    result = subprocess.run(
        [
            find_tool("ffmpeg"),
            "-v",
            "error",
            "-i",
            str(path),
            "-vf",
            f"select=eq(n\\,{index}),scale=160:90",
            "-frames:v",
            "1",
            "-f",
            "rawvideo",
            "-pix_fmt",
            "rgb24",
            "pipe:1",
        ],
        capture_output=True,
        check=True,
        timeout=30,
    )
    assert len(result.stdout) == 160 * 90 * 3
    return result.stdout


def difference(left, right):
    return sum(abs(a - b) for a, b in zip(left, right)) / len(left)


def audio_rms(path, start):
    data = subprocess.run(
        [
            find_tool("ffmpeg"),
            "-v",
            "error",
            "-i",
            str(path),
            "-ss",
            str(start),
            "-t",
            "0.15",
            "-vn",
            "-ac",
            "1",
            "-ar",
            "48000",
            "-f",
            "s16le",
            "pipe:1",
        ],
        capture_output=True,
        check=True,
        timeout=30,
    ).stdout
    values = array("h", data)
    return (sum(v * v for v in values) / len(values)) ** 0.5


def test_render_trim_gap_priority_and_audio(render_edit, media_files, tmp_path):
    session, engine, clip_id = render_edit
    first = session.project.clip_by_id(clip_id)
    engine.edit_clip(clip_id, start=15, source_in=30, source_out=45)
    second = engine.add_clip(first.media_id, first.track_id, 45)
    engine.edit_clip(second, start=45, source_in=90, source_out=105)
    output = tmp_path / "cut ü space.mp4"
    progress = []
    render_project(session.project, ExportSettings(320, 180), output, progress=progress.append)
    info = probe_media(output)
    assert (info.width, info.height, info.fps, info.audio_codec) == (320, 180, 30, "aac")
    assert abs(info.duration_ms - 2000) < 60
    assert max(frame(output, 3)) < 5
    assert max(frame(output, 35)) < 5
    assert difference(frame(output, 15), frame(media_files["video"], 30)) < 12
    assert difference(frame(output, 45), frame(media_files["video"], 90)) < 12
    assert audio_rms(output, 0.1) < 5
    assert audio_rms(output, 0.6) > 100
    assert audio_rms(output, 1.15) < 5
    assert progress[-1] == 100
    raw = subprocess.run(
        [
            find_tool("ffprobe"),
            "-v",
            "error",
            "-show_entries",
            "stream=nb_frames",
            "-of",
            "json",
            str(output),
        ],
        capture_output=True,
        check=True,
        timeout=30,
    )
    assert json.loads(raw.stdout)["streams"][0]["nb_frames"] == "60"


@pytest.mark.parametrize(
    "effect",
    [
        VideoEffects(brightness=0.3),
        VideoEffects(contrast=0.3),
        VideoEffects(saturation=0),
        VideoEffects(negative=True),
        VideoEffects(grayscale=True),
        VideoEffects(thermal=True),
        VideoEffects(blur=8),
        VideoEffects(crop_left=160, crop_right=160),
    ],
)
def test_effect_changes_decoded_pixels(render_edit, tmp_path, effect):
    session, engine, clip = render_edit
    baseline = tmp_path / "baseline.mp4"
    render_project(session.project, ExportSettings(320, 180), baseline)
    engine.set_effects(clip, effect)
    output = tmp_path / "effect.mp4"
    render_project(session.project, ExportSettings(320, 180), output)
    before, after = frame(baseline), frame(output)
    assert difference(before, after) > 3
    if effect.grayscale or effect.saturation == 0:
        assert (
            sum(abs(after[i] - after[i + 1]) for i in range(0, len(after), 3)) / (len(after) / 3)
            < 5  # YUV conversion/quantization can leave a few RGB levels of chroma.
        )
    if effect.brightness:
        assert sum(after) > sum(before)
    path = tmp_path / "effects.astra"
    save_project(session.project, path)
    assert load_project(path) == session.project
    engine.session.undo()
    assert session.project.clip_by_id(clip).effects == VideoEffects()


def test_image_priority_hide_mute_and_audio_only(render_edit, media_files, tmp_path):
    session, engine, clip_id = render_edit
    top = session.project.tracks[0].id
    lower = engine.add_track("video")
    image_id = engine.import_media(probe_media(media_files["image"]))
    image_clip = engine.add_clip(image_id, lower, 0)
    engine.edit_clip(image_clip, start=0, source_in=0, source_out=30)
    path = tmp_path / "layers.mp4"
    render_project(session.project, ExportSettings(320, 180), path)
    assert difference(frame(path, 0), frame(path, 20)) > 20
    engine.set_track(top, hidden=True, muted=True)
    path2 = tmp_path / "hidden.mp4"
    render_project(session.project, ExportSettings(320, 180), path2)
    assert difference(frame(path2), frame(path, 20)) < 3
    assert audio_rms(path2, 0.1) < 5
    engine.set_track(lower, hidden=True)
    audio_id = engine.import_media(probe_media(media_files["audio"]))
    engine.add_clip(audio_id, session.project.tracks[1].id, 0)
    path3 = tmp_path / "audio.mp4"
    render_project(session.project, ExportSettings(320, 180), path3)
    assert max(frame(path3)) < 5
    assert audio_rms(path3, 0.1) > 100


def test_migration_validation_and_output_protection(render_edit, tmp_path, monkeypatch):
    session, engine, clip = render_edit
    data = encode(session.project, tmp_path)
    data["schema_version"] = 1
    for key in ("subtitles", "subtitle_style", "transcription", "audio_master"):
        data.pop(key)
    for track in data["tracks"]:
        track.pop("audio")
    for item in data["clips"]:
        item.pop("effects")
        item.pop("fade_in_ms")
        item.pop("fade_out_ms")
    assert decode(data, tmp_path) == session.project
    for effect in (VideoEffects(crop_left=640), VideoEffects(brightness=float("nan"))):
        with pytest.raises(ValueError):
            engine.set_effects(clip, effect)
    settings = ExportSettings(320, 180)
    source = session.project.media[0].info.path
    with pytest.raises(ValueError, match="source"):
        render_project(session.project, settings, source, overwrite=True)
    destination = tmp_path / "existing.mp4"
    destination.write_bytes(b"preserve me")
    with pytest.raises(FileExistsError):
        render_project(session.project, settings, destination)
    cancel = Event()
    cancel.set()
    with pytest.raises(RenderCancelled):
        render_project(session.project, settings, destination, cancel, overwrite=True)
    monkeypatch.setenv("ASTRA_FFMPEG", str(tmp_path / "missing.exe"))
    with pytest.raises(FileNotFoundError):
        render_project(session.project, settings, destination, overwrite=True)
    assert destination.read_bytes() == b"preserve me"
    assert not list(tmp_path.glob(".astra-render-*"))


def test_fractional_fps_output(render_edit, tmp_path):
    project = replace(render_edit[0].project, fps_num=30000, fps_den=1001)
    output = tmp_path / "fractional.mp4"
    render_project(project, ExportSettings(320, 180), output)
    assert probe_media(output).fps == project.fps


def test_empty_export_rejected(tmp_path):
    with pytest.raises(ValueError, match="at least one"):
        render_project(Project(), ExportSettings(), tmp_path / "empty.mp4")


@pytest.mark.parametrize(
    "effect",
    [
        VideoEffects(sepia=True),
        VideoEffects(mirror=True),
        VideoEffects(pixelation=16),
        VideoEffects(sharpen=2),
        VideoEffects(vignette=1),
    ],
)
def test_phase7_effect_changes_render(render_edit, tmp_path, effect):
    session, engine, clip_id = render_edit
    baseline = tmp_path / "baseline.mp4"
    changed = tmp_path / "changed.mp4"
    render_project(session.project, ExportSettings(320, 180, 0), baseline)
    engine.set_effects(clip_id, effect)
    assert decode(encode(session.project, tmp_path), tmp_path) == session.project
    render_project(session.project, ExportSettings(320, 180, 0), changed)
    assert difference(frame(baseline), frame(changed)) > 0.2


@pytest.mark.parametrize("inverted", [False, True])
def test_phase7_mask_blur_region(render_edit, tmp_path, inverted):
    from app.video.masks import Mask

    session, engine, clip_id = render_edit
    baseline = tmp_path / "baseline.mp4"
    changed = tmp_path / "masked.mp4"
    render_project(session.project, ExportSettings(320, 180, 0), baseline)
    engine.set_effects(
        clip_id,
        VideoEffects(
            mask=Mask(
                shape="rectangle",
                x=0,
                y=0,
                width=0.5,
                height=1,
                blur=40,
                inverted=inverted,
            )
        ),
    )
    assert decode(encode(session.project, tmp_path), tmp_path) == session.project
    render_project(session.project, ExportSettings(320, 180, 0), changed)
    before, after = frame(baseline), frame(changed)

    def region(data, left, right):
        return bytes(
            v
            for y in range(10, 80)
            for x in range(left, right)
            for v in data[(y * 160 + x) * 3 : (y * 160 + x + 1) * 3]
        )

    left = difference(region(before, 5, 65), region(after, 5, 65))
    right = difference(region(before, 95, 155), region(after, 95, 155))
    affected, preserved = (right, left) if inverted else (left, right)
    assert affected > 2
    assert preserved < 2


def test_mask_feather_strength_pixels(render_edit, tmp_path):
    from app.video.masks import Mask

    session, engine, clip = render_edit
    outputs = []
    for strength, feather in ((0, 0), (1, 0), (0.5, 0), (1, 40)):
        engine.set_effects(
            clip,
            VideoEffects(mask=Mask(shape="ellipse", blur=40, strength=strength, feather=feather)),
        )
        target = tmp_path / f"mask-{strength}-{feather}.mp4"
        render_project(session.project, ExportSettings(320, 180, 0), target)
        outputs.append(frame(target))
    original, full, half, feathered = outputs
    assert difference(original, full) > difference(original, half) > 0.1
    assert difference(full, feathered) > 0.1
