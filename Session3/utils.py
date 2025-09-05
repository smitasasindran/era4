import os
import re
import subprocess


def ensure_dir(path: str):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)

YOUTUBE_ID_RE = re.compile(r"(?:(?:v=|be/|shorts/))([\w-]{11})")

def extract_video_id(url: str) -> str:
    m = YOUTUBE_ID_RE.search(url)
    if m:
        return m.group(1)
    tail = url.strip().split("?")[0].rstrip("/").split("/")[-1]
    if re.fullmatch(r"[\w-]{11}", tail):
        return tail
    raise ValueError(f"Could not parse a YouTube video ID from URL: {url}")


def ffmpeg_screenshot(input_source: str, ts_seconds: float, out_path: str) -> None:
    """
    Capture a single frame at ts_seconds from either a local file path
    or a remote media URL (e.g. from yt-dlp -g).
    """
    ensure_dir(out_path)
    cmd = [
        "ffmpeg",
        "-y",
        "-ss", str(ts_seconds),
        "-i", input_source,
        "-frames:v", "1",
        "-q:v", "2",
        out_path,
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def human_time(seconds: float) -> str:
    seconds = max(0, int(seconds))
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    if h > 0:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"
