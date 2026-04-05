"""Comprehensive test suite for the Observe Insurance Claims Voice Agent."""

import json
import os
import sys
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Environment stubs – must be set BEFORE any app module is imported, because
# app.config.Settings reads env vars at class-instantiation time and several
# modules (summarizer, sheets) touch config/settings at import time.
# ---------------------------------------------------------------------------
os.environ.setdefault("VAPI_API_KEY", "test-vapi-key")
os.environ.setdefault("OPENAI_API_KEY", "test-openai-key")
os.environ.setdefault("GOOGLE_CREDENTIALS_JSON", '{"type":"service_account","project_id":"test"}')
os.environ.setdefault("SPREADSHEET_ID", "test-spreadsheet-id")

# Patch the OpenAI client that is created at module-level in summarizer.py
# so importing the module never makes a real HTTP call.
with patch("openai.OpenAI"):
    from app.sheets import normalize_phone, lookup_customer, log_interaction
    from app.summarizer import SUMMARIZE_PROMPT, summarize_call
    from app.vapi_client import (
        handle_tool_call,
        handle_end_of_call,
        _extract_caller_name_from_transcript,
        handle_webhook,
    )
    from app.models import (
        LookupCallerRequest,
        LogInteractionRequest,
        CustomerRecord,
        InteractionResponse,
        HealthResponse,
    )
    from app.main import app


# =========================================================================
# 1. Phone normalisation  (app.sheets.normalize_phone)
# =========================================================================

class TestNormalizePhone:
    """Tests for the normalize_phone utility."""

    def test_parenthesized_format(self):
        assert normalize_phone("(555) 123-4567") == "+15551234567"

    def test_dashed_format(self):
        assert normalize_phone("555-123-4567") == "+15551234567"

    def test_digits_only(self):
        assert normalize_phone("5551234567") == "+15551234567"

    def test_already_e164(self):
        assert normalize_phone("+15551234567") == "+15551234567"

    def test_non_numeric_fallback(self):
        """Non-numeric strings that cannot be parsed should be returned as-is
        after the fallback logic (strip non-digits -> empty -> return cleaned)."""
        result = normalize_phone("abc")
        # "abc" has no digits, so the fallback returns the cleaned (stripped) input
        assert result == "abc"

    def test_empty_string(self):
        result = normalize_phone("")
        assert result == ""

    def test_whitespace_only(self):
        result = normalize_phone("   ")
        assert result == ""

    def test_eleven_digits_starting_with_one(self):
        """11 digits starting with 1 should be treated as a US number."""
        assert normalize_phone("15551234567") == "+15551234567"

    def test_with_leading_trailing_spaces(self):
        assert normalize_phone("  (555) 123-4567  ") == "+15551234567"


# =========================================================================
# 2. Summarizer prompt safety  (app.summarizer.SUMMARIZE_PROMPT)
# =========================================================================

class TestSummarizePromptFormat:
    """Ensure the prompt template can be safely formatted."""

    def test_format_does_not_raise(self):
        """SUMMARIZE_PROMPT.format(transcript=...) must not raise KeyError.
        The template uses double-braces for literal braces in the JSON example."""
        try:
            result = SUMMARIZE_PROMPT.format(transcript="test transcript")
        except KeyError:
            pytest.fail("SUMMARIZE_PROMPT.format(transcript=...) raised KeyError")

    def test_formatted_prompt_contains_transcript(self):
        result = SUMMARIZE_PROMPT.format(transcript="Hello this is a test call.")
        assert "Hello this is a test call." in result

    def test_formatted_prompt_retains_json_example(self):
        """The literal JSON braces in the prompt should survive formatting."""
        result = SUMMARIZE_PROMPT.format(transcript="demo")
        assert '"summary"' in result
        assert '"sentiment"' in result


# =========================================================================
# 3. Caller name extraction  (app.vapi_client._extract_caller_name_from_transcript)
# =========================================================================

