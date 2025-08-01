from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.responses import JSONResponse, StreamingResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
from datetime import datetime, timedelta
import logging
import json
import io

from app.models import SignerInfo, SigningSessionResponse, SigningStatusResponse
from app.config import get_dropbox_sign_config
from app.services.dropbox_sign_service import DropboxSignService
from app.services.session_manager import SessionManager
from app.handlers.webhook_handlers import WebhookHandlers

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = FastAPI()

# Initialize services
config = get_dropbox_sign_config()
dropbox_service = DropboxSignService(config)
session_manager = SessionManager()
webhook_handlers = WebhookHandlers(session_manager)

@app.post("/create-signing-session", response_model=SigningSessionResponse)
async def create_signing_session(signer_info: SignerInfo):
    """Creates a signing session using Dropbox Sign embedded signing."""
    logger.debug(f"[1] Received /create-signing-session for email={signer_info.email}")
    
    try:
        # Create signature request
        result = dropbox_service.create_embedded_signature_request(signer_info, "temp_session")
        
        signature_request = result["signature_request"]
        signature_request_id = signature_request["signature_request_id"]
        signature_id = signature_request["signatures"][0]["signature_id"]
        
        # Get embedded signing URL
        embedded_sign_url = dropbox_service.get_embedded_sign_url(signature_id)
        expires_at = datetime.now() + timedelta(minutes=60)
        
        # Create session
        session_id = session_manager.create_session(
            signer_info, signature_request_id, signature_id, embedded_sign_url, expires_at
        )
        
        return SigningSessionResponse(
            signing_url=embedded_sign_url,
            session_id=session_id,
            envelope_id=signature_request_id,
            expires_at=expires_at,
            client_id=config["client_id"]
        )
        
    except Exception as e:
        logger.error(f"Error creating signing session: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to create signing session")

@app.get("/signing-status/{session_id}")
async def get_signing_status(session_id: str):
    """Get the status of a signing session."""
    try:
        session = session_manager.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        return {
            "status": session.get("status", "pending"),
            "signature_request_id": session.get("signature_request_id"),
            "completed_at": session.get("completed_at"),
            "expired": session.get("expired", False)
        }
    except Exception as e:
        logger.error(f"Error getting signing status: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get signing status")


@app.post("/dropbox-sign-callback")
async def handle_dropbox_sign_callback(request: Request, background_tasks: BackgroundTasks):
    """Handles callbacks from Dropbox Sign."""
    try:
        form_data = await request.form()
        json_data = form_data.get("json")
        
        if json_data:
            event_data = json.loads(json_data)
        else:
            body = await request.body()
            event_data = json.loads(body)
        
        event_type = event_data.get("event", {}).get("event_type")
        signature_request_id = event_data.get("signature_request", {}).get("signature_request_id")
        
        # Route to appropriate handler
        if event_type == "signature_request_all_signed":
            await webhook_handlers.handle_all_signed(signature_request_id, event_data)
        elif event_type == "signature_request_signed":
            await webhook_handlers.handle_signature_signed(signature_request_id, event_data)
        elif event_type == "signature_request_declined":
            await webhook_handlers.handle_signature_declined(signature_request_id, event_data)
        elif event_type == "signature_request_canceled":
            await webhook_handlers.handle_signature_canceled(signature_request_id, event_data)
        
        return JSONResponse(content={"HelloSign API Event Received": True})
        
    except Exception as e:
        logger.error(f"Error processing callback: {str(e)}")
        return JSONResponse(content={"HelloSign API Event Received": True})

# ... other endpoints (status, download, etc.) - also refactored to use services

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)