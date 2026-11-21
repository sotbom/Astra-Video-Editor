"""Real optional model integration. No downloaded/user speech is needed."""

from threading import Event

import pytest

from app.ai.model_manager import installed
from app.ai.transcription import AICancelled, run_ai
from app.utils.paths import ROOT

SPEECH = ROOT / "tests/fixtures/generated/speech.wav"


@pytest.fixture
def speech_request():
    if not installed("tiny.en") or not SPEECH.exists():
        pytest.skip(
            "Install tiny.en and run scripts/generate_speech.ps1 for optional real AI tests"
        )
    return {
        "task": "transcribe",
        "model": "tiny.en",
        "device": "cpu",
        "compute": "int8",
        "language": "en",
        "source": str(SPEECH),
        "start_ms": 0,
        "duration_ms": 12000,
    }


def test_real_cpu_transcription_and_timestamps(speech_request, monkeypatch):
    monkeypatch.setenv("HF_HUB_OFFLINE", "1")
    result = run_ai(speech_request)
    text = " ".join(s["text"] for s in result["segments"]).lower()
    assert "video editor" in text and "speech recognition" in text
    assert result["device"] == "cpu" and result["language"] == "en"
    assert result["words"]
    assert all(0 <= s["start_ms"] < s["end_ms"] <= 12000 for s in result["segments"])


def test_failed_cuda_compute_really_falls_back_to_cpu(speech_request):
    result = run_ai({**speech_request, "device": "cuda", "compute": "unsupported-test-type"})
    assert result["device"] == "cpu" and result["fallback"]
    assert "video editor" in " ".join(s["text"] for s in result["segments"]).lower()


def test_real_job_cancellation(speech_request):
    cancel = Event()

    def progress(percent, message):
        if "Initializing" in message:
            cancel.set()

    with pytest.raises(AICancelled):
        run_ai(speech_request, cancel, progress)


def test_missing_model_gives_local_error(speech_request, tmp_path, monkeypatch):
    monkeypatch.setenv("ASTRA_MODELS_DIR", str(tmp_path))
    with pytest.raises(RuntimeError, match="missing or incomplete"):
        run_ai(speech_request)
