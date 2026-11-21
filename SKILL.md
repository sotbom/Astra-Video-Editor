SKILL.md — Astra Video Editor

Project codename: Astra Video Editor
Document version: 1.0
Project type: Offline-first AI-assisted non-linear video editor
Target OS: Windows 10 and Windows 11, 64-bit
Development environment: Codex Desktop
Development agent: Astra Medium (or another capable coding agent)
Primary GPU: NVIDIA CUDA-compatible GPU
Distribution: Portable ZIP edition + Windows installer
Application language: Python
UI language: English initially
License strategy: Open-source dependencies with documented license compliance

1. YOUR ROLE

You are the lead software architect, senior Python developer, desktop application engineer, multimedia engineer, AI integration engineer, QA engineer, and release engineer responsible for building Astra Video Editor.

Your task is to build a real, usable, offline-first desktop video editing application.

You must not simply produce a UI mockup, demonstration, prototype with fake buttons, or a collection of disconnected scripts.

You are responsible for:

Designing the application architecture.
Implementing the graphical interface.
Integrating FFmpeg and FFprobe.
Implementing video playback and editing.
Integrating offline Whisper transcription.
Implementing subtitle editing.
Integrating audio enhancement and noise reduction.
Implementing voice transformation.
Implementing multitrack audio editing.
Implementing video effects and masks.
Implementing project saving and reopening.
Implementing rendering and export.
Building Windows executables.
Creating an automated GitHub Actions pipeline.
Publishing versioned GitHub Releases.
Testing the application and fixing defects.

You must work incrementally and verify each feature.

Do not claim a feature is complete until it has been implemented and tested.

2. PROJECT VISION

Astra Video Editor is a modern desktop video editor that combines:

Traditional non-linear video editing.
Offline AI transcription.
AI-assisted audio enhancement.
Voice transformation.
Multitrack audio editing.
FFmpeg-powered video effects.
Flexible export and rendering.
A fully offline operating mode.

The application should combine ideas from:

DaVinci Resolve.
CapCut.
Audacity.
FFmpeg-based editing tools.
Whisper-powered transcription applications.

It is not necessary to reproduce every feature of those applications.

Prioritize a stable, responsive and extensible editor.

Primary principles
Offline-first.
Privacy-oriented.
Modular architecture.
GPU acceleration when available.
CPU fallback when GPU acceleration is unavailable.
Non-destructive editing.
Recoverable projects.
Reliable rendering.
No mandatory subscriptions.
No mandatory cloud APIs.
No artificial feature limitations.
No fake controls or placeholder functionality presented as complete.

The application must not require an internet connection for normal editing after dependencies and AI models have been installed.

Internet access may be used for initial installation, updates and downloading models.

3. DEVELOPMENT ENVIRONMENT

Target development environment:

Windows 10/11 64-bit.
Codex Desktop.
Python 3.12 or another version verified against all selected dependencies.
NVIDIA CUDA-compatible GPU.
Git.
GitHub repository.
GitHub Actions.
FFmpeg.
PySide6.

Do not assume that the NVIDIA GPU supports every CUDA version.

At the beginning of development:

Inspect the operating system.
Inspect the installed Python version.
Inspect available disk space.
Inspect NVIDIA GPU information using nvidia-smi, if available.
Inspect the installed NVIDIA driver.
Determine CUDA compatibility.
Check whether FFmpeg and FFprobe are installed.
Check Git availability.
Determine whether the project directory is already initialized.
Record the findings in docs/ENVIRONMENT.md.

Do not upgrade or replace system drivers automatically.

Never assume that CUDA is available simply because an NVIDIA GPU exists.

Implement GPU capability detection and CPU fallback.

4. TECHNOLOGY STACK

Use the following preferred stack.

Desktop interface
Python.
PySide6.
Qt 6.
Qt Multimedia where appropriate.
QGraphicsView/QGraphicsScene for interactive graphics and masks.

The application must use a consistent dark interface.

Avoid introducing additional UI frameworks without a strong architectural reason.

Video processing
FFmpeg.
FFprobe.
FFmpeg filter graphs.
Python subprocess integration.

FFmpeg must handle:

Video encoding.
Video decoding.
Audio encoding.
Audio decoding.
Trimming.
Cropping.
Scaling.
Rotation.
Color adjustments.
Video effects.
Audio filtering.
Subtitle rendering.
Final rendering.
AI transcription

Preferred:

faster-whisper.
CTranslate2.
OpenAI Whisper model compatibility.

