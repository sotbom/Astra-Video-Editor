# Offline transcription and subtitles

Run `./scripts/setup_ai.ps1` once to install the separately locked AI environment. The editor
continues to work without it. Dependencies are isolated in `.venv-ai`; `ASTRA_AI_PYTHON` can
point to another compatible interpreter. The tested combination is Python 3.14.3,
faster-whisper 1.2.1, CTranslate2 4.9.0 and PyAV 16.0.1. PyAV 19.0.2 was incompatible with
faster-whisper's audio-decoding call and is deliberately not used.

1. Import video/audio and place it on the timeline. Select the clip to transcribe.
2. Open **Subtitles → Edit / transcribe subtitles**. Download a selected model explicitly
   (requires Internet once). `tiny.en` is the verified English model in this checkout.
3. Choose language code or leave blank for automatic detection. Use CPU/int8 by default.
   Press **Transcribe selected timeline clip**. Only that clip's trimmed source range is
   extracted by FFmpeg into a temporary mono 16 kHz WAV. No media is uploaded.
4. Successful results map back to the clip's timeline offset and become one undoable edit.
   Reprocessing asks before replacing overlapping subtitle segments. Failure/cancellation
   preserves the project. No-speech results preserve existing subtitles.
5. Select a subtitle row, edit text/start/end (integer milliseconds), and Apply. Add, delete,
   split at playhead, merge next, literal replace-all, undo and redo are available. Splitting
   duplicates the text into both pieces for subsequent editing. Double-click a row to seek.
6. Save the project normally. Recognized text, segment times, global subtitle style and the
   last model/language/device/compute provenance reopen without running inference again.
7. Export SRT, VTT or ASS independently. SRT/VTT import appends cues. In **Export timeline**,
   enable **Burn project subtitles into video** to render the ASS style through FFmpeg/libass.

The Timeline monitor displays synchronized plain subtitle text beneath its image. Styling
(font, size, color, outline, bottom margin) is applied to ASS and burned video, not reproduced
exactly in that preview. Subtitle editing is in a separate table rather than draggable timeline
subtitle blocks. Subtitle times are timeline-absolute; moving an associated video clip later
does not move subtitles automatically. Subtitle ends can extend the project into a black tail.

Current import supports simple UTF-8 SRT/VTT with full HH:MM:SS timestamps; WebVTT positioning,
HTML styling and ASS import are not supported. ASS export treats override syntax as literal
text. Word timestamps are returned by the backend and integration-tested, but the editor
currently persists/edits segment timestamps only. Recognition is imperfect: the test voice's
“Astra” was recognized as “Astro”; review text before delivery.

## CPU and CUDA

The GTX 1660 SUPER driver initializes, but actual CUDA inference failed because
`cublas64_12.dll` is unavailable. The isolated CUDA job then successfully retried on CPU/int8.
GPU inference is **not verified working**. No driver/CUDA runtime was installed or replaced.
The CUDA option is an explicit attempt with visible fallback, not a promise of acceleration.
Supported compute types are checked by CTranslate2; invalid choices produce an error or CPU
fallback. CPU is always the initial default.

Each job runs in a child process so native crashes and cancellation cannot take down the
editor. On Windows cancellation terminates the venv launcher and child interpreter together.
Temporary audio, request/result/status/log files are cleaned after the job. Downloaded model
files remain for reuse. Jobs time out after 12 hours; extraction has a one-hour limit. Speech
recognition accuracy beyond the generated English fixture, large models, long recordings and
GPU execution require further qualification.

See the upstream [faster-whisper installation notes](https://github.com/SYSTRAN/faster-whisper)
and [CTranslate2 installation guide](https://opennmt.net/CTranslate2/installation.html).
