# Voice transformation — Phase 6

Open **Audio → Audio Studio → Voice transformation** and select a track. Enable voice
transformation, set pitch (−12 to +12 semitones), tempo (0.5–2×), formant mode and timbre
(warm to bright). Controls are reversible and saved with the project. Voice bypass leaves
the other track processors active. Reset voice changes only voice controls; the general
Neutral preset resets the entire track processing chain.

Natural lower (−3 semitones), Natural higher (+3) and Neutral altered (+1 with shifted
formants) provide conservative starting points. **Load voice preset** populates controls;
**Apply track / fades / master** commits them. Preset names describe intended results, not
a guarantee of perceptual quality. Pitch changes alone do not guarantee anonymity.

Render original and processed mixes once, then use **Load original preview** and **Load
processed preview** to switch between their cached results. Each loads paused from the
start; press Play. This is sequential comparison, not a seamless synchronized A/B switch.
Edits/undo/redo invalidate both snapshots, so render again after applying changes. Edits in
controls are not committed until Apply. Export WAV and MP4 use the same applied processing.

## Timing and formants

Pitch does not change the timeline duration. Tempo changes the trimmed source audio inside
the existing clip slot: faster audio leaves trailing silence, while slower audio is cut at
the slot end. Other clips, video and subtitles are not moved or retimed. This mode is useful
for fitting a short voice segment, but it is not ripple speed editing. Fades follow processing
and use the fixed clip duration. Source waveforms still depict untreated source timing.

The installed FFmpeg Rubber Band filter supports formants preserved or shifted with pitch.
It does not expose independent numeric formant scaling, so no independent formant slider is
provided. Timbre uses gentle bass/treble shelves and is not formant shifting or AI conversion.
The processing order is denoise, voice transform, EQ, compression, gain/balance, fades, mix,
then master. Processing resets per clip. The Timeline monitor remains untreated.

## Backend and optional model evaluation

The installed FFmpeg 9.0.2 exposes `rubberband`, verified locally with its filter help and
actual renders. Rendering checks the configured binary's filter inventory in the worker;
an unavailable backend produces an actionable error and preserves existing output. Bypassed
voice processing still works with ordinary FFmpeg. No new Python dependency, model, GPU
runtime or network call is required.

[FFmpeg's filter documentation](https://ffmpeg.org/ffmpeg-filters.html#rubberband) documents
separate pitch/tempo and formant preservation. [Rubber Band upstream](https://breakfastquay.com/rubberband/)
lists GPL licensing and commercial licensing options; the existing FFmpeg build is GPL-enabled.
Distribution remains subject to the Phase 8 audit.

Optional AI conversion was evaluated from the [VC Client project documentation](https://github.com/w-okada/voice-changer/blob/master/README_en.md).
Its RVC/Beatrice and related backends require separate model/runtime choices, with Torch/ONNX
options. Its [license notice](https://github.com/w-okada/voice-changer/blob/master/LICENSE-NOTICE)
points to component-specific vocoder and Beatrice terms; its README also documents restrictions
for some bundled voices. This is not a single unrestricted weight set suitable for automatic
bundling. No model weights were downloaded, no AI identity conversion was integrated, and
no claim is made about compatibility or performance in Astra's isolated Python 3.14 environments.
Any future integration needs a separately verified runtime and explicitly licensed weights.

## Verification limits

Real PCM tests measure pitch frequency, independent tempo, fixed duration, delayed starts,
silence padding, formant-mode output differences, timbre shelf energy and exact bypass output.
Project tests cover schema 5, schema 4 migration, validation and undo/redo. Desktop tests cover
preset application, actual rendering, both cached previews, playback clock and invalidation.
These checks do not prove natural speech quality or anonymity. Speaker audibility, broad voice
datasets, perceptual listening assessment and long-project performance remain unverified.
