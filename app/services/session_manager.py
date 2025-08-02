from typing import Dict, Any, Optional
from datetime import datetime
from models import EnvelopeStatus, SignerInfo
import uuid

class SessionManager:
    def __init__(self):
        self.signing_sessions: Dict[str, Dict[str, Any]] = {}
        self.signature_request_to_session: Dict[str, str] = {}
    
    def create_session(self, signer_info: SignerInfo, signature_request_id: str, 
                      signature_id: str, signing_url: str, expires_at: datetime) -> str:
        """Create a new signing session."""
        session_id = str(uuid.uuid4())
        
        session_data = {
            "session_id": session_id,
            "signature_request_id": signature_request_id,
            "signature_id": signature_id,
            "signer_info": signer_info.model_dump(),
            "status": EnvelopeStatus.SENT,
            "created_at": datetime.now(),
            "expires_at": expires_at,
            "signing_url": signing_url
        }
        
        self.signing_sessions[session_id] = session_data
        self.signature_request_to_session[signature_request_id] = session_id
        
        return session_id
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session data by session ID."""
        return self.signing_sessions.get(session_id)
    
    def get_session_by_signature_request(self, signature_request_id: str) -> Optional[str]:
        """Get session ID by signature request ID."""
        return self.signature_request_to_session.get(signature_request_id)
    
    def update_session_status(self, session_id: str, status: EnvelopeStatus, **kwargs):
        """Update session status and additional fields."""
        if session_id in self.signing_sessions:
            self.signing_sessions[session_id]["status"] = status
            for key, value in kwargs.items():
                self.signing_sessions[session_id][key] = value