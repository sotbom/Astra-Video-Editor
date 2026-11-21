"""Validated subtitle records, reversible editing and plain-text interchange."""

import re
from dataclasses import dataclass, replace
from uuid import uuid4


@dataclass(frozen=True)
class Subtitle:
    id: str
    start_ms: int
    end_ms: int
    text: str


@dataclass(frozen=True)
class SubtitleStyle:
    font: str = "Arial"
    size: int = 48
    color: str = "#FFFFFF"
    outline: int = 2
    bottom_margin: int = 40


def validate_subtitles(segments, style):
    if len(segments) > 10000 or len({s.id for s in segments}) != len(segments):
        raise ValueError("Too many or duplicate subtitle segments.")
    for s in segments:
        if not isinstance(s.id, str) or not 1 <= len(s.id) <= 100:
            raise ValueError("Invalid subtitle identifier.")
        if (
            type(s.start_ms) is not int
            or type(s.end_ms) is not int
            or not 0 <= s.start_ms < s.end_ms <= 604800000
        ):
            raise ValueError("Subtitle times must be integer milliseconds with end after start.")
        if (
            not isinstance(s.text, str)
            or not s.text.strip()
            or len(s.text) > 4000
            or "\x00" in s.text
        ):
            raise ValueError("Subtitle text must contain 1–4000 characters.")
    if not isinstance(style, SubtitleStyle) or not re.fullmatch(r"[\w .-]{1,80}", style.font):
        raise ValueError("Invalid subtitle font.")
    if not re.fullmatch(r"#[0-9A-Fa-f]{6}", style.color):
        raise ValueError("Subtitle color must be #RRGGBB.")
    for value, low, high in (
        (style.size, 8, 200),
        (style.outline, 0, 10),
        (style.bottom_margin, 0, 500),
    ):
        if type(value) is not int or not low <= value <= high:
            raise ValueError("Subtitle style is out of range.")


def timestamp(ms, separator=","):
    hours, remainder = divmod(ms, 3600000)
    minutes, remainder = divmod(remainder, 60000)
    seconds, milliseconds = divmod(remainder, 1000)
    return f"{hours:02}:{minutes:02}:{seconds:02}{separator}{milliseconds:03}"


def export_text(segments, kind, style=SubtitleStyle(), width=1920, height=1080):
    validate_subtitles(segments, style)
    ordered = sorted(segments, key=lambda s: (s.start_ms, s.end_ms))
    if kind in ("srt", "vtt"):
        separator = "," if kind == "srt" else "."
        header = "WEBVTT\n\n" if kind == "vtt" else ""
        return (
            header
            + "\n\n".join(
                f"{i}\n{timestamp(s.start_ms, separator)} --> "
                f"{timestamp(s.end_ms, separator)}\n{s.text}"
                for i, s in enumerate(ordered, 1)
            )
            + "\n"
        )
    if kind != "ass":
        raise ValueError("Choose SRT, VTT or ASS.")
    color = "&H00" + style.color[5:7] + style.color[3:5] + style.color[1:3]
    header = (
        f"[Script Info]\nScriptType: v4.00+\nPlayResX: {width}\nPlayResY: {height}\n"
        "WrapStyle: 0\n\n[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, "
        "SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, "
        "ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, "
        "MarginL, MarginR, MarginV, Encoding\n"
        f"Style: Default,{style.font},{style.size},{color},{color},&H00000000,&H80000000,"
        f"0,0,0,0,100,100,0,0,1,{style.outline},0,2,20,20,{style.bottom_margin},1\n\n"
        "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, "
        "MarginV, Effect, Text\n"
    )

    def ass_time(ms):
        return timestamp(ms, ".")[:-1]

    lines = []
    for s in ordered:
        # Literal text cannot inject ASS override commands.
        text = (
            s.text.replace("\\", "＼")
            .replace("{", "｛")
            .replace("}", "｝")
            .replace("\r", "")
            .replace("\n", r"\N")
        )
        lines.append(
            f"Dialogue: 0,{ass_time(s.start_ms)},{ass_time(s.end_ms)},Default,,0,0,0,,{text}"
        )
    return header + "\n".join(lines) + "\n"


def parse_text(text, kind):
    if len(text) > 8 * 1024 * 1024:
        raise ValueError("Subtitle file exceeds 8 MiB.")
    if kind not in ("srt", "vtt"):
        raise ValueError("Import supports SRT and VTT.")
    pattern = re.compile(r"(\d{1,3}):(\d{2}):(\d{2})[,.](\d{3})")

    def milliseconds(value):
        match = pattern.fullmatch(value.strip())
        if not match:
            raise ValueError("Expected HH:MM:SS.mmm subtitle timestamps.")
        h, m, s, ms = map(int, match.groups())
        if m >= 60 or s >= 60:
            raise ValueError("Invalid subtitle timestamp.")
        return ((h * 60 + m) * 60 + s) * 1000 + ms

    result = []
    for block in re.split(r"\n\s*\n", text.lstrip("\ufeff").replace("\r\n", "\n").strip()):
        lines = block.splitlines()
        if lines and (lines[0] == "WEBVTT" or lines[0].startswith("NOTE")):
            continue
        timing = next((i for i, line in enumerate(lines) if "-->" in line), None)
        if timing is None:
            raise ValueError("Subtitle cue is missing its timing line.")
        start, end = lines[timing].split("-->", 1)
        result.append(
            Subtitle(
                uuid4().hex, milliseconds(start), milliseconds(end), "\n".join(lines[timing + 1 :])
            )
        )
    validate_subtitles(result, SubtitleStyle())
    return tuple(result)


class SubtitleEngine:
    def __init__(self, session):
        self.session = session

    def update(self, segments, label="Edit subtitles", **changes):
        self.session.execute(
            label, replace(self.session.project, subtitles=tuple(segments), **changes)
        )

    def add(self, start, end, text):
        segment = Subtitle(uuid4().hex, start, end, text)
        self.update((*self.session.project.subtitles, segment), "Add subtitle")
        return segment.id

    def edit(self, identifier, start, end, text):
        self.update(
            [
                replace(s, start_ms=start, end_ms=end, text=text) if s.id == identifier else s
                for s in self.session.project.subtitles
            ]
        )

    def delete(self, identifier):
        self.update(
            [s for s in self.session.project.subtitles if s.id != identifier], "Delete subtitle"
        )

    def split(self, identifier, at):
        segments = list(self.session.project.subtitles)
        index = next(i for i, s in enumerate(segments) if s.id == identifier)
        segment = segments[index]
        if not segment.start_ms < at < segment.end_ms:
            raise ValueError("Place the playhead inside the selected subtitle.")
        segments[index : index + 1] = [
            replace(segment, end_ms=at),
            replace(segment, id=uuid4().hex, start_ms=at),
        ]
        self.update(segments, "Split subtitle")

    def merge(self, identifier):
        segments = sorted(self.session.project.subtitles, key=lambda s: s.start_ms)
        index = next(i for i, s in enumerate(segments) if s.id == identifier)
        if index + 1 == len(segments):
            raise ValueError("There is no following subtitle to merge.")
        left, right = segments[index : index + 2]
        segments[index : index + 2] = [
            replace(left, end_ms=max(left.end_ms, right.end_ms), text=left.text + " " + right.text)
        ]
        self.update(segments, "Merge subtitles")
