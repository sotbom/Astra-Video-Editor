# Astra Video Editor

Offline-first Windows desktop video editor under incremental development.
The current milestone is Phase 7: a non-destructive multitrack timeline with editable
clips, project recovery, video effects, MP4 export, offline transcription, subtitles and Audio Studio.
See [PROGRESS.md](PROGRESS.md) for verified status.

## Run from this checkout

```powershell
./scripts/run.ps1
```

For a fresh checkout, follow [DEVELOPMENT.md](DEVELOPMENT.md). Requirements are 64-bit
Windows 10/11, Python 3.12â€“3.14, pinned PySide6 and FFmpeg/FFprobe. No NVIDIA GPU is
required for the desktop foundation. This is a source checkout, not a packaged release.

Choose **Import mediaâ€¦** or press **Ctrl+I**, select local files, then select an item in
the library. Use Play/Pause (Space), Stop, seek, speed and volume. Files can also be
dropped onto the window. The inspector shows duration, resolution, rational frame rate,
codecs, channel count and location. Import failures appear below the workspace.

## Edit and save

Select imported media and choose **Add selected media**, or drag it onto a compatible
timeline track. The selected track and playhead determine insertion. Add video/audio tracks
with the timeline buttons. Drag a clip to move it; drag its edges to trim it. The inspector
also accepts exact project-frame start and source in/out values (out is exclusive).
Place the playhead inside a selected clip and choose **Split** (Ctrl+B). Delete with
**Delete clip** (Ctrl+Delete). Undo with Ctrl+Z and redo with Ctrl+Shift+Z.

Click the ruler or change the Frame field to seek. The Timeline tab previews the edit,
including gaps and still images; its frame buttons move the playhead by one project frame.
Mute, Hide video and Lock apply to the selected track. Snap and Zoom control canvas editing.
Clips cannot overlap on the same track; use another track when needed. The first visible
video track takes priority. Active audio streams play independently.

Use **File â†’ New** to choose a name and frame rate. Save with Ctrl+S, reopen with Ctrl+O,
or use Save As. `.astra` files reference source media; they do not embed or modify it.
The previous valid save is retained as `.astra.bak`. Changed projects autosave every
30 seconds to the local application-data recovery directory. Startup offers recovery;
**File â†’ Recover autosave** can select an older copy. Save recovered work explicitly.
Select missing media in the library and use **File â†’ Relink selected media** to replace its path.

Normal operation is offline; no account or cloud API is used. AI models download only when
explicitly requested. Windows packaging follows in a later phase.
Timeline edit positions use exact integer frames and rational FPS, but Qt's decoded preview
seeks are approximate; frame-exact monitor images and seamless audio cuts are not guaranteed.

## Effects and export

Select a timeline video clip, then choose **Edit â†’ Selected clip video effects**. Crop
margins use source pixels. Brightness, contrast, saturation, negative, grayscale, thermal
false color and Gaussian blur are reversible and saved with the clip. Split clips inherit
their settings. Reset restores neutral values; Undo reverses an applied change.
The Timeline monitor currently shows source images without these effects. View the rendered
result using **Play exported file**, or import the export into the source monitor.

Choose **Export timeline** on the toolbar or press Ctrl+E. Choose an `.mp4` destination,
even output dimensions and CRF quality (lower means higher quality/larger files), then Export.
The current profile uses CPU H.264/AAC encoding at the project frame rate, preserving aspect
ratio with black padding. Output dimensions range from 16 to 3840 pixels per side. Gaps are
black/silent; the first visible video track wins; unmuted audio is mixed with a peak limiter.
Thermal is a visual palette, not temperature detection.

Export captures the timeline when the dialog opens. Progress and cancellation run in the
background. Replacing an existing destination requires confirmation; the old file is retained
until successful encoding and media verification. Source media and the open project are
protected from overwrite. Closing an active export requests cancellation; close the dialog
again after cancellation completes. Export quality/dimensions are currently dialog-local.

New saves use schema 5 for voice/audio settings, subtitles and effects. Schema 1â€“4 projects migrate automatically;
older builds cannot read schema 5. Keep the automatic previous-save backup if you
need to return to an older build. Hardware encoders, other containers and export presets
are not implemented yet, apart from Audio Studio's WAV output. Large/long projects still need performance qualification.

## Audio Studio

Select an audio-bearing timeline clip and open **Audio â†’ Audio Studio**. Build cached
waveforms, select a track, adjust gain/pan, noise reduction, EQ and compression, and set
selected-clip fades or master loudness normalization. Load a preset if useful, then **Apply**.
Changes support undo/redo and project saving. **Render processed mix**, then **Play**, previews
the applied settings; **Render original mix** bypasses processing for comparison.
The main Timeline monitor remains untreated. **Analyze preview loudness** measures the
rendered result; **Export WAV** produces 48 kHz stereo 24-bit PCM. Applied processing also
feeds MP4 exports. Noise reduction uses conventional FFmpeg spectral filtering, not AI.
See [Audio Studio workflow and limits](docs/AUDIO_STUDIO.md).

The **Voice transformation** tab adds reversible pitch, tempo, formant preservation and
warm/bright timbre controls with lower/higher/altered voice presets. Apply, render both mixes,
then use **Load original preview / Load processed preview** to compare without re-rendering.
Pitch preserves clip length; tempo pads or trims audio within its existing slot. Video and
subtitles are not retimed. Processing is offline DSP, with no AI identity model download.
See [voice workflow, timing and verification limits](docs/VOICE_TRANSFORMATION.md).

## Transcription and subtitles

Run `./scripts/setup_ai.ps1` to install the optional isolated AI environment. Select a timeline
clip with audio, then open **Subtitles â†’ Edit / transcribe subtitles**. Explicitly download a
model, choose CPU/int8 and language (or auto), and transcribe. The verified `tiny.en` model is
already installed in this checkout. CUDA currently falls back to CPU on this machine because
the required cuBLAS runtime is missing.

Edit subtitle text and millisecond timestamps, split/merge, search/replace, undo/redo, and
save them with the project. Export SRT/VTT/ASS, or enable **Burn project subtitles into video**
in the MP4 export dialog. The monitor shows synchronized plain text; ASS/burn-in applies the
selected font, size, color, outline and margin. See [the workflow and limitations](docs/TRANSCRIPTION.md).

If FFprobe is missing, run setup or configure `ASTRA_FFPROBE` with its full executable
path. Unsupported/corrupt files produce an import error. Codec playback support depends
on Qt Multimedia; file inspection success alone does not establish playback compatibility.
Logs reside in Qt's writable local application-data directory (`Astra/Astra Video Editor`).

See [SKILL.md](SKILL.md), [ARCHITECTURE.md](ARCHITECTURE.md), and
[third-party dependency notes](docs/LICENSES.md).

See [Masks and effects](docs/MASKS.md) for the Phase 7 editor and cached frame preview.

## License

Astra source is [MIT licensed](LICENSE), copyright 2026 sotbom. Bundled third-party
components have separate licenses; see [dependency notes](docs/LICENSES.md).
