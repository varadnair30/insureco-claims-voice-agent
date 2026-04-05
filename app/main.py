"""FastAPI application for Observe Insurance Claims Voice Agent backend."""

import structlog
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from app.models import (
    LookupCallerRequest,
    LogInteractionRequest,
    CustomerRecord,
    InteractionResponse,
    HealthResponse,
)
from app.sheets import lookup_customer, log_interaction
from app.vapi_client import handle_webhook

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer() if True else structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(0),
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)

app = FastAPI(
    title="Observe Insurance Claims Agent",
    description="Backend API for the Observe Insurance Claims Voice Assistant",
    version="1.0.0",
)


@app.get("/demo")
async def demo_page():
    """Serve the web call demo page."""
    return FileResponse("demo/web_call.html")


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint for monitoring and container orchestration."""
    return HealthResponse()


@app.post("/lookup-caller", response_model=CustomerRecord)
async def lookup_caller(request: LookupCallerRequest):
    """Look up a customer by phone number in the customers database.

    Called by the VAPI agent via tool call when a caller provides their phone number.
    """
    logger.info("lookup_caller_request", phone=request.phone_number)

    try:
        customer = lookup_customer(request.phone_number)
        if customer:
            return CustomerRecord(
                found=True,
                first_name=customer["first_name"],
                last_name=customer["last_name"],
                phone_number=customer["phone_number"],
                claim_status=customer["claim_status"],
            )
        return CustomerRecord(found=False, message="No customer found with that phone number")
    except Exception as e:
        logger.error("lookup_caller_error", error=str(e))
        return CustomerRecord(found=False, message="Unable to look up customer at this time")


@app.post("/log-interaction", response_model=InteractionResponse)
async def log_interaction_endpoint(request: LogInteractionRequest):
    """Log a post-call interaction record to the interactions database.

    Called after each call ends to record the call summary, sentiment, and metadata.
    """
    logger.info("log_interaction_request", caller=request.caller_name, call_id=request.call_id)

    try:
        success = log_interaction(
            caller_name=request.caller_name,
            summary=request.summary,
            sentiment=request.sentiment,
            call_id=request.call_id,
        )
        if success:
            return InteractionResponse(logged=True)
        return InteractionResponse(logged=False, message="Failed to log interaction")
    except Exception as e:
        logger.error("log_interaction_error", error=str(e))
        return InteractionResponse(logged=False, message="Unable to log interaction at this time")


@app.post("/webhook/vapi")
async def vapi_webhook(request: Request):
    """Handle incoming VAPI webhook events.

    Processes tool-calls (lookup_caller, log_interaction) and end-of-call reports.
    VAPI sends various event types; we dispatch to the appropriate handler.
    """
    try:
        payload = await request.json()
        logger.info("vapi_webhook_received", payload_type=payload.get("message", {}).get("type"))
        result = handle_webhook(payload)
        return JSONResponse(content=result)
    except Exception as e:
        logger.error("vapi_webhook_error", error=str(e))
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error processing webhook"},
        )


if __name__ == "__main__":
    import uvicorn
    from app.config import settings

    uvicorn.run("app.main:app", host="0.0.0.0", port=settings.port, reload=True)
