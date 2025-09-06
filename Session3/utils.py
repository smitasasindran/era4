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
        "-qscale:v", "2",  # high quality
        "-an", # disable audio processing
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


def parse_timecode(tc: str) -> float:
    """Convert [mm:ss] or [hh:mm:ss] into seconds."""
    if not tc:
        return 0.0
    tc = str(tc).strip("[] ")  # remove brackets
    parts = tc.split(":")
    try:
        parts = [int(p) for p in parts]
    except ValueError:
        return 0.0
    if len(parts) == 2:  # mm:ss
        m, s = parts
        return m * 60 + s
    elif len(parts) == 3:  # hh:mm:ss
        h, m, s = parts
        return h * 3600 + m * 60 + s
    return 0.0


def normalize_timecode(tc: str) -> str:
    """
    Normalize a YouTube timestamp string to properly zero-padded format.
    Input examples: "[1:8:12]", "[5:3]", "12:7", "[00:5]"
    Returns: "[hh:mm:ss]" if 3 parts, "[mm:ss]" if 2 parts
    """
    if not tc:
        return "[00:00]"

    # Strip brackets and whitespace
    tc = tc.strip().strip("[]")
    parts = tc.split(":")

    # Convert all parts to int and clamp negative values to 0
    try:
        parts = [max(0, int(p)) for p in parts]
    except ValueError:
        return "[00:00]"

    if len(parts) == 2:  # mm:ss
        mm, ss = parts
        return f"[{mm:02d}:{ss:02d}]"
    elif len(parts) == 3:  # hh:mm:ss
        hh, mm, ss = parts
        return f"[{hh:02d}:{mm:02d}:{ss:02d}]"
    else:
        # fallback if only one part or malformed
        total_sec = sum(p * 60 ** i for i, p in reversed(list(enumerate(parts))))
        mm, ss = divmod(total_sec, 60)
        if mm >= 60:
            hh, mm = divmod(mm, 60)
            return f"[{hh:02d}:{mm:02d}:{ss:02d}]"
        return f"[{mm:02d}:{ss:02d}]"
