"""Typed effect settings and trusted FFmpeg filter construction."""

import math
from dataclasses import dataclass, field

from app.video.masks import Mask, validate_mask


@dataclass(frozen=True)
class VideoEffects:
    crop_left: int = 0
    crop_top: int = 0
    crop_right: int = 0
    crop_bottom: int = 0
    brightness: float = 0.0
    contrast: float = 1.0
    saturation: float = 1.0
    negative: bool = False
    grayscale: bool = False
    thermal: bool = False
    blur: float = 0.0
    sepia: bool = False
    mirror: bool = False
    pixelation: int = 0
    sharpen: float = 0.0
    vignette: float = 0.0
    mask: Mask = field(default_factory=Mask)


def validate_effects(effects: VideoEffects, width: int, height: int) -> None:
    if not isinstance(effects, VideoEffects):
        raise ValueError("Invalid video effects.")
    validate_mask(effects.mask)
    if type(effects.pixelation) is not int or not 0 <= effects.pixelation <= 64:
        raise ValueError("Pixelation must be an integer between 0 and 64.")
    for value in (effects.crop_left, effects.crop_top, effects.crop_right, effects.crop_bottom):
        if type(value) is not int or value < 0:
            raise ValueError("Crop margins must be nonnegative integer pixels.")
    if (
        effects.crop_left + effects.crop_right >= width
        or effects.crop_top + effects.crop_bottom >= height
    ):
        raise ValueError("Crop must leave at least one pixel in each dimension.")
    for key, low, high in (
        ("brightness", -1, 1),
        ("contrast", 0, 3),
        ("saturation", 0, 3),
        ("blur", 0, 20),
        ("sharpen", 0, 3),
        ("vignette", 0, 1),
    ):
        value = getattr(effects, key)
        if type(value) not in (int, float) or not math.isfinite(value) or not low <= value <= high:
            raise ValueError(f"{key.title()} must be between {low} and {high}.")
    if any(
        type(getattr(effects, key)) is not bool
        for key in ("negative", "grayscale", "thermal", "sepia", "mirror")
    ):
        raise ValueError("Invalid effect toggle.")


def video_filters(effects: VideoEffects, width: int, height: int) -> list[str]:
    """Crop, adjust color, stylize, then blur. No user filter expressions are accepted."""
    validate_effects(effects, width, height)
    result = []
    if any((effects.crop_left, effects.crop_top, effects.crop_right, effects.crop_bottom)):
        result.append(
            f"crop={width - effects.crop_left - effects.crop_right}:"
            f"{height - effects.crop_top - effects.crop_bottom}:"
            f"{effects.crop_left}:{effects.crop_top}:exact=1"
        )
    if (effects.brightness, effects.contrast, effects.saturation) != (0, 1, 1):
        result.append(
            f"eq=brightness={effects.brightness}:contrast={effects.contrast}:saturation={effects.saturation}"
        )
    if effects.negative:
        result.append("negate")
    if effects.grayscale or effects.thermal:
        result.append("hue=s=0")
    if effects.thermal:
        # False-color luminance palette, not a temperature measurement.
        result.extend(
            [
                "format=rgb24",
                "lutrgb=r='clip(3*val-255,0,255)':g='clip(255-abs(3*val-382),0,255)':b='clip(255-3*val,0,255)'",
            ]
        )
    if effects.blur:
        result.append(f"gblur=sigma={effects.blur}")
    if effects.sepia:
        result.append("colorchannelmixer=.393:.769:.189:0:.349:.686:.168:0:.272:.534:.131")
    if effects.pixelation:
        result.append(f"pixelize=w={max(2, effects.pixelation)}:h={max(2, effects.pixelation)}")
    if effects.sharpen:
        result.append(f"unsharp=5:5:{effects.sharpen}:5:5:0")
    if effects.vignette:
        result.append(f"vignette=angle={effects.vignette * math.pi / 3}")
    if effects.mirror:
        result.append("hflip")
    return result
