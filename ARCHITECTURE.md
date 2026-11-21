# Architecture

The master specification is SKILL.md. Phases 1–6 implement source preview, timeline editing,
project persistence, video effects, rendering, offline transcription, subtitles and audio processing.

- `app/application.py`: application lifetime, theme and rotating user-data logs.
- `app/ui/main_window.py`: menus, toolbar, local file picker, drops, library and inspector.
- `app/ui/preview.py`: Qt Multimedia video/audio and image display; integer millisecond transport.
- `app/media/importer.py`: sequential background worker with queued GUI updates, cancellation
  between files and a bounded in-flight probe timeout. Closing waits asynchronously for completion.
- `app/core/media_probe.py`: immutable media records and validated FFprobe JSON; rational FPS.
- `app/utils/paths.py`: explicit environment override, project-local tools, then system PATH.

Data flow: picker/drop -> deduplicated queue -> worker -> FFprobe -> immutable MediaInfo ->
library -> preview. Original files are never modified. Player errors and import failures appear
in a bounded error panel. No network requests occur in the application.

## Timeline and project state

- `core/project_schema.py`: immutable Project/Media/Track/Clip records and strict validation.
  Timeline positions and source in/out are integer project frames, with an exclusive out point.
  Fraction-based conversions support rational FPS without accumulating floating-point drift.
- `core/command_manager.py`: reversible before/after project commands using structural sharing,
  bounded to 100 commands. No media bytes are copied. A saved snapshot determines dirty state.
- `core/timeline_engine.py`: validated add, move, trim, split, delete, track and relink operations.
- `ui/timeline.py`: QGraphicsView canvas, clip dragging, edge trimming, snapping, zoom,
  track controls and exact-frame inspector. `ui/media_library.py` supplies media drag data.
- `core/playback_engine.py` and `ui/timeline_preview.py`: a rational elapsed-time playhead,
  Qt decoder per active track, first-visible-video selection, independent audio outputs,
  still/gap display and transport. Editing pauses preview. Qt decode/seek is approximate;
  this is not a frame-exact or sample-synchronized render engine.
- `core/project_manager.py`: schema-5 JSON, relative media paths when possible, absolute paths
  across drives, bounded loading and strict validation. Writes use a same-directory temporary
  file, flush/fsync and atomic replacement; the previous valid project is backed up.
- `ui/project_actions.py`: background project I/O, unsaved-change prompts, 30-second autosave,
  explicit recovery and missing-media handling. Saves capture immutable state so concurrent
  edits stay dirty. Opens disable editing until the new state is installed.

Project files contain metadata and references, never media bytes. Missing sources remain
editable and can be relinked after probing; incompatible replacements are rejected. Schema 1
was the first persisted format; schemas 1–4 migrate to schema 5 with missing effects/subtitles/audio
initialized to defaults. Unknown
versions are rejected rather than guessed. Validation
currently bounds projects to 32 tracks, 10,000 clips/media entries and 8 MiB JSON. Same-track
overlaps are rejected. Undo history is session-local and is not serialized.

## Rendering and effects

- `video/filters.py`: immutable VideoEffects settings, finite numeric/range/crop validation
  and trusted filter construction. Order: crop, color adjustment, negative, grayscale/thermal,
  then blur. No user-supplied filter expressions or shell commands are accepted.
- `export/ffmpeg_builder.py`: explicit FFmpeg argv and a temporary graph file. Video sources
  normalize to project FPS, trim by frame, apply effects, scale/pad, and shift to timeline PTS.
  A black canvas supplies gaps; lower tracks overlay first so the first visible track wins.
  Audio resamples to 48 kHz stereo, trims/delays in samples and mixes over silence with a
  configurable peak limiter or loudness normalization. Output is CPU libx264/AAC MP4,
  fixed to the project duration/frame count, or audio-only 48 kHz stereo PCM24 WAV.
- `core/render_engine.py`: worker-owned subprocess with an immutable snapshot, file-based
  progress, cancellation and a 12-hour timeout. No blocking subprocess wait runs on the UI
  thread. A sibling temporary directory holds graph/log/progress/output, and is removed after
  success/failure/cancellation. FFprobe checks output dimensions and duration before publication.
  Existing output is replaced only when explicitly authorized; source/project paths are guarded.
- `ui/effects_dialog.py`: one undoable settings command for the selected video clip.
- `ui/export_dialog.py`: output/quality/size controls, progress, safe cancellation and an
  explicit button to open completed media in the system player. The modal dialog keeps the
  captured snapshot clear to users. Settings are not yet persisted as export preferences.

