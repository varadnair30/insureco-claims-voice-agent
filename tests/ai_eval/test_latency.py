"""
Latency regression tests for pure-Python pipeline functions.

SCOPE: Only functions with no external I/O — normalize_phone() and
_extract_caller_name_from_transcript(). These run without mocking and
measure real wall-clock time. If a refactor makes either function
significantly slower, these catch it.

NOT COVERED HERE: lookup_customer() and summarize_call() latency — those
are dominated by Google Sheets / OpenAI network time, not our code. Mocking
them would only measure mock overhead, which is meaningless.
"""

import os
import sys
import time

import pytest

os.environ.setdefault("VAPI_API_KEY", "test-vapi-key")
os.environ.setdefault("OPENAI_API_KEY", "test-openai-key")
os.environ.setdefault("GOOGLE_CREDENTIALS_JSON", '{"type":"service_account","project_id":"test"}')
os.environ.setdefault("SPREADSHEET_ID", "test-spreadsheet-id")

from unittest.mock import patch

with patch("openai.OpenAI"):
    from app.sheets import normalize_phone
    from app.vapi_client import _extract_caller_name_from_transcript


# ---------------------------------------------------------------------------
# Thresholds — tighten these over time as you optimise.
# They are deliberately generous: we're guarding against accidental O(n²)
# regressions, not micro-benchmarking.
# ---------------------------------------------------------------------------
NORMALIZE_PHONE_BATCH_MS = 200     # 1 000 calls must finish in < 200 ms
EXTRACT_NAME_SINGLE_MS   = 50      # single long transcript must finish in < 50 ms


def _percentile(data: list[float], p: float) -> float:
    sorted_data = sorted(data)
    idx = max(0, int(len(sorted_data) * p / 100) - 1)
    return sorted_data[idx]


# ---------------------------------------------------------------------------
# normalize_phone latency
# ---------------------------------------------------------------------------

class TestNormalizePhoneLatency:
    """
    normalize_phone() is called on every lookup_caller tool-call.
    It must remain fast even when processing many phone numbers in a tight loop
    (e.g., regression test runs, batch imports).
    """

    SAMPLE_INPUTS = [
        "555-867-5309",
        "(555) 123-4567",
        "5551234567",
        "+15559998888",
        "15558675309",
        "  555 867 5309  ",
        "",
        "abc",
        "1-800-555-CLAIM",
    ]

    def test_batch_1000_calls_under_threshold(self):
        """1 000 normalize_phone() calls must complete in under 200 ms."""
        inputs = (self.SAMPLE_INPUTS * 112)[:1000]  # exactly 1 000 items

        start = time.perf_counter()
        for phone in inputs:
            normalize_phone(phone)
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert elapsed_ms < NORMALIZE_PHONE_BATCH_MS, (
            f"normalize_phone latency regression: "
            f"1 000 calls took {elapsed_ms:.1f}ms > {NORMALIZE_PHONE_BATCH_MS}ms threshold.\n"
            f"Check for accidental O(n) work inside the function."
        )

    def test_per_call_p95_under_1ms(self):
        """p95 per-call time should be under 1 ms (it's pure Python + phonenumbers)."""
        latencies = []
        for _ in range(200):
            for phone in self.SAMPLE_INPUTS:
                t0 = time.perf_counter()
                normalize_phone(phone)
                latencies.append((time.perf_counter() - t0) * 1000)

        p95 = _percentile(latencies, 95)
        assert p95 < 1.0, (
            f"normalize_phone p95 latency regression: {p95:.3f}ms > 1ms.\n"
            f"Expected sub-millisecond per-call time for a pure-Python function."
        )

    def test_latency_baseline_report(self, capsys):
        """Print a latency report — run manually before model/library upgrades."""
        latencies = []
        for _ in range(500):
            for phone in self.SAMPLE_INPUTS:
                t0 = time.perf_counter()
                normalize_phone(phone)
                latencies.append((time.perf_counter() - t0) * 1000)

        with capsys.disabled():
            print(f"\n=== normalize_phone Latency Report ({len(latencies)} samples) ===")
            print(f"  p50:  {_percentile(latencies, 50):.3f}ms")
            print(f"  p95:  {_percentile(latencies, 95):.3f}ms")
            print(f"  p99:  {_percentile(latencies, 99):.3f}ms")
            print(f"  max:  {max(latencies):.3f}ms")


