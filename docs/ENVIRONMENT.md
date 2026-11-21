# Environment inspection — 2026-11-16 / 17 (Asia/Karachi)

- Active workspace: `C:/Users/PC/Downloads/YAR/Astra Video Editor`, initially empty.
- Source document: `D:/YAR/Astra Video Editor/SKILL.md - Astra Video Editor.md`;
  source directory contained only that document. Copied unchanged to workspace `SKILL.md`.
- Windows build 26200, display version 25H2, x64. Registry legacy ProductName says
  Windows 10 Pro; build identifies the Windows 11 generation.
- C: free space at start: 53.93 GB.
- Git 2.55.0.windows.2 available. No repository or remote existed at the start.
- Default Python: 3.15.2. Additional Python 3.14.3 at
  `C:/Users/PC/AppData/Local/Programs/Python/Python314/python.exe`; used for local `.venv`.
- Node 26.13.0 / npm 11.20.0 available, unused for this Python desktop application.
- dotnet, Cargo, rustc, CMake, FFmpeg, FFprobe absent from PATH at start.
- Project-local FFmpeg/FFprobe 9.0.2 essentials, Gyan build; both executed successfully.
- FFmpeg archive SHA256: `60f467265b1e312373dbcd92200c2618a74850f98d3d078e94296bb3fa2047ba`.
  Checked against the provider's published SHA256 before extraction.
- NVIDIA GeForce GTX 1660 SUPER, 6144 MiB, driver 610.88, WDDM.
- `nvidia-smi` reports CUDA UMD 13.3. This is driver capability, not proof of a
  CUDA toolkit, cuDNN, CTranslate2, or working Whisper inference installation.

AI strategy: do not install AI frameworks in Phase 1. Start future inference on CPU;
offer CUDA only after the selected backend's runtime libraries and an actual model smoke
test succeed. Keep CPU fallback on initialization/inference failure. NVENC support must
be checked independently with a real encode before presenting it as available.

CUDA Driver API `cuInit`, device count and compute-capability calls succeeded: one device,
compute capability 7.5. This still does not establish AI inference or NVENC readiness.
The detector keeps the inference strategy on CPU until those backends are verified.

Initial PySide6 6.10.1 installed successfully but exhibited a Qt audio renderer stop hang.
PySide6/Qt 6.11.3 passed the transport regression and full 13-test suite with Python 3.14.3.
Final versions are pinned in requirements-lock.txt. Git is now initialized, with no remote.
No system Python, GPU driver or system PATH was replaced.

Phase 4 (2026-11-17): separate `.venv-ai` uses Python 3.14.3, faster-whisper 1.2.1,
CTranslate2 4.9.0 and PyAV 16.0.1, with all dependencies in requirements-ai-lock.txt.
PyAV 19.0.2 failed the actual inference call (`metadata_errors` argument removed); pinning
16.0.1 passed. Both environments pass pip check. NVIDIA query still reports GTX 1660 SUPER,
driver 610.88, 6144 MiB. Actual CUDA float16 inference failed loading `cublas64_12.dll`;
the same job retried and completed on CPU/int8. No system GPU/runtime changes were made.
The tiny.en model was explicitly downloaded locally and real CPU recognition, word/segment
timestamps, native UI transcription and offline mode were tested. Other model sizes are untested.
