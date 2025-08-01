from datetime import datetime
from app.models import EnvelopeStatus
from app.services.session_manager import SessionManager
import logging

logger = logging.getLogger(__name__)

class WebhookHandlers:
    def __init__(self, session_manager: SessionManager):
        self.session_manager = session_manager
    
    async def handle_all_signed(self, signature_request_id: str, event_data: dict):
        """Handle when all signers have completed signing."""
        session_id = self.session_manager.get_session_by_signature_request(signature_request_id)
        if not session_id:
            logger.warning(f"Received callback for unknown signature request {signature_request_id}")
            return
        
        self.session_manager.update_session_status(
            session_id, 
            EnvelopeStatus.COMPLETED,
            signed_at=datetime.utcnow(),
            documents_available=True
        )
        logger.info(f"Marked session {session_id} as completed")
    
    async def handle_signature_signed(self, signature_request_id: str, event_data: dict):
        """Handle when a single signer has signed."""
        session_id = self.session_manager.get_session_by_signature_request(signature_request_id)
        if session_id:
            self.session_manager.update_session_status(
                session_id,
                EnvelopeStatus.SENT,  # Keep as sent until all complete
                last_signature_at=datetime.utcnow()
            )
            logger.info(f"Signature received for session {session_id}")
    
    async def handle_signature_declined(self, signature_request_id: str, event_data: dict):
        """Handle when a signer declines to sign."""
        session_id = self.session_manager.get_session_by_signature_request(signature_request_id)
        if session_id:
            decline_reason = event_data.get("signature_request", {}).get("response_data", {}).get("decline_reason", "No reason provided")
            self.session_manager.update_session_status(
                session_id,
                EnvelopeStatus.DECLINED,
                declined_at=datetime.utcnow(),
                decline_reason=decline_reason
            )
    
    async def handle_signature_canceled(self, signature_request_id: str, event_data: dict):
        """Handle when a signature request is canceled."""
        session_id = self.session_manager.get_session_by_signature_request(signature_request_id)
        if session_id:
            self.session_manager.update_session_status(
                session_id,
                EnvelopeStatus.VOIDED,
                voided_at=datetime.utcnow()
            )