Provide the following selectable model sizes when available:

Tiny.
Base.
Small.
Medium.
Large variants supported by the selected backend.

Use faster-whisper as the primary implementation.

Support CPU and CUDA inference.

Use configurable compute types and detect supported GPU capabilities.

Do not hardcode a CUDA configuration that only works on the developer's computer.

Audio enhancement

Investigate and integrate:

DeepFilterNet.
RNNoise.
FFmpeg audio filters.
Python audio DSP.
NumPy.
SciPy.
SoundFile.

Evaluate additional dereverberation and speech-isolation models separately.

Do not install unnecessary machine-learning frameworks into the main environment.

Keep optional AI dependencies modular.

Packaging

Preferred:

PyInstaller for the initial Windows build.
Inno Setup for the Windows installer.
GitHub Actions for automated builds.

Consider Nuitka only if it demonstrates a meaningful benefit and is compatible with the selected dependencies.

5. APPLICATION ARCHITECTURE

Build a modular application.

Use this proposed structure as the starting point:

text
AstraVideoEditor/
│
├── app/
│   ├── main.py
│   ├── application.py
│   ├── version.py
│   │
│   ├── ui/
│   │   ├── main_window.py
│   │   ├── theme.py
│   │   ├── toolbar.py
│   │   ├── menu_bar.py
│   │   ├── preview.py
│   │   ├── timeline.py
│   │   ├── media_library.py
│   │   ├── inspector.py
│   │   ├── effects_panel.py
│   │   ├── audio_panel.py
│   │   ├── subtitle_panel.py
│   │   └── dialogs/
│   │
│   ├── core/
│   │   ├── project_manager.py
│   │   ├── project_schema.py
│   │   ├── timeline_engine.py
│   │   ├── playback_engine.py
│   │   ├── render_engine.py
│   │   ├── media_probe.py
│   │   ├── command_manager.py
│   │   └── autosave.py
│   │
│   ├── media/
│   │   ├── importer.py
│   │   ├── thumbnails.py
│   │   ├── waveform.py
│   │   ├── cache.py
│   │   └── proxies.py
│   │
│   ├── ai/
│   │   ├── model_manager.py
│   │   ├── transcription.py
│   │   ├── subtitles.py
│   │   ├── noise_reduction.py
│   │   ├── voice_transform.py
│   │   ├── voice_isolation.py
│   │   └── audio_enhancement.py
│   │
│   ├── video/
│   │   ├── filters.py
│   │   ├── color.py
│   │   ├── crop.py
│   │   ├── masks.py
│   │   ├── transitions.py
│   │   └── effects.py
│   │
│   ├── audio/
│   │   ├── mixer.py
│   │   ├── tracks.py
│   │   ├── effects.py
│   │   ├── equalizer.py
│   │   ├── compressor.py
│   │   ├── mastering.py
│   │   └── automation.py
│   │
│   ├── export/
│   │   ├── export_manager.py
│   │   ├── profiles.py
│   │   └── ffmpeg_builder.py
│   │
│   └── utils/
│       ├── paths.py
│       ├── logging.py
│       ├── validation.py
│       └── hardware.py
│
├── assets/
│   ├── icons/
│   ├── fonts/
│   └── styles/
│
├── models/
│   └── README.md
│
├── scripts/
│   ├── setup_dev.ps1
│   ├── build_windows.ps1
│   └── verify_ffmpeg.ps1
│
├── installer/
│   └── astra_installer.iss
│
├── tests/
│   ├── unit/
│   ├── integration/
│   └── fixtures/
│
├── docs/
│   ├── ENVIRONMENT.md
│   ├── ARCHITECTURE.md
│   ├── DEVELOPMENT.md
│   ├── FEATURES.md
│   ├── TESTING.md
│   ├── PACKAGING.md
│   └── LICENSES.md
│
├── .github/
│   └── workflows/
│       └── release.yml
│
├── requirements.txt
├── pyproject.toml
├── README.md
├── CHANGELOG.md
├── LICENSE
├── .gitignore
├── AGENTS.md
└── PROGRESS.md


You may modify this structure when necessary.

However, preserve modular separation between UI, processing, AI and export functionality.

Do not put the entire application in main.py.

6. USER INTERFACE SPECIFICATION

Create a professional dark-themed desktop interface.

The application should have the following primary sections:

Edit.
Subtitles.
Audio Studio.
Effects.
Export.
Main editing workspace

Include:

Top menu bar.
Main toolbar.
Media library.
Video preview.
Timeline.
Properties inspector.
Status bar.

