from fastapi import FastAPI, HTTPException, Depends, Request, BackgroundTasks
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional, Dict, Any, cast
import os 
from datetime import datetime, timedelta
import logging 
from docusign_esign import ApiClient, EnvelopesApi, EnvelopeDefinition, Document, Signer, SignHere, Tabs, Recipients, RecipientViewRequest
from docusign_esign.client.api_exception import ApiException
import base64
import uuid
import hmac 
import hashlib
from enum import Enum
import json
import io 

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

DOCUSIGN_CONFIG = {
    "integration_key": os.getenv("DOCUSIGN_INTEGRATION_KEY"),
    "user_id": os.getenv("DOCUSIGN_USER_ID"),
    "account_id": os.getenv("DOCUSIGN_ACCOUNT_ID"),
    "base_path": os.getenv("DOCUSIGN_BASE_PATH"),
    "oauth_base_path": os.getenv("DOCUSIGN_OAUTH_BASE_PATH"),
    "private_key_path": os.getenv("DOCUSIGN_PRIVATE_KEY_PATH"),
    "template_id": os.getenv("DOCUSIGN_TEMPLATE_ID"),
    "redirect_uri": os.getenv("DOCUSIGN_REDIRECT_URI"),
    "webhook_secret": os.getenv("DOCUSIGN_WEBHOOK_SECRET"),
}

signing_sessions: Dict[str, Dict[str, Any]] = {}
envelope_to_session: Dict[str, str] = {}

class SignerInfo(BaseModel):
    email: EmailStr
    name: str
    role_name: str
    phone: Optional[str] = None

    @field_validator('name')
    @classmethod
    def name_must_not_be_empty(cls, value: str) -> str:
        """Ensure that the name is not empty."""
        if not value.strip():
            raise ValueError("Name must not be empty")
        if len(value) < 2:
            raise ValueError("Name must be at least 2 characters long")
        if not value.isalpha():
            raise ValueError("Name must contain only alphabetic characters")
        return value

    @field_validator('phone')
    @classmethod
    def phone_basic_validation(cls, value: Optional[str]) -> Optional[str]:
        """Basic phone validation to ensure it is not empty."""
        if value and not value.strip():
            raise ValueError("Phone must not be empty")
        if value and not value.isdigit():
            raise ValueError("Phone must contain only digits")
        if value and len(value) < 10:
            raise ValueError("Phone must be at least 10 digits long")
        return value
    
# Enum for envelope statuses - makes code more readable and prevents typos
class EnvelopeStatus(str, Enum):
    CREATED = "created"
    SENT = "sent"
    DELIVERED = "delivered"
    SIGNED = "signed"
    COMPLETED = "completed"
    DECLINED = "declined"
    VOIDED = "voided"
    
class SigningSessionResponse(BaseModel): 
    """Response model for signing session creation."""
    signing_url: str
    session_id: str 
    envelope_id: str
    expires_at: datetime

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