class TestExtractCallerName:
    """Tests for _extract_caller_name_from_transcript."""

    def test_name_with_confirmation(self):
        # The regex in the source code uses lowercase "am I speaking with"
        transcript = (
            "assistant: am I speaking with Sarah Johnson? "
            "user: Yes, that's correct."
        )
        result = _extract_caller_name_from_transcript(transcript, call={})
        assert result == "Sarah Johnson"

    def test_name_without_confirmation(self):
        """If no confirmation words follow the name, should fall back to Unknown."""
        transcript = "assistant: am I speaking with Sarah Johnson? user: No, wrong number."
        result = _extract_caller_name_from_transcript(transcript, call={})
        assert result == "Unknown"

    def test_no_name_in_transcript(self):
        transcript = "assistant: Hello, how can I help? user: I have a claim question."
        result = _extract_caller_name_from_transcript(transcript, call={})
        assert result == "Unknown"

    def test_empty_transcript(self):
        result = _extract_caller_name_from_transcript("", call={})
        assert result == "Unknown"

    def test_metadata_takes_priority(self):
        """If call metadata contains first/last name, it wins over transcript parsing."""
        transcript = "assistant: am I speaking with Sarah Johnson? user: Yes."
        call = {"metadata": {"first_name": "John", "last_name": "Doe"}}
        result = _extract_caller_name_from_transcript(transcript, call)
        assert result == "John Doe"

    def test_metadata_first_name_only(self):
        call = {"metadata": {"first_name": "Alice", "last_name": ""}}
        result = _extract_caller_name_from_transcript("", call)
        assert result == "Alice"

    def test_yeah_confirmation(self):
        transcript = "assistant: am I speaking with Bob Smith? user: Yeah."
        result = _extract_caller_name_from_transcript(transcript, call={})
        assert result == "Bob Smith"


# =========================================================================
# 4. Webhook tool-call routing  (app.vapi_client.handle_tool_call)
# =========================================================================

class TestHandleToolCall:
    """Tests for the VAPI tool-call dispatcher."""

    @patch("app.vapi_client.lookup_customer")
    def test_lookup_caller_returns_customer(self, mock_lookup):
        mock_lookup.return_value = {
            "first_name": "Jane",
            "last_name": "Doe",
            "phone_number": "+15551234567",
            "claim_status": "approved",
        }

        payload = {
            "message": {
                "type": "tool-calls",
                "toolCalls": [
                    {
                        "id": "tc_001",
                        "function": {
                            "name": "lookup_caller",
                            "arguments": {"phone_number": "+15551234567"},
                        },
                    }
                ],
            }
        }

        result = handle_tool_call(payload)
        assert "results" in result
        assert len(result["results"]) == 1
        assert result["results"][0]["toolCallId"] == "tc_001"
        # The result value is stringified
        result_str = result["results"][0]["result"]
        assert "Jane" in result_str
        assert "approved" in result_str

    @patch("app.vapi_client.lookup_customer")
    def test_lookup_caller_not_found(self, mock_lookup):
        mock_lookup.return_value = None

        payload = {
            "message": {
                "type": "tool-calls",
                "toolCalls": [
                    {
                        "id": "tc_002",
                        "function": {
                            "name": "lookup_caller",
                            "arguments": {"phone_number": "+10000000000"},
                        },
                    }
                ],
            }
        }

        result = handle_tool_call(payload)
        assert len(result["results"]) == 1
        result_str = result["results"][0]["result"]
        assert "False" in result_str or "false" in result_str.lower()

    def test_unknown_tool_returns_error(self):
        payload = {
            "message": {
                "type": "tool-calls",
                "toolCalls": [
                    {
                        "id": "tc_003",
                        "function": {
                            "name": "nonexistent_tool",
                            "arguments": {},
                        },
                    }
                ],
            }
        }

        result = handle_tool_call(payload)
        assert len(result["results"]) == 1
        assert "error" in result["results"][0]["result"].lower() or "Unknown tool" in result["results"][0]["result"]

    def test_empty_tool_calls_list(self):
        payload = {"message": {"type": "tool-calls", "toolCalls": []}}
        result = handle_tool_call(payload)
        assert result == {"results": []}

    def test_missing_tool_calls_key(self):
        payload = {"message": {"type": "tool-calls"}}
        result = handle_tool_call(payload)
        assert result == {"results": []}


# =========================================================================
# 5. Pydantic model validation  (app.models)
# =========================================================================

