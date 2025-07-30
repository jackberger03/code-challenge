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