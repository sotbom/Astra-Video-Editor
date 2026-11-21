"""Selected-clip video effects, applied as one undoable command."""

from dataclasses import fields

from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from app.ui.mask_editor import MaskEditor
from app.video.filters import VideoEffects, validate_effects
from app.video.masks import Mask
from app.video.preview import EffectPreview


class EffectsDialog(QDialog):
    def __init__(self, engine, clip_id, parent=None):
        super().__init__(parent)

        self.engine, self.clip_id = engine, clip_id

        self.setWindowTitle("Clip video effects")

        self.setMinimumWidth(440)

        self.worker = None

        self.cache = {}

        self.resize(760, 780)

        outer = QVBoxLayout(self)

        tabs = QTabWidget()

        outer.addWidget(tabs)

        page = QWidget()

        scroll = QScrollArea()

        scroll.setWidgetResizable(True)

        scroll.setWidget(page)

        tabs.addTab(scroll, "Color and effects")

        layout = QFormLayout(page)

        note = QLabel(
            "Effects apply to exported video. The Timeline monitor shows the source.\n"
            "Thermal is a false-color style, not a temperature measurement."
        )

        note.setWordWrap(True)

        layout.addRow(note)

        effects = engine.project.clip_by_id(clip_id).effects

        self.controls = {}

        for field in fields(VideoEffects):
            key, value = field.name, getattr(effects, field.name)

            if key == "mask":
                continue  # Preserve persisted masks until the canvas editor is connected.

            if type(value) is bool:
                widget = QCheckBox()

                widget.setChecked(value)

            elif key.startswith("crop_") or key == "pixelation":
                widget = QSpinBox()

                widget.setRange(0, 64 if key == "pixelation" else 65535)

                widget.setValue(value)

            else:
                widget = QDoubleSpinBox()

                low, high = (-1, 1) if key == "brightness" else (0, 20 if key == "blur" else 3)

                if key == "vignette":
                    high = 1

                widget.setRange(low, high)

                widget.setSingleStep(0.1)

                widget.setValue(value)

            widget.setAccessibleName(key.replace("_", " ").title())

            self.controls[key] = widget

            layout.addRow(key.replace("_", " ").title(), widget)

        self.mask_editor = MaskEditor(effects.mask)

        mask_scroll = QScrollArea()

        mask_scroll.setWidgetResizable(True)

        mask_scroll.setWidget(self.mask_editor)

        tabs.addTab(mask_scroll, "Mask and preview")

        self.frame = QSpinBox()

        self.frame.setRange(0, engine.project.clip_by_id(clip_id).duration - 1)

        outer.addWidget(QLabel("Preview frame offset within clip"))

        outer.addWidget(self.frame)

        self.preview_button = QPushButton("Render effects preview")

        self.preview_button.clicked.connect(self.preview)

        outer.addWidget(self.preview_button)

        self.status = QLabel("Preview is a still frame. Render again after edits.")

        outer.addWidget(self.status)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
            | QDialogButtonBox.StandardButton.Reset
        )

        buttons.accepted.connect(self.apply)

        buttons.rejected.connect(self.reject)

        buttons.button(QDialogButtonBox.StandardButton.Reset).clicked.connect(self.reset)

        outer.addWidget(buttons)

    def reset(self):
        self.mask_editor.load(Mask())

        defaults = VideoEffects()

        for key, widget in self.controls.items():
            value = getattr(defaults, key)

            widget.setChecked(value) if type(value) is bool else widget.setValue(value)

    def draft(self):
        values = {
            key: widget.isChecked() if isinstance(widget, QCheckBox) else widget.value()
            for key, widget in self.controls.items()
        }

        values["mask"] = self.mask_editor.canvas.mask

        return VideoEffects(**values)

    def preview(self):
        if self.worker:
            return

        try:
            effects = self.draft()

            clip = self.engine.project.clip_by_id(self.clip_id)

            info = self.engine.project.media_by_id(clip.media_id).info

            validate_effects(effects, info.width, info.height)

            key = (effects, self.frame.value(), info.path.stat().st_mtime_ns)

            if key in self.cache:
                self.show_preview(self.cache[key])

                return

            self.worker = EffectPreview(
                self.engine.project, self.clip_id, effects, self.frame.value(), self
            )

            self.worker.ready.connect(lambda image: self.cache_preview(key, image))

            self.worker.failed.connect(self.status.setText)

            self.worker.finished.connect(self.preview_finished)

            self.preview_button.setEnabled(False)

            self.status.setText("Rendering preview…")

            self.worker.start()

        except (ValueError, OSError) as exc:
            self.status.setText(str(exc))

    def cache_preview(self, key, image):
        if len(self.cache) >= 4:
            self.cache.pop(next(iter(self.cache)))

        self.cache[key] = image

        self.show_preview(image)

    def show_preview(self, image):
        self.mask_editor.canvas.image = image

        self.mask_editor.canvas.setFixedSize(image.width(), image.height())

        self.mask_editor.canvas.update()

        self.status.setText("Rendered frame; render again after edits. Timeline remains untreated.")

    def preview_finished(self):
        self.worker.deleteLater()

        self.worker = None

        self.preview_button.setEnabled(True)

    def done(self, result):
        if self.worker is not None:
            self.status.setText("Wait for the bounded preview job before closing.")

            return

        super().done(result)

    def apply(self):
        try:
            self.engine.set_effects(self.clip_id, self.draft())

            self.accept()

        except (ValueError, StopIteration) as exc:
            QMessageBox.warning(self, "Invalid effects", str(exc))
