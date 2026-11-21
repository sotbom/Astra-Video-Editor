"""Driver capability inspection; never equate this with AI backend readiness."""

import ctypes
import os
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class CudaCapability:
    driver_ready: bool
    devices: int
    compute_capability: tuple[int, int] | None
    inference_device: str = "cpu"
    reason: str = "AI runtime and model inference have not been verified."


def detect_cuda_driver() -> CudaCapability:
    """Initialize only the installed driver; retain CPU as the inference default."""
    if os.name != "nt":
        return CudaCapability(False, 0, None, reason="Windows CUDA detection is unavailable.")
    try:
        driver = ctypes.WinDLL("nvcuda.dll")
        count = ctypes.c_int()
        major, minor = ctypes.c_int(), ctypes.c_int()
        if driver.cuInit(0) != 0 or driver.cuDeviceGetCount(ctypes.byref(count)) != 0:
            return CudaCapability(False, 0, None, reason="CUDA driver initialization failed.")
        if count.value < 1:
            return CudaCapability(False, 0, None, reason="No CUDA device is available.")
        status = driver.cuDeviceComputeCapability(ctypes.byref(major), ctypes.byref(minor), 0)
        capability = (major.value, minor.value) if status == 0 else None
        return CudaCapability(True, count.value, capability)
    except (OSError, AttributeError):
        return CudaCapability(False, 0, None, reason="CUDA driver library is unavailable.")


if __name__ == "__main__":
    import json

    print(json.dumps(asdict(detect_cuda_driver()), indent=2))
