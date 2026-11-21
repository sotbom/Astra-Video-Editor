# Astra Video Editor Development Progress

## Current Version
0.7.0-dev

## Current Phase
Phase 6 â€” offline voice transformation implemented and functionally verified with Rubber Band.
Pitch/tempo, formant mode, timbre and cached comparison are rendered; Timeline preview is untreated.
CUDA fallback is verified; GPU inference is unavailable on this installation (missing cuBLAS).
Phase 7 â€” advanced video effects is in progress. This is a development milestone, not a release.

## Completed
- [x] Read complete master specification and followed Section 26.
- [x] Inspected empty workspace and source specification directory.
- [x] Detected GPU, driver, Python, disk space, Git and missing FFmpeg.
- [x] Installed local environment and checksum-verified FFmpeg/FFprobe.
- [x] Generated original H.264/AAC video, PCM WAV and PNG fixtures.
- [x] Initialized Git; established modular UI/core/media/utils architecture and dependency lock.
- [x] Dark resizable desktop window, menus, toolbar, media library and inspector.
- [x] Native file-picker import, local drag/drop, deduplication and background FFprobe inspection.
- [x] Play/pause, stop, seek, speed, volume and integer millisecond time display.
- [x] Video, audio and image previews; corrupt/missing media and missing-tool error handling.
- [x] Import cancellation and safe close while importing.
- [x] Actual CUDA driver initialization: one device, compute capability 7.5.
- [x] CPU inference default retained; missing/failed CUDA driver fallback tested.
- [x] Native Windows import/play/stop/shutdown verified through computer use.
- [x] Setup script rerun against the installed lock and both external binaries verified.
- [x] Integer-frame project model with rational FPS and validated reversible edits.
- [x] Video/audio tracks; add, move, edge/inspector trim, split and delete clips.
- [x] Canvas media drop, snapping, zoom/scroll, playhead and track mute/hide/lock.
- [x] Separate timeline monitor; actual video/audio playback, gaps, images and track handoff.
- [x] Versioned JSON projects, atomic save, previous-save backup and asynchronous reopen.
- [x] Autosave, recovery after abrupt process exit, missing-media detection and relinking.
- [x] Undo/redo, dirty tracking and cancellation of unsaved close/open.
- [x] Native timeline add/split/move, undo/redo, save/reopen and playback verification.
- [x] Updated user workflow, architecture, feature status and verification documentation.
- [x] FFmpeg graph builder for project-frame trimming, gaps, track priority and audio mixing.
- [x] CPU H.264/AAC MP4 export with configurable dimensions/CRF and aspect-preserving padding.
- [x] Reversible clip crop, brightness, contrast, saturation, negative, grayscale, thermal and blur.
- [x] Schema 2 effects persistence and schema 1 migration; existing project regressions preserved.
- [x] Background export progress, running-process cancellation and safe temporary cleanup.
- [x] Source/project overwrite guards, explicit destination replacement and post-render verification.
- [x] Native 1080p export and opening rendered output in Windows Media Player.
- [x] Separate locked AI environment and compatible faster-whisper/CTranslate2/PyAV integration.
- [x] Explicit model download/catalog, revision recording and local-only inference.
- [x] Actual CPU speech recognition with segment/word timestamps on original generated speech.
- [x] Language/compute selection, actual CUDA failureâ†’CPU retry, progress and process cancellation.
- [x] Subtitle add/edit/delete/split/merge/replace, undo/redo and synchronized plain-text preview.
- [x] SRT/VTT import, SRT/VTT/ASS export, global style and verified burned subtitle pixels.
- [x] Schema 3 persistence/migration, transcription provenance and native saved subtitle workflow.
- [x] Cached source waveforms aligned with trimmed timeline clips and cancellable generation.
- [x] Multitrack audio gain/balance, clip fades, spectral denoise, EQ and compression.
- [x] Master loudness normalization/limiting, presets and reversible audio edits.
- [x] Rendered original/processed mix preview, loudness analysis and PCM24 stereo WAV export.
- [x] Shared MP4 audio processing, protected atomic output and active-render cancellation.
- [x] Schema 4 audio persistence/migration and real PCM/desktop verification.
- [x] Reversible offline pitch/tempo, preserved/shifted formants and timbre shelves.
- [x] Voice presets, bypass, cached original/processed comparison and invalidation after edits.
- [x] Schema 5 persistence/migration and worker-based configured-backend capability checks.
- [x] Optional AI conversion evaluated; no model/runtime installed (see docs/VOICE_TRANSFORMATION.md).
- [x] Real voice DSP in WAV and MP4, desktop controls/playback and scrollable native layout.

