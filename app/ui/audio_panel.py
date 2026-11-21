"""Track processors, clip fades, waveform generation and rendered audio comparison."""

import tempfile
from dataclasses import fields, replace
from pathlib import Path
from uuid import uuid4

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from app.audio.analysis import AnalysisWorker
from app.audio.effects import RANGES, AudioMaster, AudioSettings
from app.audio.voice import VOICE_FIELDS, VOICE_PRESETS
from app.core.render_engine import RenderWorker
from app.export.ffmpeg_builder import ExportSettings
from app.media.waveform import WaveformWorker
from app.ui.preview import Preview


class AudioPanel(QDialog):
    def __init__(self, window):
        super().__init__(window)
        self.window, self.session = window, window.session
        self.worker = self.wave_worker = self.analysis_worker = None
        self.temp = tempfile.TemporaryDirectory(prefix="astra-audio-preview-")
        self.preview_path = None
        self.comparisons = {}
        self.comparison_project = self.session.project
        self.setWindowTitle("Audio Studio")
        self.resize(850, 740)
        layout = QVBoxLayout(self)
        layout.addWidget(
            QLabel(
                "Apply settings, then render a preview to hear processing. "
                "The Timeline monitor remains untreated."
            )
        )
        self.track = QComboBox()
        for track in self.session.project.tracks:
            self.track.addItem(track.name, track.id)
        self.track.setCurrentIndex(max(0, self.track.findData(window.timeline.track.currentData())))
        layout.addWidget(self.track)
        tabs = QTabWidget()
        layout.addWidget(tabs, 1)
        page = QWidget()
        form = QFormLayout(page)
        voice_page = QWidget()
        voice_form = QFormLayout(voice_page)
        self.controls = {}
        for field in fields(AudioSettings):
            key = field.name
            if key in ("denoise", "eq", "compressor", "voice", "preserve_formants"):
                widget = QCheckBox("Enabled")
            else:
                widget = QDoubleSpinBox()
                widget.setRange(*RANGES[key])
                widget.setDecimals(2)
                widget.setSingleStep(0.05 if key == "tempo" else 0.1 if key == "pan" else 1)
            widget.setAccessibleName(key.replace("_", " "))
            self.controls[key] = widget
            label = {
                "voice": "Voice transformation",
                "pitch_semitones": "Pitch (semitones)",
                "tempo": "Tempo (×)",
                "preserve_formants": "Preserve formants",
                "timbre_db": "Timbre: warm (−) / bright (+ dB)",
            }.get(key, key.replace("_", " ").title())
            (voice_form if key in VOICE_FIELDS else form).addRow(label, widget)
        form.addRow(
            QLabel(
                "Denoise: FFmpeg spectral reduction (conventional DSP, not AI).\n"
                "Pan is stereo balance: center preserves both channels; "
                "an edge mutes the opposite channel."
            )
        )
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(page)
        tabs.addTab(scroll, "Track processing")
        self.voice_preset = QComboBox()
        self.voice_preset.addItems(["Reset voice", *VOICE_PRESETS])
        self.load_voice = QPushButton("Load voice preset")
        self.load_voice.clicked.connect(self.load_voice_preset)
        voice_form.addRow(self.voice_preset, self.load_voice)
        note = QLabel(
            "Offline Rubber Band pitch/tempo processing. Formants can be preserved or shifted "
            "with pitch; independent formant scaling is not supported.\n\n"
            "Tempo keeps each clip's timeline length: faster audio leaves silence; slower audio "
            "is cut at the clip end. Video and subtitles are not retimed.\n\n"
            "Start with small changes and compare rendered results. Pitch changes alone do not "
            "guarantee anonymity. Preset names describe intent, not guaranteed naturalness."
        )
        note.setWordWrap(True)
        voice_form.addRow(note)
        voice_scroll = QScrollArea()
        voice_scroll.setWidgetResizable(True)
        voice_scroll.setWidget(voice_page)
        tabs.addTab(voice_scroll, "Voice transformation")
        page = QWidget()
        form = QFormLayout(page)
        self.fade_in, self.fade_out = QSpinBox(), QSpinBox()
        for spin in (self.fade_in, self.fade_out):
            spin.setRange(0, 604800000)
        self.clip_label = QLabel()
        form.addRow(self.clip_label)
        form.addRow("Fade in (ms)", self.fade_in)
        form.addRow("Fade out (ms)", self.fade_out)
        self.normalize = QCheckBox("Normalize mix (EBU R128, dynamic single pass)")
        self.target, self.peak = QDoubleSpinBox(), QDoubleSpinBox()
        self.target.setRange(-36, -5)
        self.peak.setRange(-12, -0.1)
        form.addRow(self.normalize)
        form.addRow("Target integrated loudness (LUFS)", self.target)
        form.addRow("Peak ceiling (dB)", self.peak)
        form.addRow(
            QLabel(
                "Master settings affect WAV and MP4 export. "
                "Limiting remains active when normalization is off."
            )
        )
        tabs.addTab(page, "Clip fades / master")
        row = QHBoxLayout()
        self.preset = QComboBox()
        self.preset.addItems(["Neutral", "Clean Voice", "Podcast"])
        preset_button = QPushButton("Load preset")
        preset_button.clicked.connect(self.load_preset)
        self.apply_button = QPushButton("Apply track / fades / master")
        self.apply_button.clicked.connect(self.apply)
        undo, redo = QPushButton("Undo"), QPushButton("Redo")
        undo.clicked.connect(self.session.undo)
        redo.clicked.connect(self.session.redo)
        for w in (self.preset, preset_button, self.apply_button, undo, redo):
            row.addWidget(w)
        layout.addLayout(row)
        self.preview = Preview()
        self.preview.stack.hide()
        self.preview.title.setText("Rendered mix preview")
        self.preview.failed.connect(lambda m: self.status.setText(m))
        layout.addWidget(self.preview)
        compare_row = QHBoxLayout()
        self.listen_before = QPushButton("Load original preview")
        self.listen_after = QPushButton("Load processed preview")
        self.listen_before.clicked.connect(lambda: self.load_comparison(True))
        self.listen_after.clicked.connect(lambda: self.load_comparison(False))
        compare_row.addWidget(self.listen_before)
        compare_row.addWidget(self.listen_after)
        layout.addLayout(compare_row)
        row = QHBoxLayout()
        self.wave = QPushButton("Build timeline waveforms")
        self.before = QPushButton("Render original mix")
        self.after = QPushButton("Render processed mix")
        self.export = QPushButton("Export WAV…")
        self.analyze = QPushButton("Analyze preview loudness")
        self.wave.clicked.connect(self.build_waveforms)
        self.before.clicked.connect(lambda: self.render(bypass=True))
        self.after.clicked.connect(self.render)
        self.export.clicked.connect(self.export_wav)
        self.analyze.clicked.connect(self.analyze_preview)
        for w in (self.wave, self.before, self.after, self.export, self.analyze):
            row.addWidget(w)
        layout.addLayout(row)
        self.progress = QProgressBar()
        self.progress.setValue(0)
        self.status = QLabel("Ready. Waveforms show source peaks; processing is non-destructive.")
        self.status.setWordWrap(True)
        self.cancel = QPushButton("Cancel processing")
        self.cancel.clicked.connect(self.cancel_job)
        self.cancel.setEnabled(False)
        layout.addWidget(self.progress)
        layout.addWidget(self.status)
        layout.addWidget(self.cancel)
        self.busy_controls = [
            tabs,
            self.track,
            self.preset,
            preset_button,
            self.apply_button,
            undo,
            redo,
            self.wave,
            self.before,
            self.after,
            self.export,
            self.analyze,
        ]
        self.track.currentIndexChanged.connect(self.refresh)
        self.session.changed.connect(self.refresh)
        self.refresh()

    def refresh(self):
        if self.comparison_project != self.session.project:
            self.comparisons.clear()
            self.preview.clear()
            self.preview_path = None
            self.comparison_project = self.session.project
        self.update_comparison_buttons()
        track = self.session.project.track_by_id(self.track.currentData())
        self.load_settings(track.audio)
        self.clip_id = self.window.timeline.selected_id
        clip = next(
            (
                c
                for c in self.session.project.clips
                if c.id == self.clip_id and c.track_id == track.id
            ),
            None,
        )
        self.clip_id = clip.id if clip else None
        self.fade_in.setEnabled(bool(clip))
        self.fade_out.setEnabled(bool(clip))
        self.fade_in.setValue(clip.fade_in_ms if clip else 0)
        self.fade_out.setValue(clip.fade_out_ms if clip else 0)
        self.clip_label.setText(
            "Fades apply to the selected timeline clip."
            if clip
            else "Select a clip on this track before opening Audio Studio to edit fades."
        )
        master = self.session.project.audio_master
        self.normalize.setChecked(master.normalize)
        self.target.setValue(master.target_lufs)
        self.peak.setValue(master.peak_db)

    def load_settings(self, settings):
        for key, widget in self.controls.items():
            value = getattr(settings, key)
            widget.setChecked(value) if isinstance(widget, QCheckBox) else widget.setValue(value)

    def load_preset(self):
        name = self.preset.currentText()
        settings = AudioSettings()
        if name in ("Clean Voice", "Podcast"):
            settings = AudioSettings(
                denoise=True,
                noise_reduction=10,
                eq=True,
                highpass=80,
                lowpass=16000,
                compressor=True,
                threshold_db=-20,
                ratio=2.5,
            )
        if name == "Podcast":
            settings = replace(settings, makeup_db=3, mid_db=2, mid_hz=2500)
        self.load_settings(settings)
        self.status.setText("Preset loaded. Apply to save these settings.")

    def load_voice_preset(self):
        """Change only voice controls, preserving existing enhancement settings."""
        preset = VOICE_PRESETS.get(self.voice_preset.currentText())
        settings = AudioSettings()
        if preset:
            pitch, tempo, preserve, timbre = preset
            settings = replace(
                settings,
                voice=True,
                pitch_semitones=pitch,
                tempo=tempo,
                preserve_formants=preserve,
                timbre_db=timbre,
            )
        for key in VOICE_FIELDS:
            widget, value = self.controls[key], getattr(settings, key)
            widget.setChecked(value) if isinstance(widget, QCheckBox) else widget.setValue(value)
        self.status.setText("Voice preset loaded. Apply, then render a processed preview.")

    def update_comparison_buttons(self):
        idle = not (self.worker or self.wave_worker or self.analysis_worker)
        self.listen_before.setEnabled(idle and True in self.comparisons)
        self.listen_after.setEnabled(idle and False in self.comparisons)

    def load_comparison(self, original):
        """Load a verified snapshot from the start without starting audio implicitly."""
        info = self.comparisons.get(original)
        if not info or self.worker or self.wave_worker or self.analysis_worker:
            return
        self.preview.load(info)
        self.preview_path = info.path
        label = "Original" if original else "Processed"
        self.preview.title.setText(f"{label} mix — applied settings")
        self.status.setText(f"{label} preview loaded from start. Press Play to compare.")

    def apply(self):
        values = {
            key: widget.isChecked() if isinstance(widget, QCheckBox) else widget.value()
            for key, widget in self.controls.items()
        }
        try:
            self.window.engine.set_audio(
                self.track.currentData(),
                AudioSettings(**values),
                self.clip_id,
                self.fade_in.value(),
                self.fade_out.value(),
                AudioMaster(self.normalize.isChecked(), self.target.value(), self.peak.value()),
            )
            self.status.setText(
                "Audio settings applied. Render a processed preview to hear the result."
            )
        except ValueError as exc:
            self.status.setText(str(exc))

    def busy(self, value):
        for widget in self.busy_controls:
            widget.setEnabled(not value)
        self.cancel.setEnabled(value)
        self.update_comparison_buttons()

    def render(self, checked=False, *, bypass=False, output=None, overwrite=False):
        if self.worker or self.wave_worker or self.analysis_worker:
            return
        self.preview.clear()
        project = self.session.project
        self.preview_path = None
        self.render_bypass = bypass
        self.render_succeeded = False
        if bypass:
            project = replace(
                project,
                tracks=tuple(replace(t, audio=AudioSettings()) for t in project.tracks),
                clips=tuple(replace(c, fade_in_ms=0, fade_out_ms=0) for c in project.clips),
                audio_master=AudioMaster(),
            )
        self.is_preview = output is None
        output = output or Path(self.temp.name) / f"{uuid4().hex}.wav"
        protected = (self.window.projects.path,) if self.window.projects.path else ()
        self.worker = RenderWorker(
            project,
            ExportSettings(audio_only=True),
            output,
            overwrite=overwrite,
            protected=protected,
            parent=self,
        )
        self.worker.progress.connect(self.progress.setValue)
        self.worker.succeeded.connect(self.rendered)
        self.worker.failed.connect(lambda m: self.status.setText(m))
        self.worker.cancelled.connect(
            lambda: self.status.setText("Audio processing cancelled; existing output preserved.")
        )
        self.worker.finished.connect(self.render_finished)
        self.busy(True)
        self.progress.setValue(0)
        self.status.setText("Rendering original mix…" if bypass else "Rendering processed mix…")
        self.worker.start()

    def rendered(self, path):
        self.render_succeeded = True
        if self.is_preview:
            self.comparisons[self.render_bypass] = self.worker.media_info
        else:
            self.status.setText(f"Audio exported: {path}")

    def render_finished(self):
        worker, self.worker = self.worker, None
        worker.deleteLater()
        self.busy(False)

        if self.is_preview and self.render_succeeded:
            self.load_comparison(self.render_bypass)

    def export_wav(self):
        name, _ = QFileDialog.getSaveFileName(
            self, "Export mixed audio", "Audio.wav", "WAV audio (*.wav)"
        )
        if not name:
            return
        path = Path(name)
        if not path.suffix:
            path = path.with_suffix(".wav")
        overwrite = path.exists()
        if (
            overwrite
            and QMessageBox.question(
                self,
                "Replace audio output?",
                "Replace this file only after successful rendering?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            != QMessageBox.StandardButton.Yes
        ):
            return
        self.render(output=path, overwrite=overwrite)

    def build_waveforms(self):
        media = [m.info for m in self.session.project.media if m.info.audio_codec]
        if not media:
            self.status.setText("Import a source containing audio first.")
            return
        self.wave_worker = WaveformWorker(
            media, self.window.projects.recovery_dir.parent / "waveforms", self
        )
        self.wave_worker.ready.connect(self.wave_ready)
        self.wave_worker.failed.connect(lambda m: self.status.setText(m))
        self.wave_worker.progress.connect(self.progress.setValue)
        self.wave_worker.finished.connect(self.wave_finished)
        self.busy(True)
        self.status.setText("Building cached source waveforms…")
        self.wave_worker.start()

    def wave_ready(self, path, waveform):
        self.window.timeline.view.waveforms[path] = waveform
        self.window.timeline.view.redraw()

    def wave_finished(self):
        worker, self.wave_worker = self.wave_worker, None
        worker.deleteLater()
        self.busy(False)
        self.status.setText("Waveform job finished. Available peaks are visible on timeline clips.")

    def analyze_preview(self):
        if not self.preview_path:
            self.status.setText("Render a preview before measuring it.")
            return
        self.analysis_worker = AnalysisWorker(self.preview_path, self)
        self.analysis_worker.ready.connect(
            lambda r: self.status.setText(
                f"Integrated: {r['input_i']} LUFS • True peak: {r['input_tp']} dBTP "
                f"• Range: {r['input_lra']} LU"
            )
        )
        self.analysis_worker.failed.connect(lambda m: self.status.setText(m))
        self.analysis_worker.finished.connect(self.analysis_finished)
        self.busy(True)
        self.status.setText("Measuring EBU R128 loudness (up to 120 seconds)…")
        self.analysis_worker.start()

    def analysis_finished(self):
        worker, self.analysis_worker = self.analysis_worker, None
        worker.deleteLater()
        self.busy(False)

    def cancel_job(self):
        if self.analysis_worker:
            self.analysis_worker.cancelled.set()
        if self.worker:
            self.worker.cancel_event.set()
        if self.wave_worker:
            self.wave_worker.cancelled.set()

    def reject(self):
        if self.worker or self.wave_worker or self.analysis_worker:
            self.cancel_job()
            return
        self.preview.clear()
        self.temp.cleanup()
        super().reject()

    def closeEvent(self, event):
        if self.worker or self.wave_worker or self.analysis_worker:
            self.cancel_job()
            event.ignore()
        else:
            self.preview.clear()
            self.temp.cleanup()
            event.accept()
