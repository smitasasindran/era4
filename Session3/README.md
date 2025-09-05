
YouTube ➜ PDF

- Pulls the video's transcript
- Uses Gemini API to summarize + identify important sections with timestamps
- Captures a screenshot for each section
- Compiles everything into a nicely formatted PDF

Requirements (install first):
    pip install youtube-transcript-api yt-dlp google-generativeai reportlab pillow tiktoken

Also install ffmpeg (required for screenshots):
    - macOS:   brew install ffmpeg
    - Ubuntu:  sudo apt-get update && sudo apt-get install -y ffmpeg
    - Windows: winget install Gyan.FFmpeg  (or download from ffmpeg.org)

Auth:
    export GOOGLE_API_KEY="<your key>"

Usage:
    python yt_to_pdf.py --url https://www.youtube.com/watch?v=dQw4w9WgXcQ \
        --out out/my_video_summary.pdf \
        --lang en \
        --model gemini-1.5-flash


Notes:
- If the video has no official transcript, set --use-auto to try auto-generated transcripts.
- For long videos, the script chunks the transcript and merges Gemini-suggested key sections.
- You can tune --max-sections to limit how many sections make the final PDF.