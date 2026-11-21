# Dependency and distribution inventory

No binary release has been published. This inventory is not a completed redistribution audit.

| Component | License / status | Usage |
| --- | --- | --- |
| Python | PSF license | Local development interpreter |
| PySide6 / Shiboken6 / Qt | LGPLv3/GPLv3 or commercial, module-dependent | Dynamically loaded desktop libraries |
| FFmpeg Gyan essentials 9.0.2 | Build enables GPL and version3 | Local external tools, includes x264/x265 |
| pytest, pytest-qt, Ruff | MIT (verify bundled notices at release) | Development only |
| faster-whisper 1.2.1 | MIT upstream | Isolated optional transcription backend |
| CTranslate2 4.9.0 | MIT upstream | Isolated inference runtime |
| Systran faster-whisper-tiny.en | MIT model card | Local English model, not redistributed |
| PyAV 16.0.1 | BSD package; bundled FFmpeg libraries need separate audit | Local AI audio decoding |
| Rubber Band (inside FFmpeg) | GPL; commercial licensing also available upstream | Phase 6 offline pitch/tempo/formant mode |

FFmpeg was obtained through the Windows-build provider linked from
[FFmpeg downloads](https://ffmpeg.org/download.html), at
[Gyan builds](https://www.gyan.dev/ffmpeg/builds/). Its extracted LICENSE and configuration
are retained under tools. Before redistribution retain notices, establish corresponding-source
availability and review the exact build's obligations. Do not describe this GPL build as LGPL.

[Qt licensing](https://doc.qt.io/qt-6/licensing.html) and
[PySide6 package metadata](https://pypi.org/project/PySide6/) are the upstream starting points.
Phase 8 must audit actual bundled modules, Qt plugin licenses, source/notice requirements,
user replacement/relinking provisions and codec distribution restrictions.
Astra application source is MIT licensed, copyright (c) 2026 sotbom. See ../LICENSE.
Third-party components retain their own licenses; the MIT grant does not relicense them.

Phase 4 model provenance: [Systran tiny.en model card](https://huggingface.co/Systran/faster-whisper-tiny.en),
revision `0d3d19a32d3338f10357c0889762bd8d64bbdeba`. Model download retains its README and
available notices; weights are ignored by Git. Other catalog models are not installed or
redistribution-audited. `requirements-ai-lock.txt` inventories the full optional dependency
closure (including NumPy, ONNX Runtime, tokenizers and Hugging Face libraries). Their actual
wheel notices/native libraries must be audited before packaging; this is a development
installation, not approval to redistribute that dependency set. Primary sources:
[faster-whisper](https://github.com/SYSTRAN/faster-whisper),
[CTranslate2](https://github.com/OpenNMT/CTranslate2), [PyAV](https://github.com/PyAV-Org/PyAV).

Phase 6 uses the existing FFmpeg Rubber Band integration without a new binary download.
[Rubber Band licensing](https://breakfastquay.com/rubberband/) must be included in the eventual
FFmpeg distribution audit. Optional neural voice-conversion models were evaluated but neither
installed nor approved for redistribution; see VOICE_TRANSFORMATION.md for the decision and sources.
