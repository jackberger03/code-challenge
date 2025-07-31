# tests/test_endpoints.py
"""
Tests for FastAPI endpoints.
These tests verify our API endpoints work correctly without
making real calls to DocuSign.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import uuid
from app.main import signing_sessions, EnvelopeStatus
# TODO 