The interface should be responsive to window resizing.

Use sensible minimum window dimensions.

Do not overcrowd the interface.

Media library

Allow importing:

MP4.
MKV.
MOV.
AVI.
WebM.
MP3.
WAV.
FLAC.
AAC.
M4A.
PNG.
JPG.
JPEG.
Other formats supported by the installed FFmpeg build.

Display:

Filename.
Duration.
Resolution.
Frame rate.
Audio information.
Thumbnail.
File location.

Use FFprobe for media inspection.

Preview player

Implement:

Play.
Pause.
Stop.
Seek.
Frame stepping.
Timeline synchronization.
Volume control.
Full-screen preview.
Playback speed.
Timecode display.

Use Qt Multimedia initially where suitable.

If Qt Multimedia does not provide reliable compatibility with the selected codecs, implement an alternative playback backend.

Playback must not block the GUI thread.

Timeline

Implement:

Multiple video tracks.
Multiple audio tracks.
Subtitle tracks.
Clip selection.
Clip movement.
Clip trimming.
Clip splitting.
Clip deletion.
Track visibility.
Track mute.
Track locking.
Zoom.
Horizontal scrolling.
Snapping.
Playhead movement.
Waveform display.
Basic fade controls.

Use frame-accurate time calculations.

Avoid using floating-point seconds as the sole source of truth for frame positioning.

Represent time using rational frame rates or another accurate timing model.

Editing interaction

Support:

Drag-and-drop media import.
Dragging clips onto tracks.
Selecting clips.
Moving clips.
Resizing clip boundaries.
Keyboard shortcuts.
Undo and redo.
Context menus.

Use a command-based editing architecture so undo and redo are reliable.

7. PROJECT FILE FORMAT

Create a versioned JSON project format.

Suggested extension:

.astra

The project must contain:

Project version.
Project name.
Canvas resolution.
Frame rate.
Media references.
Track definitions.
Clip positions.
Clip source in/out points.
Audio levels.
Effect settings.
Subtitle segments.
Transcription information.
Export preferences.

Example conceptual structure:

json
{
  "schema_version": 1,
  "project": {
    "name": "My Project",
    "width": 1920,
    "height": 1080,
    "fps_num": 30,
    "fps_den": 1
  },
  "media": [],
  "tracks": [],
  "clips": [],
  "subtitles": [],
  "export_settings": {}
}


Implement:

New project.
Save.
Save as.
Open.
Autosave.
Recovery after unexpected termination.
Missing-media detection.
Relinking media.
Project schema migration.

Do not store large media files directly inside the project JSON.

Use relative paths when possible.

Support absolute paths when necessary.

Do not overwrite source media.

8. AI TRANSCRIPTION AND SUBTITLES

This is one of the most important application features.

Implement offline transcription using faster-whisper.

Requirements
Load an audio track or extract audio from a video.
Select a Whisper model.
Select language or use automatic detection.
Configure transcription device.
Configure compute type.
Display processing progress.
Cancel transcription safely.
Display transcription results.
Edit recognized text.
Preserve timestamps.
Reprocess selected sections.
Export subtitles.

Support:

SRT.
VTT.
ASS.

Where supported, provide word-level timestamps.

Subtitle editor

Implement:

Editable subtitle text.
Start time.
End time.
Subtitle duration.
Add segment.
Delete segment.
Split segment.
Merge segments.
Adjust timing.
Subtitle synchronization.
Search and replace.
Import existing subtitle files.
Subtitle styling

Support:

Font family.
Font size.
Font color.
Outline.
Shadow.
Background.
Position.
Alignment.
Margin.
Bold.
Italic.

Provide subtitle preview.

Allow subtitles to remain separate or become permanently embedded during rendering.

Do not require transcription every time the project opens.

Persist transcription and subtitle data.

9. AUDIO STUDIO

Create a dedicated audio-processing workspace.

Audio processing must be non-destructive wherever practical.

Preserve original audio files.

A. Noise reduction

Integrate DeepFilterNet or another verified offline noise-reduction implementation.

Provide:

Background noise reduction.
Adjustable processing strength where supported.
Preview.
Before/after comparison.
Processing progress.
Cancellation.
Export of processed audio.

RNNoise may be provided as an alternative.

Do not pretend a filter is AI-based if it is merely a conventional EQ or gate.

B. Audio enhancement

Implement a processing chain:

Noise reduction.
Optional voice isolation.
Equalization.
De-essing.
Compression.
Loudness normalization.
Limiting.

