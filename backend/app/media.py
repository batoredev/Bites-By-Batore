"""Bounded local frame extraction. No network protocols are passed to ffmpeg."""

import base64
import re
import subprocess
import tempfile
from pathlib import Path
from .config import settings
from .providers import Unavailable


def frame_points(seconds, maximum, cuts):
    """Preserve clip endpoints and distribute remaining samples over the timeline."""
    end = max(0, seconds - 0.15)
    if maximum <= 1 or end == 0:
        return [0.0]
    selected = [0.0, end]
    candidates = sorted(set([*cuts, *(i * end / (maximum - 1) for i in range(maximum))]))
    candidates = [p for p in candidates if 0 < p < end]
    while candidates and len(selected) < maximum:
        # Farthest-point selection keeps coverage when cuts cluster near the start.
        point = max(candidates, key=lambda p: (min(abs(p - s) for s in selected), p in cuts))
        selected.append(point)
        candidates.remove(point)
    return sorted(selected)


def extract_frames(media, timestamps=None):
    from imageio_ffmpeg import get_ffmpeg_exe

    cfg = settings()
    data = base64.b64decode(media["base64"], validate=True)
    if len(data) > cfg.max_media_mb * 1024 * 1024:
        raise Unavailable("Media exceeds local analysis limit")
    maximum = min(max(cfg.media_max_frames, 1), 24)
    seconds = min(max(cfg.media_max_seconds, 1), 300)
    binary = cfg.ffmpeg_binary or get_ffmpeg_exe()
    results = []
    with tempfile.TemporaryDirectory(prefix="batore-media-") as folder:
        source = Path(folder) / "input.video"
        source.write_bytes(data)
        try:
            probe = subprocess.run(
                [binary, "-hide_banner", "-nostdin", "-protocol_whitelist", "file,pipe", "-i", str(source)],
                capture_output=True,
                timeout=10,
                check=False,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            duration = re.search(rb"Duration: (\d+):(\d+):(\d+\.\d+)", probe.stderr)
            if duration:
                seconds = min(seconds, int(duration[1]) * 3600 + int(duration[2]) * 60 + float(duration[3]))
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise Unavailable("Local media duration inspection failed") from exc
        cuts = []
        if timestamps is None and maximum > 2:
            try:
                scenes = subprocess.run(
                    [
                        binary,
                        "-nostdin",
                        "-threads",
                        "1",
                        "-protocol_whitelist",
                        "file,pipe",
                        "-i",
                        str(source),
                        "-t",
                        str(seconds),
                        "-vf",
                        "scale=320:-2,select=gt(scene\\,0.28),showinfo",
                        "-an",
                        "-f",
                        "null",
                        "-",
                    ],
                    capture_output=True,
                    timeout=30,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
                if scenes.returncode == 0:
                    cuts = [
                        float(x)
                        for x in re.findall(rb"pts_time:([\d.]+)", scenes.stderr)
                        if 0 < float(x) < seconds
                    ]
            except (OSError, subprocess.TimeoutExpired):
                pass  # Evenly spaced frames remain available if scene detection fails.
        points = timestamps if timestamps is not None else frame_points(seconds, maximum, cuts)
        for index, second in enumerate(points[:maximum]):
            second = float(second)
            if not 0 <= second < seconds:
                continue
            target = Path(folder) / f"frame-{index}.jpg"
            command = [
                binary,
                "-hide_banner",
                "-loglevel",
                "error",
                "-nostdin",
                "-threads",
                "1",
                "-protocol_whitelist",
                "file,pipe",
                "-ss",
                str(second),
                "-i",
                str(source),
                "-frames:v",
                "1",
                "-vf",
                "scale=768:768:force_original_aspect_ratio=decrease",
                "-q:v",
                "4",
                "-y",
                str(target),
            ]
            try:
                result = subprocess.run(
                    command,
                    capture_output=True,
                    timeout=10,
                    check=False,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
            except (OSError, subprocess.TimeoutExpired) as exc:
                raise Unavailable("Local video frame extraction failed or timed out") from exc
            if result.returncode:
                raise Unavailable("The uploaded video could not be decoded")
            if target.exists() and target.stat().st_size:
                results.append(
                    {
                        "seconds": second,
                        "mime": "image/jpeg",
                        "base64": base64.b64encode(target.read_bytes()).decode("ascii"),
                    }
                )
            elif not timestamps:
                break
    return results