## In Progress
No core Phase 6 DSP milestone tasks remain. Perceptual quality and broader qualification remain below.

## Pending
- [ ] Phases 7â€“9: advanced video effects, packaging and stabilization.
- [ ] Successful CUDA inference after a compatible runtime is available; multilingual/large-model tests.
- [ ] Live effect preview, additional export formats/profiles, hardware encoding and larger projects.

## Tests
- Passed on 2026-11-17: 85 pytest tests in 44.00 seconds, process exit 0, no skips.
  Report: `artifacts/phase6-tests.xml`; per-test log: `artifacts/phase6-full.log`.
- After native inspection found clipped voice help text, added scrolling; all three Audio Studio
  desktop tests passed in 3.94 seconds (`artifacts/phase6-layout-tests.log`).
- Passed: Ruff lint/format (61 Python files) and pip check in both environments.
- Phase 6: nine DSP/persistence cases and one desktop case verify pitch frequency, independent
  tempo, fixed slots/delay/padding, formant modes, timbre energy, bypass, schema migration,
  invalid values, backend failure preservation, MP4 audio and cached comparison playback.
- Native Phase 6: reopened the Phase 5 speech project, loaded/applied Natural lower (âˆ’3 semitones,
  preserved formants, âˆ’1.5 dB timbre), rendered both 12.100-second previews, observed processed
  playback past 7 seconds and switched to the cached original. Scrolling revealed all guidance.
  Saved `artifacts/phase6-native.astra` through the native picker; reloaded settings independently
  and rendered `artifacts/phase6-lower-voice.wav` (PCM24, 48 kHz stereo, 12.100 seconds).
- First full run: 83 passed, one test failed on Windows path separator comparison; corrected
  path normalization and added an MP4 voice case, then all 85 passed. Initial tone assertions
  were adjusted to separate pitch from formant-preservation amplitude and test shelves at 6 kHz.
- Phase 5: seven real audio tests and two desktop tests verify PCM gain/pan/fades, overlapping
  mixes/mute, EQ/compression, synthetic-noise attenuation, normalization, WAV properties,
  cache reuse, persistence/undo, playback clock, loudness measurement and cancellation.
- Native Phase 5: waveform visible, Clean Voice loaded/applied, processed preview completed
  at 100% with 12.100-second duration; playback observed past 5 seconds.
- Native loudness analysis reported âˆ’22.95 LUFS / âˆ’7.37 dBTP / 2.10 LU for the Clean Voice
  speech sample. Saved `artifacts/phase5-native.astra` through the Windows picker. Native WAV
  export completed; independent FFprobe verified `artifacts/phase5-native.wav` as PCM24,
  48 kHz stereo, 12.100 seconds. This sample does not enable master normalization.
- Verified: changing decoded H.264 frames, AAC video playback, PCM audio playback clock,
  pause stability, seeking, stop/reset, speed and volume state, PNG display, import recovery,
  deduplication, drop import, remote-drop rejection, cancellation and safe shutdown.
- Native GUI: imported `Astra test Ã¼ space.mp4` through the real Windows picker;
  displayed 640Ã—360 / 30 fps / AAC metadata; observed video frames and stop/reset.
- Phase 2 native GUI: added/split/moved clips, used undo/redo, saved via the actual Windows
  picker and reopened `artifacts/phase2-native.astra`. Verified serialized source ranges,
  gap and clean state; playback reached the saved timeline's end at frame 210.