Provide configurable presets:

Clean Voice.
Podcast.
Studio Voice.
Dialogue.
Broadcast.
Custom.

The user must be able to adjust individual processing stages.

Provide a bypass option for each stage.

Do not automatically apply destructive processing to the original media.

C. Equalizer

Implement:

High-pass filter.
Low-pass filter.
Parametric EQ.
Bass adjustment.
Midrange adjustment.
Treble adjustment.

Provide an interactive frequency response display if practical.

D. Compression and mastering

Implement:

Threshold.
Ratio.
Attack.
Release.
Makeup gain.
Limiter ceiling.
Loudness target.

Support EBU R128 loudness analysis and normalization.

Do not assume one loudness target is suitable for every platform.

Provide configurable presets.

E. Voice transformation

Implement privacy-oriented voice transformation.

Initial features:

Pitch adjustment.
Formant adjustment where supported.
Speed adjustment without unnecessary pitch changes.
Subtle timbre adjustment.
Natural lower voice.
Natural higher voice.
Neutral altered voice.
Custom settings.

Investigate suitable offline voice-conversion models if they can be distributed and used legally.

Do not make voice imitation or unauthorized identity cloning a default feature.

Provide a before/after comparison.

Keep processing reversible.

Avoid transformations that introduce excessive artifacts.

Explain that pitch changes alone do not guarantee anonymity.

F. Audio editing

Implement:

Import audio.
Trim.
Split.
Move.
Duplicate.
Fade-in.
Fade-out.
Gain adjustment.
Pan.
Mute.
Solo.
Crossfade.
Waveform display.
Audio synchronization.
G. Multitrack audio

Allow independent tracks for:

Original video audio.
Voice-over.
Background music.
Sound effects.
Additional audio.

Each track should have:

Volume.
Pan.
Mute.
Solo.
Fade controls.
Track name.
Timeline positioning.

Implement mixing during final rendering.

Do not permanently flatten tracks during editing.

10. VIDEO EDITING AND EFFECTS

Use FFmpeg filters for the underlying rendering operations.

Create a modular effect system.

Each effect must have:

Unique identifier.
Display name.
Parameters.
Defaults.
Validation.
Preview representation.
Render implementation.
Basic editing

Implement:

Trim.
Split.
Crop.
Rotate.
Flip.
Resize.
Aspect ratio adjustment.
Speed adjustment.
Color adjustment

Implement:

Brightness.
Contrast.
Saturation.
Gamma.
Exposure where appropriate.
Hue.
Temperature where supported.
Grayscale.
Blur effects

Implement:

Gaussian blur.
Box blur.
Directional blur.
Adjustable blur strength.
Mask editor

Implement:

Rectangle mask.
Ellipse mask.
Polygon mask.
Freehand mask.

Allow users to position and resize masks over the video preview.

Implement:

Mask inversion.
Feathering where supported.
Blur inside mask.
Blur outside mask.
Adjustable mask strength.
Mask positioning.

Masks should be represented in project data.

Do not limit the user to fixed preset shapes.

Special effects

Implement:

Negative.
Thermal / false-color palette.
Sepia.
Pixelation.
Sharpen.
Vignette.
Mirror.
Grayscale.
Basic chromatic effects where practical.

Thermal effect should be implemented using a false-color mapping.

Negative should use proper color inversion.

Do not create misleading effect controls that do nothing.

Effect preview

Provide preview before rendering.

Use a proxy or lower-resolution preview if full-resolution real-time processing is too expensive.

Do not sacrifice application responsiveness to provide real-time effects.

11. AUDIO AND VIDEO RENDERING ENGINE

FFmpeg is the primary rendering engine.

Implement a dedicated FFmpeg command builder.

Do not construct complicated FFmpeg commands directly inside UI classes.

Separate:

Project interpretation.
Filter graph generation.
Input mapping.
Encoding configuration.
Rendering execution.
Progress reporting.
Error reporting.
Rendering requirements

Support:

MP4.
MKV.
MOV where compatible.
WebM where compatible.

Provide export settings for:

Resolution.
Frame rate.
Video codec.
Audio codec.
Bitrate.
Quality.
Audio sample rate.
Audio channels.

Initial preferred video codecs:

H.264.
H.265 where supported.
VP9 where appropriate.

Initial preferred audio codecs:

AAC.
Opus.
FLAC.
PCM where appropriate.

Support NVIDIA NVENC when the installed FFmpeg build and GPU support it.

Always provide a CPU encoding fallback.

