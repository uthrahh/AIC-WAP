from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "WAP Worklog System"
    debug: bool = False

    database_url: str = "postgresql://postgres:postgres@localhost:5432/worklog"
    redis_url: str = "redis://localhost:6379/0"

    secret_key: str = "change-this-secret-key-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 480

    whatsapp_gateway_url: str = "http://localhost:3001"
    whatsapp_group_name: str = "AIC-CIIC Worklog"

    office_start_hour: int = 9
    office_end_hour: int = 19
    reminder_end_hour: int = 21
    timezone: str = "Asia/Kolkata"

    openai_api_key: str = ""
    gemini_api_key: str = ""
    ai_provider: str = "regex"  # regex | openai | gemini
    api_url: str = "http://localhost:8000"

    google_sheets_credentials_file: str = ""
    google_sheets_spreadsheet_id: str = ""

    reports_dir: str = "reports"
    logs_dir: str = "logs"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    return Settings()
