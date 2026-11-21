"""Interactive normalized mask drawing and positioning."""

from dataclasses import replace

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QImage, QPainter, QPen
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.video.masks import Mask, mask_path


class MaskCanvas(QWidget):
    changed = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.mask = Mask()
        self.image = QImage()
        self.points = []
        self.origin = None
        self.setMinimumSize(480, 270)

    def paintEvent(self, event):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor("#181818"))
        if not self.image.isNull():
            p.drawImage(self.rect(), self.image)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(QPen(QColor("#40dfff"), 2))
        p.drawPath(mask_path(self.mask, self.width(), self.height()))
        p.end()

    def point(self, event):
        return (
            max(0, min(1, event.position().x() / self.width())),
            max(0, min(1, event.position().y() / self.height())),
        )

    def mousePressEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton:
            return
        self.origin = self.point(event)
        if self.mask.shape == "polygon":
            self.points = (self.points + [self.origin])[:256]
            self.commit_points()
        else:
            self.points = [self.origin]

    def mouseMoveEvent(self, event):
        if self.origin is None or not event.buttons() & Qt.MouseButton.LeftButton:
            return
        point = self.point(event)
        if self.mask.shape == "freehand":
            if len(self.points) < 256:
                self.points.append(point)
            self.commit_points()
        elif self.mask.shape in ("rectangle", "ellipse"):
            x, y = min(self.origin[0], point[0]), min(self.origin[1], point[1])
            w, h = abs(point[0] - self.origin[0]), abs(point[1] - self.origin[1])
            if w >= 0.001 and h >= 0.001:
                self.mask = replace(self.mask, x=x, y=y, width=w, height=h)
                self.changed.emit(self.mask)
                self.update()

    def mouseReleaseEvent(self, event):
        self.mouseMoveEvent(event)
        self.origin = None

    def commit_points(self):
        if len(self.points) >= 3:
            xs, ys = zip(*self.points)
            if max(xs) - min(xs) >= 0.001 and max(ys) - min(ys) >= 0.001:
                self.mask = replace(
                    self.mask,
                    points=tuple(self.points),
                    x=min(xs),
                    y=min(ys),
                    width=max(xs) - min(xs),
                    height=max(ys) - min(ys),
                )
                self.changed.emit(self.mask)
                self.update()


class MaskEditor(QWidget):
    def __init__(self, mask, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.addWidget(
            QLabel(
                "Drag rectangles, ellipses or freehand shapes. Click polygon vertices.\n"
                "Position and size use canvas fractions. Invert blurs outside."
            )
        )
        self.canvas = MaskCanvas()
        layout.addWidget(self.canvas)
        form = QFormLayout()
        layout.addLayout(form)
        self.shape = QComboBox()
        self.shape.addItems(["none", "rectangle", "ellipse", "polygon", "freehand"])
        form.addRow("Shape", self.shape)
        self.controls = {}
        for name, low, high in [
            ("x", 0, 1),
            ("y", 0, 1),
            ("width", 0.001, 1),
            ("height", 0.001, 1),
            ("feather", 0, 40),
            ("blur", 0.1, 40),
            ("strength", 0, 1),
        ]:
            spin = QDoubleSpinBox()
            spin.setDecimals(3)
            spin.setRange(low, high)
            spin.setSingleStep(0.05 if high == 1 else 1)
            form.addRow(name.title(), spin)
            self.controls[name] = spin
            spin.valueChanged.connect(self.edit)
        self.inverted = QCheckBox("Invert mask")
        form.addRow(self.inverted)
        clear = QPushButton("Start new drawing")
        clear.clicked.connect(self.new_drawing)
        form.addRow(clear)
        self.shape.currentTextChanged.connect(self.change_shape)
        self.inverted.toggled.connect(self.edit)
        self.canvas.changed.connect(self.load)
        self.load(mask)

    def new_drawing(self):
        self.canvas.points = []

    def load(self, mask):
        self.canvas.mask = mask
        for key, widget in self.controls.items():
            widget.blockSignals(True)
            widget.setValue(getattr(mask, key))
            widget.blockSignals(False)
        self.shape.blockSignals(True)
        self.shape.setCurrentText(mask.shape)
        self.shape.blockSignals(False)
        self.inverted.blockSignals(True)
        self.inverted.setChecked(mask.inverted)
        self.inverted.blockSignals(False)
        self.canvas.update()

    def change_shape(self, shape):
        self.canvas.points = []
        self.load(replace(self.canvas.mask, shape=shape, points=()))

    def edit(self):
        old = self.canvas.mask
        values = {k: w.value() for k, w in self.controls.items()}
        values["x"] = min(values["x"], 1 - values["width"])
        values["y"] = min(values["y"], 1 - values["height"])
        points = tuple(
            (
                values["x"] + (x - old.x) * values["width"] / old.width,
                values["y"] + (y - old.y) * values["height"] / old.height,
            )
            for x, y in old.points
        )
        self.load(replace(old, **values, points=points, inverted=self.inverted.isChecked()))
