import pytest

from app.utils.text_parser import (
    parse_pending_work_command,
    parse_wap_command,
    parse_worklog_message,
    tasks_match,
)


def test_parse_worklog():
    msg = """Completed Tasks:
1. ERP Dashboard
2. API Integration

Pending Tasks:
1. PDF Export

Blockers:
1. Waiting for credentials"""
    result = parse_worklog_message(msg)
    assert result.completed_tasks == ["ERP Dashboard", "API Integration"]
    assert result.pending_tasks == ["PDF Export"]
    assert result.blockers == ["Waiting for credentials"]
    assert not result.is_leave


def test_on_leave():
    result = parse_worklog_message("On Leave today")
    assert result.is_leave


def test_pending_work_command():
    msg = """@WAP 12-06-2026 pending work:
1. ERP Dashboard
2. Attendance Module"""
    date_str, tasks = parse_pending_work_command(msg)
    assert date_str == "12-06-2026"
    assert len(tasks) == 2


def test_wap_menu():
    assert parse_wap_command("@WAP") == "menu"


def test_wap_daily_summary():
    assert parse_wap_command("@WAP Generate Daily Summary") == "daily_summary"


def test_tasks_match():
    assert tasks_match("ERP Dashboard", "erp dashboard api")
    assert not tasks_match("Unrelated", "Something else")