Detect available encoders rather than assuming their presence.

Rendering progress

Show:

Progress percentage.
Current processing stage.
Elapsed time.
Estimated remaining time where reliable.
Output file.
Cancel button.

Use a worker process.

Do not freeze the UI.

Render to a temporary output file and replace the final output only after successful completion.

Preserve existing output files if a render fails.

12. PERFORMANCE AND RESOURCE MANAGEMENT

The application must remain usable on systems without a powerful GPU.

Use:

Background workers.
Queues.
Caching.
Proxy media.
Thumbnail caching.
Waveform caching.
Lazy loading.
Memory-conscious AI model management.

Do not load every AI model into memory at application startup.

Implement an AI Model Manager.

It must support:

Model discovery.
Model downloading.
Download progress.
Model verification.
Local storage.
Model removal.
Model availability status.
Model selection.
GPU and CPU compatibility information.

Do not bundle large Whisper or enhancement models into the default executable.

Store models in an appropriate user data directory.

Use a configurable cache location.

Allow users to clear generated caches without deleting source media or projects.

13. OFFLINE-FIRST OPERATION

After installation and model acquisition, the application must work without internet access.

No mandatory cloud transcription.

No mandatory cloud audio processing.

No mandatory cloud rendering.

No mandatory account registration.

Do not transmit user media or project files.

The application must clearly distinguish:

Features that work offline.
Optional initial downloads.
Optional update checks.

Model downloads must be explicit user actions.

Verify downloaded model files using available checksums or trusted repository metadata.

Do not silently download large models.

Provide an offline status indicator or model availability information.

14. SECURITY AND STABILITY

Follow these rules throughout development.

Never execute arbitrary commands supplied by media filenames or project contents.
Use argument lists with subprocess rather than shell command concatenation.
Validate media paths.
Validate project JSON.
Handle malformed media files.
Handle missing codecs.
Handle missing AI models.
Handle GPU initialization errors.
Provide CPU fallback.
Handle interrupted renders.
Handle failed downloads.
Prevent UI thread blocking.
Avoid unbounded memory allocation.
Log errors without recording private media content unnecessarily.

Treat project files and imported media metadata as untrusted input.

Do not use shell=True for user-controlled command construction.

Do not silently overwrite files.

Provide meaningful error messages.

15. PROJECT HISTORY AND RECOVERY

Implement:

Undo.
Redo.
Autosave.
Crash recovery.
Project backups.

Maintain an editing history.

Use command objects or an equivalent architecture.

Actions that modify project state should be reversible where practical.

Do not make an undo stack that stores entire copies of large video files.

16. TESTING REQUIREMENTS

Testing is mandatory.

Use pytest.

Create:

Unit tests.
Integration tests.
FFmpeg tests.
Project serialization tests.
Timeline tests.
Audio processing tests.
Transcription integration tests.
Packaging smoke tests.

Tests must use generated or legally usable sample media.

Do not depend on private user media.

Required tests
Project tests
Create a project.
Save a project.
Reopen a project.
Validate project schema.
Recover autosaved project.
Handle missing media.
Timeline tests
Add clips.
Move clips.
Split clips.
Trim clips.
Add audio tracks.
Add subtitles.
Undo and redo changes.
AI tests
Load an available Whisper model.
Transcribe a known sample.
Validate timestamps.
Export SRT.
Export VTT.
Handle missing models.
Handle CUDA failure.
Test CPU fallback.
Audio tests
Process sample audio.
Apply noise reduction.
Apply EQ.
Apply compression.
Normalize loudness.
Mix multiple tracks.
Verify output duration and audio stream.
Video tests
Probe media.
Crop.
Resize.
Change brightness.
Change contrast.
Change saturation.
Apply negative.
Apply thermal.
Apply blur.
Render a short video.
Packaging tests
Build portable distribution.
Launch packaged application.
Verify bundled FFmpeg.
Verify required Qt plugins.
Verify missing model handling.
Build installer.
Verify installation and launch.

A test must verify actual behavior rather than merely checking that a Python method exists.

Do not use fake test results.

17. WINDOWS DISTRIBUTION

Provide two release artifacts.

A. Portable edition

Create:

AstraVideoEditor-Portable-Windows-x64.zip

It should contain:

Executable.
Required application libraries.
FFmpeg binaries.
Required Qt plugins.
Application assets.
Configuration defaults.
Documentation.
Third-party notices.

The portable edition must run without requiring a Python installation.

Use a writable user-data directory rather than assuming the application folder is writable.

