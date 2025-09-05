import os
import re
import tempfile
import argparse

from utils import extract_video_id, ffmpeg_screenshot, human_time
from youtube import ytdlp_extract, fetch_transcript, segments_to_text
from youtube import ytdlp_get_stream_url
from gemini import init_gemini, call_gemini_sections
from pdf_builder import build_pdf, Section


def main():
    parser = argparse.ArgumentParser(description="Convert a YouTube video into a summarized PDF with screenshots.")
    parser.add_argument('--url', required=True)
    parser.add_argument('--out', required=True)
    parser.add_argument('--lang', default='en')
    parser.add_argument('--use-auto', action='store_true', default=True)
    parser.add_argument('--model', default='gemini-1.5-flash')
    parser.add_argument('--max-sections', type=int, default=8)
    parser.add_argument('--screenshots', action='store_true', default=True)
    parser.add_argument('--workdir', default=None)
    args = parser.parse_args()

    video_id = extract_video_id(args.url)
    info = ytdlp_extract(args.url)
    title = info.get('title') or f"YouTube Video {video_id}"

    segs = fetch_transcript(video_id, lang=args.lang, use_auto=args.use_auto)
    # print(f"Original segs: {segs}")
    transcript_text = segments_to_text(segs)
    # print(f"Transcript text: {transcript_text}")
    print(f"Got transcripts from youtube video")

    model = init_gemini(args.model)
    sections_json = call_gemini_sections(model, transcript_text, max_sections=args.max_sections)
    raw_sections = sections_json.get('sections', [])
    print(f"\n\nGemini raw sections: {raw_sections}")

    sections = []
    for r in raw_sections:
        s = Section(
            title=str(r.get('title', '')).strip() or 'Untitled Section',
            start=float(r.get('start', 0)),
            end=float(r.get('end', 0)),
            summary=str(r.get('summary', '')).strip(),
            key_points=[re.sub(r"\s+", " ", str(p)).strip() for p in r.get('key_points', [])][:6],
        )
        sections.append(s)

    if args.screenshots:
        workdir = args.workdir if args.workdir else ""
        stream_url = ytdlp_get_stream_url(args.url)
        shots_dir = os.path.join(workdir, 'shots')
        os.makedirs(shots_dir, exist_ok=True)
        for i, s in enumerate(sections, 1):
            mid = max(0, (s.start + s.end) / 2.0)
            shot_path = os.path.join(shots_dir, f"section_{i:02d}.jpg")
            try:
                ffmpeg_screenshot(stream_url, mid, shot_path)
                s.screenshot_path = shot_path
            except Exception as e:
                print(f"Failed screenshot section {i}: {e}")

    build_pdf(args.out, title=title, video_url=args.url, sections=sections)
    print(f"Done. Wrote {args.out}")


if __name__ == "__main__":
    main()