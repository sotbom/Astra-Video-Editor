# Feature status

Verified Phase 1: local imports (picker/drop), background FFprobe, duplicate prevention,
media metadata/library, video/audio/image preview, play/pause/stop/seek, playback speed,
volume, error display, import cancellation and safe shutdown. See TESTING.md for exact coverage.

Verified Phase 2: video/audio tracks, add/trim/split/move/delete, canvas drag/drop,
snapping, zoom/scroll, playhead, mute/hide/lock, undo/redo, timeline video/audio/image
preview, project save/open/backup, autosave, abrupt-exit recovery and media relinking.
Edit times are exact project frames; decoded preview seeking is approximate. Track audio
plays independently; rendered mixing, waveforms and fades are covered by Phase 5 below.
Verified Phase 3: MP4 CPU H.264/AAC export, timeline trims/gaps/track priority, unmuted audio
mixing, output resize/padding, selected-clip crop/brightness/contrast/saturation/negative/
grayscale/thermal/blur, schema 1→2 migration, background progress, cancellation and output
protection. Effects apply to export; the Timeline monitor remains an untreated source preview.
CRF/dimensions are dialog-local; NVENC, more formats/profiles and long-project qualification
remain future work. See TESTING.md for the exact evidence.
Verified Phase 4: explicit model catalog/download, real offline selected-clip English CPU
transcription, language selection, timestamps, CUDA failure→CPU fallback, process cancellation,
subtitle editing/split/merge/search-replace/undo, SRT/VTT import, SRT/VTT/ASS export, synchronized
plain-text preview, basic ASS styling and burned-video rendering, schema 3 migration/persistence.
GPU inference is not working on this installation (missing cuBLAS); multilingual/large models,
word-level UI, advanced subtitle styling/import and long recordings are not qualified.
Verified Phase 5: cached source waveforms, multitrack rendered audio, gain/stereo balance,
clip fades, conventional spectral denoise, EQ, compression, master normalization/limiting,
presets, undo/redo, schema 4 persistence, processed/original rendered previews, loudness
measurement, 48 kHz stereo PCM24 WAV export and active-job cancellation. MP4 shares audio
processing. Timeline monitor audio remains untreated. DeepFilterNet is not integrated;
FFmpeg provides the alternative denoising backend. See AUDIO_STUDIO.md for exact semantics.

Verified Phase 6: offline pitch and tempo, preserved/shifted formant mode, warm/bright timbre,
voice presets, bypass, schema 5 persistence, undo/redo, cached before/after previews and WAV/MP4
processing. Tempo pads/trims within fixed clip slots. Independent formant scaling and neural
voice conversion are not integrated; perceptual quality remains unverified. See VOICE_TRANSFORMATION.md.

Planned later: masks, additional effects and portable/installer releases.
