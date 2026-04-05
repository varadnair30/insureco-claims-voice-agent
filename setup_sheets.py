"""Setup script to populate an existing Google Spreadsheet with test data.

Usage:
    python setup_sheets.py --credentials path/to/service_account.json --spreadsheet-id YOUR_SHEET_ID

Prerequisites:
    1. Create a blank spreadsheet at sheets.google.com
    2. Share it with your service account email as Editor
    3. Copy the spreadsheet ID from the URL

This script will:
1. Rename/create sheets: "customers" and "interactions"
2. Populate "customers" with sample data
3. Set up headers for "interactions"
4. Format headers
"""

import argparse
import json

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

SAMPLE_CUSTOMERS = [
    ["phone_number", "first_name", "last_name", "claim_status"],
    ["+15551234567", "Sarah", "Johnson", "pending"],
    ["+15559876543", "Michael", "Chen", "approved"],
    ["+15551112222", "Emily", "Davis", "requires_documentation"],
    ["+15553334444", "James", "Wilson", "pending"],
    ["+15555556666", "Maria", "Garcia", "approved"],
]

INTERACTION_HEADERS = [
    ["timestamp", "caller_name", "summary", "sentiment", "call_id"],
]


def populate_spreadsheet(creds_path: str, spreadsheet_id: str):
    """Populate an existing Google Spreadsheet with test data."""

    creds = Credentials.from_service_account_file(creds_path, scopes=SCOPES)
    service = build("sheets", "v4", credentials=creds, cache_discovery=False)

    # Get current sheets info
    spreadsheet = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    existing_sheets = {s["properties"]["title"]: s["properties"]["sheetId"] for s in spreadsheet["sheets"]}

    print(f"Connected to spreadsheet: {spreadsheet['properties']['title']}")
    print(f"Existing sheets: {list(existing_sheets.keys())}")

    requests = []

    # Rename first sheet to "customers" if it's "Sheet1"
    if "Sheet1" in existing_sheets and "customers" not in existing_sheets:
        requests.append({
            "updateSheetProperties": {
                "properties": {"sheetId": existing_sheets["Sheet1"], "title": "customers"},
                "fields": "title",
            }
        })
        existing_sheets["customers"] = existing_sheets.pop("Sheet1")
        print("Renamed 'Sheet1' to 'customers'")

    # Add "interactions" sheet if it doesn't exist
    if "interactions" not in existing_sheets:
        requests.append({
            "addSheet": {
                "properties": {"title": "interactions", "gridProperties": {"frozenRowCount": 1}}
            }
        })
        print("Adding 'interactions' sheet")

    # Freeze header row on customers
    if "customers" in existing_sheets:
        requests.append({
            "updateSheetProperties": {
                "properties": {
                    "sheetId": existing_sheets["customers"],
                    "gridProperties": {"frozenRowCount": 1},
                },
                "fields": "gridProperties.frozenRowCount",
            }
        })

    # Execute structural changes first
    if requests:
        service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id, body={"requests": requests}
        ).execute()
        print("Sheet structure updated")

    # Populate customers
    print("Populating customers...")
    service.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range="customers!A1",
        valueInputOption="RAW",
        body={"values": SAMPLE_CUSTOMERS},
    ).execute()

    # Set up interactions headers
    print("Setting up interactions headers...")
    service.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range="interactions!A1",
        valueInputOption="RAW",
        body={"values": INTERACTION_HEADERS},
    ).execute()

    # Format headers (bold + blue background)
    spreadsheet = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    format_requests = []
    for sheet in spreadsheet["sheets"]:
        sheet_id = sheet["properties"]["sheetId"]
        format_requests.append({
            "repeatCell": {
                "range": {"sheetId": sheet_id, "startRowIndex": 0, "endRowIndex": 1},
                "cell": {
                    "userEnteredFormat": {
                        "textFormat": {"bold": True},
                        "backgroundColor": {"red": 0.9, "green": 0.93, "blue": 0.98},
                    }
                },
                "fields": "userEnteredFormat(textFormat,backgroundColor)",
            }
        })

    service.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id, body={"requests": format_requests}
    ).execute()
    print("Headers formatted")

    # Print results
    print("\n" + "=" * 60)
    print("SETUP COMPLETE")
    print("=" * 60)
    print(f"\nSpreadsheet ID: {spreadsheet_id}")
    print(f"URL: https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit")
    print(f"\nSample customers loaded: {len(SAMPLE_CUSTOMERS) - 1}")
    for row in SAMPLE_CUSTOMERS[1:]:
        print(f"  {row[1]} {row[2]} | {row[0]} | {row[3]}")

    # Save credentials snippet for .env
    with open(creds_path) as f:
        creds_json = json.load(f)
    single_line = json.dumps(creds_json, separators=(",", ":"))

    print(f"\n>> Add these to your .env file:")
    print(f"   SPREADSHEET_ID={spreadsheet_id}")
    print(f"\n   GOOGLE_CREDENTIALS_JSON saved to .env_credentials_snippet.txt")

    with open(".env_credentials_snippet.txt", "w") as f:
        f.write(f"GOOGLE_CREDENTIALS_JSON='{single_line}'\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Populate Google Sheets for Observe Claims Agent")
    parser.add_argument("--credentials", required=True, help="Path to service account JSON key")
    parser.add_argument("--spreadsheet-id", required=True, help="Existing Google Spreadsheet ID")
    args = parser.parse_args()
    populate_spreadsheet(args.credentials, args.spreadsheet_id)
