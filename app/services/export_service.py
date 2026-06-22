from pathlib import Path

import pandas as pd
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

from app.core.config import get_settings


def _ensure_reports_dir() -> Path:
    path = Path(get_settings().reports_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def export_to_pdf(title: str, content: str, filename: str) -> str:
    reports_dir = _ensure_reports_dir()
    filepath = reports_dir / filename
    doc = SimpleDocTemplate(str(filepath), pagesize=A4)
    styles = getSampleStyleSheet()
    story = [
        Paragraph(title, styles["Title"]),
        Spacer(1, 12),
    ]
    for line in content.splitlines():
        if line.strip():
            story.append(Paragraph(line.replace("&", "&amp;"), styles["Normal"]))
            story.append(Spacer(1, 6))
    doc.build(story)
    return str(filepath)


def export_to_excel(data: list[dict], filename: str, sheet_name: str = "Report") -> str:
    reports_dir = _ensure_reports_dir()
    filepath = reports_dir / filename
    df = pd.DataFrame(data)
    df.to_excel(filepath, index=False, sheet_name=sheet_name, engine="openpyxl")
    return str(filepath)
