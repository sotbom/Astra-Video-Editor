"""Build an explicit offline graph from an immutable timeline snapshot."""

from dataclasses import dataclass
from pathlib import Path

from app.audio.effects import audio_filters, master_filters
from app.audio.voice import require_rubberband
from app.core.project_schema import Project, validate
from app.core.subtitles import export_text
from app.utils.paths import find_tool
from app.video.filters import video_filters
from app.video.masks import write_mask


@dataclass(frozen=True)
class ExportSettings:
    width: int = 1920
    height: int = 1080
    crf: int = 20
    burn_subtitles: bool = False
    audio_only: bool = False

    def validate(self):
        if type(self.burn_subtitles) is not bool:
            raise ValueError("Invalid subtitle export option.")
        if type(self.audio_only) is not bool:
            raise ValueError("Invalid audio export option.")
        for value in (self.width, self.height):
            if type(value) is not int or not 16 <= value <= 3840 or value % 2:
                raise ValueError("Output dimensions must be even integers from 16 to 3840.")
        if type(self.crf) is not int or not 0 <= self.crf <= 40:
            raise ValueError("Quality CRF must be between 0 and 40.")


def seconds(project: Project, frames: int) -> str:
    return f"{frames * project.fps_den / project.fps_num:.12f}"


def build_command(
    project: Project, settings: ExportSettings, output: Path, graph_path: Path, progress_path: Path
) -> list[str]:
    """Use a graph file to avoid Windows command-length limits; paths are separate argv."""
    validate(project)
    settings.validate()
    if any(
        not t.muted
        and t.audio.voice
        and (t.audio.pitch_semitones or t.audio.tempo != 1)
        and any(
            c.track_id == t.id and project.media_by_id(c.media_id).info.audio_codec
            for c in project.clips
        )
        for t in project.tracks
    ):
        require_rubberband()
    if not project.end:
        raise ValueError("Add at least one timeline clip before exporting.")
    rate = f"{project.fps_num}/{project.fps_den}"
    duration = seconds(project, project.end)
    cmd = [
        find_tool("ffmpeg"),
        "-hide_banner",
        "-nostdin",
        "-y",
        "-loglevel",
        "error",
        "-filter_complex_threads",
        "1",
    ]
    graph = [
        f"color=c=black:s={settings.width}x{settings.height}:r={rate},trim=end_frame={project.end},setpts=PTS-STARTPTS[base]"
    ]
    if settings.audio_only:
        graph.clear()
    graph.append(f"anullsrc=r=48000:cl=stereo,atrim=duration={duration}[silence]")
    video, audio = [], ["[silence]"]
    # Bottom tracks first: first visible track in the editor must win.
    for track in reversed(project.tracks):
        for clip in sorted(
            (c for c in project.clips if c.track_id == track.id), key=lambda c: c.start
        ):
            info = project.media_by_id(clip.media_id).info
            use_video = track.kind == "video" and not track.hidden and not settings.audio_only
            use_audio = bool(info.audio_codec) and not track.muted
            if not use_video and not use_audio:
                continue
            if not info.path.is_file():
                raise ValueError(f"Missing source: {info.path.name}. Relink before exporting.")
            index = sum(arg == "-i" for arg in cmd)
            cmd += ["-threads", "2", "-protocol_whitelist", "file,pipe"]
            if info.is_image:
                cmd += ["-loop", "1", "-framerate", rate]
            cmd += ["-i", str(info.path)]
            if use_video:
                filters = [
                    "setpts=PTS-STARTPTS",
                    f"fps={rate}",
                    f"trim=start_frame={0 if info.is_image else clip.source_in}:"
                    f"end_frame={clip.duration if info.is_image else clip.source_out}",
                    "setpts=PTS-STARTPTS",
                ]
                filters += video_filters(clip.effects, info.width, info.height)
                filters += [
                    f"scale={settings.width}:{settings.height}:force_original_aspect_ratio=decrease:force_divisible_by=2",
                    f"pad={settings.width}:{settings.height}:(ow-iw)/2:(oh-ih)/2:black",
                    "setsar=1",
                    "format=yuv420p",
                    f"setpts=PTS+{clip.start}*{project.fps_den}/{project.fps_num}/TB",
                ]
                label = f"v{index}"
                graph.append(f"[{index}:v:0]" + ",".join(filters) + f"[{label}]")
                mask = clip.effects.mask
                if mask.shape != "none" and mask.strength:
                    mask_path = graph_path.parent / f"mask-{index}.png"
                    write_mask(mask, settings.width, settings.height, mask_path)
                    mask_index = sum(arg == "-i" for arg in cmd)
                    cmd += ["-loop", "1", "-framerate", rate, "-i", str(mask_path)]
                    # Match all three planes: grayscale RGB raster has equal R/G/B coverage.
                    graph.append(f"[{label}]format=gbrp,split=2[clean{index}][soft{index}]")
                    scale = settings.width / project.width
                    graph.append(
                        f"[soft{index}]gblur=sigma={max(0.01, mask.blur * scale)}[blur{index}]"
                    )
                    feather = (
                        f",gblur=sigma={max(0.01, mask.feather * scale)}" if mask.feather else ""
                    )
                    graph.append(
                        f"[{mask_index}:v:0]format=gbrp{feather},"
                        f"lutrgb=r='val*{mask.strength}':g='val*{mask.strength}':b='val*{mask.strength}'[mask{index}]"
                    )
                    graph.append(
                        f"[clean{index}][blur{index}][mask{index}]maskedmerge[masked{index}]"
                    )
                    label = f"masked{index}"
                video.append((label, clip))
            if use_audio:
                start_sample = round(clip.source_in * 48000 * project.fps_den / project.fps_num)
                count = round(clip.duration * 48000 * project.fps_den / project.fps_num)
                delay = round(clip.start * 48000 * project.fps_den / project.fps_num)
                processing = audio_filters(
                    track.audio,
                    clip.fade_in_ms,
                    clip.fade_out_ms,
                    project.milliseconds(clip.duration),
                )
                processing = (",".join(processing) + ",") if processing else ""
                graph.append(
                    f"[{index}:a:0]aresample=48000,asetpts=PTS-STARTPTS,"
                    f"atrim=start_sample={start_sample}:end_sample={start_sample + count},"
                    "asetpts=PTS-STARTPTS,aformat=channel_layouts=stereo,"
                    f"{processing}adelay={delay}S:all=1[a{index}]"
                )
                audio.append(f"[a{index}]")
    last = "base"
    for number, (label, clip) in enumerate(video):
        target = f"layer{number}"
        graph.append(
            f"[{last}][{label}]overlay=eof_action=pass:repeatlast=0:"
            f"enable='gte(t,{seconds(project, clip.start)})*"
            f"lt(t,{seconds(project, clip.end)})'[{target}]"
        )
        last = target
    subtitle_filter = ""
    if settings.burn_subtitles and project.subtitles and not settings.audio_only:
        subtitle_path = graph_path.parent / "subtitles.ass"
        subtitle_path.write_text(
            export_text(
                project.subtitles, "ass", project.subtitle_style, project.width, project.height
            ),
            encoding="utf-8",
        )
        # Quote the private generated filename for FFmpeg's filter parser.
        escaped = str(subtitle_path).replace("\\", "/").replace(":", r"\:").replace("'", r"'\''")
        subtitle_filter = f",ass=filename='{escaped}'"
    if not settings.audio_only:
        graph.append(
            f"[{last}]trim=end_frame={project.end},setpts=PTS-STARTPTS{subtitle_filter}[vout]"
        )
    graph.append(
        "".join(audio) + f"amix=inputs={len(audio)}:normalize=0:duration=first,"
        f"{master_filters(project.audio_master)},atrim=duration={duration}[aout]"
    )
    graph_path.write_text(";\n".join(graph), encoding="utf-8")
    if settings.audio_only:
        return cmd + [
            "-/filter_complex",
            str(graph_path),
            "-map",
            "[aout]",
            "-c:a",
            "pcm_s24le",
            "-ar",
            "48000",
            "-t",
            duration,
            "-progress",
            str(progress_path),
            "-nostats",
            str(output),
        ]
    cmd += [
        "-/filter_complex",
        str(graph_path),
        "-map",
        "[vout]",
        "-map",
        "[aout]",
        "-c:v",
        "libx264",
        "-threads",
        "2",
        "-preset",
        "fast",
        "-crf",
        str(settings.crf),
        "-pix_fmt",
        "yuv420p",
        "-r",
        rate,
        "-frames:v",
        str(project.end),
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-t",
        duration,
        "-movflags",
        "+faststart",
        "-progress",
        str(progress_path),
        "-nostats",
        str(output),
    ]
    return cmd
