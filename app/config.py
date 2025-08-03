import os
from typing import Dict, Any
from dotenv import load_dotenv

load_dotenv()

def get_dropbox_sign_config() -> Dict[str, Any]:
    """Get Dropbox Sign configuration from environment variables."""
    return {
        "api_key": os.getenv("DROPBOX_SIGN_API_KEY"),
        "client_id": os.getenv("DROPBOX_SIGN_CLIENT_ID"),
        "template_id": os.getenv("DROPBOX_SIGN_TEMPLATE_ID"),
        "test_mode": os.getenv("DROPBOX_SIGN_TEST_MODE", "true").lower() == "true",
        "callback_url": os.getenv("DROPBOX_SIGN_CALLBACK_URL"),
        "api_base_url": os.getenv("DROPBOX_SIGN_API_BASE_URL", "https://api.hellosign.com/v3"),
    }