from fastapi import FastAPI, HTTPException, Depends, Request, BackgroundTasks
from fastapi.responses import JSONResponse, StreamingResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, Dict, Any, List
import os 
from datetime import datetime, timedelta
import logging 
import requests
import uuid
import hmac 
import hashlib
import json
import io
from app.models import EnvelopeStatus, SignerInfo, SigningSessionResponse, SigningStatusResponse 
from dotenv import load_dotenv
import base64

load_dotenv()  # Load environment variables from .env file

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = FastAPI()

# Dropbox Sign configuration
DROPBOX_SIGN_CONFIG = {
    "api_key": os.getenv("DROPBOX_SIGN_API_KEY"),
    "client_id": os.getenv("DROPBOX_SIGN_CLIENT_ID"),
    "template_id": os.getenv("DROPBOX_SIGN_TEMPLATE_ID"),
    "test_mode": os.getenv("DROPBOX_SIGN_TEST_MODE", "true").lower() == "true",
    "callback_url": os.getenv("DROPBOX_SIGN_CALLBACK_URL"),
    "api_base_url": os.getenv("DROPBOX_SIGN_API_BASE_URL", "https://api.hellosign.com/v3"),
}

# Session storage
signing_sessions: Dict[str, Dict[str, Any]] = {}
signature_request_to_session: Dict[str, str] = {}  # Maps signature_request_id to session_id
 
def get_auth_headers() -> Dict[str, str]:
    """
    Get headers for Dropbox Sign API authentication.
    Using API key authentication which is simpler than OAuth for server-to-server.
    """
    # Dropbox Sign uses Basic auth with API key as username, no password
    auth_string = f"{DROPBOX_SIGN_CONFIG['api_key']}:"
    encoded_auth = base64.b64encode(auth_string.encode()).decode() # TODO: Understand this better
    
    return {
        "Authorization": f"Basic {encoded_auth}",
        "Content-Type": "application/json"
    }

