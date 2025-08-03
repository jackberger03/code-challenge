# Backend API - Document Signing Portal

This directory contains the FastAPI backend implementation for a document signing portal that integrates with Dropbox Sign (formerly HelloSign) for embedded document signing functionality.

## Overview

The backend is built with FastAPI and provides a REST API for managing document signing sessions, handling webhooks from Dropbox Sign, and coordinating the entire signing workflow. It features a clean architecture with separation of concerns across services, handlers, and models.

## Architecture

```
app/
├── main.py                    # FastAPI application and route definitions
├── config.py                  # Configuration management and environment variables
├── models.py                  # Pydantic models for request/response validation
├── requirements.txt           # Python dependencies
├── __init__.py               # Package initialization
├── services/
│   ├── dropbox_sign_service.py    # Dropbox Sign API integration
│   └── session_manager.py         # In-memory session management
└── handlers/
    └── webhook_handlers.py        # Webhook event processing
```

## Core Components

### 1. **FastAPI Application** (`main.py`)

The main application file that defines all API endpoints and coordinates the signing workflow.

**Key Endpoints:**

-   `POST /create-signing-session` - Creates a new signing session with Dropbox Sign
-   `GET /signing-status/{session_id}` - Retrieves the current status of a signing session
-   `POST /dropbox-sign-callback` - Handles webhook events from Dropbox Sign
-   `POST /force-completion/{session_id}` - Manually marks a session as completed
-   `GET /health` - Health check endpoint for monitoring
-   `GET /` - Serves the frontend HTML application

**Features:**

-   CORS middleware for cross-origin requests
-   Static file serving for frontend assets
-   Comprehensive error handling and logging
-   Background task processing for webhooks
-   JSON and form-data webhook support

### 2. **Configuration Management** (`config.py`)

Centralized configuration using environment variables with the `python-dotenv` library.

**Environment Variables:**

