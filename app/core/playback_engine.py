"""Responsive timeline preview: rational clock, one decoder per active track."""

from PySide6.QtCore import QElapsedTimer, QObject, Qt, QTimer, QUrl, Signal, Slot
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer

from app.core.project_schema import MAX_FRAME, Project


class TrackPlayback(QObject):
    failed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.player = QMediaPlayer(self)
        self.audio = QAudioOutput(self)
        self.audio.setVolume(0.7)
        self.player.setAudioOutput(self.audio)
        self.clip_id = ""
        self.target_ms = 0
        self.running = False
        self.awaiting_load = False
        self.player.mediaStatusChanged.connect(self._loaded, Qt.ConnectionType.QueuedConnection)
        self.player.errorOccurred.connect(self._error)

    @Slot(QMediaPlayer.MediaStatus)
    def _loaded(self, status) -> None:
        if (
            self.awaiting_load
            and status
            in {QMediaPlayer.MediaStatus.LoadedMedia, QMediaPlayer.MediaStatus.BufferedMedia}
            and self.player.mediaStatus()
            in {QMediaPlayer.MediaStatus.LoadedMedia, QMediaPlayer.MediaStatus.BufferedMedia}
        ):
            self.awaiting_load = False
            self.player.setPosition(self.target_ms)
            if self.running:
                self.player.play()
            else:
                self.player.pause()

    @Slot(QMediaPlayer.Error, str)
    def _error(self, error, message) -> None:
        if error != QMediaPlayer.Error.NoError:
            self.failed.emit(f"Timeline preview: {message}")

    def clear(self) -> None:
        self.running = False
        self.awaiting_load = False
        self.clip_id = ""
        self.player.stop()
        self.player.setSource(QUrl())


class TimelinePlayback(QObject):
    position_changed = Signal(int)
    playing_changed = Signal(bool)
    visual_changed = Signal(object)  # MediaInfo image, 'video', or gap message
    failed = Signal(str)

    def __init__(self, video_output, parent=None):
        super().__init__(parent)
        self.video_output = video_output
        self.project = Project()
        self.frame = 0
        self.playing = False
        self.volume = 0.7
        self.streams: dict[str, TrackPlayback] = {}
        self.visual_track = None
        self.visual_key = None
        self.timer = QTimer(self)
        self.timer.setInterval(16)
        self.timer.timeout.connect(self._tick)
        self.clock = QElapsedTimer()
        self.origin = 0

    def set_project(self, project: Project) -> None:
        """Pause on edits; never retain players for removed tracks or relinked media."""
        if self.project == project:
            return
        self.pause()
        for stream in self.streams.values():
            stream.clear()
            stream.player.setVideoOutput(None)
            stream.deleteLater()
        self.streams.clear()
        self.visual_track = None
        self.visual_key = None
        self.project = project
        self.frame = min(self.frame, project.end)
        self._sync(True)
        self.position_changed.emit(self.frame)

    def seek(self, frame: int) -> None:
        self.frame = max(0, min(frame, MAX_FRAME))
        self.origin = self.frame
        self.clock.restart()
        self._sync(True)
        self.position_changed.emit(self.frame)

    def toggle(self) -> None:
        if self.playing:
            self.pause()
        else:
            self.play()

    def play(self) -> None:
        if not self.project.end:
            return
        if self.frame >= self.project.end:
            self.frame = 0
        self.playing = True
        self.origin = self.frame
        self.clock.start()
        self._sync(True)
        self.timer.start()
        self.playing_changed.emit(True)

    def pause(self) -> None:
        self.timer.stop()
        self.playing = False
        for stream in self.streams.values():
            stream.running = False
            stream.player.pause()
        self.playing_changed.emit(False)

    def stop(self) -> None:
        self.pause()
        self.seek(0)

    def shutdown(self) -> None:
        self.pause()
        for stream in self.streams.values():
            stream.clear()

    def set_volume(self, value: int) -> None:
        self.volume = value / 100
        for stream in self.streams.values():
            stream.audio.setVolume(self.volume)

    @Slot()
    def _tick(self) -> None:
        self.frame = min(self.project.end, self.origin + self.project.frames(self.clock.elapsed()))
        if self.frame >= self.project.end:
            self.pause()
        self._sync()
        self.position_changed.emit(self.frame)

    def _sync(self, force: bool = False) -> None:
        active = {
            clip.track_id: clip
            for clip in self.project.clips
            if clip.start <= self.frame < clip.end
        }
        visual = next(
            (
                track.id
                for track in self.project.tracks
                if track.kind == "video" and not track.hidden and track.id in active
            ),
            None,
        )
        previous_visual = self.visual_track
        self.visual_track = visual
        for track in self.project.tracks:
            clip = active.get(track.id)
            stream = self.streams.get(track.id)
            if clip is None:
                if stream and stream.clip_id:
                    stream.clear()
                continue
            media = self.project.media_by_id(clip.media_id).info
            if media.is_image or not media.path.is_file():
                if stream and stream.clip_id:
                    stream.clear()
                continue
            if stream is None:
                stream = TrackPlayback(self)
                stream.failed.connect(self.failed)
                self.streams[track.id] = stream
            if track.id == visual:
                stream.player.setVideoOutput(self.video_output)
            stream.audio.setMuted(track.muted)
            stream.audio.setVolume(self.volume)
            stream.target_ms = self.project.milliseconds(clip.source_in + self.frame - clip.start)
            stream.running = self.playing
            changed = stream.clip_id != clip.id
            if changed:
                stream.clip_id = clip.id
                source = QUrl.fromLocalFile(str(media.path))
                if stream.player.source() != source:
                    stream.awaiting_load = True
                    stream.player.setSource(source)
            if changed or force:
                stream.player.setPosition(stream.target_ms)
                if self.playing:
                    stream.player.play()
                else:
                    stream.player.pause()
        # Stop inactive decoders before detaching their output. Detaching an active
        # Qt FFmpeg sink first can deadlock its audio renderer during stop on Windows.
        if previous_visual != visual and previous_visual in self.streams:
            self.streams[previous_visual].player.setVideoOutput(None)
        clip = active.get(visual)
        key = clip.id if clip else None
        if force or key != self.visual_key:
            self.visual_key = key
            if clip:
                media = self.project.media_by_id(clip.media_id).info
                if not media.path.is_file():
                    self.visual_changed.emit("Missing media — relink the source in the library")
                else:
                    self.visual_changed.emit(media if media.is_image else "video")
            else:
                self.visual_changed.emit("No video at this frame")
