"""Subprocess entry point: optional AI packages never import into the editor process."""

import json
import os
import sys
import time
from pathlib import Path


def write_json(path, value):
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
    # Windows readers can briefly hold the destination without delete sharing.
    for attempt in range(20):
        try:
            os.replace(temp, path)
            break
        except PermissionError:
            if attempt == 19:
                raise
            time.sleep(0.01)


def execute(request, status):
    from app.ai.model_manager import MODELS, installed, model_path

    def report(percent, message):
        write_json(status, {"progress": percent, "message": message})

    name = request["model"]
    target = model_path(name)
    if request["task"] == "download":
        from huggingface_hub import HfApi, snapshot_download

        repo = MODELS[name][0]
        report(-1, "Downloading model from Hugging Face…")
        revision = HfApi().model_info(repo).sha
        snapshot_download(
            repo,
            revision=revision,
            local_dir=str(target),
            allow_patterns=["*.json", "*.txt", "model.bin", "README.md", "LICENSE*"],
            max_workers=2,
        )
        write_json(
            target / "astra-model.json",
            {"repository": repo, "revision": revision, "license": "MIT", "model": name},
        )
        report(100, "Model downloaded")
        return {"model": name, "revision": revision}
    if not installed(name):
        raise ValueError("Model is missing or incomplete. Download it explicitly in Model Manager.")
    # Runtime inference must never fetch weights/tokenizers or send media over the network.
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    import ctranslate2
    from faster_whisper import WhisperModel

    device, compute = request.get("device", "cpu"), request.get("compute", "int8")
    if device not in ("cpu", "cuda"):
        raise ValueError("Unknown inference device.")
    report(0, f"Initializing {device} model…")
    supported = ctranslate2.get_supported_compute_types(device)
    if compute not in supported:
        raise ValueError(f"{compute} is not supported on {device}; available: {sorted(supported)}")
    model = WhisperModel(
        str(target),
        device=device,
        compute_type=compute,
        cpu_threads=4,
        num_workers=1,
        local_files_only=True,
    )
    segments, info = model.transcribe(
        request["audio"],
        language=request.get("language") or None,
        beam_size=5,
        word_timestamps=True,
        vad_filter=False,
    )
    result = []
    words = []
    for segment in segments:
        text = segment.text.strip()
        if text:
            result.append(
                {
                    "start_ms": round(segment.start * 1000),
                    "end_ms": round(segment.end * 1000),
                    "text": text,
                }
            )
            words.extend(
                {"start_ms": round(w.start * 1000), "end_ms": round(w.end * 1000), "text": w.word}
                for w in segment.words or []
            )
        report(
            min(99, round(segment.end / max(info.duration, 0.01) * 100)), "Transcribing locally…"
        )
    report(100, "Transcription complete")
    return {
        "segments": result,
        "words": words,
        "language": info.language,
        "device": device,
        "compute": compute,
        "model": name,
        "duration": info.duration,
    }


if __name__ == "__main__":
    request_path, result_path, status_path = map(Path, sys.argv[1:4])
    try:
        write_json(
            result_path,
            {"result": execute(json.loads(request_path.read_text(encoding="utf-8")), status_path)},
        )
    except Exception as exc:
        write_json(result_path, {"error": f"{type(exc).__name__}: {exc}"})
        sys.exit(1)
