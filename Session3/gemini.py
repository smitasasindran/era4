import os
import re
import json
import base64
from typing import Dict, Any
import google.generativeai as genai

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

IMPORTANT INSTRUCTIONS FOR FORMATTING (READ CAREFULLY):
1) Output an EXACTLY VALID JSON object matching the schema above. No extra commentary.
2) Wrap that JSON in a fenced code block labeled ```json ... ```.
3) ALSO (on its own line) output the SAME JSON encoded in BASE64 and labeled like this:

BASE64_JSON: <base64-encoded-json>

(We will prefer the BASE64_JSON value when parsing; it guarantees machine-safe transmission.)

Output example (the JSON shown below is illustrative — DO NOT add extra fields):
```json
{{
  "sections": [ {{"title":..., "start":..., "end":..., "summary":..., "key_points": [...]}} , ... ]
}}
```
BASE64_JSON: <base64>

If you cannot follow the exact formatting, reply with ONLY the JSON inside the fenced block and nothing else.
    """
)


def init_gemini(model_name: str, api_key: str = None):
    api_key = api_key or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError("Missing GOOGLE_API_KEY. Set env var first.")
    genai.configure(api_key=api_key)
    return genai.GenerativeModel(model_name)


def _extract_json_candidate_from_text(txt: str) -> str:
    """Try several robust extraction strategies in order:
    1) Find a BASE64_JSON: <base64> line and decode it.
    2) Find a ```json fenced block.
    3) Fall back to the last {...} JSON-like block in the text.
    Returns the JSON string candidate or None.
    """
    # 1) BASE64 hint (preferred)
    m = re.search(r"BASE64_JSON:\s*([A-Za-z0-9+/=]+)", txt, re.IGNORECASE)
    if m:
        b64 = m.group(1).strip()
        try:
            return base64.b64decode(b64).decode('utf-8')
        except Exception:
            pass

    # 2) fenced ```json block
    m = re.search(r"```json\s*([\s\S]*?)```", txt, re.IGNORECASE)
    if m:
        return m.group(1).strip()

    # 3) last {...} block
    m = re.search(r"(\{[\s\S]*\})", txt.strip())
    if m:
        return m.group(1)

    return None


def _escape_unescaped_quotes(s: str) -> str:
    # Escape double quotes that are not already escaped
    return re.sub(r'(?<!\\)"', r'\\"', s)


def _repair_summary_field(json_text: str) -> str:
    """A targeted repair that escapes unescaped double quotes inside the 'summary' value.
    This fixes the most common model failure where the summary contains unescaped quotes.
    """
    pat = re.compile(r'("summary"\s*:\s*")(?P<content>.*?)(?P<end>"\s*,\s*"key_points")', re.DOTALL)
    m = pat.search(json_text)
    if not m:
        return json_text
    content = m.group('content')
    fixed = _escape_unescaped_quotes(content)
    repaired = json_text[:m.start('content')] + fixed + json_text[m.end('content'):]
    return repaired


def call_gemini_sections(model, transcript_text: str, max_sections: int = 8) -> Dict[str, Any]:
    sys_prompt = SECTION_SCHEMA_INSTRUCTIONS.format(max_sections=max_sections)
    # content = [{"role": "user", "parts": [sys_prompt, "\n\nTRANSCRIPT:\n", transcript_text]}]
    content = [
        {"role": "user", "parts": [
            sys_prompt,
            "\n\nTRANSCRIPT:\n",
            transcript_text,
        ]}
    ]
    resp = model.generate_content(content, safety_settings=None)
    txt = resp.text.strip()
    print(f"Raw gemini text: {txt}")
    if 'json' in txt:
        txt = txt[8:-3]

    # 0) Try parsing as-is
    try:
        return json.loads(txt)
    except Exception:
        pass

    # 1) Extract candidate JSON string robustly
    candidate = _extract_json_candidate_from_text(txt)
    if not candidate:
        raise RuntimeError("Could not find a JSON payload in Gemini output. Raw output:\n" + txt)

    # 2) Try parsing candidate
    try:
        return json.loads(candidate)
    except Exception:
        pass

    # 3) Try targeted repair for summary field and re-parse
    repaired = _repair_summary_field(candidate)
    try:
        return json.loads(repaired)
    except Exception:
        pass

    # 4) As a last resort, attempt to escape ALL unescaped quotes (dangerous but may recover output)
    aggressively = _escape_unescaped_quotes(candidate)
    try:
        return json.loads(aggressively)
    except Exception:
        # If still failing, raise a helpful error showing what we tried
        msg = (
            "Gemini returned JSON-like text but parsing failed.\n"
            "We attempted: direct parse, targeted summary repair, and aggressive escaping.\n"
            "Raw output:\n" + txt + "\n\n" +
            "Candidate extracted for parsing:\n" + candidate + "\n\n" +
            "After targeted repair:\n" + repaired
        )
        raise RuntimeError(msg)
