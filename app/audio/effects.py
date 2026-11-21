"""Validated track processing, clip fades and project mastering settings."""

import math
from dataclasses import dataclass

from app.audio.voice import voice_filters


@dataclass(frozen=True)
class AudioSettings:
    gain_db: float = 0.0
    pan: float = 0.0
    denoise: bool = False
    noise_reduction: float = 12.0
    noise_floor: float = -50.0
    eq: bool = False
    highpass: float = 80.0
    lowpass: float = 18000.0
    bass_db: float = 0.0
    mid_db: float = 0.0
    mid_hz: float = 1000.0
    mid_q: float = 1.0
    treble_db: float = 0.0
    compressor: bool = False
    threshold_db: float = -18.0
    ratio: float = 3.0
    attack_ms: float = 20.0
    release_ms: float = 250.0
    makeup_db: float = 0.0
    voice: bool = False
    pitch_semitones: float = 0.0
    tempo: float = 1.0
    preserve_formants: bool = True
    timbre_db: float = 0.0


@dataclass(frozen=True)
class AudioMaster:
    normalize: bool = False
    target_lufs: float = -16.0
    peak_db: float = -1.0


RANGES = {
    "pitch_semitones": (-12, 12),
    "tempo": (0.5, 2),
    "timbre_db": (-6, 6),
    "gain_db": (-60, 24),
    "pan": (-1, 1),
    "noise_reduction": (0.01, 97),
    "noise_floor": (-80, -20),
    "highpass": (20, 2000),
    "lowpass": (2000, 22000),
    "bass_db": (-20, 20),
    "mid_db": (-20, 20),
    "mid_hz": (100, 12000),
    "mid_q": (0.1, 10),
    "treble_db": (-20, 20),
    "threshold_db": (-60, 0),
    "ratio": (1, 20),
    "attack_ms": (0.01, 2000),
    "release_ms": (0.01, 9000),
    "makeup_db": (0, 24),
}


def number(value, low, high):
    if type(value) not in (int, float) or not math.isfinite(value) or not low <= value <= high:
        raise ValueError(f"Audio value must be a finite number between {low} and {high}.")


def validate_audio(settings):
    if not isinstance(settings, AudioSettings):
        raise ValueError("Invalid track audio settings.")
    for key, bounds in RANGES.items():
        number(getattr(settings, key), *bounds)
    for key in ("denoise", "eq", "compressor", "voice", "preserve_formants"):
        if type(getattr(settings, key)) is not bool:
            raise ValueError("Invalid audio bypass toggle.")
    if settings.highpass >= settings.lowpass:
        raise ValueError("High-pass frequency must be below low-pass frequency.")


def validate_master(master):
    if not isinstance(master, AudioMaster) or type(master.normalize) is not bool:
        raise ValueError("Invalid master audio settings.")
    number(master.target_lufs, -36, -5)
    number(master.peak_db, -12, -0.1)


def audio_filters(settings, fade_in_ms, fade_out_ms, duration_ms):
    """Noise reduction → voice → EQ → compression → gain/balance → clip fades."""
    validate_audio(settings)
    filters = []
    if settings.denoise:
        filters.append(f"afftdn=nr={settings.noise_reduction}:nf={settings.noise_floor}:tn=0")
    filters.extend(voice_filters(settings, duration_ms))
    if settings.eq:
        filters.extend(
            [
                f"highpass=f={settings.highpass}",
                f"lowpass=f={settings.lowpass}",
                f"bass=g={settings.bass_db}:f=150",
                f"equalizer=f={settings.mid_hz}:t=q:w={settings.mid_q}:g={settings.mid_db}",
                f"treble=g={settings.treble_db}:f=6000",
            ]
        )
    if settings.compressor:
        threshold = 10 ** (settings.threshold_db / 20)
        makeup = 10 ** (settings.makeup_db / 20)
        filters.append(
            f"acompressor=threshold={threshold}:ratio={settings.ratio}:attack={settings.attack_ms}:release={settings.release_ms}:makeup={makeup}:detection=rms"
        )
    if settings.gain_db:
        filters.append(f"volume={settings.gain_db}dB")
    if settings.pan:
        # Stereo balance: unity at center, attenuate the opposite channel toward either edge.
        left, right = min(1, 1 - settings.pan), min(1, 1 + settings.pan)
        filters.append(f"pan=stereo|c0={left}*c0|c1={right}*c1")
    if fade_in_ms:
        filters.append(f"afade=t=in:st=0:d={min(fade_in_ms, duration_ms) / 1000}")
    if fade_out_ms:
        length = min(fade_out_ms, duration_ms)
        filters.append(f"afade=t=out:st={(duration_ms - length) / 1000}:d={length / 1000}")
    return filters


def master_filters(master):
    validate_master(master)
    if master.normalize:
        return (
            f"loudnorm=I={master.target_lufs}:TP={master.peak_db}:"
            "LRA=11:linear=false,aresample=48000"
        )
    return f"alimiter=limit={10 ** (master.peak_db / 20)}:level=0:latency=1"
