import os
import re
import html as html_escape
import base64
import tempfile
import streamlit as st
import streamlit.components.v1 as components

from utils import extract_video_id, ffmpeg_screenshot, human_time
from youtube import ytdlp_extract, ytdlp_get_stream_url, fetch_transcript, segments_to_text
from gemini import init_gemini, call_gemini_sections
from pdf_builder import build_pdf, Section


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
    print(f"Got transcriots for video")

    model_obj = init_gemini(model)
    sections_json = call_gemini_sections(model_obj, transcript_text, max_sections=max_sections)
    print(f"Got section summary from Gemini")
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

    return title, sections, video_id


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


def embed_player_with_sections(video_id: str, sections, player_width=800, player_height=450):
    """
    Render a components.html block containing the YouTube player and a list of sections.
    """
    style = """
    <style>
      body { font-family: Arial, Helvetica, sans-serif; margin: 10px; color: #222; }
      .player-wrap { text-align: center; margin-bottom: 20px; }
      .sections { display:flex; flex-direction: column; gap: 20px; }
      .section { display:flex; gap:20px; align-items:flex-start; padding:16px; border-radius:10px; border: 1px solid #ddd; background: #fdfdfd; }
      .thumb { width: 60%; max-width: 700px; border-radius:8px; object-fit: contain; background:#f5f5f5; }
      .meta { flex: 1; min-width: 0; max-width: 40%; }
      .meta h3 { margin: 0 0 8px 0; font-size: 18px; }
      .meta .ts { color:#0b5ed7; font-weight:600; margin-bottom:8px; display:inline-block; }
      .meta p { margin: 6px 0; line-height: 1.4; }
      .meta ul { margin: 6px 0 0 18px; }
      a.ts-link { color: #0b5ed7; text-decoration: none; font-weight: 600; }
      a.ts-link:hover { text-decoration: underline; cursor: pointer; }
    </style>
    """

    sections_html_parts = []
    for idx, s in enumerate(sections, start=1):
        safe_title = html_escape.escape(s.title)
        safe_summary = html_escape.escape(s.summary).replace("\n", "<br/>")
        bullets_html = ""
        if s.key_points:
            bullets_html = "<ul>" + "".join(
                f"<li>{html_escape.escape(str(p))}</li>" for p in s.key_points
            ) + "</ul>"

        ts_label = f"{human_time(s.start)} – {human_time(s.end)}"

        # Thumbnail or placeholder
        if getattr(s, "screenshot_path", None) and os.path.exists(s.screenshot_path):
            img_src = _image_to_data_uri(s.screenshot_path)
            thumb_html = f'<img class="thumb" src="{img_src}" alt="screenshot_{idx}" />'
        else:
            thumb_html = '<div class="thumb" style="height:200px; background:#fafafa; display:flex; align-items:center; justify-content:center; color:#aaa; font-size:14px;">No Screenshot</div>'

        section_html = f"""
        <div class="section" id="section_{idx}">
          {thumb_html}
          <div class="meta">
            <h3>{idx}. {safe_title}</h3>
            <div><a class="ts-link" onclick="seek({int(s.start)}); return false;">⏱️ {ts_label}</a></div>
            <p>{safe_summary}</p>
            {bullets_html}
          </div>
        </div>
        """
        sections_html_parts.append(section_html)

    sections_html = "\n".join(sections_html_parts)

    html_doc = f"""
    <!doctype html>
    <html>
    <head>
      <meta charset="utf-8"/>
      {style}
    </head>
    <body>
      <div class="player-wrap">
        <div id="player"></div>
      </div>

      <div class="sections">
        {sections_html}
      </div>

      <script src="https://www.youtube.com/iframe_api"></script>
      <script>
        var player = null;
        function onYouTubeIframeAPIReady() {{
          player = new YT.Player('player', {{
            height: '{player_height}',
            width: '{player_width}',
            videoId: '{video_id}',
            playerVars: {{ 'playsinline': 1 }}
          }});
        }}
        function seek(seconds) {{
          if (player && player.seekTo) {{
            player.seekTo(seconds, true);
            player.playVideo();
          }}
        }}
      </script>
    </body>
    </html>
    """

    frame_height = player_height + len(sections) * 320 + 100
    components.html(html_doc, height=frame_height, scrolling=True)


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

    # # Preview (small centered player) — optional, but keep it minimal
    # if url:
    #     with st.container():
    #         cols = st.columns([1, 2, 1])
    #         with cols[1]:
    #             # small preview using the iframe API too so it looks consistent
    #             vid = extract_video_id(url)
    #             # Use embed_player_with_sections with zero sections for preview (no sections displayed)
    #             embed_player_with_sections(vid, [], player_width=560, player_height=315)

    if st.button("▶️ Start Summarization"):
        with st.spinner("Processing..."):
            title, sections, video_id = run_pipeline(
                url,
                lang=lang,
                use_auto=use_auto,
                model=model,
                max_sections=max_sections,
                screenshots=screenshots,
                screenshot_resolution=screenshot_resolution,
            )

        st.success("Summarization complete!")

        # Render player + sections inside same iframe so timestamps seek inline
        embed_player_with_sections(video_id, sections, player_width=720, player_height=405)

        # Generate PDF after loop
        out_path = os.path.join(tempfile.gettempdir(), "yt_summary.pdf")
        build_pdf(out_path, title=title, video_url=url, sections=sections, continuous=True)

        with open(out_path, "rb") as f:
            st.download_button("📥 Download PDF", f, file_name="yt_summary.pdf", mime="application/pdf")


if __name__ == "__main__":
    main()
