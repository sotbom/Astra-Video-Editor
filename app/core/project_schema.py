"""Immutable project data. All clip times are integer project-frame coordinates."""

from dataclasses import dataclass, field
from fractions import Fraction
from pathlib import Path
from uuid import uuid4

from app.audio.effects import AudioMaster, AudioSettings, validate_audio, validate_master
from app.core.media_probe import MediaInfo
from app.core.subtitles import Subtitle, SubtitleStyle, validate_subtitles
from app.video.filters import VideoEffects, validate_effects

MAX_FRAME = 100_000_000


def new_id() -> str:
    """Generate a stable identifier independent of display names and paths."""
    return uuid4().hex


@dataclass(frozen=True)
class Media:
    id: str
    info: MediaInfo


@dataclass(frozen=True)
class Track:
    id: str
    name: str
    kind: str
    muted: bool = False
    hidden: bool = False
    locked: bool = False
    audio: AudioSettings = field(default_factory=AudioSettings)


@dataclass(frozen=True)
class Clip:
    id: str
    media_id: str
    track_id: str
    start: int
    source_in: int
    source_out: int
    effects: VideoEffects = field(default_factory=VideoEffects)
    fade_in_ms: int = 0
    fade_out_ms: int = 0

    @property
    def duration(self) -> int:
        return self.source_out - self.source_in

    @property
    def end(self) -> int:
        return self.start + self.duration


@dataclass(frozen=True)
class Project:
    name: str = "Untitled"
    fps_num: int = 30
    fps_den: int = 1
    width: int = 1920
    height: int = 1080
    media: tuple[Media, ...] = ()
    tracks: tuple[Track, ...] = field(
        default_factory=lambda: (
            Track(new_id(), "Video 1", "video"),
            Track(new_id(), "Audio 1", "audio"),
        )
    )
    clips: tuple[Clip, ...] = ()
    subtitles: tuple[Subtitle, ...] = ()
    subtitle_style: SubtitleStyle = field(default_factory=SubtitleStyle)
    transcription: str = ""
    audio_master: AudioMaster = field(default_factory=AudioMaster)

    @property
    def fps(self) -> Fraction:
        return Fraction(self.fps_num, self.fps_den)

    @property
    def end(self) -> int:
        subtitle_end = max((s.end_ms for s in self.subtitles), default=0)
        subtitle_frames = -(-subtitle_end * self.fps_num // (1000 * self.fps_den))
        return max(max((clip.end for clip in self.clips), default=0), subtitle_frames)

    def milliseconds(self, frame: int) -> int:
        """Convert only at the Qt playback boundary; project timing stays exact."""
        return round(Fraction(frame * 1000, 1) / self.fps)

    def frames(self, milliseconds: int) -> int:
        return int(Fraction(milliseconds, 1000) * self.fps)

    def media_by_id(self, media_id: str) -> Media:
        return next(item for item in self.media if item.id == media_id)

    def track_by_id(self, track_id: str) -> Track:
        return next(item for item in self.tracks if item.id == track_id)

    def clip_by_id(self, clip_id: str) -> Clip:
        return next(item for item in self.clips if item.id == clip_id)

    def source_length(self, media: Media) -> int:
        return MAX_FRAME if media.info.is_image else self.frames(media.info.duration_ms)

    def missing_media(self) -> list[Media]:
        return [media for media in self.media if not media.info.path.is_file()]


def validate(project: Project) -> None:
    """Reject invalid references, overlapping clips, incompatible tracks and source ranges."""

    validate_subtitles(project.subtitles, project.subtitle_style)
    validate_master(project.audio_master)
    if not isinstance(project.transcription, str) or len(project.transcription) > 4000:
        raise ValueError("Invalid transcription provenance.")

    def integer(value, low=0, high=MAX_FRAME):
        if type(value) is not int or not low <= value <= high:
            raise ValueError(f"Expected integer in range {low}–{high}.")

    if not isinstance(project.name, str) or not 1 <= len(project.name) <= 200:
        raise ValueError("Project name must contain 1–200 characters.")
    integer(project.fps_num, 1, 240_000)
    integer(project.fps_den, 1, 100_000)
    if not 1 <= project.fps <= 240:
        raise ValueError("Project frame rate must be between 1 and 240 fps.")
    integer(project.width, 1, 16384)
    integer(project.height, 1, 16384)
    if not 1 <= len(project.tracks) <= 32 or len(project.clips) > 10000:
        raise ValueError("Projects support 1–32 tracks and up to 10,000 clips.")
    if len(project.media) > 10000:
        raise ValueError("Too many media references.")
    if len({media.info.path for media in project.media}) != len(project.media):
        raise ValueError("This source path is already in the project.")
    for group in (project.media, project.tracks, project.clips):
        ids = [item.id for item in group]
        if any(not isinstance(i, str) or not 1 <= len(i) <= 100 for i in ids):
            raise ValueError("Invalid identifier.")
        if len(set(ids)) != len(ids):
            raise ValueError("Duplicate identifiers.")
    for media in project.media:
        info = media.info
        if not isinstance(info.path, Path) or not info.path.is_absolute():
            raise ValueError("Media paths must resolve to local absolute paths.")
        integer(info.duration_ms, 0, 604800000)
        integer(info.width, 0, 65536)
        integer(info.height, 0, 65536)
        integer(info.sample_rate, 0, 768000)
        integer(info.channels, 0, 256)
        if not 0 <= info.fps <= 1000 or type(info.is_image) is not bool:
            raise ValueError("Invalid media properties.")
        if any(
            not isinstance(v, str) or len(v) > 100 for v in (info.video_codec, info.audio_codec)
        ):
            raise ValueError("Invalid codec metadata.")
    for track in project.tracks:
        validate_audio(track.audio)
        if track.kind not in {"video", "audio"}:
            raise ValueError("Unsupported track kind.")
        if not isinstance(track.name, str) or not 1 <= len(track.name) <= 100:
            raise ValueError("Invalid track name.")
        if any(type(v) is not bool for v in (track.hidden, track.muted, track.locked)):
            raise ValueError("Invalid track flags.")
    for clip in project.clips:
        integer(clip.fade_in_ms, 0, 604800000)
        integer(clip.fade_out_ms, 0, 604800000)
        for value in (clip.start, clip.source_in, clip.source_out, clip.end):
            integer(value)
        if clip.duration <= 0:
            raise ValueError("Clips must contain at least one frame.")
        try:
            media = project.media_by_id(clip.media_id)
            track = project.track_by_id(clip.track_id)
        except StopIteration as exc:
            raise ValueError("Clip references missing media or track.") from exc
        if clip.source_out > project.source_length(media):
            raise ValueError("Clip extends beyond its source media.")
        if track.kind == "video" and not media.info.video_codec:
            raise ValueError("Audio-only files belong on audio tracks.")
        if track.kind == "audio" and not media.info.audio_codec:
            raise ValueError("This source has no audio stream.")
        if track.kind == "video":
            validate_effects(clip.effects, media.info.width, media.info.height)
        elif clip.effects != VideoEffects():
            raise ValueError("Video effects require a video track.")
    for track in project.tracks:
        clips = sorted((c for c in project.clips if c.track_id == track.id), key=lambda c: c.start)
        if any(left.end > right.start for left, right in zip(clips, clips[1:])):
            raise ValueError("Clips cannot overlap on the same track; use another track.")
