import os
from typing import List
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Image, PageBreak,
    ListFlowable, ListItem
)
from PIL import Image as PILImage

from utils import ensure_dir, human_time

class Section:
    def __init__(self, title, start, end, summary, key_points, screenshot_path=None, raw_start="[00:00]", raw_end="[00:00]"):
        self.title = title
        self.start = start
        self.end = end
        self.summary = summary
        self.key_points = key_points
        self.screenshot_path = screenshot_path
        self.raw_start = raw_start
        self.raw_end = raw_end


def build_pdf(out_path: str, title: str, video_url: str, sections: List[Section], page_size=A4, continuous=False):
    ensure_dir(out_path)
    doc = SimpleDocTemplate(out_path, pagesize=page_size, leftMargin=54, rightMargin=54, topMargin=54, bottomMargin=54)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='TitleCenter', parent=styles['Title'], alignment=TA_CENTER, spaceAfter=18))
    styles.add(ParagraphStyle(name='H2', parent=styles['Heading2'], spaceBefore=12, spaceAfter=6))
    styles.add(ParagraphStyle(name='H3', parent=styles['Heading3'], spaceBefore=8, spaceAfter=4))
    styles.add(ParagraphStyle(name='Body', parent=styles['BodyText'], leading=16))
    styles.add(ParagraphStyle(name='CustomBullet', parent=styles['BodyText'], fontSize=9, leading=12, leftIndent=14, spaceBefore=2))

    story = []
    story.append(Paragraph(title, styles['TitleCenter']))
    story.append(Paragraph(f"Source: <a href='{video_url}' color='blue'>{video_url}</a>", styles['Body']))
    story.append(Spacer(1, 0.4*inch))

    # --- Table of Contents ---
    story.append(Paragraph("<a name='toc'/>Key Sections", styles['H2']))
    for i, s in enumerate(sections, 1):
        toc_entry = f"<a href='#section_{i}' color='blue'>{i}. {s.title}</a>  —  {human_time(s.start)}–{human_time(s.end)}"
        story.append(Paragraph(toc_entry, styles['Body']))
    story.append(PageBreak())

    # --- Detailed Sections ---
    for i, s in enumerate(sections, 1):
        # Anchor for internal link target
        story.append(Paragraph(f"<a name='section_{i}'/>", styles['Body']))
        story.append(Paragraph(f"{i}. {s.title}", styles['H2']))
        story.append(Paragraph(f"Timestamp: {human_time(s.start)}–{human_time(s.end)}", styles['Body']))
        story.append(Spacer(1, 0.1*inch))
        if s.screenshot_path and os.path.exists(s.screenshot_path):
            try:
                with PILImage.open(s.screenshot_path) as im:
                    width, height = im.size
                max_width = doc.width
                scale = min(1.0, max_width / width)
                story.append(Image(s.screenshot_path, width=width*scale, height=height*scale))
                story.append(Spacer(1, 0.15*inch))
            except Exception:
                pass
        # Summary with smaller heading
        story.append(Paragraph("Summary", styles['H3']))
        story.append(Paragraph(s.summary, styles['Body']))
        # Proper bullet points
        if s.key_points:
            bullet_items = [
                ListItem(Paragraph(str(p), styles['CustomBullet'])) for p in s.key_points
            ]
            story.append(ListFlowable(bullet_items, bulletType='bullet', start='circle'))
        # Back link
        story.append(Spacer(1, 0.2*inch))
        story.append(Paragraph("<a href='#toc' color='blue'>Back to Key Sections</a>", styles['Body']))
        if not continuous and i < len(sections):
            story.append(PageBreak())
        else:
            story.append(Spacer(1, 0.4*inch))

    doc.build(story)
