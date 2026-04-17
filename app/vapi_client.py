"""VAPI webhook handler for processing call events."""

import structlog

from app.sheets import lookup_customer, log_interaction
from app.summarizer import summarize_call

logger = structlog.get_logger(__name__)


def handle_tool_call(payload: dict) -> dict:
    """Process a VAPI tool-call request and return the appropriate response.

    VAPI sends tool calls when the agent invokes a function defined in its config.
    We handle one tool: lookup_caller.
    Post-call logging is handled exclusively by the end-of-call-report webhook,
    which has access to the real VAPI call ID and full transcript.
    """
    message = payload.get("message", {})
    tool_calls = message.get("toolCalls", [])

    if not tool_calls:
        logger.warning("no_tool_calls_in_payload")
        return {"results": []}

    results = []
    for tool_call in tool_calls:
        tool_name = tool_call.get("function", {}).get("name", "")
        arguments = tool_call.get("function", {}).get("arguments", {})
        tool_call_id = tool_call.get("id", "")

        logger.info("processing_tool_call", tool=tool_name, args=arguments)

        if tool_name == "lookup_caller":
            result = _handle_lookup(arguments)
        else:
            logger.warning("unknown_tool_call", tool=tool_name)
            result = {"error": f"Unknown tool: {tool_name}"}

        results.append({"toolCallId": tool_call_id, "result": str(result)})

    return {"results": results}


def _handle_lookup(arguments: dict) -> dict:
    """Handle the lookup_caller tool call."""
    phone = arguments.get("phone_number", "")
    if not phone:
        return {"error": "No phone number provided", "found": False}

    customer = lookup_customer(phone)
    if customer:
        return {
            "found": True,
            "first_name": customer["first_name"],
            "last_name": customer["last_name"],
            "claim_status": customer["claim_status"],
        }
    return {"found": False, "message": "No customer found with that phone number"}


def handle_end_of_call(payload: dict) -> dict:
    """Process the end-of-call webhook event.

    This is the SOLE logging mechanism for all calls. It fires after every call
    ends (regardless of how it ended) and has access to the real VAPI call ID
    and the full conversation transcript.

    Flow: extract transcript -> GPT-4o-mini summarizes -> write to Google Sheets
    """
    message = payload.get("message", {})
    call = message.get("call", {})
    call_id = call.get("id", "unknown")

    logger.info(
        "end_of_call_received",
        call_id=call_id,
        message_keys=list(message.keys()),
    )

    # Extract transcript — VAPI puts it in different places depending on version
    artifact = message.get("artifact", {})
    transcript = artifact.get("transcript", "")
    if not transcript:
        # Fallback: build transcript from messages array
        messages = artifact.get("messages", [])
        if messages:
            transcript = " ".join(
                f"{m.get('role', 'unknown')}: {m.get('content', '')}"
                for m in messages if m.get("content")
            )

    logger.info(
        "end_of_call_processing",
        call_id=call_id,
        transcript_length=len(transcript),
    )

    # Generate caller name, summary, and sentiment from transcript using GPT-4o-mini
    analysis = summarize_call(transcript)
    caller_name = analysis.get("caller_name", "Unknown")

    # Fallback: if LLM didn't identify a caller, try call metadata or regex on transcript
    if caller_name == "Unknown":
        caller_name = _extract_caller_name_from_transcript(transcript, call)

    # Log to Google Sheets
    log_interaction(
        caller_name=caller_name,
        summary=analysis["summary"],
        sentiment=analysis["sentiment"],
        call_id=call_id,
    )

    logger.info(
        "end_of_call_logged",
        call_id=call_id,
        sentiment=analysis["sentiment"],
    )

    return {
        "status": "logged",
        "call_id": call_id,
        "summary": analysis["summary"],
        "sentiment": analysis["sentiment"],
    }


def _extract_caller_name_from_transcript(transcript: str, call: dict) -> str:
    """Extract the caller name from call metadata or transcript.

    Priority:
    1. Call metadata (if set during the conversation)
    2. Parse transcript for identity confirmation pattern
    3. Default to "Unknown"
    """
    # Check call metadata first
    metadata = call.get("metadata", {})
    if metadata:
        first = metadata.get("first_name", "")
        last = metadata.get("last_name", "")
        if first or last:
            return f"{first} {last}".strip()

    # Parse transcript for "Am I speaking with {name}?" followed by confirmation
    if transcript:
        import re
        match = re.search(
            r"am I speaking with ([A-Z][a-z]+ [A-Z][a-z]+)\?", transcript
        )
        if match:
            # Check if the user confirmed after this
            name = match.group(1)
            # Find text after the name confirmation
            after_match = transcript[match.end():]
            # Look for confirmation words in the next ~100 chars
            confirmation_zone = after_match[:100].lower()
            if any(word in confirmation_zone for word in ["yes", "yeah", "yep", "correct", "that's me", "speaking"]):
                return name

    return "Unknown"


def handle_webhook(payload: dict) -> dict:
    """Main webhook dispatcher. Routes VAPI events to appropriate handlers."""
    message = payload.get("message", {})
    event_type = message.get("type", "")

    logger.info("webhook_received", event_type=event_type)

    if event_type == "tool-calls":
        return handle_tool_call(payload)
    elif event_type == "end-of-call-report":
        return handle_end_of_call(payload)
    elif event_type == "status-update":
        status = message.get("status", "")
        logger.info("call_status_update", status=status)
        return {"status": "acknowledged"}
    elif event_type == "hang":
        logger.info("call_hang_event")
        return {"status": "acknowledged"}
    elif event_type == "speech-update":
        return {"status": "acknowledged"}
    elif event_type == "transcript":
        return {"status": "acknowledged"}
    else:
        logger.info("unhandled_webhook_event", event_type=event_type)
        return {"status": "acknowledged"}