@app.post("/create-signing-session", response_model=SigningSessionResponse)
async def create_signing_session(
    signer_info: SignerInfo,
    auth_headers: Dict[str, str] = Depends(get_auth_headers)
):
    """
    Creates a signing session using Dropbox Sign embedded signing.
    This replaces the DocuSign envelope creation flow.
    """
    logger.debug(f"[1] Received /create-signing-session for email={signer_info.email}, role={signer_info.role_name}")
    try:
        
        session_id = str(uuid.uuid4())
        logger.debug(f"Creating signing session {session_id} for {signer_info.email}")
        
        # Step 1: Create embedded signature request from template
        # This is similar to creating an envelope in DocuSign
        create_url = f"{DROPBOX_SIGN_CONFIG['api_base_url']}/signature_request/create_embedded_with_template"
        
        # Prepare signers list 
        # FIXME
        signers = [{
            "role": signer_info.role_name,  # TODO: Make sure role name changes back to 'signer'
            "name": signer_info.name,
            "email_address": signer_info.email,
            "pin": None,  # Optional PIN for extra security
            "sms_phone_number": signer_info.phone if signer_info.phone else None
        }]
        
        # For form data, Dropbox Sign expects a different format
        form_data = {
            # Your API app’s client ID
            "client_id": DROPBOX_SIGN_CONFIG["client_id"],

            # The template you created in Dropbox Sign
            "template_ids[0]": DROPBOX_SIGN_CONFIG["template_id"],

            # Signer info (must match the “signer” role in your template)
            "signers[0][role]": signer_info.role_name,        # e.g. "signer"
            "signers[0][name]": signer_info.name,             # e.g. "John"
            "signers[0][email_address]": signer_info.email,   # e.g. "john.doe@example.com"

            # Test mode flag (“1” or “0”)
            "test_mode": "1" if DROPBOX_SIGN_CONFIG["test_mode"] else "0",

            # Prefill your custom textboxes #FIXME
            "custom_fields[name]": signer_info.name,     # Must match exactly “name”
            "custom_fields[phone]": signer_info.phone or "",  # Must match exactly “phone”
            "custom_fields[email]": signer_info.email,  # Must match exactly “email”
        }

        logger.debug(f"[2] Building Dropbox Sign API payload: form_data={form_data}")
        
        # Use form data for this endpoint
        headers = {
            "Authorization": auth_headers["Authorization"]
        }
        logger.debug(f"[3] Sending POST to Dropbox Sign: {create_url}")
        response = requests.post(create_url, data=form_data, headers=headers)
        response.raise_for_status()
        
        result = response.json()
        logger.debug(f"[3.1] Dropbox Sign response: {response.status_code} {response.text}")


        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"]["error_msg"])
        
        signature_request = result["signature_request"]
        signature_request_id = signature_request["signature_request_id"]
        logger.info(f"[4] Received signature_request_id={signature_request_id} from Dropbox Sign")
        
        # Step 2: Get the embedded sign URL for the signer
        # Find the signature_id for our signer
        signatures = signature_request.get("signatures", [])
        if not signatures:
            raise HTTPException(status_code=500, detail="No signatures found in response")
        
        signature_id = signatures[0]["signature_id"]
        
        # Get embedded sign URL
        sign_url_endpoint = f"{DROPBOX_SIGN_CONFIG['api_base_url']}/embedded/sign_url/{signature_id}"
        logger.info(f"[5] Getting embedded sign URL for signature_id={signature_id}")

        sign_url_response = requests.get(sign_url_endpoint, headers=auth_headers)
        sign_url_response.raise_for_status()
        
        sign_url_result = sign_url_response.json()
        logger.debug(f"[5.1] Embedded sign URL response: {sign_url_response.status_code} {sign_url_response.text}")
        
        if "error" in sign_url_result:
            raise HTTPException(status_code=400, detail=sign_url_result["error"]["error_msg"])
        
        embedded_sign_url = sign_url_result["embedded"]["sign_url"]
        expires_at = datetime.now() + timedelta(minutes=60)  # Dropbox Sign URLs last longer
        
        # Store session data 
        # FIXME understand this better
        session_data = {
            "session_id": session_id,
            "signature_request_id": signature_request_id,  # This is like envelope_id
            "signature_id": signature_id,
            "signer_info": signer_info.model_dump(),
            "status": EnvelopeStatus.SENT,
            "created_at": datetime.now(),
            "expires_at": expires_at,
            "signing_url": embedded_sign_url
        }
        
        signing_sessions[session_id] = session_data
        signature_request_to_session[signature_request_id] = session_id
        logger.debug(f"[6] Caching signing session with session_id={session_id}, signature_request_id={signature_request_id}")
        
        logger.debug(f"Successfully created signing URL for session {session_id}")
        
        # Return response (using envelope_id for backward compatibility)
        logger.debug(f"[7] Returning signing URL for session_id={session_id}")
        
        return SigningSessionResponse(
            signing_url=embedded_sign_url,
            session_id=session_id,
            envelope_id=signature_request_id,
            expires_at=expires_at,
            client_id=DROPBOX_SIGN_CONFIG["client_id"],    # ← inject here
        )
    
    except requests.exceptions.RequestException as e:
        logger.error(f"Dropbox Sign API error: {str(e)}")
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_data = e.response.json()
                error_msg = error_data.get("error", {}).get("error_msg", str(e))
            except:
                error_msg = e.response.text
        else:
            error_msg = str(e)
        raise HTTPException(status_code=500, detail=f"Dropbox Sign error: {error_msg}")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to create signing session")

