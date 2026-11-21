# Audio Studio — Phase 5

Open **Audio → Audio Studio** after placing media on the timeline. Select a track in the
dialog. **Build timeline waveforms** creates cached source peaks for audio-bearing media;
trimmed clips display the corresponding source region. Rebuild after opening a project to
load cached peaks. Processing is cancellable and runs outside the GUI thread.

Track controls include gain in dB, stereo balance (−1 left, 0 center, +1 right), spectral
noise reduction, high/low-pass filters, bass/mid/treble EQ and compression. Neutral, Clean
Voice and Podcast presets populate controls; **Apply track / fades / master** commits one
undoable command. Locked tracks reject changes. Presets are starting points, not a guarantee
of improved speech quality.

The second tab controls fades in milliseconds for the selected timeline clip on that track,
plus project-wide loudness target and peak ceiling. Fades clamp to the rendered clip duration.
Split clips inherit fade settings on both halves; fade-envelope continuity across edits is
not implemented. Save the project to retain settings. Schema 5 reads older projects with
default audio settings; older versions cannot read new saves.

After applying changes, **Render processed mix** creates a temporary WAV preview. Play,
pause, stop, seek, speed and volume operate on that result. **Render original mix** bypasses
track processing and fades while retaining timeline edits, mute state and the default master
limiter. Render again after edits: preview audio is a snapshot. **Analyze preview loudness**
reports integrated LUFS, true peak and loudness range for the loaded result.

**Export WAV** writes 48 kHz stereo 24-bit PCM for the whole timeline. Applied settings also
feed MP4 audio exports. Background progress and cancellation preserve existing destinations;
replacing a file requires confirmation. Source media and the project cannot be overwritten.
Closing an active job requests cancellation; close again when it finishes.

## Processing and limits

Noise reduction uses FFmpeg `afftdn`, a conventional spectral alternative to DeepFilterNet.
No neural enhancement model was installed. EQ, compression and fades run per clip; compressor
state resets at cuts. Balance attenuates the opposite stereo channel and leaves center unity.
Sources are converted to stereo before processing. Multiple unmuted clips mix at their timeline
positions. Master normalization uses dynamic single-pass `loudnorm`; otherwise a peak limiter
uses the chosen ceiling (default −1 dB). This is not a two-pass broadcast compliance workflow.

The Timeline monitor remains untreated. Use rendered previews to inspect processing.
Waveform cache bins are bounded to about 8,000 per source and drawings to 1,000 per clip;
they are visual summaries, not a sample editor. Cache invalidation uses file metadata, not
full content hashes. Cache files live in the local application-data waveform directory.

Functional checks cover real PCM gain/pan/fades, overlapping/muted tracks, filter attenuation,
synthetic-noise reduction, target loudness, schema persistence, cache reuse, playback progress,
WAV output and cancellation. Tests do not establish subjective speech quality, audible speaker
output, long-session stability, huge-project performance or sample-synchronized live monitoring.
