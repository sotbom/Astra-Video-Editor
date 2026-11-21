"""Interactive track canvas, frame-based inspector and reversible edit controls."""

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QBrush, QColor, QFontMetrics, QPainterPath, QPen
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QGraphicsScene,
    QGraphicsView,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from app.core.command_manager import ProjectSession
from app.core.project_schema import MAX_FRAME
from app.core.timeline_engine import TimelineEngine

MEDIA_MIME = "application/x-astra-media-path"
LEFT = 150
TOP = 30
ROW = 54


class TimelineView(QGraphicsView):
    selected = Signal(str)
    seek = Signal(int)
    failed = Signal(str)
    edited = Signal()

    def __init__(self, session: ProjectSession, engine: TimelineEngine, parent=None):
        super().__init__(parent)
        self.session, self.engine = session, engine
        self.setScene(QGraphicsScene(self))
        self.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self.setAcceptDrops(True)
        self.setMinimumHeight(180)
        self.setAccessibleName("Timeline tracks")
        self.scale_x = 3.0
        self.playhead = 0
        self.selected_id = ""
        self.snap = True
        self.gesture = None
        self.ghost = None
        self.playhead_line = None
        self.waveforms = {}
        self.redraw()

    def frame_at(self, x: float) -> int:
        return min(MAX_FRAME, max(0, round((x - LEFT) / self.scale_x)))

    def track_at(self, y: float) -> int:
        return max(0, min(len(self.session.project.tracks) - 1, int((y - TOP) // ROW)))

    def redraw(self) -> None:
        self.gesture = None
        self.ghost = None
        self.scene().clear()
        project = self.session.project
        extent = min(
            MAX_FRAME,
            max(project.end + round(project.fps * 10), self.playhead + round(project.fps * 5), 900),
        )
        width = LEFT + extent * self.scale_x
        height = TOP + max(3, len(project.tracks)) * ROW
        self.scene().setSceneRect(0, 0, width, height)
        self.scene().setBackgroundBrush(QColor("#10151e"))
        # Bound ruler density even on long projects or at extreme zoom.
        step = max(1, round(float(project.fps)))
        while extent // step > 300 or step * self.scale_x < 55:
            step *= 2
        for frame in range(0, extent + 1, step):
            x = LEFT + frame * self.scale_x
            self.scene().addLine(x, 0, x, height, QPen(QColor("#273244")))
            label = self.scene().addText(f"{project.milliseconds(frame) / 1000:g}s")
            label.setDefaultTextColor(QColor("#94a5bd"))
            label.setPos(x + 2, 0)
        for index, track in enumerate(project.tracks):
            y = TOP + index * ROW
            self.scene().addRect(0, y, width, ROW, QPen(QColor("#303a4e")))
            text = track.name + (" [locked]" if track.locked else "")
            text += " [mute]" if track.muted else ""
            label = self.scene().addText(text)
            label.setDefaultTextColor(QColor("#e6eaf2"))
            label.setTextWidth(LEFT - 8)
            label.setPos(4, y + 3)
            for clip in (c for c in project.clips if c.track_id == track.id):
                media = project.media_by_id(clip.media_id)
                color = "#2e6980" if track.kind == "audio" else "#395c95"
                if not media.info.path.is_file():
                    color = "#803f49"
                rect = self.scene().addRect(
                    LEFT + clip.start * self.scale_x,
                    y + 5,
                    max(2, clip.duration * self.scale_x),
                    ROW - 10,
                    QPen(
                        QColor("#91caff" if clip.id == self.selected_id else "#536b8b"),
                        2 if clip.id == self.selected_id else 1,
                    ),
                    QBrush(QColor(color)),
                )
                rect.setData(0, clip.id)
                waveform = self.waveforms.get(media.info.path)
                if waveform and media.info.audio_codec:
                    start_ms = project.milliseconds(clip.source_in)
                    duration_ms = project.milliseconds(clip.duration)
                    points = min(1000, max(2, int(clip.duration * self.scale_x)))
                    wave = QPainterPath()
                    for n in range(points):
                        index = int((start_ms + duration_ms * n / points) / waveform["bin_ms"])
                        peak = waveform["peaks"][index] if index < len(waveform["peaks"]) else 0
                        x = LEFT + (clip.start + clip.duration * n / points) * self.scale_x
                        wave.moveTo(x, y + 35 - peak * 12)
                        wave.lineTo(x, y + 35 + peak * 12)
                    item = self.scene().addPath(wave, QPen(QColor("#8be0cb")))
                    item.setParentItem(rect)
                title = QFontMetrics(self.font()).elidedText(
                    media.info.name,
                    Qt.TextElideMode.ElideRight,
                    max(1, int(clip.duration * self.scale_x - 12)),
                )
                label = self.scene().addSimpleText(title)
                label.setBrush(QColor("#ffffff"))
                label.setPos(LEFT + clip.start * self.scale_x + 5, y + 10)
                label.setParentItem(rect)
                # Rect coordinates are in scene coordinates; parent transform is identity.
                label.setToolTip(f"{media.info.name} • frames {clip.start}–{clip.end}")
        self.playhead_line = self.scene().addLine(
            LEFT + self.playhead * self.scale_x,
            0,
            LEFT + self.playhead * self.scale_x,
            height,
            QPen(QColor("#ffcc66"), 2),
        )
        self.playhead_line.setZValue(10)

    def set_playhead(self, frame: int) -> None:
        self.playhead = frame
        if self.playhead_line:
            x = LEFT + frame * self.scale_x
            if x > self.sceneRect().right():
                self.scene().setSceneRect(0, 0, x + 500, self.sceneRect().height())
            self.playhead_line.setLine(x, 0, x, self.sceneRect().height())

    def _snap_frame(self, frame: int, excluded: str) -> int:
        if not self.snap:
            return frame
        targets = [0, self.playhead]
        for clip in self.session.project.clips:
            if clip.id != excluded:
                targets.extend((clip.start, clip.end))
        target = min(targets, key=lambda t: abs(t - frame))
        return target if abs(target - frame) * self.scale_x <= 8 else frame

    def mousePressEvent(self, event) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            return super().mousePressEvent(event)
        point = self.mapToScene(event.position().toPoint())
        if point.x() < LEFT:
            return
        index = self.track_at(point.y())
        frame = self.frame_at(point.x())
        track = self.session.project.tracks[index]
        clip = next(
            (
                c
                for c in self.session.project.clips
                if c.track_id == track.id and c.start <= frame < c.end
            ),
            None,
        )
        if point.y() < TOP or clip is None:
            self.seek.emit(frame)
            return
        self.selected_id = clip.id
        self.selected.emit(clip.id)
        self.redraw()
        if track.locked:
            return
        left = LEFT + clip.start * self.scale_x
        right = LEFT + clip.end * self.scale_x
        mode = "left" if point.x() - left < 8 else "right" if right - point.x() < 8 else "move"
        self.gesture = (clip, frame, mode)
        event.accept()

    def _proposal(self, point):
        clip, origin, mode = self.gesture
        delta = self.frame_at(point.x()) - origin
        start, source_in, source_out, track_id = (
            clip.start,
            clip.source_in,
            clip.source_out,
            clip.track_id,
        )
        if mode == "move":
            start = max(0, self._snap_frame(clip.start + delta, clip.id))
            track_id = self.session.project.tracks[self.track_at(point.y())].id
        elif mode == "left":
            start = self._snap_frame(clip.start + delta, clip.id)
            start = max(0, clip.start - clip.source_in, min(clip.end - 1, start))
            source_in += start - clip.start
        else:
            end = self._snap_frame(clip.end + delta, clip.id)
            limit = self.session.project.source_length(
                self.session.project.media_by_id(clip.media_id)
            )
            source_out = max(source_in + 1, min(limit, clip.source_out + end - clip.end))
        return dict(start=start, source_in=source_in, source_out=source_out, track_id=track_id)

    def mouseMoveEvent(self, event) -> None:
        if not self.gesture:
            return super().mouseMoveEvent(event)
        proposal = self._proposal(self.mapToScene(event.position().toPoint()))
        if self.ghost:
            self.scene().removeItem(self.ghost)
        row = next(
            i for i, t in enumerate(self.session.project.tracks) if t.id == proposal["track_id"]
        )
        self.ghost = self.scene().addRect(
            LEFT + proposal["start"] * self.scale_x,
            TOP + row * ROW + 5,
            (proposal["source_out"] - proposal["source_in"]) * self.scale_x,
            ROW - 10,
            QPen(QColor("#ffcc66"), 2),
            QBrush(QColor(255, 204, 102, 80)),
        )
        event.accept()

    def mouseReleaseEvent(self, event) -> None:
        if not self.gesture:
            return super().mouseReleaseEvent(event)
        clip = self.gesture[0]
        proposal = self._proposal(self.mapToScene(event.position().toPoint()))
        self.gesture = None
        try:
            self.engine.edit_clip(clip.id, **proposal)
            self.edited.emit()
        except ValueError as exc:
            self.failed.emit(str(exc))
        self.redraw()

    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasFormat(MEDIA_MIME):
            event.acceptProposedAction()

    def dragMoveEvent(self, event) -> None:
        if event.mimeData().hasFormat(MEDIA_MIME):
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:
        if not event.mimeData().hasFormat(MEDIA_MIME):
            return
        point = self.mapToScene(event.position().toPoint())
        try:
            path = Path(bytes(event.mimeData().data(MEDIA_MIME)).decode("utf-8"))
            media_id = self.engine.media_id_for_path(path)
            track_id = self.session.project.tracks[self.track_at(point.y())].id
            clip_id = self.engine.add_clip(media_id, track_id, self.frame_at(point.x()))
            self.selected_id = clip_id
            self.selected.emit(clip_id)
            self.redraw()
            self.edited.emit()
            event.acceptProposedAction()
        except (ValueError, StopIteration, UnicodeError) as exc:
            self.failed.emit(str(exc) or "This media is no longer in the project.")


class TimelineWidget(QWidget):
    seek = Signal(int)
    add_requested = Signal(str, int)
    failed = Signal(str)

    def __init__(self, session: ProjectSession, parent=None):
        super().__init__(parent)
        self.session = session
        self.engine = TimelineEngine(session)
        self.selected_id = ""
        self.view = TimelineView(session, self.engine)
        self.view.selected.connect(self.select_clip)
        self.view.seek.connect(self.set_playhead)
        self.view.failed.connect(self.failed)
        self.playhead = QSpinBox()
        self.playhead.setRange(0, MAX_FRAME)
        self.playhead.setPrefix("Frame ")
        self.playhead.setAccessibleName("Timeline playhead frame")
        self.playhead.valueChanged.connect(self._seek)
        self.track = QComboBox()
        self.track.setAccessibleName("Target track")
        self.track.currentIndexChanged.connect(self._track_flags)
        self.add_button = QPushButton("Add selected media")
        self.add_button.clicked.connect(
            lambda: self.add_requested.emit(self.track.currentData(), self.playhead.value())
        )
        self.split_button = QPushButton("Split")
        self.split_button.clicked.connect(self.split)
        self.delete_button = QPushButton("Delete clip")
        self.delete_button.clicked.connect(self.delete)
        row = QHBoxLayout()
        row.addWidget(QLabel("TIMELINE"))
        for widget in (
            self.track,
            self.add_button,
            self.split_button,
            self.delete_button,
            self.playhead,
        ):
            row.addWidget(widget)
        row2 = QHBoxLayout()
        for kind in ("video", "audio"):
            button = QPushButton(f"+ {kind.title()} track")
            button.clicked.connect(
                lambda checked=False, k=kind: self.perform(self.engine.add_track, k)
            )
            row2.addWidget(button)
        self.flags = {}
        for key, label in (("muted", "Mute"), ("hidden", "Hide video"), ("locked", "Lock")):
            check = QCheckBox(label)
            check.toggled.connect(lambda value, k=key: self.change_track(k, value))
            self.flags[key] = check
            row2.addWidget(check)
        snap = QCheckBox("Snap")
        snap.setChecked(True)
        snap.toggled.connect(lambda value: setattr(self.view, "snap", value))
        row2.addWidget(snap)
        row2.addStretch()
        row2.addWidget(QLabel("Zoom"))
        zoom = QSlider(Qt.Orientation.Horizontal)
        zoom.setRange(5, 100)
        zoom.setValue(30)
        zoom.setMaximumWidth(140)
        zoom.valueChanged.connect(self._zoom)
        row2.addWidget(zoom)
        self.start, self.source_in, self.source_out = QSpinBox(), QSpinBox(), QSpinBox()
        inspector = QHBoxLayout()
        for label, spin in (
            ("Start frame", self.start),
            ("Source in", self.source_in),
            ("Source out (exclusive)", self.source_out),
        ):
            spin.setRange(0, MAX_FRAME)
            spin.setAccessibleName(label)
            inspector.addWidget(QLabel(label))
            inspector.addWidget(spin)
        self.apply_button = QPushButton("Apply move / trim")
        self.apply_button.clicked.connect(self.apply_edit)
        inspector.addWidget(self.apply_button)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(row)
        layout.addLayout(row2)
        layout.addWidget(self.view, 1)
        layout.addLayout(inspector)
        session.changed.connect(self.refresh)
        self.refresh()

    def perform(self, operation, *args, **kwargs):
        try:
            return operation(*args, **kwargs)
        except (ValueError, StopIteration) as exc:
            self.failed.emit(str(exc) or "Select a valid clip or track.")
            return None

    def _zoom(self, value):
        self.view.scale_x = value / 10
        self.view.redraw()

    def _seek(self, frame):
        self.view.set_playhead(frame)
        self.seek.emit(frame)

    def set_playhead(self, frame: int) -> None:
        self.playhead.setValue(frame)

    def follow_playhead(self, frame: int) -> None:
        self.playhead.blockSignals(True)
        self.playhead.setValue(frame)
        self.playhead.blockSignals(False)
        self.view.set_playhead(frame)

    def refresh(self) -> None:
        current = self.track.currentData()
        self.track.blockSignals(True)
        self.track.clear()
        for track in self.session.project.tracks:
            self.track.addItem(track.name, track.id)
        index = self.track.findData(current)
        self.track.setCurrentIndex(max(0, index))
        self.track.blockSignals(False)
        self._track_flags()
        if not any(c.id == self.selected_id for c in self.session.project.clips):
            self.selected_id = ""
        self.view.selected_id = self.selected_id
        self.view.redraw()
        self.select_clip(self.selected_id)

    def _track_flags(self) -> None:
        if not self.track.currentData():
            return
        track = self.session.project.track_by_id(self.track.currentData())
        for key, check in self.flags.items():
            check.blockSignals(True)
            check.setChecked(getattr(track, key))
            check.setEnabled(key != "hidden" or track.kind == "video")
            check.blockSignals(False)

    def change_track(self, key: str, value: bool) -> None:
        self.perform(self.engine.set_track, self.track.currentData(), **{key: value})

    def select_clip(self, clip_id: str) -> None:
        self.selected_id = clip_id
        exists = any(c.id == clip_id for c in self.session.project.clips)
        for widget in (
            self.split_button,
            self.delete_button,
            self.apply_button,
            self.start,
            self.source_in,
            self.source_out,
        ):
            widget.setEnabled(exists)
        if exists:
            clip = self.session.project.clip_by_id(clip_id)
            self.start.setValue(clip.start)
            self.source_in.setValue(clip.source_in)
            self.source_out.setValue(clip.source_out)
            self.track.setCurrentIndex(self.track.findData(clip.track_id))
        self.view.selected_id = clip_id

    def apply_edit(self) -> None:
        if self.selected_id:
            self.perform(
                self.engine.edit_clip,
                self.selected_id,
                start=self.start.value(),
                source_in=self.source_in.value(),
                source_out=self.source_out.value(),
                track_id=self.track.currentData(),
            )

    def split(self) -> None:
        if self.selected_id:
            result = self.perform(self.engine.split, self.selected_id, self.playhead.value())
            if result:
                self.select_clip(result)
                self.view.redraw()

    def delete(self) -> None:
        if self.selected_id:
            self.perform(self.engine.delete, self.selected_id)