# ---------------------------------------------------------------------------
# _extract_caller_name_from_transcript latency
# ---------------------------------------------------------------------------

class TestExtractCallerNameLatency:
    """
    _extract_caller_name_from_transcript() runs on every end-of-call-report
    as a fallback when the LLM didn't identify the caller. It processes the
    full call transcript, which can be long.
    """

    SHORT_TRANSCRIPT = (
        "assistant: am I speaking with Sarah Johnson? "
        "user: Yes that's correct."
    )

    LONG_TRANSCRIPT = " ".join([
        "assistant: Hello, thank you for calling InsureCo.",
        "user: Hi I need help with my claim.",
        "assistant: Of course. Could you share your phone number?",
        "user: Sure it is 555-867-5309.",
        "assistant: One moment.",
        "assistant: Great I found your account. am I speaking with Sarah Johnson?",
        "user: Yes that is me.",
        "assistant: Thank you Sarah. Your claim is currently pending review.",
        "user: How long will that take?",
        "assistant: Typically 5 to 7 business days.",
        "user: OK thanks goodbye.",
        "assistant: Thank you for calling InsureCo. Have a wonderful day.",
    ] * 20)  # ~20x repeated to simulate a verbose transcript

    def test_short_transcript_under_threshold(self):
        """Single short transcript must extract in under 50 ms."""
        t0 = time.perf_counter()
        _extract_caller_name_from_transcript(self.SHORT_TRANSCRIPT, call={})
        elapsed_ms = (time.perf_counter() - t0) * 1000

        assert elapsed_ms < EXTRACT_NAME_SINGLE_MS, (
            f"extract_caller_name latency regression on short transcript: "
            f"{elapsed_ms:.1f}ms > {EXTRACT_NAME_SINGLE_MS}ms."
        )

    def test_long_transcript_under_threshold(self):
        """Long transcript (repeated 20×) must still finish under 50 ms.
        Guards against regex patterns that are accidentally O(n²) on long input."""
        t0 = time.perf_counter()
        result = _extract_caller_name_from_transcript(self.LONG_TRANSCRIPT, call={})
        elapsed_ms = (time.perf_counter() - t0) * 1000

        assert elapsed_ms < EXTRACT_NAME_SINGLE_MS, (
            f"extract_caller_name latency regression on long transcript "
            f"({len(self.LONG_TRANSCRIPT)} chars): {elapsed_ms:.1f}ms > {EXTRACT_NAME_SINGLE_MS}ms.\n"
            f"Possible catastrophic backtracking in the regex."
        )
        # Correctness check — must still find the name despite length
        assert result == "Sarah Johnson", (
            f"Latency optimisation must not break correctness: got '{result}'"
        )

    def test_latency_baseline_report(self, capsys):
        """Print a latency report across transcript sizes."""
        cases = [
            ("short",  self.SHORT_TRANSCRIPT),
            ("long",   self.LONG_TRANSCRIPT),
            ("empty",  ""),
        ]
        with capsys.disabled():
            print(f"\n=== extract_caller_name Latency Report ===")
            for label, transcript in cases:
                latencies = []
                for _ in range(200):
                    t0 = time.perf_counter()
                    _extract_caller_name_from_transcript(transcript, call={})
                    latencies.append((time.perf_counter() - t0) * 1000)
                print(
                    f"  [{label:6s}] p50={_percentile(latencies,50):.3f}ms  "
                    f"p95={_percentile(latencies,95):.3f}ms  "
                    f"max={max(latencies):.3f}ms  "
                    f"(transcript len={len(transcript)})"
                )
