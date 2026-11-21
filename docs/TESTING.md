# Functional verification — Phases 1–6

Latest full run (2026-11-17): 85 passed in 44.00 seconds, exit 0, Windows build 26200,
Python 3.14.3, PySide6/Qt 6.11.3 and FFmpeg 9.0.2. Machine-readable evidence:
`artifacts/phase6-tests.xml`; per-test log: `artifacts/phase6-full.log`.
Prior Phase 2 evidence remains in `artifacts/phase2-tests.xml`.

The suite generates a six-second 640×360 30 fps H.264/AAC video, a PCM WAV and PNG.
It checks real FFprobe metadata, live GUI processing during imports, changing decoded
video images, play/pause/seek/stop, volume/speed values, image pixels, audio progress,
bad/missing files, missing FFprobe, duplicate imports, native-picker wiring, actual Qt drop
events, remote drop rejection, cancellation/recovery and close while importing.
The picker-wiring test substitutes file selection only; probing and playback stay real.
Two tests verify CPU selection when CUDA is missing or fails initialization.

Phase 2 adds 12 model/persistence tests, 10 timeline desktop tests and one process-exit
recovery test. They exercise integer/rational timing; add/move/trim/split/delete; undo/redo;
same-track overlap/source bounds/locked tracks; Qt mouse drag and edge trim; media drops;
changing decoded timeline images; cuts, gaps, pause and stop; audio progress and mute;
video-track handoff and still-image pixels; JSON roundtrip/backup/atomic failure; source
overwrite prevention; missing-media relinking; save/reopen/autosave; failed operation state
preservation; and unsaved-change cancellation. The crash test exits a real child process
without close cleanup, recovers its saved edits and explicitly saves the recovered project.

Separate Windows GUI verification used the actual native file picker, selected the generated
Unicode/space filename, observed metadata and the rendered test pattern, stopped/reset playback
and closed the window successfully. No private media was used.
Phase 2 native verification added and split the video at frame 60, moved the second clip to
frame 90, used undo/redo, saved through the Windows picker and reopened the file. The saved
JSON and reopened timeline retained the gap and source ranges; playback reached frame 210.
The example project is `artifacts/phase2-native.astra` and references generated local media.

Phase 3 adds 13 real FFmpeg render cases and four desktop cases. Decoded pixels verify trim
source frames, black gaps, track priority/hiding, still images and changes from each of the
eight effect settings (including crop). PCM checks verify silence in gaps/muted tracks and
audio in active regions. FFprobe checks resolution, fractional FPS, duration and exact output
frame count. Other cases verify effect serialization/undo, schema migration, invalid settings,
source overwrite rejection, missing tools, existing destination preservation and empty exports.
Desktop tests exercise the effects controls, live event-loop callbacks during export, progress
to 100%, decoded playback of the output, cancellation of an already-running encode, temporary
cleanup and visible errors. They do not replace broader media/large-project qualification.

Native Phase 3 verification opened the saved Phase 2 project, used the toolbar export dialog,
rendered `artifacts/phase3-native.mp4`, observed 100% completion and opened the result with
the Play exported file button. Windows Media Player displayed the generated test pattern.
Independent FFprobe verified H.264/AAC, 1920×1080, 30 fps, 210 video frames and 7.000 seconds.

Phase 4 adds six subtitle/model/render cases, four actual optional inference cases and three
desktop cases. They verify segment edit/split/merge/undo, style validation, schema migration,
save/reopen, SRT/VTT roundtrip, ASS escape safety and decoded subtitle pixels at active/inactive
times. Inference uses the explicitly downloaded tiny.en model and original Windows SAPI speech.
Tests check recognized phrases, bounded segment and word timestamps, offline CPU execution,
failed CUDA compute selection followed by real CPU inference, actual process cancellation and
missing-model errors. Desktop tests use connected subtitle controls, preview timing, all three
subtitle exports, import and real selected-clip transcription with a timeline offset.
These optional AI tests skip on checkouts without the model/fixture; none skipped in this run.

An actual CUDA float16 attempt on this GPU failed for missing `cublas64_12.dll`, then returned
real CPU results. `artifacts/phase4-inference-result.json` records that outcome. The native
editor recognized two segments at 0–5700 ms and 6720–11240 ms, displayed 100% completion and
saved `artifacts/phase4-native.astra`. This saved result generated SRT/VTT/ASS and
`artifacts/phase4-captioned.mp4` with burned captions. The proper name Astra was recognized as
Astro: recognition quality is not asserted perfect. Only generated English speech was qualified.
Final visual inspection confirmed the active subtitle at frame 30 in the native monitor and
legible burned text in `artifacts/phase4-caption-frame.png`. The captioned MP4 contains
363 video frames at 640×360, H.264/AAC, with a 12.100-second duration.

Fixed during Phase 4: incompatible PyAV 19 API (pinned 16.0.1), atomic status-file replacement
occasionally failing while a Windows reader held it (bounded sharing retry), and cancellation
leaving a venv child interpreter holding temporary logs (terminate the owned process tree).
The first full run had 65 passes and one cancellation failure; the corrected full run passed 66.

