
### YouTube ➜ PDF converter 


This repo takes a youtube url, summarizes it and converts it into a pdf:
- Pulls the video's transcript
- Uses Gemini API to summarize + identify important sections with timestamps
- Captures a screenshot for each section
- Compiles everything into a nicely formatted PDF
- Also has a streamlit UI, where the sections can be seen

**Requirements:**

    pip install youtube-transcript-api yt-dlp google-generativeai reportlab pillow tiktoken

Also install ffmpeg (required for screenshots):    
    - macOS:   brew install ffmpeg  
    - Ubuntu:  sudo apt-get update && sudo apt-get install -y ffmpeg  
    - Windows: winget install Gyan.FFmpeg  (or download from ffmpeg.org)  

Auth:
    export GOOGLE_API_KEY="<your key>"

Usage:
```commandline
python main.py --url https://www.youtube.com/watch?v=dQw4w9WgXcQ \
    --out out/my_video_summary.pdf \
    --lang en \
    --model gemini-1.5-flash
```

OR to run a UI:

```commandline
streamlit run main_st.py
```



Notes:
- If the video has no official transcript, set --use-auto to try auto-generated transcripts.
- For long videos, the script chunks the transcript and merges Gemini-suggested key sections.
- You can tune --max-sections to limit how many sections make the final PDF.