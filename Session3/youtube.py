import os
from typing import List, Dict, Any
from dataclasses import dataclass

from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound

from utils import human_time

@dataclass
class TranscriptSegment:
    start: float
    dur: float
    text: str


def ytdlp_extract(url: str) -> Dict[str, Any]:
    import yt_dlp
    ydl_opts = {
        'quiet': True,
        'skip_download': True,
        'noplaylist': True,
        'cachedir': False,
        'ignoreerrors': True
    }
    try:

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            return ydl.extract_info(url, download=False)
    except Exception as ex:
        return {}


def ytdlp_get_stream_url(url: str, resolution: int = 720) -> str:
    """
    Return the highest resolution progressive MP4 video+audio stream URL
    available, preferring >=min_resolution.
    """
    import yt_dlp

    ydl_opts = {
        'quiet': True,
        'noplaylist': True,
        'cachedir': False,
        'ignoreerrors': True,
        'format': 'bestvideo+bestaudio/best',
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)

        formats = info.get("formats", [])

        # Filter for progressive mp4 formats with video and audio
        progressive_formats = [
            f for f in formats
            if f.get("ext") == "mp4"
            # and f.get("height") is not None
            # and f.get("url")
            # and not f.get("vcodec", "").startswith("none")  # ensure it has video
            # and not f.get("acodec", "").startswith("none")  # ensure it has audio
        ]

        # Sort descending by resolution (height)
        progressive_formats.sort(key=lambda f: f["height"], reverse=True)

        # Pick the first that meets min_resolution
        for f in progressive_formats:
            if f["height"] >= resolution or f["width"] >= resolution:
                print(f"Got format >= min_res")
                return f["url"]

        # Fallback: just return the highest available progressive format
        if progressive_formats:
            print(f"Returning highest available progressive youtube format")
            return progressive_formats[0]["url"]

        # As a last resort, fall back to the best format URL (may be adaptive)
        if "url" in info:
            return info["url"]

        raise RuntimeError(f"Could not resolve a suitable stream URL for {url}")


def ytdlp_download_best_mp4(url: str, out_dir: str) -> str:
    import yt_dlp
    os.makedirs(out_dir, exist_ok=True)
    out_tmpl = os.path.join(out_dir, "%(title).200B-%(id)s.%(ext)s")
    ydl_opts = {
        'format': 'bv*[vcodec^=avc1][ext=mp4]+ba[ext=m4a]/b[ext=mp4]/best',
        'outtmpl': out_tmpl,
        'merge_output_format': 'mp4',
        'quiet': True,
        'noplaylist': True,
        'cachedir': False,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        return ydl.prepare_filename(info).rsplit('.', 1)[0] + '.mp4'


def fetch_transcript(video_id: str, lang: str = 'en', use_auto: bool = False) -> List[TranscriptSegment]:
    try:
        ytt = YouTubeTranscriptApi()
        transcript_list = ytt.list(video_id)
        t = None
        try:
            # Try to find a manually created transcript first
            t = transcript_list.find_transcript([lang])
            print(f"Found manually created transcript")
        except NoTranscriptFound:
            if use_auto:
                # Fall back to auto-generated transcript
                try:
                    t = transcript_list.find_generated_transcript([lang])
                except NoTranscriptFound:
                    pass
        if not t:
            raise RuntimeError(f"No transcript (manual or auto) found for {video_id} in language {lang}")
        fetched = t.fetch()
    except (TranscriptsDisabled, NoTranscriptFound) as e:
        raise RuntimeError(f"No transcript available for {video_id} (lang={lang}).") from e

    # Access attributes instead of dict keys
    return [TranscriptSegment(start=s.start, dur=s.duration, text=s.text) for s in fetched]


# def segments_to_text(segs: List[TranscriptSegment]) -> str:
#     return "\n".join([f"[{human_time(s.start)}] {s.text}" for s in segs])

def segments_to_text(segs: List[TranscriptSegment]) -> str:
    # Keep simple lines with [mm:ss] prefix for better model grounding
    lines = []
    for s in segs:
        cleaned_text = s.text.replace('\n', ' ')
        # lines.append(f"[{human_time(s.start)}] {s.text}")
        lines.append(f"[{human_time(s.start)}] {cleaned_text}")
    return "\n".join(lines)