Do not claim that a ZIP containing external dependencies is a single-file executable.

B. Windows installer

Create:

AstraVideoEditor-Setup-Windows-x64.exe

Use Inno Setup.

Include:

Installation directory selection.
Start menu shortcut.
Optional desktop shortcut.
Uninstaller.
Application icon.
Version information.
Third-party license notices.

The installer must not silently install AI models that occupy several gigabytes.

The user should be able to download models from the application's Model Manager.

Dependency packaging

Bundle required FFmpeg binaries or provide an explicit, verified installation strategy.

Ensure Qt multimedia plugins and required runtime libraries are included.

Do not assume the development environment will exist on the target PC.

Test the packaged application on a clean Windows environment.

18. GITHUB ACTIONS AUTOMATION

Create:

.github/workflows/release.yml

Implement three types of workflow triggers.

Pull requests
Set up Python.
Install development dependencies.
Run linting.
Run tests.
Validate packaging configuration.

Do not publish a release.

Push to main
Run tests.
Build a development portable artifact.
Upload the build as a workflow artifact.

Do not automatically publish a stable release.

Version tags

Trigger on:

v*

Example:

v0.1.0

The release pipeline must:

Check out the repository.
Set up Python.
Install dependencies.
Run tests.
Verify FFmpeg.
Build the portable edition.
Package the portable ZIP.
Build the installer.
Validate generated artifacts.
Generate SHA256 checksums.
Create a GitHub Release.
Upload the ZIP.
Upload the installer.
Upload checksums.
Publish release notes.

Use GitHub's official release mechanisms and least-privilege permissions.

Use a pinned or otherwise controlled version of third-party GitHub Actions.

Never expose personal access tokens in source code.

Use the built-in GITHUB_TOKEN where sufficient.

Configure release permissions explicitly.

The release pipeline must fail if the executable or installer is missing.

Do not publish incomplete or failed builds.

Prefer GitHub-hosted Windows runners initially.

Document any limitations caused by GPU hardware not being available on hosted runners.

Do not require an NVIDIA GPU to build the application.

GPU testing can be performed separately on compatible hardware.

19. VERSIONING

Use semantic versioning.

Format:

MAJOR.MINOR.PATCH

Examples:

0.1.0
0.2.0
0.5.0
1.0.0

Maintain:

CHANGELOG.md
Application version.
Release notes.
Build metadata.

Do not publish a version without testing the packaged application.

20. LICENSE AND REDISTRIBUTION COMPLIANCE

This is mandatory.

Before distributing dependencies:

Identify each dependency.
Record its license.
Check redistribution requirements.
Check commercial-use permissions.
Check model licenses.
Check model weight redistribution conditions.
Check FFmpeg build configuration.
Check Qt/PySide6 licensing.
Include third-party notices.
Document any dependency that must be downloaded separately.

Pay special attention to:

FFmpeg LGPL/GPL configuration.
PySide6 and Qt licensing.
AI model licenses.
Voice-conversion model licenses.
Codec redistribution restrictions.
Third-party binaries.

Do not assume that an open-source project automatically permits unrestricted redistribution of its pretrained models.

Do not bundle restricted components without resolving their licensing requirements.

21. DOCUMENTATION

Maintain the following documentation:

README.md

Explain:

What Astra Video Editor is.
Features.
Screenshots when available.
Installation.
System requirements.
Model downloads.
Offline usage.
Basic instructions.
Troubleshooting.
ARCHITECTURE.md

Explain:

Main components.
Data flow.
Timeline model.
Playback architecture.
Rendering architecture.
AI integration.
Project format.
DEVELOPMENT.md

Explain:

Development environment.
Python setup.
Dependency installation.
Running the application.
Running tests.
Building locally.
PACKAGING.md

Explain:

Portable build.
Installer build.
FFmpeg bundling.
GitHub Actions.
Release tagging.
LICENSES.md

List third-party components and licensing information.

22. DEVELOPMENT ROADMAP

Follow this order.

Do not skip phases merely to make the project appear more complete.

Phase 0 — Environment and architecture

Tasks:

Inspect environment.
Inspect GPU.
Verify Python.
Verify FFmpeg.
Create repository structure.
Create development environment.
Establish dependency management.
Create project documentation.
Create progress tracking.

Deliverable:

A reproducible development environment and architecture skeleton.

Phase 1 — Desktop foundation

Tasks:

Create main window.
Create dark theme.
Implement menus.
Implement toolbar.
Implement media library.
Implement file import.
Implement FFprobe integration.
Implement basic playback.
Implement error handling.

