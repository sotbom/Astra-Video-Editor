"""Strict, versioned JSON persistence with atomic writes and last-save backup."""

import json
import os
import tempfile
from dataclasses import asdict
from fractions import Fraction
from pathlib import Path

from PySide6.QtCore import QThread, Signal

from app.audio.effects import AudioMaster, AudioSettings
from app.core.media_probe import MediaInfo
from app.core.project_schema import Clip, Media, Project, Track, validate
from app.core.subtitles import Subtitle, SubtitleStyle
from app.video.filters import VideoEffects
from app.video.masks import decode_mask

MAX_PROJECT_BYTES = 8 * 1024 * 1024


def encode(project: Project, base: Path) -> dict:
    """Serialize metadata only; prefer paths relative to the project directory."""
    validate(project)
    media = []
    for item in project.media:
        info = asdict(item.info)
        try:
            info["path"] = os.path.relpath(item.info.path, base)
        except ValueError:
            info["path"] = str(item.info.path)
        info["fps"] = [item.info.fps.numerator, item.info.fps.denominator]
        media.append({"id": item.id, "info": info})
    return {
        "schema_version": 6,
        "time_unit": "project_frames",
        "project": {
            key: getattr(project, key) for key in ("name", "fps_num", "fps_den", "width", "height")
        },
        "media": media,
        "tracks": [asdict(t) for t in project.tracks],
        "clips": [asdict(c) for c in project.clips],
        "subtitles": [asdict(s) for s in project.subtitles],
        "subtitle_style": asdict(project.subtitle_style),
        "transcription": project.transcription,
        "audio_master": asdict(project.audio_master),
    }


def decode(data: dict, base: Path) -> Project:
    """Reject unknown schemas and unsupported fields rather than silently lose edits."""
    try:
        expected = {"schema_version", "time_unit", "project", "media", "tracks", "clips"}
        if data.get("schema_version") in (3, 4, 5, 6):
            expected |= {"subtitles", "subtitle_style", "transcription"}
        if data.get("schema_version") in (4, 5, 6):
            expected.add("audio_master")
        if set(data) != expected:
            raise ValueError("Unexpected or missing project fields.")
        if type(data["schema_version"]) is not int or data["schema_version"] not in (
            1,
            2,
            3,
            4,
            5,
            6,
        ):
            raise ValueError("Unsupported project version. This build reads schemas 1–6.")
        if data["time_unit"] != "project_frames":
            raise ValueError("Unsupported timeline time unit.")
        media = []
        for item in data["media"]:
            info = dict(item["info"])
            raw = info["path"]
            if not isinstance(raw, str) or not raw or len(raw) > 32767 or "\x00" in raw:
                raise ValueError("Invalid media path.")
            if "://" in raw or raw.startswith(("\\\\", "//")):
                raise ValueError("Only local media paths are supported.")
            info["path"] = (base / raw).resolve()
            num, den = info["fps"]
            if type(num) is not int or type(den) is not int or den < 1:
                raise ValueError("Invalid source frame rate.")
            info["fps"] = Fraction(num, den)
            media.append(Media(item["id"], MediaInfo(**info)))
        clips = []
        for raw_clip in data["clips"]:
            item = dict(raw_clip)
            if data["schema_version"] == 1:
                if "effects" in item:
                    raise ValueError("Schema 1 cannot contain effects.")
                item["effects"] = VideoEffects()
            else:
                effect = dict(item["effects"])
                if "mask" in effect:
                    effect["mask"] = decode_mask(effect["mask"])
                item["effects"] = VideoEffects(**effect)
            clips.append(Clip(**item))
        tracks = []
        for raw_track in data["tracks"]:
            item = dict(raw_track)
            if data["schema_version"] in (4, 5, 6):
                item["audio"] = AudioSettings(**item["audio"])
            tracks.append(Track(**item))
        project = Project(
            **data["project"],
            media=tuple(media),
            tracks=tuple(tracks),
            clips=tuple(clips),
            subtitles=tuple(Subtitle(**s) for s in data.get("subtitles", [])),
            subtitle_style=SubtitleStyle(**data.get("subtitle_style", {})),
            transcription=data.get("transcription", ""),
            audio_master=AudioMaster(**data.get("audio_master", {})),
        )
        validate(project)
        return project
    except (KeyError, TypeError, AttributeError, ZeroDivisionError, OSError) as exc:
        raise ValueError(f"Malformed project: {exc}") from exc


def load_project(path: Path) -> Project:
    """Read a bounded project without trusting its references or metadata."""
    with path.open("rb") as stream:
        payload = stream.read(MAX_PROJECT_BYTES + 1)
    if len(payload) > MAX_PROJECT_BYTES:
        raise ValueError("Project exceeds the 8 MiB metadata limit.")
    try:
        return decode(json.loads(payload), path.resolve().parent)
    except (UnicodeError, RecursionError) as exc:
        raise ValueError("Invalid project JSON encoding or nesting.") from exc


def atomic_write(path: Path, payload: bytes) -> None:
    """Replace only after flush/fsync; remove a failed temporary without touching the target."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def save_project(project: Project, path: Path, backup: bool = True) -> None:
    """Save a project atomically, retaining one previous valid save as .bak."""
    path = path.resolve()
    protected = {media.info.path.resolve() for media in project.media}
    backup_path = path.with_suffix(path.suffix + ".bak")
    if path in protected or backup_path in protected:
        raise ValueError("A project must never overwrite source media.")
    payload = json.dumps(encode(project, path.parent), ensure_ascii=False, indent=2).encode("utf-8")
    if len(payload) > MAX_PROJECT_BYTES:
        raise ValueError("Project exceeds the 8 MiB metadata limit.")
    if backup and path.exists():
        load_project(path)  # Do not overwrite unrelated or malformed files silently.
        atomic_write(backup_path, path.read_bytes())
    atomic_write(path, payload)


class ProjectIOWorker(QThread):
    succeeded = Signal(object)
    failed = Signal(str)

    def __init__(self, path: Path, project: Project | None = None, *, backup=True, parent=None):
        super().__init__(parent)
        self.path, self.project, self.backup = path, project, backup

    def run(self) -> None:
        try:
            if self.project is None:
                result = load_project(self.path)
            else:
                save_project(self.project, self.path, self.backup)
                result = self.project
            self.succeeded.emit(result)
        except (OSError, ValueError, RecursionError) as exc:
            self.failed.emit(str(exc))
