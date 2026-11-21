"""Validated static masks, shared by the canvas and FFmpeg raster input."""

import math
from dataclasses import dataclass

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QImage, QPainter, QPainterPath


@dataclass(frozen=True)
class Mask:
    shape: str = "none"
    x: float = 0.25
    y: float = 0.25
    width: float = 0.5
    height: float = 0.5
    points: tuple[tuple[float, float], ...] = ()
    inverted: bool = False
    feather: float = 0.0
    blur: float = 12.0
    strength: float = 1.0


def validate_mask(mask: Mask) -> None:
    if not isinstance(mask, Mask) or mask.shape not in (
        "none",
        "rectangle",
        "ellipse",
        "polygon",
        "freehand",
    ):
        raise ValueError("Invalid mask shape.")
    for name, low, high in (
        ("x", 0, 1),
        ("y", 0, 1),
        ("width", 0.001, 1),
        ("height", 0.001, 1),
        ("feather", 0, 40),
        ("blur", 0.1, 40),
        ("strength", 0, 1),
    ):
        value = getattr(mask, name)
        if type(value) not in (int, float) or not math.isfinite(value) or not low <= value <= high:
            raise ValueError(f"Mask {name} must be between {low} and {high}.")
    if mask.x + mask.width > 1.000001 or mask.y + mask.height > 1.000001:
        raise ValueError("Mask bounds must stay inside the canvas.")
    if type(mask.inverted) is not bool or type(mask.points) is not tuple or len(mask.points) > 256:
        raise ValueError("Invalid mask points or inversion.")
    for point in mask.points:
        if (
            type(point) is not tuple
            or len(point) != 2
            or any(
                type(v) not in (int, float) or not math.isfinite(v) or not 0 <= v <= 1
                for v in point
            )
        ):
            raise ValueError("Mask points must be normalized coordinate pairs.")
    if mask.shape in ("polygon", "freehand"):
        if len(mask.points) < 3:
            raise ValueError("Draw at least three mask points.")
        xs, ys = zip(*mask.points)
        if max(xs) - min(xs) < 0.001 or max(ys) - min(ys) < 0.001:
            raise ValueError("Mask must cover a two-dimensional area.")


def mask_path(mask: Mask, width: float, height: float) -> QPainterPath:
    """Map the shape to the output canvas, after crop/resize/padding."""
    path = QPainterPath()
    rect = QRectF(mask.x * width, mask.y * height, mask.width * width, mask.height * height)
    if mask.shape == "rectangle":
        path.addRect(rect)
    elif mask.shape == "ellipse":
        path.addEllipse(rect)
    elif mask.shape in ("polygon", "freehand") and mask.points:
        path.moveTo(QPointF(mask.points[0][0] * width, mask.points[0][1] * height))
        for x, y in mask.points[1:]:
            path.lineTo(x * width, y * height)
        path.closeSubpath()
    return path


def write_mask(mask: Mask, width: int, height: int, path) -> None:
    """Rasterize without a GUI application; FFmpeg applies feathering at output scale."""
    validate_mask(mask)
    image = QImage(width, height, QImage.Format.Format_RGB32)
    image.fill(Qt.GlobalColor.white if mask.inverted else Qt.GlobalColor.black)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.fillPath(mask_path(mask, width, height), QColor("black" if mask.inverted else "white"))
    painter.end()
    if not image.save(str(path), "PNG"):
        raise OSError("Could not write temporary mask image.")


def decode_mask(data: dict) -> Mask:
    values = dict(data)
    values["points"] = tuple(tuple(p) for p in values.get("points", ()))
    mask = Mask(**values)
    validate_mask(mask)
    return mask