Deliverable:

A functioning desktop application that imports and plays local media.

Phase 2 — Timeline and project management

Tasks:

Create timeline.
Implement tracks.
Implement clips.
Implement trim.
Implement split.
Implement movement.
Implement playhead.
Implement project saving.
Implement project reopening.
Implement autosave.
Implement undo and redo.

Deliverable:

A basic but genuinely editable non-linear video editor.

Phase 3 — Video rendering and basic effects

Tasks:

Implement FFmpeg command builder.
Implement trimming.
Implement cropping.
Implement resizing.
Implement brightness.
Implement contrast.
Implement saturation.
Implement negative.
Implement grayscale.
Implement thermal.
Implement basic blur.
Implement export progress.

Deliverable:

A video editor capable of producing edited output files.

Phase 4 — AI transcription and subtitles

Tasks:

Implement model manager.
Integrate faster-whisper.
Implement CUDA detection.
Implement CPU fallback.
Implement transcription.
Implement timestamp handling.
Implement subtitle editing.
Implement SRT export.
Implement VTT export.
Implement ASS export.
Implement subtitle rendering.

Deliverable:

A functioning offline transcription and subtitle workflow.

Phase 5 — Audio Studio

Tasks:

Implement audio timeline.
Implement waveforms.
Implement multitrack audio.
Implement volume and pan.
Implement fade controls.
Integrate DeepFilterNet or an alternative.
Implement EQ.
Implement compression.
Implement normalization.
Implement audio mixing.
Implement audio export.

Deliverable:

A working multitrack audio editor and enhancement suite.

Phase 6 — Advanced audio and voice transformation

Tasks:

Implement voice transformation.
Implement pitch control.
Implement formant processing where supported.
Evaluate optional AI voice-conversion models.
Implement presets.
Implement preview.
Implement before/after comparison.

Deliverable:

A usable voice transformation system with natural-sounding output as the objective.

Phase 7 — Advanced video effects

Tasks:

Implement shape masks.
Implement freehand masks.
Implement mask inversion.
Implement feathering.
Implement masked blur.
Implement additional visual effects.
Improve preview performance.

Deliverable:

A more advanced effects editor.

Phase 8 — Packaging and releases

Tasks:

Build portable application.
Build installer.
Validate bundled dependencies.
Test on clean Windows.
Create GitHub Actions workflow.
Automate releases.
Generate checksums.
Publish release notes.

Deliverable:

A downloadable Windows application with automated releases.

Phase 9 — Stabilization

Tasks:

Fix bugs.
Optimize performance.
Improve usability.
Improve documentation.
Audit licenses.
Improve recovery.
Test larger projects.
Test long-duration audio and video.
Verify offline operation.

Deliverable:

A stable 1.0 release.

23. CODING STANDARDS

Follow these rules:

Use readable Python.
Use type hints.
Use docstrings for public APIs.
Use modular classes.
Avoid unnecessary global state.
Avoid circular imports.
Use structured logging.
Handle exceptions appropriately.
Keep UI and processing logic separate.
Use background workers for expensive tasks.
Use signals and slots for UI communication.
Validate all external inputs.
Keep functions reasonably small.
Use meaningful names.
Write tests for important functionality.

Use ruff or an equivalent tool for linting.

Use pytest for automated testing.

Use a dependency lock file or another reproducible dependency strategy.

Do not casually change dependencies without verifying compatibility.

24. AGENT WORKING RULES

These rules are especially important when operating inside Codex Desktop.

Rule 1: Inspect before modifying

Before changing existing code:

Inspect the repository.
Read README.
Read AGENTS.md if present.
Read PROGRESS.md.
Inspect relevant modules.
Understand the current architecture.

Never overwrite existing working functionality without understanding it.

Rule 2: Work incrementally

Do not generate the entire application in one response.

Complete one logical development task at a time.

After each task:

Run relevant tests.
Inspect errors.
Fix regressions.
Update documentation.
Update PROGRESS.md.
Summarize completed work.
Rule 3: Implement real functionality

Do not create fake buttons.

Do not use placeholder functions that claim to perform operations.

Do not create UI controls that have no working backend.

If a feature cannot yet be implemented:

Mark it as planned.
Disable the unavailable control.
Explain its status.
Add it to the development roadmap.

Never represent unfinished functionality as complete.

Rule 4: Keep the application runnable

After every meaningful milestone:

Start the application.
Check the GUI.
Verify the relevant feature.
Inspect logs.
Run automated tests.

