import ctypes

from app.utils.hardware import detect_cuda_driver


def test_missing_driver_keeps_cpu(monkeypatch):
    def unavailable(*args):
        raise OSError("Missing driver")

    monkeypatch.setattr(ctypes, "WinDLL", unavailable, raising=False)
    result = detect_cuda_driver()
    assert not result.driver_ready
    assert result.inference_device == "cpu"


def test_driver_initialization_failure_keeps_cpu(monkeypatch):
    class FailedDriver:
        def cuInit(self, flags):
            return 999

    monkeypatch.setattr(ctypes, "WinDLL", lambda name: FailedDriver(), raising=False)
    result = detect_cuda_driver()
    assert not result.driver_ready
    assert result.inference_device == "cpu"
