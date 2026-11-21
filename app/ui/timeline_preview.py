"""Timeline monitor, separate from the existing source preview."""

from PySide6.QtCore import Qt
from PySide6.QtGui import QImageReader, QPixmap
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.core.media_probe import MediaInfo
from app.core.playback_engine import TimelinePlayback
from app.ui.preview import timecode


class TimelinePreview(QWidget):
    def __init__(self, session, parent=None):
        super().__init__(parent)
        self.video = QVideoWidget()
        self.still = QLabel("Add clips to the timeline to begin")
        self.still.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.stack = QStackedWidget()
        self.stack.addWidget(self.still)
        self.stack.addWidget(self.video)
        self.engine = TimelinePlayback(self.video, self)
        self.play = QPushButton("Play timeline")
        self.play.clicked.connect(self.engine.toggle)
        self.stop = QPushButton("Stop")
        self.stop.clicked.connect(self.engine.stop)
        self.previous = QPushButton("−1 frame")
        self.previous.clicked.connect(lambda: self.step(-1))
        self.next = QPushButton("+1 frame")
        self.next.clicked.connect(lambda: self.step(1))
        self.clock = QLabel()
        self.volume = QSlider(Qt.Orientation.Horizontal)
        self.volume.setAccessibleName("Timeline volume")
        self.volume.setRange(0, 100)
        self.volume.setValue(70)
        self.volume.setMaximumWidth(100)
        self.volume.valueChanged.connect(self.engine.set_volume)
        controls = QHBoxLayout()
        for widget in (self.play, self.stop, self.previous, self.next, self.clock, self.volume):
            controls.addWidget(widget)
        layout = QVBoxLayout(self)
        layout.addWidget(self.stack, 1)
        self.caption = QLabel()
        self.caption.setTextFormat(Qt.TextFormat.PlainText)
        self.caption.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.caption.setWordWrap(True)
        self.caption.setMaximumHeight(75)
        layout.addWidget(self.caption)
        layout.addLayout(controls)
        self.engine.position_changed.connect(self._position)
        self.engine.playing_changed.connect(
            lambda playing: self.play.setText("Pause timeline" if playing else "Play timeline")
        )
        self.engine.visual_changed.connect(self._visual)
        session.changed.connect(lambda: self.engine.set_project(session.project))
        self.engine.set_project(session.project)
        self._position(0)

    def step(self, amount: int) -> None:
        self.engine.pause()
        self.engine.seek(self.engine.frame + amount)

    def _position(self, frame: int) -> None:
        project = self.engine.project
        self.clock.setText(f"{timecode(project.milliseconds(frame))}  ·  frame {frame}")
        ms = project.milliseconds(frame)
        self.caption.setText(
            "\n".join(s.text for s in project.subtitles if s.start_ms <= ms < s.end_ms)
        )

    def _visual(self, source) -> None:
        if source == "video":
            self.stack.setCurrentWidget(self.video)
            return
        self.stack.setCurrentWidget(self.still)
        if isinstance(source, MediaInfo):
            reader = QImageReader(str(source.path))
            reader.setAutoTransform(True)
            reader.setScaledSize(
                reader.size().scaled(1280, 720, Qt.AspectRatioMode.KeepAspectRatio)
            )
            pixmap = QPixmap.fromImage(reader.read())
            self.still.setPixmap(
                pixmap.scaled(
                    self.still.size(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
        else:
            self.still.setText(source)
