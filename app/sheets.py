"""Google Sheets client for customer lookup and interaction logging."""

from datetime import datetime, timezone
from typing import Optional

import phonenumbers
import structlog
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from googleapiclient.errors import HttpError

from app.config import settings

logger = structlog.get_logger(__name__)

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
CUSTOMERS_RANGE = "customers!A:D"
INTERACTIONS_RANGE = "interactions!A:E"


def _get_sheets_service():
    """Build and return an authenticated Google Sheets service client."""
    creds = Credentials.from_service_account_info(
        settings.google_credentials, scopes=SCOPES
    )
    return build("sheets", "v4", credentials=creds, cache_discovery=False)


def normalize_phone(raw_phone: str) -> str:
    """Normalize a phone number to E.164 format for consistent lookups.

    Handles spoken formats like '555-123-4567', '(555) 123 4567',
    and already-formatted numbers like '+15551234567'.
    """
    cleaned = raw_phone.strip()
    try:
        parsed = phonenumbers.parse(cleaned, "US")
        if phonenumbers.is_valid_number(parsed):
            return phonenumbers.format_number(
                parsed, phonenumbers.PhoneNumberFormat.E164
            )
    except phonenumbers.NumberParseException:
        pass

    # Fallback: strip non-digits, prepend +1 if 10 digits
    digits = "".join(c for c in cleaned if c.isdigit())
    if len(digits) == 10:
        return f"+1{digits}"
    if len(digits) == 11 and digits.startswith("1"):
        return f"+{digits}"
    return cleaned


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type(HttpError),
    before_sleep=lambda retry_state: structlog.get_logger().warning(
        "sheets_retry", attempt=retry_state.attempt_number
    ),
)
def lookup_customer(phone_number: str) -> Optional[dict]:
    """Look up a customer by phone number in the Google Sheets 'customers' tab.

    Returns dict with first_name, last_name, phone_number, claim_status if found,
    or None if not found.
    """
    normalized = normalize_phone(phone_number)
    logger.info("customer_lookup", phone=normalized)

    service = _get_sheets_service()
    result = (
        service.spreadsheets()
        .values()
        .get(spreadsheetId=settings.spreadsheet_id, range=CUSTOMERS_RANGE)
        .execute()
    )

    rows = result.get("values", [])
    if not rows:
        logger.warning("customer_lookup_empty_sheet")
        return None

    # First row is header: phone_number, first_name, last_name, claim_status
    for row in rows[1:]:
        if len(row) < 4:
            continue
        row_phone = normalize_phone(row[0])
        if row_phone == normalized:
            customer = {
                "phone_number": row[0],
                "first_name": row[1],
                "last_name": row[2],
                "claim_status": row[3].strip().lower(),
            }
            logger.info("customer_found", customer=customer["first_name"])
            return customer

    logger.info("customer_not_found", phone=normalized)
    return None


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type(HttpError),
    before_sleep=lambda retry_state: structlog.get_logger().warning(
        "sheets_retry", attempt=retry_state.attempt_number
    ),
)
def log_interaction(
    caller_name: str,
    summary: str,
    sentiment: str,
    call_id: str,
) -> bool:
    """Write a post-call interaction record to the 'interactions' tab.

    Returns True on success, False on failure.
    """
    timestamp = datetime.now(timezone.utc).isoformat()
    logger.info(
        "logging_interaction",
        caller=caller_name,
        sentiment=sentiment,
        call_id=call_id,
    )

    service = _get_sheets_service()
    body = {"values": [[timestamp, caller_name, summary, sentiment, call_id]]}
    service.spreadsheets().values().append(
        spreadsheetId=settings.spreadsheet_id,
        range=INTERACTIONS_RANGE,
        valueInputOption="USER_ENTERED",
        insertDataOption="INSERT_ROWS",
        body=body,
    ).execute()

    logger.info("interaction_logged", call_id=call_id)
    return True
