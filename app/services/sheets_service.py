from loguru import logger

from app.core.config import get_settings


def sync_daily_updates_to_sheets(records: list[dict]) -> bool:
    settings = get_settings()
    if not settings.google_sheets_credentials_file or not settings.google_sheets_spreadsheet_id:
        logger.debug("Google Sheets not configured, skipping sync")
        return False

    try:
        import gspread
        from google.oauth2.service_account import Credentials

        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]
        creds = Credentials.from_service_account_file(
            settings.google_sheets_credentials_file,
            scopes=scopes,
        )
        client = gspread.authorize(creds)
        sheet = client.open_by_key(settings.google_sheets_spreadsheet_id)
        worksheet = sheet.sheet1

        if records:
            headers = list(records[0].keys())
            rows = [headers] + [[str(r.get(h, "")) for h in headers] for r in records]
            worksheet.clear()
            worksheet.update(rows, value_input_option="USER_ENTERED")

        logger.info(f"Synced {len(records)} records to Google Sheets")
        return True
    except Exception as exc:
        logger.error(f"Google Sheets sync failed: {exc}")
        return False
