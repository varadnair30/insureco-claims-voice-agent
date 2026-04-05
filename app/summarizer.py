"""Post-call summarization and sentiment analysis using GPT-4o-mini."""

import structlog
from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import settings

logger = structlog.get_logger(__name__)

client = OpenAI(api_key=settings.openai_api_key)

SUMMARIZE_PROMPT = """You are analyzing a customer support call transcript for an insurance claims assistant.

Given the transcript below, provide:
1. A concise 2-3 sentence summary of what was discussed and the outcome.
2. The overall sentiment of the caller: "positive", "neutral", or "negative".

Respond in exactly this JSON format (no markdown, no extra text):
{{"summary": "...", "sentiment": "positive|neutral|negative"}}

Transcript:
{transcript}"""


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
)
def summarize_call(transcript: str) -> dict:
    """Generate a summary and sentiment analysis from a call transcript.

    Returns dict with 'summary' (str) and 'sentiment' (str).
    Falls back to defaults if parsing fails.
    """
    if not transcript or not transcript.strip():
        logger.warning("empty_transcript")
        return {"summary": "Call ended with no transcript available.", "sentiment": "neutral"}

    logger.info("summarizing_call", transcript_length=len(transcript))

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a concise call analyst. Respond only in valid JSON."},
            {"role": "user", "content": SUMMARIZE_PROMPT.format(transcript=transcript)},
        ],
        temperature=0.3,
        max_tokens=300,
    )

    raw = response.choices[0].message.content.strip()
    logger.info("summarizer_raw_response", response=raw)

    import json
    try:
        result = json.loads(raw)
        if "summary" in result and "sentiment" in result:
            result["sentiment"] = result["sentiment"].lower().strip()
            if result["sentiment"] not in ("positive", "neutral", "negative"):
                result["sentiment"] = "neutral"
            return result
    except (json.JSONDecodeError, KeyError):
        logger.error("summarizer_parse_error", raw=raw)

    return {"summary": raw[:500], "sentiment": "neutral"}