- Automated Phase 2: 12 project tests, 10 desktop timeline tests and one abrupt-process-exit
  recovery test, alongside the 13 Phase 1 regressions. Includes real decoded frame changes,
  video-track handoff, image display, audio progress, move/trim/drop, save failure preservation,
  backup/roundtrip, missing-media relink, rational FPS and source-overwrite protection.
- Automated Phase 3: 13 render tests and four desktop tests. Actual decoded pixels verify
  trims, gaps, all eight effect settings, still images and video priority; decoded PCM verifies
  active/muted/gap audio. Resolution, fractional FPS, duration and video frame count checked.
  UI tests verify effect apply/undo, responsive export, progress, cancellation during encoding,
  existing-file preservation, failure messages and real playback of the exported video.
- Native Phase 3: exported `artifacts/phase3-native.mp4` through the new toolbar dialog,
  observed 100% completion and opened it in Media Player. Independent FFprobe confirmed
  H.264/AAC, 1920Ã—1080, 30 fps, 210 frames and 7.000 seconds from the saved Phase 2 edit.
- Phase 4: six subtitle tests, four real inference tests and three desktop tests. Verified
  timestamps/text, edit/undo/reopen, subtitle formats, timed preview/burned pixels, selected
  clip offsets, missing models, cancellation and real CPU fallback. No tests used private media.
- Native Phase 4: selected generated speech clip, transcribed on CPU, observed two timed rows
  and 100% completion, saved `artifacts/phase4-native.astra`; generated three subtitle formats
  and `artifacts/phase4-captioned.mp4` from that persisted result.
- Final visual check: native playhead at frame 30 displayed the correct active subtitle;
  inspected the burned caption frame. FFprobe verified the captioned sample as 640Ã—360
  H.264/AAC, 363 video frames and 12.100 seconds.
- Fixed: PyAV API incompatibility, Windows status-file sharing race and venv child-process
  cancellation. First full run: 65 pass/one cancellation failure; corrected run: all 66 pass.
- Fixed: initial missing pytest output directory and Qt 6.10.1 stop hang. PySide6 6.11.3
  and explicit slots are pinned; the same transport regression test now passes.
- Fixed in Phase 2: stop inactive Qt decoders before detaching the sink, and ignore stale
  queued media-load events. Regression tests cover stopping after a gap and source seeks.
- Diagnostic: some GUI runs print Windows COM `0x8001010d` through faulthandler but continue.
  The restricted runner also terminated in native initialization. One interactive full run
  stalled without output and was stopped; a diagnostic rerun passed all 36 tests. The stall's
  cause remains unisolated; do not claim repeated-run stability or suppress diagnostics.
- Not run: broad codec matrix, audible speaker confirmation, Windows 10/clean-PC testing,
  successful CUDA inference, multilingual/large models, NVENC, long projects and packaging.

## Known Issues
- Non-terminating Windows COM diagnostic during GUI tests remains documented for follow-up.
- No thumbnails, draggable subtitle timeline blocks, advanced video effects or fullscreen.
- Audio processing is rendered, not applied in the main Timeline monitor. Waveforms show source
  peaks. Pan is balance; processors reset per clip; split clips inherit fades on both halves.
- Normalization is dynamic single-pass. Denoising is conventional FFmpeg filtering; no AI
  enhancement model or perceptual speech-quality claim. See docs/AUDIO_STUDIO.md.
- Voice tempo pads/trims within existing clip slots; it does not retime video/subtitles or ripple
  the timeline. Formants can be preserved or shifted with pitch, not scaled independently.
- Voice processing uses offline DSP, not neural identity conversion. Naturalness, audible speaker
  output and anonymity are not established; comparison restarts each cached preview from zero.
- CUDA float16 failed to load cublas64_12.dll; no runtime/driver changes made. CPU/int8 works.
- Only tiny.en English recognition is qualified; catalog models beyond tiny.en are not tested.
- Subtitle preview is plain text below the image. Styling is applied in ASS/burned output.
  Segment times persist; backend word timestamps are not yet exposed/persisted in the editor.