Do not leave the repository in a permanently broken state.

Rule 5: Protect working code

Do not rewrite functioning subsystems merely because a different implementation looks more attractive.

Refactor only when there is a clear technical reason.

Rule 6: Verify external dependencies

Before integrating a new library:

Check compatibility.
Check Python version support.
Check Windows support.
Check CUDA compatibility if applicable.
Check maintenance status.
Check licensing.
Test a minimal integration.
Rule 7: Be transparent

Never say that a feature works unless it has been tested.

Report:

Implemented features.
Tested features.
Known limitations.
Outstanding defects.
Required dependencies.
Rule 8: Do not stop after planning

Once the repository is inspected and the environment is understood, begin implementing the first working phase.

Do not spend the entire session writing documentation and architectural proposals.

The objective is working software.

25. PROGRESS TRACKING

Create and maintain PROGRESS.md.

Use this structure:

markdown
# Astra Video Editor Development Progress

## Current Version
0.1.0-dev

## Current Phase
Phase 0

## Completed
- [ ] Environment inspection
- [ ] Repository structure
- [ ] Dependency configuration

## In Progress
- [ ] Current development task

## Pending
- [ ] Upcoming task

## Tests
- Passed:
- Failed:
- Not run:

## Known Issues
- None documented yet.

## Architecture Decisions
- Record important decisions here.

## Next Action
- Describe the exact next implementation task.


Update it after every meaningful development session.

Do not mark tasks complete simply because files were created.

Only mark them complete after functional verification.

26. FIRST SESSION INSTRUCTIONS

When this skill is provided to a fresh Codex Desktop session, follow these exact initial steps.

Step 1

Inspect the repository and development environment.

Determine whether this is a new repository or an existing project.

Step 2

Inspect the NVIDIA GPU and available CUDA support.

Determine the correct AI execution strategy.

Step 3

Verify Python, FFmpeg, FFprobe and Git.

Step 4

Create or inspect the repository structure.

Step 5

Create:

README.md
AGENTS.md
PROGRESS.md
ARCHITECTURE.md
DEVELOPMENT.md
requirements.txt or pyproject.toml
.gitignore
Step 6

Set up a clean Python virtual environment.

Do not install every optional AI dependency immediately.

Start with the minimum dependencies required for the desktop foundation.

Step 7

Implement Phase 1.

Build the first actual application window.

It must have:

A dark interface.
Media import.
Media library.
Preview player.
Basic playback controls.
FFprobe integration.
Proper error handling.
Step 8

Run the application.

Import a test video.

Verify playback.

Fix errors.

Step 9

Run automated tests.

Step 10

Update PROGRESS.md and explain the next implementation milestone.

Do not stop after producing an architecture document.

Start writing and testing actual application code.

27. DEFINITION OF DONE

A feature is complete only when:

Its implementation exists.
Its UI is connected to its backend.
Its inputs are validated.
Its errors are handled.
It does not freeze the GUI.
Its output is verified.
Relevant tests pass.
Its documentation is updated.
It works with the project architecture.
Its limitations are documented.

A release is complete only when:

The portable ZIP builds successfully.
The installer builds successfully.
The packaged application launches.
FFmpeg works in the packaged environment.
Required Qt plugins are available.
Project saving and reopening work.
Basic rendering works.
Required tests pass.
Dependency licensing has been reviewed.
GitHub Release assets are uploaded correctly.
28. FINAL PROJECT OBJECTIVE

The final application should be a polished Windows desktop video editor with:

Offline Whisper transcription.
Editable subtitles.
SRT/VTT/ASS export.
AI-assisted noise removal.
Natural-sounding audio enhancement.
Privacy-oriented voice transformation.
Multitrack audio editing.
Background music and sound-effect support.
FFmpeg-powered video editing.
Cropping and trimming.
Brightness, contrast and saturation adjustments.
Shape and freehand masks.
Masked blur.
Negative and thermal effects.
Project saving and reopening.
Timeline editing.
GPU acceleration where available.
CPU fallback.
High-quality rendering.
Portable Windows distribution.
Windows installer.
Automatic GitHub Releases.

The application must remain modular and extensible.

Future development should be able to add transitions, keyframes, more advanced color grading, proxy workflows, additional AI models and more sophisticated editing features without replacing the entire architecture.

Most important instruction: Build a real application, not a demonstration. Work incrementally, test every milestone, preserve existing functionality, and continue until the application is genuinely usable.

END OF SKILL.md