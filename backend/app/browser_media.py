"""Download and join public video/audio tracks identified in one reel's page data."""

import base64
import subprocess
import tempfile
from pathlib import Path
import httpx
from .config import settings
from .providers import Unavailable, quota
from .social import allowed_media_url


from .performance import measured


@measured("audio_download")
def download_audio(db, url):
    quota(db)
    maximum = min(settings().max_media_mb, 8) * 1024 * 1024
    try:
        with httpx.Client(timeout=25, trust_env=False, follow_redirects=False) as client:
            with client.stream("GET", allowed_media_url(url)) as response:
                if response.status_code != 200:
                    raise Unavailable("The public audio track could not be downloaded")
                data = bytearray()
                for chunk in response.iter_bytes():
                    data.extend(chunk)
                    if len(data) > maximum:
                        raise Unavailable("Public audio track exceeds the download limit")
        if len(data) < 12 or data[4:8] != b"ftyp":
            raise Unavailable("The public audio response was not a complete MP4 audio track")
        return bytes(data)
    except httpx.HTTPError as exc:
        raise Unavailable("Public audio download failed or timed out") from exc


@measured("audio_video_join")
def join_tracks(media, audio):
    from imageio_ffmpeg import get_ffmpeg_exe

    maximum = settings().max_media_mb * 1024 * 1024
    video = base64.b64decode(media["base64"], validate=True)
    if len(video) + len(audio) > maximum:
        raise Unavailable("Combined reel exceeds the local media size limit")
    with tempfile.TemporaryDirectory(prefix="batore-tracks-") as folder:
        source, sound, target = [Path(folder) / name for name in ("video.mp4", "audio.mp4", "joined.mp4")]
        source.write_bytes(video)
        sound.write_bytes(audio)
        try:
            result = subprocess.run(
                [
                    settings().ffmpeg_binary or get_ffmpeg_exe(),
                    "-nostdin",
                    "-loglevel",
                    "error",
                    "-protocol_whitelist",
                    "file,pipe",
                    "-i",
                    str(source),
                    "-protocol_whitelist",
                    "file,pipe",
                    "-i",
                    str(sound),
                    "-map",
                    "0:v:0",
                    "-map",
                    "1:a:0",
                    "-c",
                    "copy",
                    "-shortest",
                    "-movflags",
                    "+faststart",
                    "-y",
                    str(target),
                ],
                capture_output=True,
                timeout=25,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            if result.returncode or not target.exists():
                raise Unavailable("Public video/audio tracks could not be combined")
            if target.stat().st_size > maximum:
                raise Unavailable("Combined reel exceeds the local media size limit")
            return {"mime": "video/mp4", "base64": base64.b64encode(target.read_bytes()).decode("ascii")}
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise Unavailable("Local audio/video combination failed") from exc