@app.post("/dropbox-sign-callback")
async def handle_dropbox_sign_callback(
    request: Request,
    background_tasks: BackgroundTasks # TODO Understand this better
):
    """
    Handles callbacks from Dropbox Sign for signature request events.
    Dropbox Sign sends webhook events to notify about document status changes 
    """
    try:
        # Parse the callback data
        body = await request.body()
        form_data = await request.form()
        
        # Dropbox Sign sends JSON in the 'json' field of form data
        json_data = form_data.get("json")
        if json_data:
            event_data = json.loads(json_data)
        else:
            # Fallback to raw body parsing
            event_data = json.loads(body)
        
        event_type = event_data.get("event", {}).get("event_type")
        signature_request_id = event_data.get("signature_request", {}).get("signature_request_id")
        
        logger.info(f"Received Dropbox Sign event: {event_type} for request {signature_request_id}")
        
        # Handle different event types
        if event_type == "signature_request_all_signed":
            await handle_all_signed(signature_request_id, event_data)
        elif event_type == "signature_request_signed":
            await handle_signature_signed(signature_request_id, event_data)
        elif event_type == "signature_request_declined":
            await handle_signature_declined(signature_request_id, event_data)
        elif event_type == "signature_request_canceled":
            await handle_signature_canceled(signature_request_id, event_data)
        
        # Dropbox Sign expects a specific response
        return JSONResponse(content={"HelloSign API Event Received": True})
        
    except Exception as e:
        logger.error(f"Error processing callback: {str(e)}")
        # Still return success to prevent retries
        return JSONResponse(content={"HelloSign API Event Received": True})

async def handle_all_signed(signature_request_id: str, event_data: dict):
    """Handle when all signers have completed signing."""
    session_id = signature_request_to_session.get(signature_request_id)
    if not session_id:
        logger.warning(f"Received callback for unknown signature request {signature_request_id}")
        return
    
    if session_id in signing_sessions:
        signing_sessions[session_id]["status"] = EnvelopeStatus.COMPLETED
        signing_sessions[session_id]["signed_at"] = datetime.utcnow()
        signing_sessions[session_id]["documents_available"] = True
        logger.info(f"Marked session {session_id} as completed")

async def handle_signature_signed(signature_request_id: str, event_data: dict):
    """Handle when a single signer has signed (useful for multi-signer flows)."""
    session_id = signature_request_to_session.get(signature_request_id)
    if session_id and session_id in signing_sessions:
        # Update status to show progress
        signing_sessions[session_id]["last_signature_at"] = datetime.utcnow()
        logger.info(f"Signature received for session {session_id}")

async def handle_signature_declined(signature_request_id: str, event_data: dict):
    """Handle when a signer declines to sign."""
    session_id = signature_request_to_session.get(signature_request_id)
    if session_id and session_id in signing_sessions:
        signing_sessions[session_id]["status"] = EnvelopeStatus.DECLINED
        signing_sessions[session_id]["declined_at"] = datetime.utcnow()
        decline_reason = event_data.get("signature_request", {}).get("response_data", {}).get("decline_reason", "No reason provided")
        signing_sessions[session_id]["decline_reason"] = decline_reason

async def handle_signature_canceled(signature_request_id: str, event_data: dict):
    """Handle when a signature request is canceled."""
    session_id = signature_request_to_session.get(signature_request_id)
    if session_id and session_id in signing_sessions:
        signing_sessions[session_id]["status"] = EnvelopeStatus.VOIDED
        signing_sessions[session_id]["voided_at"] = datetime.utcnow()

@app.get("/signing-status/{session_id}", response_model=SigningStatusResponse)
async def get_signing_status(session_id: str):
    """
    Get the current status of a signing session.
    This endpoint remains largely unchanged as it uses our local session storage.
    """
    session_data = signing_sessions.get(session_id)
    if not session_data:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return SigningStatusResponse(
        session_id=session_id,
        envelope_id=session_data["signature_request_id"],  # Maps to signature_request_id
        status=session_data["status"],
        signed_at=session_data.get("signed_at"),
        declined_at=session_data.get("declined_at"),
        decline_reason=session_data.get("decline_reason"),
        documents_available=session_data.get("documents_available", False)
    )

@app.get("/download-document/{session_id}")
async def download_signed_document(
    session_id: str,
    auth_headers: Dict[str, str] = Depends(get_auth_headers)
):
    """
    Download the completed signed document from Dropbox Sign.
    """
    session_data = signing_sessions.get(session_id)
    if not session_data:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if session_data["status"] != EnvelopeStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Document not yet signed")
    
    try:
        # Download the signed document
        signature_request_id = session_data["signature_request_id"]
        download_url = f"{DROPBOX_SIGN_CONFIG['api_base_url']}/signature_request/download/{signature_request_id}"
        
        # Add file_type parameter to get PDF
        params = {"file_type": "pdf"}
        
        response = requests.get(download_url, headers=auth_headers, params=params)
        response.raise_for_status()
        
        return StreamingResponse(
            io.BytesIO(response.content),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=signed_document_{session_id}.pdf"
            }
        )
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to download document: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve document")

