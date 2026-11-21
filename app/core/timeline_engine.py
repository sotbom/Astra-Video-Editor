"""Validated non-destructive editing operations; no widget or decoder dependencies."""

from dataclasses import replace
from pathlib import Path

from app.core.command_manager import ProjectSession
from app.core.media_probe import MediaInfo
from app.core.project_schema import Clip, Media, Track, new_id


class TimelineEngine:
    def __init__(self, session: ProjectSession):
        self.session = session

    @property
    def project(self):
        return self.session.project

    def import_media(self, info: MediaInfo) -> str:
        """Add inspected media once; preserve stable references across edits."""
        existing = next((m for m in self.project.media if m.info.path == info.path), None)
        if existing:
            return existing.id
        media = Media(new_id(), info)
        self.session.execute(
            "Import media", replace(self.project, media=(*self.project.media, media))
        )
        return media.id

    def add_track(self, kind: str) -> str:
        track = Track(
            new_id(), f"{kind.title()} {sum(t.kind == kind for t in self.project.tracks) + 1}", kind
        )
        self.session.execute(
            "Add track", replace(self.project, tracks=(*self.project.tracks, track))
        )
        return track.id

    def set_track(self, track_id: str, **changes) -> None:
        if not changes.keys() <= {"name", "locked", "hidden", "muted"}:
            raise ValueError("Unsupported track property.")
        tracks = tuple(
            replace(t, **changes) if t.id == track_id else t for t in self.project.tracks
        )
        self.session.execute("Track properties", replace(self.project, tracks=tracks))

    def _unlocked(self, track_id: str) -> None:
        if self.project.track_by_id(track_id).locked:
            raise ValueError("Unlock the track before editing its clips.")

    def add_clip(self, media_id: str, track_id: str, start: int) -> str:
        self._unlocked(track_id)
        media = self.project.media_by_id(media_id)
        length = (
            self.project.frames(5000) if media.info.is_image else self.project.source_length(media)
        )
        clip = Clip(new_id(), media_id, track_id, start, 0, length)
        self.session.execute("Add clip", replace(self.project, clips=(*self.project.clips, clip)))
        return clip.id

    def edit_clip(
        self,
        clip_id: str,
        *,
        start: int,
        source_in: int,
        source_out: int,
        track_id: str | None = None,
    ) -> None:
        clip = self.project.clip_by_id(clip_id)
        self._unlocked(clip.track_id)
        target = track_id or clip.track_id
        self._unlocked(target)
        updated = replace(
            clip, start=start, source_in=source_in, source_out=source_out, track_id=target
        )
        clips = tuple(updated if c.id == clip_id else c for c in self.project.clips)
        self.session.execute("Move / trim clip", replace(self.project, clips=clips))

    def split(self, clip_id: str, frame: int) -> str:
        clip = self.project.clip_by_id(clip_id)
        self._unlocked(clip.track_id)
        if not clip.start < frame < clip.end:
            raise ValueError("Place the playhead inside the selected clip to split it.")
        cut = clip.source_in + frame - clip.start
        left = replace(clip, source_out=cut)
        right = replace(clip, id=new_id(), start=frame, source_in=cut)
        clips = tuple(left if c.id == clip_id else c for c in self.project.clips) + (right,)
        self.session.execute("Split clip", replace(self.project, clips=clips))
        return right.id

    def delete(self, clip_id: str) -> None:
        clip = self.project.clip_by_id(clip_id)
        self._unlocked(clip.track_id)
        self.session.execute(
            "Delete clip",
            replace(self.project, clips=tuple(c for c in self.project.clips if c.id != clip_id)),
        )

    def set_effects(self, clip_id: str, effects) -> None:
        """Apply validated reversible video settings to a selected clip."""
        clip = self.project.clip_by_id(clip_id)
        self._unlocked(clip.track_id)
        self.session.execute(
            "Video effects",
            replace(
                self.project,
                clips=tuple(
                    replace(c, effects=effects) if c.id == clip_id else c
                    for c in self.project.clips
                ),
            ),
        )

    def set_audio(self, track_id, settings, clip_id=None, fade_in_ms=0, fade_out_ms=0, master=None):
        """Apply a track processor chain, optional clip fades and mastering as one edit."""
        self._unlocked(track_id)
        tracks = tuple(
            replace(t, audio=settings) if t.id == track_id else t for t in self.project.tracks
        )
        clips = self.project.clips
        if clip_id:
            clip = self.project.clip_by_id(clip_id)
            if clip.track_id != track_id:
                raise ValueError("Selected clip must belong to the chosen track.")
            clips = tuple(
                replace(c, fade_in_ms=fade_in_ms, fade_out_ms=fade_out_ms) if c.id == clip_id else c
                for c in clips
            )
        self.session.execute(
            "Audio processing",
            replace(
                self.project,
                tracks=tracks,
                clips=clips,
                audio_master=master or self.project.audio_master,
            ),
        )

    def relink(self, media_id: str, info: MediaInfo) -> None:
        """Use newly probed metadata; reject shorter/incompatible replacement sources."""
        media = tuple(replace(m, info=info) if m.id == media_id else m for m in self.project.media)
        self.session.execute("Relink media", replace(self.project, media=media))

    def media_id_for_path(self, path: Path) -> str:
        return next(m.id for m in self.project.media if m.info.path == path)
