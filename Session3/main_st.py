import os
import re
import html as html_escape
import base64
import tempfile
import streamlit as st
import streamlit.components.v1 as components

from utils import extract_video_id, ffmpeg_screenshot, human_time, parse_timecode, normalize_timecode
from youtube import ytdlp_extract, ytdlp_get_stream_url, fetch_transcript, segments_to_text
from gemini import init_gemini, call_gemini_sections
from pdf_builder import build_pdf, Section
from search import openai_embed, build_faiss_index, search_transcripts


def run_pipeline(url, lang="en", use_auto=False, model="gemini-1.5-flash",
                 max_sections=8, screenshots=True, screenshot_resolution=720):
    """
    Returns: (title, sections, video_id)
    Sections are pdf_builder.Section objects with optional screenshot_path.
    """
    video_id = extract_video_id(url)
    info = ytdlp_extract(url)
    title = info.get("title") or f"YouTube Video {video_id}"

    print(f"Getting transcripts")
    segs = fetch_transcript(video_id, lang=lang, use_auto=use_auto)
    transcript_text = segments_to_text(segs)
    print(f"Got transcripts for video")
    print(transcript_text)

    model_obj = init_gemini(model)
    print(f"Getting sections summary from Gemini")
    sections_json = call_gemini_sections(model_obj, transcript_text, max_sections=max_sections)
    print(f"Got section summary from Gemini")
    raw_sections = sections_json.get("sections", [])
    print(f"Gemini sections: {raw_sections}")

    sections = []
    for r in raw_sections:
        s = Section(
            title=str(r.get("title", "")).strip() or "Untitled Section",
            start=parse_timecode(r.get("start", 0)),
            end=parse_timecode(r.get("end", 0)),
            summary=str(r.get("summary", "")).strip(),
            key_points=[re.sub(r"\s+", " ", str(p)).strip() for p in r.get("key_points", [])][:6],
            raw_start=normalize_timecode(r.get("start", "")),  # store human-readable
            raw_end=normalize_timecode(r.get("end", ""))
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

    return title, sections, video_id, segs


def _image_to_data_uri(path: str) -> str:
    """Return a data:image/...;base64,... for a local image file. Returns empty string on failure."""
    if not path or not os.path.exists(path):
        return ""
    try:
        with open(path, "rb") as f:
            data = f.read()
        b64 = base64.b64encode(data).decode("utf-8")
        # best-effort mime type based on extension
        ext = os.path.splitext(path)[1].lower()
        if ext in (".jpg", ".jpeg"):
            mime = "image/jpeg"
        elif ext == ".png":
            mime = "image/png"
        else:
            mime = "image/jpeg"
        return f"data:{mime};base64,{b64}"
    except Exception:
        return ""

def show_search_results(results):
    if not results:
        st.info("No results found.")
        return

    for r in results:
        ts_label = f"{human_time(r['start'])} – {human_time(r['end'])}"
        st.markdown(
            f"""
            <div style="padding:8px; border:1px solid #ddd; border-radius:8px; margin:6px 0; background:#fafafa;">
                <a href="#" onclick="seek({int(r['start'])}); return false;" style="text-decoration:none; font-weight:bold; color:#0b5ed7;">
                    ⏱️ {ts_label}
                </a>
                <div style="margin-top:4px;">{html_escape.escape(r['text'])}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

def embed_player_with_sections(video_id: str, sections, player_width=720, player_height=405):
    style = """
    <style>
      body { font-family: Arial, Helvetica, sans-serif; margin: 10px; color: #222; }
      .player-wrap { text-align: center; margin-bottom: 20px; }
      .sections { display:flex; flex-direction: column; gap: 20px; }
      .section { display:flex; gap:20px; align-items:flex-start; padding:16px; border-radius:10px; border:1px solid #ddd; background:#fdfdfd; }
      .thumb { width:60%; max-width:700px; border-radius:8px; object-fit:contain; background:#f5f5f5; }
      .meta { flex:1; min-width:0; max-width:40%; }
      a.ts-link { color:#0b5ed7; text-decoration:none; font-weight:600; }
      a.ts-link:hover { text-decoration:underline; cursor:pointer; }
      ul { margin:6px 0 0 18px; }
    </style>
    """

    sections_html_parts = []
    section_heights = []

    for idx, s in enumerate(sections, start=1):
        safe_title = html_escape.escape(s.title)
        safe_summary = html_escape.escape(s.summary).replace("\n","<br/>")
        bullets_html = ""
        if s.key_points:
            bullets_html = "<ul>" + "".join(f"<li>{html_escape.escape(str(p))}</li>" for p in s.key_points) + "</ul>"

        ts_label = f"{human_time(s.start)} – {human_time(s.end)}"

        # Embed screenshot if available
        img_src = _image_to_data_uri(getattr(s,"screenshot_path",None))
        img_height = 0
        if img_src and "R0lGODlhAQAB" not in img_src:  # not the empty placeholder
            img_height = 360  # default estimate for thumbnail height
        else:
            img_src = "data:image/gif;base64,R0lGODlhAQABAPAAAP///wAAACH5BAAAAAAALAAAAAABAAEAAAICRAEAOw=="
            img_height = 0

        section_html = f"""
        <div class="section" id="section_{idx}">
            <img class="thumb" src="{img_src}" alt="screenshot_{idx}" />
            <div class="meta">
                <strong>{idx}. {safe_title}</strong><br/>
                <a class="ts-link" href="#" onclick="seek({int(s.start)}); return false;">⏱️ {ts_label}</a>
                <p>{safe_summary}</p>
                {bullets_html}
            </div>
        </div>
        """
        sections_html_parts.append(section_html)

        # Estimate text height: ~20px per line, assume ~3 lines per summary + 20px for bullets
        num_lines = max(3, safe_summary.count("<br/>")+1)
        text_height = num_lines * 20 + (len(s.key_points) * 20)
        total_section_height = img_height + text_height + 40  # padding + margin
        section_heights.append(total_section_height)

    sections_html = "\n".join(sections_html_parts)

    html_doc = f"""
    <!doctype html>
    <html>
    <head>
      <meta charset="utf-8"/>
      {style}
    </head>
    <body>
      <div class="player-wrap"><div id="player"></div></div>
      <div class="sections">{sections_html}</div>

      <script src="https://www.youtube.com/iframe_api"></script>
      <script>
        var player = null;
        function onYouTubeIframeAPIReady() {{
            player = new YT.Player('player', {{
                height: '{player_height}',
                width: '{player_width}',
                videoId: '{video_id}',
                playerVars: {{ 'playsinline':1 }}
            }});
        }}
        function seek(seconds) {{
            if(player && player.seekTo){{
                try{{player.seekTo(seconds,true); player.playVideo();}}catch(e){{console.error(e);}}
            }}
        }}
      </script>
    </body>
    </html>
    """

    # calculate total iframe height based on actual section heights
    frame_height = player_height + sum(section_heights) + 50
    components.html(html_doc, height=frame_height, scrolling=False)


def main():
    st.set_page_config(layout="wide")
    st.title("📺 YouTube ➜ PDF Summarizer with Gemini")

    # --- URL input ---
    if "url" not in st.session_state:
        st.session_state.url = ""
    st.markdown("#### Enter YouTube URL:")
    c1, c2, c3 = st.columns([1, 2, 1])
    with c1:
        st.session_state.url = st.text_input("", value=st.session_state.url)

    # --- Parameters ---
    st.markdown("#### Parameters:")
    col1, col2, col3, col4 = st.columns([0.7, 0.5, 1, 4])

    if "max_sections" not in st.session_state:
        st.session_state.max_sections = 8
    with col1:
        st.session_state.max_sections = st.number_input(
            "Maximum sections", min_value=1, max_value=20, value=st.session_state.max_sections
        )

    if "screenshot_resolution" not in st.session_state:
        st.session_state.screenshot_resolution = 720
    with col2:
        st.session_state.screenshot_resolution = st.selectbox(
            "Screenshot resolution",
            [360, 480, 720, 1080, 1440, 2160],
            index=[360, 480, 720, 1080, 1440, 2160].index(st.session_state.screenshot_resolution)
        )

    if "screenshots" not in st.session_state:
        st.session_state.screenshots = True
    with col3:
        st.session_state.screenshots = st.checkbox("Include screenshots", value=st.session_state.screenshots)

    # --- Actions: Start / Download ---
    st.markdown("#### Actions:")
    action_col1, action_col2, _ = st.columns([1, 1, 6])
    start_btn = action_col1.button("▶️ Start Summarization")
    pdf_placeholder = action_col2.empty()

    # --- Run summarization ---
    if start_btn and st.session_state.url:
        with st.spinner("Processing..."):
            title, sections, video_id, transcript_text = run_pipeline(
                st.session_state.url,
                max_sections=st.session_state.max_sections,
                screenshots=st.session_state.screenshots,
                screenshot_resolution=st.session_state.screenshot_resolution,
            )
            # Save results in session_state
            st.session_state.title = title
            st.session_state.sections = sections
            st.session_state.video_id = video_id
            st.session_state.transcript_text = transcript_text
            st.success("Summarization complete!")

    # --- Render player + sections if available ---
    # if "sections" in st.session_state and st.session_state.sections:
    if "sections" in st.session_state and "video_id" in st.session_state:
        c1, c2 = st.columns([3, 1])
        with c1:
            embed_player_with_sections(
                st.session_state.video_id,
                st.session_state.sections,
                player_width = 720,
                player_height=405
            )

        # # Build FAISS index
        # index, vector_texts = build_faiss_index(st.session_state.transcript_text, openai_embed)
        #
        # # Search input
        # search_query = st.text_input("Search transcript:")
        #
        # if search_query:
        #     results = search_transcripts(index, vector_texts, search_query)
        #     with c2:
        #         st.markdown("#### Search Results:")
        #         show_search_results(results)

        # Generate PDF once and store path
        if "pdf_path" not in st.session_state:
            out_path = os.path.join(tempfile.gettempdir(), "yt_summary.pdf")
            build_pdf(
                out_path,
                title=st.session_state.title,
                video_url=st.session_state.url,
                sections=st.session_state.sections,
                continuous=True
            )
            st.session_state.pdf_path = out_path
            st.info(f"✅ PDF successfully generated at: `{out_path}`")

        # # Download PDF button
        # pdf_bytes = build_pdf(st.session_state.title, st.session_state.sections)
        # st.download_button(
        #     label="📥 Download PDF",
        #     data=pdf_bytes,
        #     file_name=f"{st.session_state.title}.pdf",
        #     mime="application/pdf",
        # )
        with open(st.session_state.pdf_path, "rb") as f:
            pdf_placeholder.download_button(
                "📥 Download PDF",
                f,
                # file_name = "yt_summary.pdf",
                file_name=f"{st.session_state.title}.pdf",
                mime="application/pdf"
            )

if __name__ == "__main__":
    main()