class TokenManager:
    """
    Manages DocuSign OAuth tokens with automatic refresh.
    This implements the strategy we discussed about handling authentication efficiently.
    """
    def __init__(self):
        self._token: Optional[str] = None
        self._token_expires_at: Optional[datetime] = None
        self._api_client: Optional[ApiClient] = None
    
    def get_api_client(self) -> ApiClient:
        """
        Returns an authenticated API client, refreshing the token if necessary.
        This method implements smart token management - only authenticating when needed.
        """
        # Check if we need a new token (first time or expired)
        if not self._token or not self._token_expires_at or datetime.utcnow() >= self._token_expires_at:
            logger.info("Obtaining new DocuSign access token...")
            self._refresh_token()
        assert self._api_client is not None
        return self._api_client
    
    def _refresh_token(self):
        """
        Obtains a new access token using JWT authentication.
        DocuSign's JWT flow is perfect for server applications.
        """
        api_client = ApiClient()
        api_client.set_base_path(DOCUSIGN_CONFIG["base_path"])
        private_key_path = DOCUSIGN_CONFIG["private_key_path"]
        if private_key_path is None:
            raise RuntimeError("DOCUSIGN_PRIVATE_KEY_PATH env var not set")

        with open(private_key_path, "rb") as key_file:
            private_key = key_file.read()
        
        try:
            # Request token with 1 hour lifetime (3600 seconds)
            token_response: Any = api_client.request_jwt_user_token(
                client_id=DOCUSIGN_CONFIG["integration_key"],
                user_id=DOCUSIGN_CONFIG["user_id"],
                oauth_host_name=DOCUSIGN_CONFIG["oauth_base_path"],
                private_key_bytes=private_key,
                expires_in=3600,
                scopes=["signature", "impersonation"]
            )
            
            # Store the token and calculate expiration (subtract 5 minutes for safety margin)
            self._token = cast(str, token_response.access_token)
            self._token_expires_at = datetime.now() + timedelta(seconds=3600 - 300)
            
            # Configure the API client with the new token
            self._api_client = api_client
            self._api_client.set_default_header("Authorization", f"Bearer {self._token}")
            
            logger.info("Successfully obtained new access token")
            
        except Exception as e:
            logger.error(f"Failed to obtain access token: {str(e)}")
            raise HTTPException(status_code=500, detail="Authentication with DocuSign failed")

# Create a singleton token manager instance
token_manager = TokenManager()

def get_envelopes_api() -> EnvelopesApi:
    """
    Dependency to get an authenticated EnvelopesApi instance.
    This ensures we reuse the token efficiently across requests.
    """
    api_client = token_manager.get_api_client()
    return EnvelopesApi(api_client)


@app.post("/create-signing-session", response_model=SigningSessionResponse)
async def create_signing_session(
    signer_info: SignerInfo, 
    envelopes_api: EnvelopesApi = Depends(get_envelopes_api)
):
    """Creates a signing session for the specified signer."""
    try: 
        session_id = str(uuid.uuid4())
        logger.info(f"Creating signing session with ID: {session_id} for signer {signer_info.email}")

        envelope_definition = create_envelope_from_template(signer_info)

        envelope_summary = envelopes_api.create_envelope(
            account_id=DOCUSIGN_CONFIG["account_id"],
            envelope_definition=envelope_definition
        )
        envelope_id = envelope_summary.envelope_id  
        logger.info(f"Envelope created with ID: {envelope_id}")

        recipient_view_request = RecipientViewRequest(
            authentication_method="none",  # handling auth at the app level
            client_user_id=session_id,  # Links this view to our signer
            recipient_id="1",  # Must match the recipient ID in the envelope
            return_url=DOCUSIGN_CONFIG["redirect_url"],
            user_name=signer_info.name,
            email=signer_info.email
        )

        recipient_view = envelopes_api.create_recipient_view(
            account_id=DOCUSIGN_CONFIG["account_id"],
            envelope_id=envelope_id,
            recipient_view_request=recipient_view_request
        )

        expires_at = datetime.now() + timedelta(minutes=5)  # Session valid for 5 minutes

        session_data = {
            "session_id": session_id,
            "envelope_id": envelope_id,
            "signer_info": signer_info.model_dump(),
            "status": EnvelopeStatus.SENT,
            "created_at": datetime.now(),
            "expires_at": expires_at,
            "signing_url": recipient_view.url
        }

        # Store in our in-memory database
        signing_sessions[session_id] = session_data
        envelope_to_session[envelope_id] = session_id  # For webhook lookups
        
        logger.info(f"Successfully created signing URL for session {session_id}")
        
        return SigningSessionResponse(
            signing_url=recipient_view.url,
            session_id=session_id,
            envelope_id=envelope_id,
            expires_at=expires_at
        )
    
    except ApiException as e:
        logger.error(f"DocuSign API error: {e.body}")
        raise HTTPException(status_code=e.status if e.status is not None else 500, detail=f"DocuSign error: {e.reason}")
    except Exception as e:
        logger.error(f"Unexpected error in create_signing_session: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to create signing session")
    
