# Offline transcription models

Models are optional, not committed or bundled. Use **Subtitles → Edit / transcribe subtitles**
and **Download selected model** to fetch a catalog model explicitly. Normal transcription
uses local files only. Downloads can be cancelled; an installation marker is written only
after completion. Download progress is indeterminate; inference progress follows decoded segments.

This checkout verified `tiny.en` from `Systran/faster-whisper-tiny.en` at revision
`0d3d19a32d3338f10357c0889762bd8d64bbdeba` (MIT model card). The exact revision is stored
in each model's `astra-model.json`. Other model sizes are selectable but have not been
downloaded or accuracy/performance qualified here. `tiny.en` recognizes English only.

The catalog offers tiny, base, small, medium and large-v3 multilingual conversions as well.
Models consume roughly 75 MB to 3 GB. Downloads go to this directory by default;
`ASTRA_MODELS_DIR` can select another location. Retain model cards/notices and recheck
redistribution obligations before any binary release. No model weights are currently distributed.

References: [tiny.en model card](https://huggingface.co/Systran/faster-whisper-tiny.en),
[faster-whisper](https://github.com/SYSTRAN/faster-whisper).