The Qt Timeline monitor remains a source preview; effects are evaluated by FFmpeg during
export. Graph generation follows the official [filter reference](https://ffmpeg.org/ffmpeg-filters.html)
and [CLI reference](https://ffmpeg.org/ffmpeg.html). The verified binary is FFmpeg 9.0.2;
`-/filter_complex` loads graph text from a file. Older FFmpeg versions are not qualified.
The renderer opens an input per active clip; long/high-clip-count timelines need optimization
and qualification. Windows command-length overflow is rejected with a visible error.

## AI and subtitles

- `core/subtitles.py`: immutable integer-millisecond segments, global ASS style, strict
  validation, reversible edit operations and plain UTF-8 SRT/VTT/ASS serialization.
  Subtitles use absolute timeline times; clip movement does not implicitly retime them.
- `ui/subtitle_panel.py`: separate editor/table, model catalog, language/device/compute
  selection, selected-clip transcription, replacement confirmation, file interchange and style.
- `ai/model_manager.py`: explicit catalog paths and completion-marker checks. Downloads alone
  use the network; each completed model records its repository/revision.
- `ai/backend.py`: runs only in `.venv-ai`; loads local models with offline mode enabled,
  checks CTranslate2 compute types and runs faster-whisper with word timestamps. No AI
  libraries are imported into the editor's Python process.
- `ai/transcription.py`: worker owns FFmpeg audio extraction and a separate Python process;
  cancellation terminates the Windows launcher/child process tree. Atomic status/result JSON
  crosses the boundary, with Windows sharing retries. A failed CUDA subprocess retries once
  on CPU/int8, reporting the actual device and reason. Temporary media/results are removed.

Recognized segments map to the selected clip's timeline start and are clamped to its end.
The whole result is one command; errors/cancellation leave existing subtitles intact. Schema 3
persists segments, style and last transcription provenance. Backend word timestamps are tested
but not yet stored in the editing model. The monitor displays plain text under the image;
optional export burn-in generates a private escaped ASS file for FFmpeg/libass. No automatic
transcription occurs on project reopen.

Optional dependencies are separately locked. CPU/int8 is verified; actual CUDA inference
failed for missing cuBLAS and successfully fell back. The driver detector alone never marks
GPU inference ready. No driver or CUDA runtime was installed. See docs/TRANSCRIPTION.md.

## Audio Studio

- `audio/effects.py`: immutable per-track AudioSettings and project AudioMaster; finite/range
  validation and trusted FFmpeg filters for spectral denoise, EQ, compression, gain, balance,
  clip fades and master limiting/normalization. Processing runs per clip before timeline delay
  and mixing; master processing runs after the mix. No user filter strings are executed.
- `media/waveform.py`: cancellable worker decodes mono 8 kHz PCM into bounded peak bins.
  Atomic JSON caches use source path/size/mtime/duration keys; timeline drawings respect trims.
- `audio/analysis.py`: cancellable FFmpeg loudness measurement in a worker.
- `ui/audio_panel.py`: undoable track/fade/master edits, presets, waveform jobs, original and
  processed rendered previews, loudness analysis and WAV export. It reuses RenderWorker's
  snapshot, cancellation, source protection, verification and atomic publication.
- Schema 4 stores track audio, clip fade milliseconds and project master settings.

Waveforms represent source amplitudes, not processed output. Track processing resets at clip
boundaries; this is not a continuous mixer bus. Pan is stereo balance. Normalization is dynamic
single-pass loudnorm. The Qt Timeline monitor does not apply these settings; render a mix to
preview them. No new Python dependency or AI denoising model is installed. See docs/AUDIO_STUDIO.md.

## Voice transformation

`audio/voice.py` defines presets, capability checks and trusted Rubber Band filters.
AudioSettings adds voice bypass, semitone pitch, tempo, formant preservation and timbre
shelves. Schema 5 persists these; older schemas default to voice bypass. The render worker
checks the selected FFmpeg binary only when needed, caching by executable metadata.

Voice processing follows denoise and precedes EQ/compression/fades. It consumes trimmed
source audio, applies independent pitch/tempo, then pads/trims to the existing slot before
delaying and mixing. Timeline geometry, video and subtitle times do not change. Timbre uses
shelves; independent formant scaling is unsupported. WAV and MP4 share the processing path.

AudioPanel retains verified original/processed preview metadata for the applied project.
Loading either switches the paused player to the start without re-rendering; project changes
invalidate both. Failures/cancellation do not load an old preview as a new successful render.
See docs/VOICE_TRANSFORMATION.md for backend evaluation and perceptual limitations.
