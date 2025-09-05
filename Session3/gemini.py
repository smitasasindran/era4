import os
import re
import json
from typing import Dict, Any
import google.generativeai as genai

# SECTION_SCHEMA_INSTRUCTIONS = """
# You are given a YouTube transcript with timestamps like [mm:ss] or [hh:mm:ss].
# Extract the MOST IMPORTANT sections of the video in JSON only.
# Return up to {max_sections} sections.
# Each section: {title, start, end, summary, key_points}
# Output format:
# {"sections": [ {...}, ... ]}
# """

SECTION_SCHEMA_INSTRUCTIONS = (
    """
You are given a YouTube transcript with timestamps like [mm:ss] or [hh:mm:ss].
Extract the MOST IMPORTANT sections of the video in JSON only, no commentary.
Return up to {max_sections} sections.
Each section must be a JSON object with fields:
  - title: short, descriptive (<= 60 chars)
  - start: start time in SECONDS (number)
  - end: end time in SECONDS (number)
  - summary: 2-4 sentence summary
  - key_points: array of 3-6 crisp bullet points
Rules:
  - Always align start/end to the closest spoken-word boundaries you can detect from timestamps.
  - Ensure sections are non-overlapping and ordered by start.
  - Prefer moments where the speaker introduces a topic, demo, definition, or conclusion.
  - If the transcript is partial, still produce your best structured output.
Output format:
{
  "sections": [ {"title":..., "start":..., "end":..., "summary":..., "key_points": [...]}, ... ]
}
    """
)


def init_gemini(model_name: str, api_key: str = None):
    api_key = api_key or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError("Missing GOOGLE_API_KEY. Set env var first.")
    genai.configure(api_key=api_key)
    return genai.GenerativeModel(model_name)


# def call_gemini_sections(model, transcript_text: str, max_sections: int = 8) -> Dict[str, Any]:
#     sys_prompt = SECTION_SCHEMA_INSTRUCTIONS.format(max_sections=max_sections)
#     content = [{"role": "user", "parts": [sys_prompt, "\n\nTRANSCRIPT:\n", transcript_text]}]
#     resp = model.generate_content(content, safety_settings=None)
#     txt = resp.text
#     try:
#         return json.loads(txt)
#     except Exception:
#         m = re.search(r"\{[\s\S]*\}$", txt.strip())
#         if m:
#             return json.loads(m.group(0))
#     raise RuntimeError("Gemini did not return valid JSON. Raw output:\n" + txt)

def call_gemini_sections(model, transcript_text: str, max_sections: int = 8) -> Dict[str, Any]:
    sys_prompt = SECTION_SCHEMA_INSTRUCTIONS.format(max_sections=max_sections)
    # We use a single prompt. For very long transcripts, you could chunk and merge.
    content = [
        {"role": "user", "parts": [
            sys_prompt,
            "\n\nTRANSCRIPT:\n",
            transcript_text,
        ]}
    ]
    resp = model.generate_content(content, safety_settings=None)
    txt = resp.text
    # Extract JSON payload
    j = None
    try:
        # Try direct JSON
        j = json.loads(txt)
    except Exception:
        # Try to find a JSON block
        m = re.search(r"\{[\s\S]*\}$", txt.strip())
        if m:
            j = json.loads(m.group(0))
    if not j or 'sections' not in j:
        raise RuntimeError("Gemini did not return a valid JSON with 'sections'. Raw output:\n" + txt)
    return j
