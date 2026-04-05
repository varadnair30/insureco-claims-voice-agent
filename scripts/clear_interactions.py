"""One-off utility to clear the interactions tab (keeps header row)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.sheets import _get_sheets_service, CUSTOMERS_RANGE
from app.config import settings


def clear_interactions_keep_header():
    service = _get_sheets_service()
    # Clear everything from row 2 onward
    service.spreadsheets().values().clear(
        spreadsheetId=settings.spreadsheet_id,
        range="interactions!A2:Z",
        body={},
    ).execute()
    print("Cleared interactions tab (header preserved).")


def show_customers():
    service = _get_sheets_service()
    result = (
        service.spreadsheets()
        .values()
        .get(spreadsheetId=settings.spreadsheet_id, range=CUSTOMERS_RANGE)
        .execute()
    )
    rows = result.get("values", [])
    print("\nCustomers tab:")
    for r in rows:
        print("  ", r)


if __name__ == "__main__":
    clear_interactions_keep_header()
    show_customers()
