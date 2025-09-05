import os
import re
import tempfile
import streamlit as st

from utils import extract_video_id, ffmpeg_screenshot
from youtube import ytdlp_extract, ytdlp_get_stream_url, fetch_transcript, segments_to_text
from gemini import init_gemini, call_gemini_sections
from pdf_builder import build_pdf, Section


def run_pipeline(url, lang="en", use_auto=False, model="gemini-1.5-flash",
                 max_sections=8, screenshots=True, screenshot_resolution=720):

    video_id = extract_video_id(url)
    info = ytdlp_extract(url)
    title = info.get("title") or f"YouTube Video {video_id}"

    segs = fetch_transcript(video_id, lang=lang, use_auto=use_auto)
    transcript_text = segments_to_text(segs)

    model_obj = init_gemini(model)
    sections_json = call_gemini_sections(model_obj, transcript_text, max_sections=max_sections)
    raw_sections = sections_json.get("sections", [])

    sections = []
    for r in raw_sections:
        s = Section(
            title=str(r.get("title", "")).strip() or "Untitled Section",
            start=float(r.get("start", 0)),
            end=float(r.get("end", 0)),
            summary=str(r.get("summary", "")).strip(),
            key_points=[re.sub(r"\s+", " ", str(p)).strip() for p in r.get("key_points", [])][:6],
        )
        sections.append(s)

    if screenshots and sections:
        workdir = tempfile.mkdtemp(prefix="yt2pdf_")
        shots_dir = os.path.join(workdir, "shots")
        os.makedirs(shots_dir, exist_ok=True)

        try:
            stream_url = ytdlp_get_stream_url(url, resolution=screenshot_resolution)
        except Exception as e:
            st.warning(f"Failed to resolve stream URL for screenshots: {e}")
            stream_url = None

        if stream_url:
            for i, s in enumerate(sections, 1):
                mid = max(0, (s.start + s.end) / 2.0)
                shot_path = os.path.join(shots_dir, f"section_{i:02d}.jpg")
                try:
                    ffmpeg_screenshot(stream_url, mid, shot_path)
                    s.screenshot_path = shot_path
                except Exception as e:
                    st.warning(f"Failed screenshot section {i}: {e}")

    return title, sections


def main():
    st.set_page_config(layout="wide")
    st.title("📺 YouTube ➜ PDF Summarizer with Gemini")

    url = st.text_input("Enter YouTube URL:")

    st.subheader("Options")
    col1, col2 = st.columns(2)
    with col1:
        lang = st.text_input("Transcript language (default 'en')", value="en")
        use_auto = st.checkbox("Use auto-generated transcript if manual not available", value=False)
        model = st.text_input("Gemini model", value="gemini-1.5-flash")
    with col2:
        max_sections = st.number_input("Maximum sections", min_value=1, max_value=20, value=8)
        screenshots = st.checkbox("Include screenshots", value=True)
        screenshot_resolution = st.selectbox("Screenshot resolution", [360, 480, 720, 1080, 1440, 2160], index=2)

    if url:
        st.markdown("### Preview Video")
        with st.container():
            cols = st.columns([1, 2, 1])  # center the player
            with cols[1]:
                st.video(url)

    if st.button("▶️ Start Summarization"):
        with st.spinner("Processing..."):
            title, sections = run_pipeline(
                url,
                lang=lang,
                use_auto=use_auto,
                model=model,
                max_sections=max_sections,
                screenshots=screenshots,
                screenshot_resolution=screenshot_resolution,
            )

        st.success("Summarization complete!")
        st.subheader("Extracted Sections")

        progress = st.progress(0)
        total = len(sections)

        for i, s in enumerate(sections, 1):
            with st.container():
                cols = st.columns([1, 2])  # left = image, right = text
                with cols[0]:
                    if s.screenshot_path and os.path.exists(s.screenshot_path):
                        st.image(s.screenshot_path, use_column_width=True)
                with cols[1]:
                    st.markdown(f"### {i}. {s.title}")
                    # clickable timestamp
                    ts_link = f"https://www.youtube.com/watch?v={extract_video_id(url)}&t={int(s.start)}s"
                    st.markdown(f"[⏱️ {s.start:.0f}s – {s.end:.0f}s]({ts_link})")
                    st.markdown("**Summary**")
                    st.write(s.summary)
                    if s.key_points:
                        st.markdown("**Key Points**")
                        st.markdown("\n".join([f"- {p}" for p in s.key_points]))

            progress.progress(i / total)

        # Generate PDF after loop
        out_path = os.path.join(tempfile.gettempdir(), "yt_summary.pdf")
        build_pdf(out_path, title=title, video_url=url, sections=sections, continuous=True)

        with open(out_path, "rb") as f:
            st.download_button("📥 Download PDF", f, file_name="yt_summary.pdf", mime="application/pdf")


if __name__ == "__main__":
    main()
