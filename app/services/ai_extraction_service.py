"""Optional AI-enhanced extraction using OpenAI or Gemini."""

from loguru import logger

from app.core.config import get_settings
from app.utils.text_parser import ParsedWorklog, parse_worklog_message


def extract_with_ai(message: str) -> ParsedWorklog:
    settings = get_settings()
    if settings.ai_provider == "openai" and settings.openai_api_key:
        return _extract_openai(message, settings.openai_api_key)
    if settings.ai_provider == "gemini" and settings.gemini_api_key:
        return _extract_gemini(message, settings.gemini_api_key)
    return parse_worklog_message(message)


def _extract_openai(message: str, api_key: str) -> ParsedWorklog:
    try:
        import httpx

        prompt = (
            "Extract completed_tasks, pending_tasks, "
            "and is_leave (boolean) from this worklog. Return JSON only.\n\n"
            f"{message}"
        )
        response = httpx.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0,
            },
            timeout=30.0,
        )
        response.raise_for_status()
        import json

        content = response.json()["choices"][0]["message"]["content"]
        data = json.loads(content.strip().strip("`").replace("json", ""))
        return ParsedWorklog(
            completed_tasks=data.get("completed_tasks", []),
            pending_tasks=data.get("pending_tasks", []),
            is_leave=data.get("is_leave", False),
        )
    except Exception as exc:
        logger.warning(f"OpenAI extraction failed, using regex: {exc}")
        return parse_worklog_message(message)


def _extract_gemini(message: str, api_key: str) -> ParsedWorklog:
    try:
        import httpx
        import json

        prompt = (
            "Extract completed_tasks, pending_tasks, "
            "and is_leave (boolean) from this worklog. Return JSON only.\n\n"
            f"{message}"
        )
        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"gemini-2.0-flash:generateContent?key={api_key}"
        )
        response = httpx.post(
            url,
            json={"contents": [{"parts": [{"text": prompt}]}]},
            timeout=30.0,
        )
        response.raise_for_status()
        text = response.json()["candidates"][0]["content"]["parts"][0]["text"]
        data = json.loads(text.strip().strip("`").replace("json", ""))
        return ParsedWorklog(
            completed_tasks=data.get("completed_tasks", []),
            pending_tasks=data.get("pending_tasks", []),
            is_leave=data.get("is_leave", False),
        )
    except Exception as exc:
        logger.warning(f"Gemini extraction failed, using regex: {exc}")
        return parse_worklog_message(message)
