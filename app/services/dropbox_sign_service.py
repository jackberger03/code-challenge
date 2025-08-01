import requests
import base64
import json
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from app.models import SignerInfo, EnvelopeStatus
import logging

logger = logging.getLogger(__name__)

class DropboxSignService:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        
    def get_auth_headers(self) -> Dict[str, str]:
        """Get headers for Dropbox Sign API authentication."""
        auth_string = f"{self.config['api_key']}:"
        encoded_auth = base64.b64encode(auth_string.encode()).decode()
        
        return {
            "Authorization": f"Basic {encoded_auth}"
        }
    
    def create_embedded_signature_request(self, signer_info: SignerInfo, session_id: str) -> Dict[str, Any]:
        """Create an embedded signature request with template."""
        create_url = f"{self.config['api_base_url']}/signature_request/create_embedded_with_template"

        form_data = {
            "client_id": self.config["client_id"],
            "template_ids[0]": self.config["template_id"],
            "signers[signer][name]": signer_info.name,
            "signers[signer][email_address]": signer_info.email,
            "test_mode": "1" if self.config["test_mode"] else "0",
            
            "custom_fields": json.dumps([
                {"name": "name", "value": signer_info.name},
                {"name": "phone", "value": signer_info.phone or ""},
                {"name": "email", "value": signer_info.email}
            ])
        }
        
        headers = {
            "Authorization": self.get_auth_headers()["Authorization"]
        }
        
        logger.debug(f"Sending form data to Dropbox Sign: {form_data}")
        
        try:
            response = requests.post(create_url, data=form_data, headers=headers)
            response.raise_for_status()
            
            result = response.json()
            
            # CRITICAL FIX: Add error checking from original code
            if "error" in result:
                error_msg = result.get("error", {}).get("error_msg", "Unknown API error")
                logger.error(f"Dropbox Sign API error: {error_msg}")
                raise Exception(f"Dropbox Sign error: {error_msg}")
                
            return result
            
        except requests.exceptions.RequestException as e:
            # Add better error handling like in the original code
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_data = e.response.json()
                    error_msg = error_data.get("error", {}).get("error_msg", str(e))
                    logger.error(f"Request failed: {error_msg}")
                except:
                    error_msg = e.response.text if e.response.text else str(e)
                    logger.error(f"Request failed: {error_msg}")
            else:
                logger.error(f"Request failed: {str(e)}")
            raise Exception(f"Dropbox Sign API request failed: {str(e)}")
    
    def get_embedded_sign_url(self, signature_id: str) -> str:
        """Get the embedded signing URL for a signature."""
        sign_url_endpoint = f"{self.config['api_base_url']}/embedded/sign_url/{signature_id}"
        
        response = requests.get(sign_url_endpoint, headers=self.get_auth_headers())
        response.raise_for_status()
        
        result = response.json()
        return result["embedded"]["sign_url"]
    
    def get_signature_request_status(self, signature_request_id: str) -> Dict[str, Any]:
        """Get the status of a signature request."""
        status_url = f"{self.config['api_base_url']}/signature_request/{signature_request_id}"
        
        response = requests.get(status_url, headers=self.get_auth_headers())
        response.raise_for_status()
        
        return response.json()
    
    def download_document(self, signature_request_id: str) -> bytes:
        """Download the completed signed document."""
        download_url = f"{self.config['api_base_url']}/signature_request/download/{signature_request_id}"
        params = {"file_type": "pdf"}
        
        response = requests.get(download_url, headers=self.get_auth_headers(), params=params)
        response.raise_for_status()
        
        return response.content