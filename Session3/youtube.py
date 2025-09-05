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
    ydl_opts = {'quiet': True, 'skip_download': True, 'noplaylist': True, 'cachedir': False}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        return ydl.extract_info(url, download=False)


def ytdlp_get_stream_url(url: str) -> str:
    """
    Return a direct video+audio stream URL, preferring >=720p progressive MP4.
    Falls back to best if 720p not available.
    """
    import yt_dlp
    ydl_opts = {
        # Prefer mp4 progressive streams at >=720p, otherwise best
        'format': "bestvideo[height>=720][ext=mp4]+bestaudio[ext=m4a]/best[height>=720][ext=mp4]/best",
        'quiet': True,
        'noplaylist': True,
        'cachedir': False,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        # Case 1: merged format (most common with -g)
        if "url" in info and info["url"]:
            return info["url"]
        # Case 2: adaptive formats list
        if "formats" in info:
            for f in info["formats"]:
                if f.get("ext") == "mp4" and f.get("url"):
                    return f["url"]
        raise RuntimeError(f"Could not resolve a direct stream URL for {url}")



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