-   `DROPBOX_SIGN_API_KEY` - Dropbox Sign API authentication key
-   `DROPBOX_SIGN_CLIENT_ID` - Client ID for embedded signing
-   `DROPBOX_SIGN_TEMPLATE_ID` - Document template identifier
-   `DROPBOX_SIGN_TEST_MODE` - Enable/disable test mode (default: true)
-   `DROPBOX_SIGN_CALLBACK_URL` - Webhook callback URL
-   `DROPBOX_SIGN_API_BASE_URL` - API base URL (default: https://api.hellosign.com/v3)

**Features:**

-   Type-safe configuration with TypedDict
-   Environment variable validation
-   Default value handling
-   Secure credential management

### 3. **Data Models** (`models.py`)

Pydantic models for request/response validation and data serialization.

**Models:**

#### `SignerInfo`

Represents signer information for document signing requests.

-   `email` (EmailStr) - Validated email address
-   `name` (str) - Full name (min 2 characters)
-   `role_name` (str) - Signer role designation
-   `phone` (Optional[str]) - Phone number (min 10 digits if provided)

**Validation:**

-   Email format validation
-   Name length and content validation
-   Phone number format checking
-   Automatic whitespace trimming

#### `SigningSessionResponse`

Response model for signing session creation.

-   `signing_url` (str) - Embedded signing URL
-   `session_id` (str) - Unique session identifier
-   `envelope_id` (str) - Dropbox Sign envelope ID
-   `expires_at` (datetime) - Session expiration timestamp
-   `client_id` (str) - Dropbox Sign client ID

#### `EnvelopeStatus`

Enumeration for document status tracking.

-   `CREATED` - Document created but not sent
-   `SENT` - Document sent to signers
-   `DELIVERED` - Document delivered to signers
-   `SIGNED` - Document signed by at least one signer
-   `COMPLETED` - All signatures completed
-   `DECLINED` - Signing declined by signer
-   `VOIDED` - Document cancelled/voided

#### `WebhookEvent`

Model for processing Dropbox Sign webhook events.

-   `event` (str) - Event type identifier
-   `apiVersion` (str) - API version
-   `data` (Dict) - Event payload data
-   `generatedDateTime` (datetime) - Event timestamp

### 4. **Dropbox Sign Service** (`services/dropbox_sign_service.py`)

Service class for all Dropbox Sign API interactions.

**Key Methods:**

#### `create_embedded_signature_request(signer_info, session_id)`

Creates a new signature request using a template.

-   Uses template-based document creation
-   Configures embedded signing mode
-   Sets custom fields for personalization
-   Handles API authentication and error responses

#### `get_embedded_sign_url(signature_id)`

Retrieves the embedded signing URL for a specific signature.

-   Required for embedding the signing interface
-   Returns time-limited signing URL
-   Handles authentication and API errors

#### `get_signature_request_status(signature_request_id)`

Polls the current status of a signature request.

-   Used for status synchronization
-   Returns comprehensive status information
-   Handles rate limiting and errors

#### `download_document(signature_request_id)`

Downloads the completed signed document as PDF.

-   Returns document binary content
-   Supports various file formats
-   Requires completed signing status

**Features:**

-   Base64 HTTP Basic authentication
-   Comprehensive error handling
-   Request/response logging
-   Configurable API endpoints
-   Test mode support

### 5. **Session Manager** (`services/session_manager.py`)

In-memory session management for tracking signing workflows.

**Storage:**

-   `signing_sessions` - Main session data store (session_id → session_data)
-   `signature_request_to_session` - Lookup mapping (signature_request_id → session_id)

**Key Methods:**

#### `create_session(signer_info, signature_request_id, signature_id, signing_url, expires_at)`

Creates a new signing session with comprehensive tracking.

-   Generates unique session UUID
-   Stores signer information and Dropbox Sign IDs
-   Sets initial status and timestamps
-   Creates bidirectional lookup mappings

#### `get_session(session_id)`

Retrieves session data by session ID.

-   Returns complete session information
-   Used by status endpoints
-   Handles missing sessions gracefully

#### `get_session_by_signature_request(signature_request_id)`

Finds session by Dropbox Sign signature request ID.

-   Required for webhook processing
-   Enables bidirectional lookups
-   Critical for status synchronization

#### `update_session_status(session_id, status, **kwargs)`

Updates session status and additional metadata.

-   Status transitions (sent → completed/declined/voided)
-   Timestamp tracking (signed_at, declined_at, etc.)
-   Additional metadata storage
-   Flexible keyword argument support

**Data Structure:**

```python
{
    "session_id": "uuid4-string",
    "signature_request_id": "dropbox-sign-id",
    "signature_id": "dropbox-sign-signature-id",
    "signer_info": {...},
    "status": "EnvelopeStatus.SENT",
    "created_at": "datetime",
    "expires_at": "datetime",
    "signing_url": "embedded-url",
    "signed_at": "datetime",  # Added when completed
    "documents_available": "boolean"  # Added when completed
}
```

### 6. **Webhook Handlers** (`handlers/webhook_handlers.py`)

Processes webhook events from Dropbox Sign to maintain status synchronization.

**Event Handlers:**

#### `handle_all_signed(signature_request_id, event_data)`

Processes when all required signatures are completed.

-   Updates session status to COMPLETED
-   Sets signed_at timestamp
-   Marks documents as available
-   Enables document download

#### `handle_signature_signed(signature_request_id, event_data)`

Handles individual signature completion events.

-   Updates last_signature_at timestamp
-   Maintains SENT status until all complete
-   Tracks signing progress

#### `handle_signature_declined(signature_request_id, event_data)`

Processes signature decline events.

-   Updates status to DECLINED
-   Records decline timestamp and reason
-   Ends signing workflow

#### `handle_signature_canceled(signature_request_id, event_data)`

Handles signature request cancellation.

-   Updates status to VOIDED
-   Records cancellation timestamp
-   Cleanup of active sessions

**Features:**

-   Comprehensive event logging
-   Session lookup and updates
-   Error handling for unknown sessions
-   Timestamp tracking for audit trails

## API Endpoints

### Signing Workflow

#### `POST /create-signing-session`

Creates a new document signing session.

**Request Body:**

```json
{
	"name": "John Doe",
	"email": "john@example.com",
	"phone": "555-123-4567",
	"role_name": "Hiring Manager"
}
```

**Response:**

```json
{
	"signing_url": "https://app.hellosign.com/editor/embeddedSign?...",
	"session_id": "12345678-1234-1234-1234-123456789012",
	"envelope_id": "dropbox-sign-envelope-id",
	"expires_at": "2024-01-01T12:00:00Z",
	"client_id": "dropbox-sign-client-id"
}
```

#### `GET /signing-status/{session_id}`

Retrieves the current status of a signing session.

**Response:**

```json
{
	"status": "completed",
	"signature_request_id": "dropbox-sign-request-id",
	"completed_at": "2024-01-01T12:00:00Z",
	"expired": false
}
```

### Webhook Processing

#### `POST /dropbox-sign-callback`

Handles webhook events from Dropbox Sign.

**Supported Event Types:**

-   `signature_request_all_signed` - All signatures completed
-   `signature_request_signed` - Individual signature completed
-   `signature_request_declined` - Signature declined
-   `signature_request_canceled` - Request cancelled

**Request Formats:**

-   Form data with JSON field: `json={"event": {...}}`
-   Raw JSON body: `{"event": {...}}`

### Utility Endpoints

#### `POST /force-completion/{session_id}`

Manually marks a session as completed (fallback mechanism).

#### `GET /health`

Health check endpoint for monitoring and Docker health checks.

#### `GET /`

Serves the frontend HTML application.

## Dependencies

### Core Framework

-   **FastAPI** (0.116.1) - Modern Python web framework
-   **Uvicorn** (0.35.0) - ASGI server for FastAPI
-   **Starlette** (0.47.2) - FastAPI foundation

### Data Validation

-   **Pydantic** (2.11.7) - Data validation and serialization
-   **email-validator** (2.2.0) - Email format validation

### HTTP and Networking

-   **Requests** (2.32.4) - HTTP client for Dropbox Sign API
-   **python-multipart** (0.0.20) - Form data parsing
-   **httpx** (0.28.1) - Async HTTP client

### Authentication and Security

-   **cryptography** (45.0.5) - Cryptographic operations
-   **PyJWT** (2.10.1) - JSON Web Token handling

### Configuration and Environment

-   **python-dotenv** (1.1.1) - Environment variable management

### Development and Testing

-   **pytest** (8.4.1) - Testing framework

## Configuration

### Environment Setup

Create a `.env` file in the project root:

```env
DROPBOX_SIGN_API_KEY=your_api_key_here
DROPBOX_SIGN_CLIENT_ID=your_client_id_here
DROPBOX_SIGN_TEMPLATE_ID=your_template_id_here
DROPBOX_SIGN_TEST_MODE=true
DROPBOX_SIGN_CALLBACK_URL=http://localhost:8000/dropbox-sign-callback
DROPBOX_SIGN_API_BASE_URL=https://api.hellosign.com/v3
```

### Template Configuration

The application uses Dropbox Sign templates with predefined fields:

-   Document template must be created in Dropbox Sign dashboard
-   Template should include signer roles and form fields
-   Custom fields supported: name, email, phone

## Running the Application

### Development Mode

```bash
cd app/
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Production Mode

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Docker

The application is designed to run in Docker containers with proper health checks and static file serving.

## Error Handling

### API Error Responses

-   **400 Bad Request** - Invalid input data or validation errors
-   **404 Not Found** - Session or resource not found
-   **500 Internal Server Error** - Service or API failures

### Logging

-   Comprehensive logging at DEBUG level for development
-   ERROR level logging for production issues
-   Request/response logging for API calls
-   Webhook event logging for audit trails

### Resilience Features

-   Graceful handling of Dropbox Sign API failures
-   Fallback completion mechanisms
-   Webhook retry tolerance
-   Session expiration handling

## Security Considerations

### Authentication

-   Dropbox Sign API key protection
-   Environment variable isolation
-   No hardcoded credentials

### Data Protection

-   No persistent storage of sensitive data
-   In-memory session management only
-   Secure HTTP communication with Dropbox Sign

### Input Validation

-   Comprehensive Pydantic validation
-   Email format verification
-   Phone number sanitization
-   XSS protection through proper data handling

## Monitoring and Health

### Health Checks

-   `/health` endpoint for container orchestration
-   Service dependency validation
-   Basic connectivity verification

### Logging

-   Structured logging with timestamps
-   Request/response tracking
-   Error context preservation
-   Webhook event audit trails

## Development Notes

### Architecture Patterns

-   **Service Layer Pattern**: Separation of business logic into service classes
-   **Repository Pattern**: Session management abstraction
-   **Handler Pattern**: Event-driven webhook processing
-   **Factory Pattern**: Configuration management

### State Management

-   **In-Memory Storage**: Fast access but not persistent across restarts
-   **Session Lifecycle**: Create → Active → Completed/Declined/Voided
-   **Bidirectional Lookups**: Support for both session ID and signature request ID queries

### Integration Points

-   **Dropbox Sign API**: Template-based document creation and embedded signing
-   **Frontend**: REST API for SPA communication
-   **Webhooks**: Real-time status synchronization
-   **Static Assets**: Frontend file serving

This backend provides a robust, scalable foundation for document signing workflows with comprehensive error handling, real-time status updates, and secure integration with Dropbox Sign services.
