"""
Golden dataset for InsureCo AI regression tests.

Text-only — no audio files. Each case maps a real input the pipeline
receives (phone number or transcript fragment) to the expected output.
Cases are derived from the actual production flows in app/sheets.py and
app/vapi_client.py, not hypothetical scenarios.

Add a new case every time a production bug is found so it can never recur.
"""

import pytest


# ---------------------------------------------------------------------------
# Phone normalisation golden cases
# Covers every format a caller might speak or the STT might produce.
# normalize_phone() in app/sheets.py must handle all of these.
# ---------------------------------------------------------------------------
PHONE_GOLDEN_CASES = [
    # (raw_input, expected_e164, tags)
    ("555-867-5309",        "+15558675309", ["dashed"]),
    ("(555) 867-5309",      "+15558675309", ["parenthesized"]),
    ("5558675309",          "+15558675309", ["digits_only"]),
    ("+15558675309",        "+15558675309", ["already_e164"]),
    ("15558675309",         "+15558675309", ["eleven_digits"]),
    ("  555-867-5309  ",    "+15558675309", ["whitespace"]),
    ("555 867 5309",        "+15558675309", ["space_separated"]),
    # Known hard cases — STT sometimes produces these
    ("five five five eight six seven five three oh nine", "five five five eight six seven five three oh nine", ["stt_words_fallback"]),
    ("",                    "",             ["empty"]),
]

# ---------------------------------------------------------------------------
# Caller-name extraction golden cases
# _extract_caller_name_from_transcript() in app/vapi_client.py must handle
# these. The agent confirms identity with "am I speaking with X?" — the
# caller's confirmation is required before the name is accepted.
# ---------------------------------------------------------------------------
NAME_EXTRACTION_GOLDEN_CASES = [
    # (transcript_fragment, call_metadata, expected_name, tags)
    (
        "assistant: am I speaking with Sarah Johnson? user: Yes that's correct.",
        {},
        "Sarah Johnson",
        ["happy_path", "yes_confirmation"],
    ),
    (
        "assistant: am I speaking with Michael Chen? user: Yeah.",
        {},
        "Michael Chen",
        ["yeah_confirmation"],
    ),
    (
        "assistant: am I speaking with Bob Smith? user: No, wrong number.",
        {},
        "Unknown",
        ["denial_returns_unknown"],
    ),
    (
        "assistant: What can I help you with? user: I have a question.",
        {},
        "Unknown",
        ["no_identity_check"],
    ),
    (
        "",
        {},
        "Unknown",
        ["empty_transcript"],
    ),
    (
        "assistant: am I speaking with Jane Doe? user: Yes.",
        {"first_name": "Override", "last_name": "Name"},
        "Override Name",
        ["metadata_takes_priority"],
    ),
]

# ---------------------------------------------------------------------------
# Summariser output contract golden cases
# summarize_call() must always return all three keys with valid values.
# These are the inputs most likely to break the output format.
# ---------------------------------------------------------------------------
SUMMARIZER_CONTRACT_CASES = [
    # (description, transcript)
    ("empty_transcript",      ""),
    ("whitespace_only",       "   \n  "),
    ("normal_happy_path",     "assistant: am I speaking with Sarah Johnson? user: Yes. assistant: Your claim is pending review. user: Thanks, goodbye."),
    ("no_auth_completed",     "assistant: What is your number? user: I do not know. assistant: I can arrange a callback. user: OK bye."),
    ("very_long_transcript",  "user: hello " * 500),
]

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def phone_golden_cases():
    return PHONE_GOLDEN_CASES


@pytest.fixture
def name_extraction_golden_cases():
    return NAME_EXTRACTION_GOLDEN_CASES


@pytest.fixture
def summarizer_contract_cases():
    return SUMMARIZER_CONTRACT_CASES
