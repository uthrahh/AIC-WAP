"""
export_service.py
-----------------
All PDF / Excel export helpers.

export_tasklog_pdf(work_map, report_date, filename)
    work_map: dict[str, list[str]]
        key   = task description (lowercase string)
        value = sorted list of employee full names

The caller (reports.py) is responsible for building work_map correctly
from the JSON stored in DailyUpdate.completed_tasks via tasks_from_json().
"""

from __future__ import annotations

import os
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

# Output directory — use a temp folder so FastAPI can serve it
_OUTPUT_DIR = Path("exports")
_OUTPUT_DIR.mkdir(exist_ok=True)


# ---------------------------------------------------------------------------
# Today's task-log PDF
# ---------------------------------------------------------------------------

def export_tasklog_pdf(
    work_map: dict[str, list[str]],
    report_date: date,
    filename: str,
) -> str:
    """
    Render a clean task-log PDF.

    work_map  — {task_description: [employee_name, ...]}
                Keys are already the final, human-readable task strings.
                Values are sorted lists of full employee names.
    """

    pdf_path = str(_OUTPUT_DIR / filename)

    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )

    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Title"],
        fontSize=18,
        spaceAfter=4,
    )
    date_style = ParagraphStyle(
        "DateLine",
        parent=styles["Normal"],
        fontSize=11,
        textColor=colors.HexColor("#555555"),
        spaceAfter=6,
    )
    subtitle_style = ParagraphStyle(
        "Subtitle",
        parent=styles["Normal"],
        fontSize=10,
        textColor=colors.HexColor("#888888"),
        spaceAfter=14,
    )
    task_style = ParagraphStyle(
        "TaskText",
        parent=styles["Normal"],
        fontSize=10,
        leading=14,
    )
    emp_style = ParagraphStyle(
        "EmpText",
        parent=styles["Normal"],
        fontSize=9,
        textColor=colors.HexColor("#444444"),
        leftIndent=12,
        leading=13,
    )

    story = []

    # Header
    story.append(Paragraph("Today's Updates", title_style))
    story.append(
        Paragraph(
            report_date.strftime("%d/%m/%Y | %A"),
            date_style,
        )
    )

    task_count = len(work_map)
    # We don't know total employees here, so omit that sub-line
    # (the caller can pass it if needed — keep the service simple)
    story.append(
        Paragraph(
            f"{task_count} task{'s' if task_count != 1 else ''} completed today",
            subtitle_style,
        )
    )

    if not work_map:
        story.append(Paragraph("No updates submitted today.", styles["Normal"]))
    else:
        for idx, (task, employees) in enumerate(work_map.items(), start=1):
            # Task line: "1. Electronics lab glass design development progressed"
            story.append(
                Paragraph(
                    f"{idx}. {task.strip()}",
                    task_style,
                )
            )
            # One line per employee, indented
            for emp in employees:
                story.append(Paragraph(emp, emp_style))
            story.append(Spacer(1, 6))

    doc.build(story)
    return pdf_path


# ---------------------------------------------------------------------------
# Date-range completed-tasks PDF
# ---------------------------------------------------------------------------

def export_completed_tasks_report(
    rows: list[dict[str, Any]],
    filename: str,
) -> str:
    """
    rows: list of dicts with keys:
        month, week, date, day, task, employees
    """

    pdf_path = str(_OUTPUT_DIR / filename)

    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=A4,
        leftMargin=1.5 * cm,
        rightMargin=1.5 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )

    styles = getSampleStyleSheet()
    story  = []

    story.append(Paragraph("Completed Tasks Report", styles["Title"]))
    story.append(Spacer(1, 12))

    if not rows:
        story.append(Paragraph("No tasks found for the selected period.", styles["Normal"]))
        doc.build(story)
        return pdf_path

    # Table header
    header = ["#", "Date", "Day", "Task", "Employees"]
    data   = [header]

    for i, row in enumerate(rows, start=1):
        data.append([
            str(i),
            row.get("date", ""),
            row.get("day",  ""),
            row.get("task", ""),
            row.get("employees", ""),
        ])

    col_widths = [1 * cm, 2.5 * cm, 2.5 * cm, 9 * cm, 4 * cm]

    table = Table(data, colWidths=col_widths, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND",  (0, 0), (-1, 0),  colors.HexColor("#2c3e50")),
        ("TEXTCOLOR",   (0, 0), (-1, 0),  colors.white),
        ("FONTNAME",    (0, 0), (-1, 0),  "Helvetica-Bold"),
        ("FONTSIZE",    (0, 0), (-1, 0),  9),
        ("FONTSIZE",    (0, 1), (-1, -1), 8),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5f5f5")]),
        ("GRID",        (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
        ("VALIGN",      (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING",(0, 0), (-1, -1), 4),
        ("TOPPADDING",  (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING",(0, 0),(-1, -1), 3),
    ]))

    story.append(table)
    doc.build(story)
    return pdf_path


# ---------------------------------------------------------------------------
# Excel export
# ---------------------------------------------------------------------------

def export_to_excel(
    rows: list[dict[str, Any]],
    filename: str,
) -> str:

    excel_path = str(_OUTPUT_DIR / filename)
    df = pd.DataFrame(rows)
    df.to_excel(excel_path, index=False)
    return excel_path