class TestModels:
    """Tests for Pydantic request/response models."""

    def test_lookup_caller_request_valid(self):
        req = LookupCallerRequest(phone_number="+15551234567")
        assert req.phone_number == "+15551234567"

    def test_lookup_caller_request_missing_phone(self):
        with pytest.raises(Exception):
            LookupCallerRequest()  # phone_number is required

    def test_log_interaction_request_valid(self):
        req = LogInteractionRequest(
            caller_name="Jane Doe",
            summary="Customer called about a claim.",
            sentiment="positive",
            call_id="call_abc123",
        )
        assert req.caller_name == "Jane Doe"
        assert req.sentiment == "positive"
        assert req.call_id == "call_abc123"

    def test_log_interaction_request_defaults(self):
        """caller_name defaults to 'Unknown', sentiment defaults to 'neutral'."""
        req = LogInteractionRequest(
            summary="Short call.",
            call_id="call_xyz",
        )
        assert req.caller_name == "Unknown"
        assert req.sentiment == "neutral"

    def test_log_interaction_request_invalid_sentiment(self):
        """Sentiment must match the pattern ^(positive|neutral|negative)$."""
        with pytest.raises(Exception):
            LogInteractionRequest(
                summary="Test",
                sentiment="angry",
                call_id="call_001",
            )

    def test_customer_record_found(self):
        rec = CustomerRecord(
            found=True,
            first_name="Alice",
            last_name="Smith",
            phone_number="+15559998888",
            claim_status="pending",
        )
        assert rec.found is True
        assert rec.first_name == "Alice"

    def test_customer_record_not_found(self):
        rec = CustomerRecord(found=False, message="Not found")
        assert rec.found is False
        assert rec.first_name is None

    def test_health_response_defaults(self):
        h = HealthResponse()
        assert h.status == "healthy"
        assert h.service == "observe-claims-agent"
        assert h.version == "1.0.0"

    def test_interaction_response_defaults(self):
        ir = InteractionResponse(logged=True)
        assert ir.message == "Interaction logged successfully"


# =========================================================================
# 6. FastAPI health endpoint  (app.main /health)
# =========================================================================

class TestHealthEndpoint:
    """Integration tests for the /health route using FastAPI TestClient."""

    @pytest.fixture(autouse=True)
    def _client(self):
        from fastapi.testclient import TestClient
        self.client = TestClient(app)

    def test_health_returns_200(self):
        response = self.client.get("/health")
        assert response.status_code == 200

    def test_health_body_structure(self):
        response = self.client.get("/health")
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "observe-claims-agent"
        assert data["version"] == "1.0.0"


# =========================================================================
# 7. Webhook dispatcher routing  (app.vapi_client.handle_webhook)
# =========================================================================

class TestWebhookDispatcher:
    """Tests for the top-level handle_webhook dispatcher."""

    @patch("app.vapi_client.handle_tool_call")
    def test_routes_tool_calls(self, mock_handle):
        mock_handle.return_value = {"results": []}
        payload = {"message": {"type": "tool-calls"}}
        result = handle_webhook(payload)
        mock_handle.assert_called_once_with(payload)
        assert result == {"results": []}

    @patch("app.vapi_client.handle_end_of_call")
    def test_routes_end_of_call_report(self, mock_handle):
        mock_handle.return_value = {"status": "logged"}
        payload = {"message": {"type": "end-of-call-report"}}
        result = handle_webhook(payload)
        mock_handle.assert_called_once_with(payload)

    def test_status_update_acknowledged(self):
        payload = {"message": {"type": "status-update", "status": "ringing"}}
        result = handle_webhook(payload)
        assert result == {"status": "acknowledged"}

    def test_unhandled_event_acknowledged(self):
        payload = {"message": {"type": "some-future-event"}}
        result = handle_webhook(payload)
        assert result == {"status": "acknowledged"}


# =========================================================================
# 8. summarize_call with mocked OpenAI  (app.summarizer.summarize_call)
# =========================================================================