- Subtitle times are absolute; moving video does not move subtitles. Basic SRT/VTT import only,
  no ASS import/WebVTT positioning. Advanced styling, word-level editing and long speech await testing.
- Video effects apply to exports; the Qt Timeline monitor still displays untreated source frames.
- Video export is CPU H.264/AAC MP4; audio export is 48 kHz stereo PCM24 WAV.
  Video uses even dimensions 16â€“3840 and project FPS.
  Quality/dimensions are dialog-local. Hardware codecs and saved export profiles are not implemented.
- Export currently opens a decoder input per active clip and rejects Windows command-length
  overflow. Long/high-clip-count, VFR, rotated and HDR sources need further qualification.
- Audio playback clock can be tested; audible speaker output is not independently verified.
- Edit positions and frame-step targets are exact project frames; Qt decoded preview seeking
  is approximate. Seamless/sample-accurate audio cuts and long-duration sync are not verified.
- First visible video track wins; active audio streams use independent Qt outputs. Same-track
  overlaps are rejected. Projects currently have bounded validation limits (see ARCHITECTURE.md).
- Cancellation finishes the current FFprobe operation (20-second maximum), then stops.
- No Git remote, commits or binary releases created. Application license remains unselected.

## Architecture Decisions
- Python/PySide6 with Qt Multimedia and external FFprobe.
- Verified foundation: Python 3.14.3 / PySide6 6.11.3 / FFmpeg 9.0.2 on Windows build 26200.
- Worker-based importing; rational FPS; source media never modified.
- Immutable project state and bounded command history; schema-5 metadata-only JSON, atomic
  replacement and last-valid-save backup. Project I/O runs in a worker; autosave every 30 seconds.
- Schema 1 migrates with neutral effects. Typed effects generate trusted FFmpeg filters.
  Export uses an immutable snapshot, worker-owned subprocess and same-volume temporary output;
  only verified successful results replace a destination. No new Python packages were needed.
- `.venv-ai` isolates optional native dependencies; requirements-ai-lock.txt pins PyAV 16.0.1,
  faster-whisper 1.2.1 and CTranslate2 4.9.0. Inference is a cancellable subprocess; CPU default.
- tiny.en downloaded explicitly at revision 0d3d19a32d3338f10357c0889762bd8d64bbdeba.
  Models stay local/ignored by Git. Inference uses offline flags and never uploads source audio.
- Phase 6 uses Rubber Band already present in the GPL-enabled FFmpeg build; no dependencies
  changed. Optional neural conversion was assessed from upstream runtime/license documentation
  and deferred without downloading weights. Independent numeric formant scaling is not exposed
  by this backend. Schema 5 defaults older projects to voice bypass.

## Next Action
Phase 7 milestone complete. Phase 8 packaging is next. Investigate native-run intermittency during packaging qualification.

## Phase 7 increment â€” 2026-11-21
- In progress, not complete. Added schema-6 static mask persistence and FFmpeg masked blur.
- Verified five additional export effects (sepia, mirror, pixelation, sharpen, vignette)
  with decoded-frame differences and project round trips. Rectangle blur and inversion
  passed region-specific pixel comparisons. Existing effects dialog preserves saved masks.
- Targeted render and desktop integration suite: 24 passed in 13.63 seconds;
  artifacts/phase7-increment-tests.xml. Desktop tests launch MainWindow, edit effects,
  export and decode playback frames. Ruff passed.
- Full restricted-run suite crashed with Windows 0xc0000008/access violation in
  ProjectIOWorker atomic_write; unrestricted rerun requested. Do not treat this as fixed.
- Remaining: interactive mask canvas, freehand/polygon editing, position/resize controls,
  feather/strength qualification, cached background effects preview and manual visual QA.
  Phase 8 has not started.

- Unrestricted full regression rerun: 92 passed in 44.25 seconds; artifacts/phase7-regression-tests.xml. The restricted-run native exception remains an environment limitation requiring investigation.

## Phase 7 editor verification — 2026-11-21
- Added rectangle, ellipse, polygon and freehand editing, normalized position/resize,
  inversion, feather, blur and strength controls. OK commits one undoable clip edit.
