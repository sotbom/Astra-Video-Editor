# Changelog

## 0.6.0-dev — unreleased

- Added reversible offline voice pitch/tempo, formant preservation mode and timbre shelves
  with lower/higher/altered presets in Audio Studio; WAV and MP4 share processing.
- Added cached original/processed preview switching with invalidation after edits/undo/redo.
- Added schema 5 persistence, older-project migration and worker-based Rubber Band detection.
- Verified 85 tests, including decoded frequency, slot timing, bypass, desktop comparison and
  MP4 voice output. No neural voice model installed; natural speech quality is not established.

## 0.5.0-dev — unreleased

- Added Audio Studio with cached timeline waveforms, gain/balance, clip fades, spectral noise
  reduction, EQ, compression, master normalization/limiting and reversible presets/settings.
- Added rendered original/processed previews, loudness measurement and 48 kHz stereo PCM24 WAV
  export; MP4 audio shares the processing graph and protected background rendering.
- Added schema 4 audio persistence and migration from schemas 1–3 without new dependencies.
- Verified 75 tests, including real PCM and desktop audio workflows. Processing is rendered,
  not live in the Timeline monitor; denoising is conventional FFmpeg filtering, not AI.

## 0.4.0-dev — unreleased

- Added isolated faster-whisper/CTranslate2 transcription with explicit model downloads,
  local-only inference, language/compute selection, progress, cancellation and CPU fallback.
- Added segment editing, split/merge, search/replace, undo/redo, synchronized text preview,
  SRT/VTT import, SRT/VTT/ASS export and optional subtitle burn-in.
- Added schema 3 subtitle/style/provenance persistence and migration from schemas 1–2.
- Fixed PyAV compatibility, Windows status-file sharing and cancellation of venv process trees.
- Verified real English CPU inference and native subtitle generation; CUDA falls back because
  cuBLAS is absent. Word timestamps are backend-only; the editor persists segment timestamps.

## 0.3.0-dev — unreleased

- Added real timeline MP4 export using CPU H.264/AAC, project-frame trims, gaps,
  visible-track priority and mixed unmuted audio.
- Added crop, output resizing, brightness, contrast, saturation, negative, grayscale,
  thermal false color and Gaussian blur. Clip settings support undo/redo and saving.
- Added schema 2 with automatic schema 1 migration to neutral effects.
- Added background progress, cancellation, output verification and protected atomic publication.
- Verified 53 tests and a native 1080p export opened in Windows Media Player.
- Effects are export-only; live effect preview, NVENC and additional export profiles remain future work.

## 0.2.0-dev — unreleased

- Added video/audio tracks, non-destructive clip move/trim/split/delete, snapping,
  zoom, playhead control, mute/hide/lock and undo/redo.
- Added a separate timeline monitor with video, audio, still images and gap playback.
- Added versioned `.astra` projects, atomic save/backup, asynchronous open/save,
  autosave recovery, missing-media detection and relinking.
- Fixed Qt timeline stop ordering and stale decoder-load events exposed by playback tests.
- Verified editing, persistence, abrupt-process-exit recovery and native save/reopen.
- Qt monitor seeking remains approximate. Export and effects are the next phase.

## 0.1.0-dev — unreleased

- Initial modular Python/Qt source-media workspace.
- Background FFprobe import and non-destructive local preview.
- Generated-media tests and environment/development documentation.
- No binary distribution or release yet.
