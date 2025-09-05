import os
from typing import List
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
# from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, PageBreak
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, PageBreak
from reportlab.platypus.tableofcontents import TableOfContents
from reportlab.lib import colors
from PIL import Image as PILImage

from utils import ensure_dir, human_time

class Section:
    def __init__(self, title, start, end, summary, key_points, screenshot_path=None):
        self.title = title
        self.start = start
        self.end = end
        self.summary = summary
        self.key_points = key_points
        self.screenshot_path = screenshot_path


def build_pdf(out_path: str, title: str, video_url: str, sections: List[Section], page_size=A4):
    ensure_dir(out_path)
    doc = SimpleDocTemplate(out_path, pagesize=page_size, leftMargin=54, rightMargin=54, topMargin=54, bottomMargin=54)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='TitleCenter', parent=styles['Title'], alignment=TA_CENTER, spaceAfter=18))
    styles.add(ParagraphStyle(name='H2', parent=styles['Heading2'], spaceBefore=12, spaceAfter=6))
    styles.add(ParagraphStyle(name='Body', parent=styles['BodyText'], leading=16))

    story = []
    story.append(Paragraph(title, styles['TitleCenter']))
    story.append(Paragraph(f"Source: <a href='{video_url}' color='blue'>{video_url}</a>", styles['Body']))
    story.append(Spacer(1, 0.4*inch))

    # Add Table of Contents
    story.append(Paragraph("Table of Contents", styles['H2']))
    toc = TableOfContents()
    toc.levelStyles = [
        ParagraphStyle(fontName='Times-Bold', fontSize=12, name='TOCHeading1', leftIndent=20, firstLineIndent=-20, spaceBefore=5, leading=14),
    ]
    story.append(toc)
    story.append(PageBreak())

    for i, s in enumerate(sections, 1):
        # notify TOC
        story.append(Paragraph(f"<bookmark name='section{i}'/>", styles['Body']))
        story.append(Paragraph(f"{i}. {s.title}", styles['H2']))
        story[-1].__dict__['_bookmarkName'] = f'section{i}'

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
        story.append(Paragraph("Summary", styles['H2']))
        story.append(Paragraph(s.summary, styles['Body']))
        if s.key_points:
            bullets = "".join([f"<li>{p}</li>" for p in s.key_points])
            story.append(Paragraph(f"<ul>{bullets}</ul>", styles['Body']))
        if i < len(sections):
            story.append(PageBreak())
    doc.build(story)