def create_envelope_from_template(signer_info: SignerInfo) -> EnvelopeDefinition:
    """
    Creates an envelope definition using a DocuSign template.
    Templates are pre-made documents with placeholder fields - perfect for repeated use.
    """
    # Create the signer object with the user's information
    signer = Signer(
        email=signer_info.email,
        name=signer_info.name,
        recipient_id="1",  # Identifies this recipient in the envelope
        routing_order="1",  # Order in which recipients sign (important for multiple signers)
        client_user_id=str(uuid.uuid4())  # Links this signer to the embedded view
    )
    
    # Package the signer into a recipients object
    recipients = Recipients(signers=[signer])
    
    # Create the envelope definition
    envelope_definition = EnvelopeDefinition(
        template_id=DOCUSIGN_CONFIG["template_id"],
        recipients=recipients,
        status="sent",  # "sent" means ready for signing, "created" would save as draft
        email_subject="Please sign this document",
        email_blurb="Thanks for your business. Please review and sign the attached document."
    )
    
    # to pre-fill template fields with data, add template roles:
    # envelope_definition.template_roles = [
    #     TemplateRole(
    #         email=signer_info.email,
    #         name=signer_info.name,
    #         role_name="signer",  # Must match the role name in your template
    #         tabs=TextTabs(text_tabs=[
    #             Text(tab_label="phone", value=signer_info.phone),
    #             Text(tab_label="address", value="123 Main St")
    #         ])
    #     )
    # ]
    
    return envelope_definition

@app.post("/docusign-webhook")
async def handle_docusign_webhook(
    request: Request,
    background_tasks: BackgroundTasks
):
    """
    Receives webhook notifications from DocuSign when envelope status changes.
    This is the PUSH mechanism - DocuSign tells us immediately when something happens.
    
    Webhooks are superior to polling because:
    1. They provide real-time updates (no delay)
    2. They reduce API calls (no constant checking)
    3. They capture all events (can't miss status changes between polls)
    """
    try:
        # Step 1: Verify the webhook is actually from DocuSign
        # This prevents malicious actors from spoofing status updates
        if DOCUSIGN_CONFIG.get("webhook_secret"):
            await verify_webhook_signature(request)
        
        # Step 2: Parse the webhook payload
        body = await request.body()
        webhook_data = json.loads(body)
        
        # DocuSign sends events in a specific structure
        event_type = webhook_data.get("event")
        envelope_id = webhook_data.get("data", {}).get("envelopeId")
        
        logger.info(f"Received webhook: {event_type} for envelope {envelope_id}")
        
        # Step 3: Handle different event types
        # DocuSign sends many events, but we care most about completion statuses
        if event_type == "envelope-completed":
            await handle_envelope_completed(envelope_id, webhook_data)
        elif event_type == "envelope-declined":
            await handle_envelope_declined(envelope_id, webhook_data)
        elif event_type == "envelope-voided":
            await handle_envelope_voided(envelope_id, webhook_data)
        elif event_type == "recipient-completed":
            # Individual recipient completed (useful for multi-signer flows)
            logger.info(f"Recipient completed signing for envelope {envelope_id}")
        
        # Step 4: Process any background tasks (like sending emails) asynchronously
        # This ensures the webhook response is fast, which DocuSign requires
        # background_tasks.add_task(send_completion_email, envelope_id)
        
        # Always return 200 OK quickly to acknowledge receipt
        # If you don't, DocuSign will retry the webhook
        return {"message": "Webhook processed successfully"}
        
    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}")
        # Still return 200 to prevent webhook retries for bad data
        return {"message": "Webhook received"}

async def verify_webhook_signature(request: Request):
    """
    Verifies that the webhook actually came from DocuSign using HMAC signature.
    This is critical for security - never trust webhooks without verification!
    """
    # Get the signature from headers
    signature = request.headers.get("X-DocuSign-Signature-1")
    if not signature:
        raise HTTPException(status_code=401, detail="Missing webhook signature")
    
    # Recreate the signature using the shared secret
    body = await request.body()
    webhook_secret = DOCUSIGN_CONFIG.get("webhook_secret")
    if webhook_secret is None:
        raise HTTPException(status_code=500, detail="Webhook secret not configured")
    expected_signature = hmac.new(
        webhook_secret.encode(),
        body,
        hashlib.sha256
    ).hexdigest()
    
    # Compare signatures (use hmac.compare_digest to prevent timing attacks)
    if not hmac.compare_digest(signature, expected_signature):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

