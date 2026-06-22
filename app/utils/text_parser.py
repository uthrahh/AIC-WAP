import json
import re
from dataclasses import dataclass, field


@dataclass
class ParsedWorklog:
    completed_tasks: list[str] = field(default_factory=list)
    pending_tasks: list[str] = field(default_factory=list)
    is_leave: bool = False


PENDING_WORK_PATTERN = re.compile(
    r"@WAP\s+(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})\s+pending\s+work\s*:?\s*(.*)",
    re.IGNORECASE | re.DOTALL,
)

SECTION_HEADERS = re.compile(
    r"^(Completed Tasks?|Completed Work|Done Today|Completed|"
    r"Pending Tasks?|Pending Work|In Progress|Pending|"
    r"On Leave)\s*:?\s*$",
    re.IGNORECASE | re.MULTILINE,
)


def _extract_list_items(text: str) -> list[str]:
    items = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if SECTION_HEADERS.match(line):
            continue
        cleaned = re.sub(r"^[\-\*\d]+[\.\)]\s*", "", line).strip()
        if cleaned:
            items.append(cleaned)
    return items


def _split_sections(message: str) -> dict[str, str]:
    sections: dict[str, str] = {}
    current_key = None
    buffer: list[str] = []

    for line in message.splitlines():
        header_match = SECTION_HEADERS.match(line.strip())
        if header_match:
            if current_key and buffer:
                sections[current_key] = "\n".join(buffer).strip()
            raw = header_match.group(1).lower()
            if raw.startswith("completed") or raw == "done today":
                current_key = "completed"
            elif raw.startswith("pending") or raw == "in progress":
                current_key = "pending"
            elif "leave" in raw:
                current_key = "leave"
            else:
                current_key = None
            buffer = []
        elif current_key:
            buffer.append(line)

    if current_key and buffer:
        sections[current_key] = "\n".join(buffer).strip()

    return sections


def parse_worklog_message(message: str) -> ParsedWorklog:
    if re.search(r"\bon\s+leave\b", message, re.IGNORECASE):
        return ParsedWorklog(is_leave=True)

    sections = _split_sections(message)
    if sections.get("leave"):
        return ParsedWorklog(is_leave=True)

    return ParsedWorklog(
        completed_tasks=_extract_list_items(sections.get("completed", "")),
        pending_tasks=_extract_list_items(sections.get("pending", "")),
    )


def parse_pending_work_command(message: str) -> tuple[str | None, list[str]]:
    match = PENDING_WORK_PATTERN.search(message)
    if not match:
        return None, []
    date_str = match.group(1)
    body = match.group(2).strip()
    return date_str, _extract_list_items(body)


def tasks_to_json(tasks: list[str]) -> str:
    return json.dumps(tasks, ensure_ascii=False)


def tasks_from_json(raw: str | None) -> list[str]:
    if not raw:
        return []
    try:
        data = json.loads(raw)
        return data if isinstance(data, list) else []
    except json.JSONDecodeError:
        return _extract_list_items(raw)


def normalize_task_name(name: str) -> str:
    return re.sub(r"\s+", " ", name.strip().lower())


def tasks_match(task_a: str, task_b: str, threshold: float = 0.6) -> bool:
    a = normalize_task_name(task_a)
    b = normalize_task_name(task_b)
    if a == b:
        return True
    if a in b or b in a:
        return True
    a_words = set(a.split())
    b_words = set(b.split())
    if not a_words or not b_words:
        return False
    overlap = len(a_words & b_words) / max(len(a_words), len(b_words))
    return overlap >= threshold


WAP_MENU = """Available Commands:

1. Generate Daily Summary
2. Generate Weekly Summary
3. Generate Project Summary
4. Generate Productivity Report
5. Generate Employee Contribution Report

Usage: @WAP <command>
Example: @WAP Generate Daily Summary"""


def parse_wap_command(message: str) -> str | None:
    if "@WAP" not in message.upper():
        return None
    body = re.sub(r"@WAP\s*", "", message, flags=re.IGNORECASE).strip()
    if not body:
        return "menu"
    lower = body.lower()
    if "pending work" in lower:
        return "pending_work"
    if "daily summary" in lower:
        return "daily_summary"
    if "weekly summary" in lower:
        return "weekly_summary"
    if "project summary" in lower:
        return "project_summary"
    if "productivity" in lower:
        return "productivity_report"
    if "contribution" in lower or "employee" in lower:
        return "contribution_report"
    return "custom:" + body
