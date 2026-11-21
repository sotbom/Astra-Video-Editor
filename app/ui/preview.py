"""Local Qt Multimedia playback with explicit transport controls."""

from PySide6.QtCore import Qt, QUrl, Signal, Slot
from PySide6.QtGui import QImageReader, QPixmap
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.core.media_probe import MediaInfo


def timecode(ms: int) -> str:
    """Format integer milliseconds without losing the subsecond position."""
    seconds, milliseconds = divmod(max(0, ms), 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours:02}:{minutes:02}:{seconds:02}.{milliseconds:03}"


class Preview(QWidget):
    failed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.player = QMediaPlayer(self)
        self.audio = QAudioOutput(self)
        self.audio.setVolume(0.7)
        self.player.setAudioOutput(self.audio)
        self.video = QVideoWidget()
        self.player.setVideoOutput(self.video)
        self.still = QLabel("Import local media to begin\nSelect an item in the library to preview")
        self.still.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.still.setMinimumSize(240, 180)
        self.stack = QStackedWidget()
        self.stack.addWidget(self.still)
        self.stack.addWidget(self.video)
        self.image = QPixmap()
        self.title = QLabel("SOURCE PREVIEW")
        self.title.setObjectName("heading")
        self.seek = QSlider(Qt.Orientation.Horizontal)
        self.seek.setAccessibleName("Playback position")
        self.seek.setRange(0, 0)
        self.seek.sliderMoved.connect(self.player.setPosition)
        self.seek.sliderReleased.connect(lambda: self.player.setPosition(self.seek.value()))
        self.clock = QLabel(f"{timecode(0)} / {timecode(0)}")
        self.play = QPushButton("Play")
        self.play.clicked.connect(self.toggle)
        self.stop = QPushButton("Stop")
        self.stop.clicked.connect(lambda: self.player.stop())
        self.speed = QComboBox()
        self.speed.setAccessibleName("Playback speed")
        for rate in (0.5, 1.0, 1.5, 2.0):
            self.speed.addItem(f"{rate:g}×", rate)
        self.speed.setCurrentIndex(1)
        self.speed.currentIndexChanged.connect(
            lambda: self.player.setPlaybackRate(self.speed.currentData())
        )
        self.volume = QSlider(Qt.Orientation.Horizontal)
        self.volume.setAccessibleName("Volume")
        self.volume.setRange(0, 100)
        self.volume.setValue(70)
        self.volume.setMaximumWidth(100)
        self.volume.valueChanged.connect(lambda v: self.audio.setVolume(v / 100))
        row = QHBoxLayout()
        for widget in (self.play, self.stop, self.clock, self.speed, QLabel("Volume"), self.volume):
            row.addWidget(widget)
        layout = QVBoxLayout(self)
        layout.addWidget(self.title)
        layout.addWidget(self.stack, 1)
        layout.addWidget(self.seek)
        layout.addLayout(row)
        self.player.durationChanged.connect(self._duration)
        self.player.positionChanged.connect(self._position)
        self.player.playbackStateChanged.connect(self._state)
        self.player.errorOccurred.connect(self._error)
        self._enable(False)

    def _enable(self, enabled: bool) -> None:
        for widget in (self.play, self.stop, self.seek, self.speed):
            widget.setEnabled(enabled)

    def clear(self) -> None:
        """Release a previous project's source before replacing library contents."""
        self.player.stop()
        self.player.setSource(QUrl())
        self.image = QPixmap()
        self.still.setText("Import local media to begin")
        self.stack.setCurrentWidget(self.still)
        self.title.setText("SOURCE PREVIEW")
        self._enable(False)

    def load(self, media: MediaInfo) -> None:
        """Select a source, leaving playback paused until requested."""
        self.player.stop()
        self.player.setSource(QUrl())
        self.title.setText(media.name)
        self.image = QPixmap()
        self._enable(not media.is_image)
        if media.is_image:
            reader = QImageReader(str(media.path))
            reader.setAutoTransform(True)
            reader.setScaledSize(
                reader.size().scaled(1920, 1080, Qt.AspectRatioMode.KeepAspectRatio)
            )
            self.image = QPixmap.fromImage(reader.read())
            if self.image.isNull():
                self.failed.emit("Qt could not decode this image.")
            self.stack.setCurrentWidget(self.still)
            self._scale_image()
        else:
            self.still.setText("Audio preview")
            self.stack.setCurrentWidget(self.video if media.video_codec else self.still)
            self.player.setSource(QUrl.fromLocalFile(str(media.path)))

    def toggle(self) -> None:
        """Toggle actual player state; safe with no source selected."""
        if not self.play.isEnabled():
            return
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
        else:
            self.player.play()

    @Slot("qint64")
    def _duration(self, duration: int) -> None:
        self.seek.setRange(0, min(duration, 2_147_483_647))
        self._position(self.player.position())

    @Slot("qint64")
    def _position(self, position: int) -> None:
        if not self.seek.isSliderDown():
            self.seek.setValue(position)
        self.clock.setText(f"{timecode(position)} / {timecode(self.player.duration())}")

    @Slot(QMediaPlayer.PlaybackState)
    def _state(self, state) -> None:
        self.play.setText("Pause" if state == QMediaPlayer.PlaybackState.PlayingState else "Play")

    @Slot(QMediaPlayer.Error, str)
    def _error(self, error, message: str) -> None:
        if error != QMediaPlayer.Error.NoError:
            self.failed.emit(f"Playback failed: {message}. Try another file or codec.")

    def _scale_image(self) -> None:
        if not self.image.isNull():
            self.still.setPixmap(
                self.image.scaled(
                    self.still.size(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._scale_image()