Phase 5 adds seven real audio tests and two desktop tests. Decoded PCM verifies −6 dB gain,
left balance/right silence, fades, summed overlapping tracks, mute, EQ/compressor attenuation
and synthetic-noise reduction. A six-second tone normalizes within 1 LUFS of −16 and stays
below the tested peak tolerance. WAV codec/rate/channels/duration, schema persistence, undo,
invalid settings, source protection, cache reuse and cancellation are checked. Desktop cases
exercise actual controls, waveform drawing, processed preview clock, loudness analysis,
WAV export and cancellation during an active long render. These are numerical and functional
checks, not perceptual speech-quality assessments.

Native Phase 5: generated speech waveform appeared on the timeline; loaded and applied Clean
Voice, rendered a 12.100-second processed preview to 100%, and observed playback past 5 seconds.
Native analysis returned −22.95 LUFS, −7.37 dBTP and 2.10 LU. Saved schema-4 settings through
the Windows picker in `artifacts/phase5-native.astra`. Exported `artifacts/phase5-native.wav`
through the Audio Studio picker; independent FFprobe confirmed PCM24, 48 kHz, two channels
and 12.100 seconds. The Clean Voice sample leaves master normalization disabled.

Phase 6 adds nine DSP/persistence cases and one desktop case. Real PCM verifies expected
pitch frequency, independent tempo, preserved timeline delay/duration, faster-audio silence,
both formant modes, high-frequency timbre energy and exact bypass. Tests also check schema 5
roundtrip/schema 4 migration, invalid values, undo/redo, missing-backend output preservation,
actual AAC pitch in MP4, preset application, original/processed preview playback and cache
invalidation/cleanup. Initial full run: 83 passes and one test path-separator mismatch; the
corrected run plus an MP4 case passed all 85. No product failure was hidden by that correction.
Native layout inspection found clipped help text; making the voice tab scrollable was followed
by all three Audio Studio desktop tests passing in 3.94 seconds (`artifacts/phase6-layout-tests.log`).
Pitch-only tone tests use shifted formants; preserved formants can change pure-tone amplitude.
The tests do not establish perceptual speech quality or anonymity.

Native Phase 6 loaded Natural lower onto the saved generated speech project, rendered both
12.100-second mixes, played transformed audio past 7 seconds and switched to cached original.
The scrollable tab exposed the complete timing/formant/privacy guidance. Saved through the
native picker as `artifacts/phase6-native.astra`; an independent reload retained −3 semitones,
preserved formants and −1.5 dB timbre. Rendering that saved project produced
`artifacts/phase6-lower-voice.wav`, verified as PCM24, 48 kHz stereo and 12.100 seconds.

Ruff lint and format checks pass (61 Python files); pip check reports no broken dependencies
in either environment.
The setup script successfully reruns the lock installation and verifies both binaries.
The initial download was checksum-verified; a fresh-machine scripted install is not yet tested.

## Resolved regression

Qt 6.10.1 hung in its audio renderer when stopping after seek/rate changes. Queuing the test
frame observer alone and wrapping the stop slot did not resolve it. Updating to 6.11.3 with
explicit QObject slots passed the unchanged transport assertions. Keep this regression test.
Phase 2 also exposed a stop hang when detaching a Qt video sink before stopping an inactive
decoder, plus a source seek overwritten by queued load events. The playback engine now stops
before detaching and checks pending/current load state. Gap, seek, stop and track-handoff
tests cover these paths.

## Remaining diagnostic and coverage gaps

After desktop automation attached, subsequent pytest GUI runs reported `0x8001010d` via
faulthandler, continued executing, and passed all tests. No application termination was observed.
Microsoft identifies this as an outgoing COM call attempted during synchronous input dispatch:
[COM error codes](https://learn.microsoft.com/en-us/windows/win32/com/com-error-codes-3).
The exact source is not isolated; an accessibility/COM interaction is a hypothesis, not a proven
application cause. Python installs a Windows exception handler when faulthandler is enabled:
[faulthandler documentation](https://docs.python.org/3/library/faulthandler.html).
Keep diagnostics enabled and investigate separately if reproduced without desktop automation.

The restricted runner has terminated in native Qt/Windows initialization. Run GUI verification
in an unlocked interactive session. One interactive full run also stalled without output and
was explicitly stopped; its cause is unknown. The subsequent run with `-vv` and
`-o faulthandler_timeout=25` passed all 36 tests. A passing rerun does not establish that the
intermittent stall is fixed. Preserve stack diagnostics for future reproductions.

Not verified: speaker audibility, arbitrary codecs/containers, huge/malformed metadata stress,
hour-long media, clean Windows 10/11 machines, successful CUDA AI inference, NVENC or packaging.
Timeline edit values use exact project frames. Tests do not establish frame-exact Qt monitor
images, sample-synchronized Qt preview audio or gapless preview playback. Phase 3 exports
are tested on short generated media; VFR/rotation/HDR, large clip counts, long durations,
arbitrary codecs, 4K throughput and NVENC remain unverified. Live effect preview is not implemented.
