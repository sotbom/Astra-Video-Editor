"""Explicit model catalog and local installation checks; no implicit network activity."""

import os
from pathlib import Path

from app.utils.paths import ROOT

MODELS = {
    "tiny.en": ("Systran/faster-whisper-tiny.en", "English • about 75 MB"),
    "tiny": ("Systran/faster-whisper-tiny", "Multilingual • about 75 MB"),
    "base": ("Systran/faster-whisper-base", "Multilingual • about 145 MB"),
    "small": ("Systran/faster-whisper-small", "Multilingual • about 485 MB"),
    "medium": ("Systran/faster-whisper-medium", "Multilingual • about 1.5 GB"),
    "large-v3": ("Systran/faster-whisper-large-v3", "Multilingual • about 3 GB"),
}


def model_root():
    return Path(os.environ.get("ASTRA_MODELS_DIR", ROOT / "models"))


def model_path(name):
    if name not in MODELS:
        raise ValueError("Unknown model.")
    return model_root() / name


def installed(name):
    path = model_path(name)
    return all(
        (path / file).is_file()
        for file in ("model.bin", "config.json", "tokenizer.json", "astra-model.json")
    )


def ai_python():
    path = Path(os.environ.get("ASTRA_AI_PYTHON", ROOT / ".venv-ai/Scripts/python.exe"))
    if not path.is_file():
        raise FileNotFoundError("AI environment missing. Run scripts/setup_ai.ps1 first.")
    return path