async def handle_envelope_completed(envelope_id: str, webhook_data: dict):
    """
    Handles the envelope-completed event.
    This is called when all recipients have finished signing.
    """
    session_id = envelope_to_session.get(envelope_id)
    if not session_id:
        logger.warning(f"Received webhook for unknown envelope {envelope_id}")
        return
    
    # Update the session status
    if session_id in signing_sessions:
        signing_sessions[session_id]["status"] = EnvelopeStatus.COMPLETED
        signing_sessions[session_id]["signed_at"] = datetime.utcnow()
        signing_sessions[session_id]["documents_available"] = True
        logger.info(f"Marked session {session_id} as completed")

async def handle_envelope_declined(envelope_id: str, webhook_data: dict):
    """
    Handles when a signer declines to sign.
    This is important for user experience - the frontend needs to know why signing failed.
    """
    session_id = envelope_to_session.get(envelope_id)
    if session_id and session_id in signing_sessions:
        signing_sessions[session_id]["status"] = EnvelopeStatus.DECLINED
        signing_sessions[session_id]["declined_at"] = datetime.utcnow()
        signing_sessions[session_id]["decline_reason"] = webhook_data.get("data", {}).get("declineReason", "No reason provided")

async def handle_envelope_voided(envelope_id: str, webhook_data: dict):
    """
    Handles when an envelope is voided (cancelled).
    This might happen if the sender realizes they sent the wrong document.
    """
    session_id = envelope_to_session.get(envelope_id)
    if session_id and session_id in signing_sessions:
        signing_sessions[session_id]["status"] = EnvelopeStatus.VOIDED
        signing_sessions[session_id]["voided_at"] = datetime.utcnow()

@app.get("/signing-status/{session_id}", response_model=SigningStatusResponse)
async def get_signing_status(session_id: str):
    """
    Polling endpoint for the frontend to check signing status.
    
    Why do we need polling when we have webhooks?
    1. Webhooks might fail or be delayed
    2. The frontend needs immediate feedback
    3. Network issues might prevent webhook delivery
    4. It provides a backup mechanism for reliability
    
    The frontend typically polls this every few seconds while waiting for signing.
    """
    session_data = signing_sessions.get(session_id)
    if not session_data:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return SigningStatusResponse(
        session_id=session_id,
        envelope_id=session_data["envelope_id"],
        status=session_data["status"],
        signed_at=session_data.get("signed_at"),
        declined_at=session_data.get("declined_at"),
        decline_reason=session_data.get("decline_reason"),
        documents_available=session_data.get("documents_available", False)
    )

@app.get("/download-document/{session_id}")
async def download_signed_document(
    session_id: str,
    envelopes_api: EnvelopesApi = Depends(get_envelopes_api)
):
    """
    Downloads the completed signed document.
    This is the final step - delivering the signed document to the user.
    """
    session_data = signing_sessions.get(session_id)
    if not session_data:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if session_data["status"] != EnvelopeStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Document not yet signed")
    
    try:
        # combined=true merges all documents into a single PDF
        document_response = envelopes_api.get_document(
            account_id=DOCUSIGN_CONFIG["account_id"],
            envelope_id=session_data["envelope_id"],
            document_id="combined"  # Gets all documents in one PDF
        )
        
        # Using StreamingResponse is memory-efficient for large files
        return StreamingResponse(
            io.BytesIO(document_response),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=signed_document_{session_id}.pdf"
            }
        )
        
    except ApiException as e:
        logger.error(f"Failed to download document: {e.body}")
        raise HTTPException(status_code=500, detail="Failed to retrieve document")


@app.get("/health")
async def health_check():
    """
    Health check endpoint to verify the service is running.
    In production, you might also check DocuSign connectivity here.
    """
    return {"status": "healthy", "service": "DocuSign Signing Service"}