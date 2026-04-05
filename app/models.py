"""Pydantic models for API request/response validation."""

from typing import Optional
from pydantic import BaseModel, Field


# --- Request Models ---

class LookupCallerRequest(BaseModel):
    phone_number: str = Field(..., description="Phone number to look up", examples=["+15551234567"])


class LogInteractionRequest(BaseModel):
    caller_name: str = Field(default="Unknown", description="Authenticated caller name")
    summary: str = Field(..., description="2-3 sentence call summary")
    sentiment: str = Field(
        default="neutral",
        description="Call sentiment",
        pattern="^(positive|neutral|negative)$",
    )
    call_id: str = Field(..., description="VAPI call ID")


# --- Response Models ---

class CustomerRecord(BaseModel):
    found: bool
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone_number: Optional[str] = None
    claim_status: Optional[str] = None
    message: Optional[str] = None


class InteractionResponse(BaseModel):
    logged: bool
    message: str = "Interaction logged successfully"


class HealthResponse(BaseModel):
    status: str = "healthy"
    service: str = "observe-claims-agent"
    version: str = "1.0.0"
