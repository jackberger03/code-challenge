from fastapi import FastAPI, HTTPException, Depends, Request, BackgroundTasks
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional, Dict, Any
import os 
from datetime import datetime, timedelta
import logging 
from docusign_esign import ApiClient, EnvelopesApi, EnvelopeDefinition, Document, Signer, SignHere, Tabs, RecipientViewRequest
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