@app.get("/sync-signing-status/{session_id}")
async def sync_signing_status(
    session_id: str,
    auth_headers: Dict[str, str] = Depends(get_auth_headers)
):
    """
    Sync the signing status by querying Dropbox Sign directly.
    This is your safety net when callbacks fail.
    """
    session_data = signing_sessions.get(session_id)
    if not session_data:
        raise HTTPException(status_code=404, detail="Session not found")
    
    try:
        # Get signature request details
        signature_request_id = session_data["signature_request_id"]
        status_url = f"{DROPBOX_SIGN_CONFIG['api_base_url']}/signature_request/{signature_request_id}"
        
        response = requests.get(status_url, headers=auth_headers)
        response.raise_for_status()
        
        result = response.json()
        
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"]["error_msg"])
        
        sig_request = result["signature_request"]
        
        # Map Dropbox Sign status to our enum
        is_complete = sig_request.get("is_complete", False)
        is_declined = sig_request.get("is_declined", False)
        has_error = sig_request.get("has_error", False)
        
        if is_complete:
            new_status = EnvelopeStatus.COMPLETED
        elif is_declined:
            new_status = EnvelopeStatus.DECLINED
        elif has_error:
            new_status = EnvelopeStatus.VOIDED
        else:
            new_status = EnvelopeStatus.SENT
        
        # Update our local cache
        signing_sessions[session_id]["status"] = new_status
        if new_status == EnvelopeStatus.COMPLETED:
            signing_sessions[session_id]["signed_at"] = datetime.utcnow()
            signing_sessions[session_id]["documents_available"] = True
        
        logger.info(f"Synchronized status for session {session_id}: {new_status}")
        
        return {
            "session_id": session_id,
            "signature_request_id": signature_request_id,
            "status": new_status,
            "last_sync": datetime.utcnow()
        }
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to sync status: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to sync status with Dropbox Sign")

@app.get("/signing-complete")
async def handle_signing_redirect(
    event: str = "signing_complete",
    session_id: Optional[str] = None,
    signature_request_id: Optional[str] = None
):
    """
    Handle the redirect after embedded signing is complete.
    This page is shown when the user completes/cancels signing in the iframe.
    """
    status_message = {
        "signing_complete": "Thank you for signing! You can now close this window.",
        "cancel": "Signing was cancelled. You can close this window and try again.",
        "decline": "You declined to sign the document.",
        "error": "An error occurred during signing. Please try again.",
    }.get(event, "Signing session ended.")
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Signing Complete</title>
        <style>
            body {{ 
                font-family: Arial, sans-serif; 
                display: flex; 
                justify-content: center; 
                align-items: center; 
                height: 100vh; 
                margin: 0;
                background-color: #f5f5f5;
            }}
            .message-box {{
                text-align: center;
                padding: 40px;
                background: white;
                border-radius: 8px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }}
            .status-{event} {{ color: {"#28a745" if event == "signing_complete" else "#dc3545"}; }}
        </style>
        <script>
            // Notify parent window that signing is complete
            // The hellosign-embedded library communicates with the parent window using events 
            if (window.parent !== window) {{
                window.parent.postMessage({{
                    type: 'dropbox-sign-complete',
                    event: '{event}',
                    sessionId: '{session_id or ""}',
                    signatureRequestId: '{signature_request_id or ""}'
                }}, '*');
            }}
        </script>
    </head>
    <body>
        <div class="message-box">
            <h2 class="status-{event}">{status_message}</h2>
            <p>Session ID: {session_id or 'Not provided'}</p>
        </div>
    </body>
    </html>
    """
    
    return HTMLResponse(content=html_content)

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "Dropbox Sign Signing Service"}

# Add CORS middleware if needed for embedded signing
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)