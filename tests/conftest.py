# tests/conftest.py
"""
Central test configuration and fixtures.
This file is automatically loaded by pytest and provides shared fixtures
and configuration for all tests.
"""
import pytest
import os
from unittest.mock import patch, Mock
from datetime import datetime
from fastapi.testclient import TestClient

# Set up test environment variables before any app imports
# This ensures our app doesn't fail during import due to missing config
TEST_ENV = {
    "DOCUSIGN_INTEGRATION_KEY": "test_integration_key",
    "DOCUSIGN_USER_ID": "test_user_id",
    "DOCUSIGN_ACCOUNT_ID": "test_account_id",
    "DOCUSIGN_BASE_PATH": "https://demo.docusign.net/restapi",
    "DOCUSIGN_OAUTH_BASE_PATH": "account-d.docusign.com",
    "DOCUSIGN_PRIVATE_KEY_PATH": "/tmp/test_private_key.pem",
    "DOCUSIGN_TEMPLATE_ID": "test_template_id",
    "DOCUSIGN_REDIRECT_URI": "http://localhost:8000/signing-complete",
    "DOCUSIGN_WEBHOOK_SECRET": "test_webhook_secret"
}

# Apply test environment variables
# This happens before any imports, solving the singleton initialization problem
for key, value in TEST_ENV.items():
    os.environ[key] = value

# Now it's safe to import our app
from app.main import app, signing_sessions, envelope_to_session, TokenManager

@pytest.fixture
def client():
    """
    Provides a test client for making requests to our FastAPI app.
    This client simulates HTTP requests without starting a real server.
    """
    return TestClient(app)

@pytest.fixture(autouse=True)
def reset_session_storage():
    """
    Automatically clears session data before each test.
    This ensures tests don't interfere with each other.
    The 'autouse=True' means this runs before every test automatically.
    """
    signing_sessions.clear()
    envelope_to_session.clear()
    yield  # Test runs here
    # Cleanup after test (if needed)
    signing_sessions.clear()
    envelope_to_session.clear()

@pytest.fixture
def mock_datetime_now():
    """
    Provides a consistent datetime for tests.
    This eliminates test flakiness from time-dependent code.
    """
    fixed_time = datetime(2024, 1, 1, 12, 0, 0)
    with patch('app.main.datetime') as mock_dt:
        mock_dt.now.return_value = fixed_time
        mock_dt.utcnow.return_value = fixed_time
        yield fixed_time