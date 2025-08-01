
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional
from pydantic import BaseModel
from pydantic import BaseModel, EmailStr, field_validator

class EnvelopeStatus(str, Enum):
    """Enum for envelope statuses - makes code more readable and prevents typos."""
    CREATED = "created"
    SENT = "sent"
    DELIVERED = "delivered"
    SIGNED = "signed"
    COMPLETED = "completed"
    DECLINED = "declined"
    VOIDED = "voided"


class SignerInfo(BaseModel):
    """Information about the signer for Dropbox Sign embedded signing."""
    email: EmailStr
    name: str
    role_name: str  # maps to "role" in Dropbox Sign
    phone: Optional[str] = None

    @field_validator('name')
    @classmethod
    def name_must_not_be_empty(cls, value: str) -> str:
        """Ensure that the name is not empty."""
        if not value.strip():
            raise ValueError("Name must not be empty")
        if len(value) < 2:
            raise ValueError("Name must be at least 2 characters long")
        # Dropbox Sign accepts names with spaces
        return value.strip()

    @field_validator('phone')
    @classmethod
    def phone_basic_validation(cls, value: Optional[str]) -> Optional[str]:
        """Basic phone validation."""
        if value and not value.strip():
            raise ValueError("Phone must not be empty")
        if value and len(value) < 10:
            raise ValueError("Phone must be at least 10 characters long")
        return value

    # fastapi's email validation is sufficient for EmailStr
   
    
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