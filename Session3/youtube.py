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


# def fetch_transcript(video_id: str, lang: str = 'en', use_auto: bool = False) -> List[TranscriptSegment]:
#     try:
#         if use_auto:
#             transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
#             try:
#                 t = transcript_list.find_transcript([lang])
#             except NoTranscriptFound:
#                 t = transcript_list.find_generated_transcript([lang])
#             raw = t.fetch()
#         else:
#             raw = YouTubeTranscriptApi.get_transcript(video_id, languages=[lang])
#     except (TranscriptsDisabled, NoTranscriptFound) as e:
#         raise RuntimeError(f"No transcript available for {video_id} (lang={lang}). Try --use-auto.") from e
#
#     return [TranscriptSegment(start=s['start'], dur=s['duration'], text=s['text']) for s in raw]


def fetch_transcript(video_id: str, lang: str = 'en', use_auto: bool = False) -> List[TranscriptSegment]:
    try:
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        t = None
        try:
            # Try to find a manually created transcript first
            t = transcript_list.find_transcript([lang])
        except NoTranscriptFound:
            if use_auto:
                # Fall back to auto-generated transcript
                try:
                    t = transcript_list.find_generated_transcript([lang])
                except NoTranscriptFound:
                    pass
        if not t:
            raise RuntimeError(f"No transcript (manual or auto) found for {video_id} in language {lang}")
        raw = t.fetch()
    except (TranscriptsDisabled, NoTranscriptFound) as e:
        raise RuntimeError(f"No transcript available for {video_id} (lang={lang}).") from e

    return [TranscriptSegment(start=s['start'], dur=s['duration'], text=s['text']) for s in raw]




# def segments_to_text(segs: List[TranscriptSegment]) -> str:
#     return "\n".join([f"[{human_time(s.start)}] {s.text}" for s in segs])

def segments_to_text(segs: List[TranscriptSegment]) -> str:
    # Keep simple lines with [mm:ss] prefix for better model grounding
    lines = []
    for s in segs:
        lines.append(f"[{human_time(s.start)}] {s.text}")
    return "\n".join(lines)