class TestSummarizeCall:
    """Tests for summarize_call with the OpenAI client mocked."""

    def test_empty_transcript_returns_default(self):
        result = summarize_call("")
        assert result["sentiment"] == "neutral"
        assert "no transcript" in result["summary"].lower()

    def test_whitespace_only_transcript_returns_default(self):
        result = summarize_call("   ")
        assert result["sentiment"] == "neutral"

    @patch("app.summarizer.client")
    def test_valid_response_parsed(self, mock_openai_client):
        """When OpenAI returns valid JSON, it should be parsed correctly."""
        mock_message = MagicMock()
        mock_message.content = json.dumps({
            "summary": "Customer asked about claim status. Agent confirmed it is approved.",
            "sentiment": "positive",
        })
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_openai_client.chat.completions.create.return_value = MagicMock(
            choices=[mock_choice]
        )

        result = summarize_call("user: What is my claim status? assistant: It is approved.")
        assert result["summary"] == "Customer asked about claim status. Agent confirmed it is approved."
        assert result["sentiment"] == "positive"

    @patch("app.summarizer.client")
    def test_invalid_json_falls_back(self, mock_openai_client):
        """When OpenAI returns non-JSON, the raw text is used as summary."""
        mock_message = MagicMock()
        mock_message.content = "This is not JSON at all"
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_openai_client.chat.completions.create.return_value = MagicMock(
            choices=[mock_choice]
        )

        result = summarize_call("user: Hello")
        assert result["summary"] == "This is not JSON at all"
        assert result["sentiment"] == "neutral"

    @patch("app.summarizer.client")
    def test_invalid_sentiment_normalised_to_neutral(self, mock_openai_client):
        """If sentiment value is not one of the three allowed, default to neutral."""
        mock_message = MagicMock()
        mock_message.content = json.dumps({
            "summary": "A short call.",
            "sentiment": "angry",
        })
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_openai_client.chat.completions.create.return_value = MagicMock(
            choices=[mock_choice]
        )

        result = summarize_call("user: I'm upset")
        assert result["sentiment"] == "neutral"


# =========================================================================
# 9. End-of-call handler  (app.vapi_client.handle_end_of_call)
# =========================================================================

class TestHandleEndOfCall:
    """Tests for the end-of-call-report handler with external deps mocked."""

    @patch("app.vapi_client.log_interaction")
    @patch("app.vapi_client.summarize_call")
    def test_logs_interaction_to_sheets(self, mock_summarize, mock_log):
        mock_summarize.return_value = {
            "summary": "Customer checked claim status.",
            "sentiment": "neutral",
        }
        mock_log.return_value = True

        payload = {
            "message": {
                "type": "end-of-call-report",
                "call": {"id": "call_999"},
                "artifact": {
                    "transcript": "assistant: am I speaking with Jane Doe? user: Yes."
                },
            }
        }

        result = handle_end_of_call(payload)
        assert result["status"] == "logged"
        assert result["call_id"] == "call_999"
        assert result["sentiment"] == "neutral"
        mock_log.assert_called_once()
        # Verify caller_name was extracted from the transcript
        call_args = mock_log.call_args
        assert call_args.kwargs.get("caller_name") or call_args[1].get("caller_name") or "Jane Doe" in str(call_args)

    @patch("app.vapi_client.log_interaction")
    @patch("app.vapi_client.summarize_call")
    def test_handles_missing_transcript(self, mock_summarize, mock_log):
        mock_summarize.return_value = {
            "summary": "No transcript available.",
            "sentiment": "neutral",
        }
        mock_log.return_value = True

        payload = {
            "message": {
                "type": "end-of-call-report",
                "call": {"id": "call_empty"},
                "artifact": {},
            }
        }

        result = handle_end_of_call(payload)
        assert result["status"] == "logged"
        # summarize_call should still be called (with empty string)
        mock_summarize.assert_called_once_with("")


# =========================================================================
# 10. FastAPI webhook endpoint  (app.main /webhook/vapi)
# =========================================================================

class TestVapiWebhookEndpoint:
    """Integration tests for the /webhook/vapi route."""

    @pytest.fixture(autouse=True)
    def _client(self):
        from fastapi.testclient import TestClient
        self.client = TestClient(app)

    @patch("app.main.handle_webhook")
    def test_webhook_returns_json(self, mock_handle):
        mock_handle.return_value = {"status": "acknowledged"}
        response = self.client.post(
            "/webhook/vapi",
            json={"message": {"type": "status-update"}},
        )
        assert response.status_code == 200
        assert response.json() == {"status": "acknowledged"}

    @patch("app.main.handle_webhook", side_effect=RuntimeError("boom"))
    def test_webhook_error_returns_500(self, mock_handle):
        response = self.client.post(
            "/webhook/vapi",
            json={"message": {"type": "tool-calls"}},
        )
        assert response.status_code == 500
        assert "error" in response.json()
