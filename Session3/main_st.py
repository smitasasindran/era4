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
    Render a single components.html containing the YouTube player and a list of sections
    so that timestamps call seek(seconds) in the same iframe.
    (This approach avoids cross-frame postMessage issues.)
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
            # bullets_html = "<ul>" + "".join(f"<li>{html_escape.escape(str(p))}</li>" for p in s.key_points) + "</ul>"

        ts_label = f"{human_time(s.start)} – {human_time(s.end)}  [{s.start}-{s.end}]"

        img_src = _image_to_data_uri(getattr(s, "screenshot_path", None))
        if not img_src:
            img_src = "data:image/gif;base64,R0lGODlhAQABAPAAAP///wAAACH5BAAAAAAALAAAAAABAAEAAAICRAEAOw=="

        section_html = f"""
        <div class="section" id="section_{idx}">
          <img class="thumb" src="{img_src}" alt="screenshot_{idx}" />
          <div class="meta">
            <h3>{idx}. {safe_title}</h3>
            <div><a class="ts-link" href="#" onclick="seek({int(s.start)}); return false;">⏱️ {ts_label}</a></div>
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
            try {{
              player.seekTo(seconds, true);
              player.playVideo();
            }} catch (e) {{ console.error('seek failed', e); }}
          }}
        }}
      </script>
    </body>
    </html>
    """

    # generous height so the iframe is embedded full-length (no inner scrollbar)
    frame_height = player_height + len(sections) * 300 + 200
    components.html(html_doc, height=frame_height, scrolling=False)


def main():
    st.set_page_config(layout="wide")
    st.title("📺 YouTube ➜ PDF Summarizer with Gemini")

    # centered, smaller URL input (so it doesn't span entire width)
    c1, c2, c3 = st.columns([1, 2, 1])
    with c1:
        # st.subheader("Enter Youtube URL")
        st.markdown("#### Enter YouTube URL:")
        url = st.text_input("")
    # with c2:

    # Options (remove Gemini model & transcript language per request)
    # st.subheader("Options")
    st.markdown("#### Parameters:")
    col1, col2, col3, col4 = st.columns([0.7, 0.5, 1, 4])
    with col1:
        max_sections = st.number_input("Maximum sections", min_value=1, max_value=20, value=8)
    with col2:
        screenshot_resolution = st.selectbox("Screenshot resolution", [360, 480, 720, 1080, 1440, 2160], index=2)
    with col3:
        screenshots = st.checkbox("Include screenshots", value=True)


    # Action row: Start Summarization + (disabled) Download PDF next to it
    st.markdown("#### Actions: ")
    action_col1, action_col2, _ = st.columns([1, 1, 6])
    start_btn = action_col1.button("▶️ Start Summarization")
    # placeholder for download button next to Start; initially disabled
    pdf_placeholder = action_col2.empty()
    pdf_placeholder.button("📥 Download PDF", disabled=True)

    if start_btn and url:
        with st.spinner("Processing..."):
            # call pipeline (lang & model use defaults inside run_pipeline)
            title, sections, video_id = run_pipeline(
                url,
                max_sections=max_sections,
                screenshots=screenshots,
                screenshot_resolution=screenshot_resolution,
            )

        st.success("Summarization complete!")

        # Render player + sections (player + sections live inside the same iframe)
        embed_player_with_sections(video_id, sections, player_width=720, player_height=405)

        # Generate PDF
        out_path = os.path.join(tempfile.gettempdir(), "yt_summary.pdf")
        build_pdf(out_path, title=title, video_url=url, sections=sections, continuous=True)

        # confirmation message with path
        st.info(f"✅ PDF successfully generated at: `{out_path}`")

        # replace disabled placeholder with actual download button
        with open(out_path, "rb") as f:
            pdf_placeholder.download_button("📥 Download PDF", f, file_name="yt_summary.pdf", mime="application/pdf")


if __name__ == "__main__":
    main()
