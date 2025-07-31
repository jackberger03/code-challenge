
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional
from pydantic import BaseModel


class EnvelopeStatus(str, Enum):
    """Enum for envelope statuses - makes code more readable and prevents typos."""
    CREATED = "created"
    SENT = "sent"
    DELIVERED = "delivered"
    SIGNED = "signed"
    COMPLETED = "completed"
    DECLINED = "declined"
    VOIDED = "voided"
    
class SigningSessionResponse(BaseModel): 
    """Response model for signing session creation."""
    signing_url: str # FIXME: Change from str to HttpUrl
    session_id: str 
    envelope_id: str
    expires_at: datetime
    client_id: str

class SigningStatusResponse(BaseModel):
    """Response model for signing session status."""
    session_id: str
    envelope_id: str
    status: EnvelopeStatus
    signed_at: Optional[datetime] = None
    declined_at: Optional[datetime] = None
    decline_reason: Optional[str] = None
    documents_available: bool = False

class WebhookEvent(BaseModel):
    """Model for webhook events from DocuSign."""
    event: str
    apiVersion: str
    uri: str
    retryCount: int
    configurationId: int
    generatedDateTime: datetime
    data: Dict[str, Any]