- Background still previews reuse the export graph, bounded to 30 seconds, with four cached
  proxy frames per dialog. Timeline playback remains untreated; no tracking/keyframes.
- Native Qt desktop tests: five passed, including drawing gestures, resizing, all four
  shape previews and application to the project. Captured and visually inspected
  artifacts/phase7-editor.png. Controls below the preview are scrollable.
- Pixel qualification: 21 render tests passed in 13.75 seconds, including strength blending
  and feather differences. Ruff and pip check passed. No dependency changes.
- One full-suite run stalled and was interrupted; diagnostic rerun is recorded in
  artifacts/phase7-complete.log. Native-run intermittency remains unresolved.
- Workflow and limitations: docs/MASKS.md. Phase 8 packaging has not started.

## Phase 7 final result
Completed static-mask editing and cached still-preview scope. Final diagnostic regression run: **94 passed in 49.75 seconds**, exit 0; artifacts/phase7-complete-tests.xml. Earlier in-progress entries are historical. Timeline playback remains untreated.

## Phase 8 initial packaging — 2026-11-21
- IN PROGRESS; no working portable release yet. PyInstaller 6.22.3 built the one-directory
  executable and runtime. Added pinned build requirements, build script, manifest/checksum
  generation, an uncompiled Inno Setup definition and manual CI syntax-check scaffold.
- Frozen executable fails before UI startup: QtCore DLL import reports a missing procedure.
  Tested replacing root Visual C++ runtimes with Qt-provided versions; failure persists.
  Candidate directory contains diagnostic DLL changes; ZIP is the original failing build.
  Do not distribute either as a working application. Build log: artifacts/phase8-build.log.
- Source regression: 94 passed in 48.41 seconds (artifacts/phase8-regression.xml).
  Ruff and pip check passed. No application source or AI environment changes this increment.
- Remaining: diagnose frozen Qt loader, verify import/playback/export in frozen build,
  compile/test installer, clean-Windows qualification, dependency/license audit, working
  CI release automation. No Git remote configured; application license remains unchosen.
- No release published. See docs/PACKAGING.md for candidate workflow and release gates.

## Phase 8 clean build verification — 2026-11-21
- Diagnosed incompatible icuuc.dll collected from Codex/Poppler on the host PATH.
  Build now uses a restricted Python/Windows PATH and clean dependency analysis.
  The rebuilt frozen executable successfully launched, imported the Unicode-path H.264/AAC
  fixture and played changing decoded frames (observed progression 0.277 to 4.933 seconds).
  This supersedes the earlier frozen-startup failure; it is verified on this PC only.
- Build log: artifacts/phase8-clean-build.log. Portable candidate and SHA256 are under artifacts.
- Added build contamination guard and FFmpeg license-copy step after the successful build;
  those two script additions await the next full build. No source application changes.
- Ruff passed; seven targeted hardware/media tests passed. Prior full source suite: 94 passed.
- GitHub Desktop is installed, but this checkout has no remote. Repository URL and application
  license choice requested. Nothing pushed or published. Installer compiler is not installed
  at standard locations. Frozen export, installer and clean-Windows verification remain.

## Phase 8 license and repository — 2026-11-21
- Owner selected MIT for Astra source, copyright 2026 sotbom. Added LICENSE and source
  documentation; build script now copies it alongside third-party notices.
- Repository authorized: https://github.com/sotbom/Astra-Video-Editor. Existing main contains
  .gitattributes only; preserve its history. Nested GitHub Desktop checkout left untouched.
- No second Windows PC available. Clean-machine testing remains pending; do not claim it passed.
- Binary redistribution audit, frozen export, installer and release automation remain incomplete.
- Source push succeeded: main commit 80610ea, preserving remote initial commit 5511792.
  No binaries/model weights uploaded and no GitHub release created. License/documentation
  checks: Ruff passed; 17 project/media tests passed. Normalized legacy line endings in
  effects_dialog.py and removed extra EOF blank lines after the initial source snapshot.
