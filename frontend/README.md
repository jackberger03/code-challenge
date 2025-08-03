# Frontend - Document Signing Portal

This directory contains the frontend implementation of a web-based document signing portal that integrates with Dropbox Sign (formerly HelloSign) for embedded document signing.

## Overview

The frontend is a single-page application (SPA) built with vanilla JavaScript that provides a user-friendly interface for document signing. It features a modular architecture with clear separation of concerns across multiple JavaScript modules.

## Architecture

The application follows a modular design pattern with each JavaScript file responsible for specific functionality:

```
frontend/
├── index.html          # Main HTML template
├── index.css          # Styling and responsive design
└── js/
    ├── app.js         # Main application logic and orchestration
    ├── api.js         # Backend API communication
    ├── config.js      # Configuration constants and settings
    ├── state.js       # Application state management
    ├── ui.js          # User interface utilities and DOM manipulation
    ├── validation.js  # Form validation logic
    ├── signing-events.js  # Dropbox Sign event handlers
    ├── status-polling.js  # Background status polling
    └── index.js       # Legacy/alternative entry point
```

## Core Components

### 1. **DocumentSigningApp** (`app.js`)

The main application controller that orchestrates the entire signing workflow.

**Key Methods:**

-   `handleFormSubmit()` - Processes the initial form submission
-   `initializeEmbeddedSigning()` - Sets up the Dropbox Sign embedded interface
-   `initialize()` - Application bootstrap and event listeners setup

**Features:**

-   Form submission handling with validation
-   Embedded signing interface initialization
-   Cleanup on page unload
-   Backup completion mechanism (30-second timeout)

### 2. **ApiClient** (`api.js`)

Handles all communication with the backend API.

**Endpoints:**

-   `createSigningSession(signerInfo)` - Creates a new signing session
-   `getSigningStatus(sessionId)` - Polls for signing status updates
-   `forceCompletion(sessionId)` - Manually marks a session as completed

**Features:**

-   RESTful API communication
-   Error handling with user-friendly messages
-   JSON request/response handling

### 3. **AppState** (`state.js`)

Centralized state management for the application.

**State Properties:**

-   `sessionId` - Current signing session identifier
-   `envelopeId` - Dropbox Sign envelope identifier
-   `signingUrl` - URL for the embedded signing interface
-   `hellosignClient` - Dropbox Sign client instance
-   `pollCount` - Number of status polling attempts
-   `signEventFired` - Flag for tracking signing events
-   `waitingForConfirmation` - Flag for confirmation state
-   `manuallyCompleted` - Flag for manual completion

**Methods:**

-   `reset()` - Clears all state data
-   `setSession()` - Updates session-related state
-   `setSigningClient()` - Sets the Dropbox Sign client
-   Various state tracking methods

### 4. **UI** (`ui.js`)

User interface utilities and DOM manipulation functions.

**Key Features:**

-   **Alert System**: Toast-style notifications for different message types
-   **Progress Tracking**: Visual progress bar updates
-   **Form Management**: Enable/disable form controls
-   **Phone Formatting**: Automatic phone number formatting (XXX-XXX-XXXX)
-   **Container Management**: Show/hide different UI sections
-   **Status Display**: Real-time status updates with icons

**Methods:**

-   `showAlert(message, type)` - Display alert messages
-   `updateStatusDisplay(status, message)` - Update signing status
-   `updateProgress(percentage)` - Update progress bar
-   `resetForm()` - Reset application to initial state
-   `setupPhoneFormatting()` - Auto-format phone input

### 5. **Validator** (`validation.js`)

Form validation logic with comprehensive input checking.

**Validation Rules:**

-   **Name**: Minimum 2 characters
-   **Email**: Valid email format using regex
-   **Phone**: Optional, but if provided must be at least 10 digits

**Methods:**

-   `validateSignerInfo(signerInfo)` - Validates all signer information
-   `extractSignerInfo(formData)` - Extracts data from form submission

### 6. **SigningEventHandler** (`signing-events.js`)

Handles all events from the Dropbox Sign embedded interface.

**Event Handlers:**

-   `handleSignEvent()` - Document successfully signed
-   `handleCancelEvent()` - User cancelled signing
-   `handleErrorEvent()` - Error during signing process
-   `handleCloseEvent()` - Signing interface closed
-   `handleFinishEvent()` - Signing process completed
-   `handleMessageEvent()` - General messages from interface

**Features:**

-   Event-driven state management
-   Automatic completion detection
-   Fallback completion mechanisms
-   Backend synchronization

### 7. **StatusPoller** (`status-polling.js`)

Background polling for signing status updates.

**Features:**

-   Configurable polling interval (3 seconds)
-   Maximum attempt limits (100 attempts)
-   Status-based UI updates
-   Automatic cleanup on completion

**Status Handling:**

-   `completed` - Document fully signed
-   `declined` - User declined to sign
-   `voided` - Document was cancelled
-   `sent/delivered` - Document in progress

### 8. **CONFIG** (`config.js`)

Application configuration and constants.

**Configuration:**

-   Backend API URL
-   Polling intervals and limits
-   Dropbox Sign client ID

**Constants:**

-   Status icons (emoji-based)
-   Alert types (info, success, error, warning)

## Workflow

### 1. **Initialization**

-   DOM content loaded event triggers app initialization
-   Event listeners attached to form and cleanup handlers
-   Phone number formatting enabled

### 2. **Form Submission**

-   User fills out signer information (name, email, optional phone)
-   Client-side validation performed
-   API call to create signing session
-   UI transitions to signing interface

### 3. **Embedded Signing**

-   Dropbox Sign embedded interface initialized
-   Status polling begins
-   Event handlers monitor signing progress
-   Progress bar and status updates

### 4. **Completion**

-   Multiple completion detection mechanisms:
    -   Dropbox Sign events (sign, finish, close)
    -   Backend status polling
    -   Backup timeout (30 seconds)
-   UI shows completion status
-   Option to reset and sign another document

## Dependencies

### External Libraries

-   **Dropbox Sign Embedded v2.0.0**: Document signing interface
-   Loaded via CDN: `https://cdn.hellosign.com/public/js/embedded/v2.0.0/embedded.production.min.js`

### Browser APIs

-   **Fetch API**: HTTP requests to backend
-   **FormData**: Form data handling
-   **localStorage**: Potential state persistence
-   **DOM APIs**: Element manipulation and event handling

## Configuration

The application can be configured via the `CONFIG` object in `config.js`:

```javascript
const CONFIG = {
	backendUrl: 'http://localhost:8000', // Backend API URL
	clientId: '', // Dropbox Sign client ID (set dynamically)
	pollInterval: 3000, // Status polling interval (ms)
	maxPollAttempts: 100, // Maximum polling attempts
};
```

## Browser Compatibility

-   Modern browsers with ES6+ support
-   Fetch API support (or polyfill required)
-   CSS Grid and Flexbox support
-   Local storage support

## Error Handling

The application includes comprehensive error handling:

-   **Network Errors**: API communication failures
-   **Validation Errors**: Form input validation
-   **Signing Errors**: Dropbox Sign interface errors
-   **Timeout Errors**: Polling timeout handling
-   **State Errors**: Invalid state transitions

## UI Features

### Responsive Design

-   Mobile-first approach
-   Flexible container layout
-   Touch-friendly interface

### Accessibility

-   ARIA labels and descriptions
-   Keyboard navigation support
-   Screen reader compatible
-   High contrast support

### User Experience

-   Real-time validation feedback
-   Progress indicators
-   Clear status messages
-   Retry mechanisms
-   Auto-formatting for phone numbers

## Development Notes

### Module Pattern

All JavaScript files follow a consistent module pattern:

-   Class-based organization
-   Static methods for utilities
-   CommonJS export compatibility
-   Clear separation of concerns

### State Management

-   Centralized state in `AppState` class
-   Immutable state updates
-   Clear state transitions
-   Comprehensive state tracking

### Event Handling

-   Event-driven architecture
-   Comprehensive event coverage
-   Fallback mechanisms
-   Cleanup on completion

This frontend provides a robust, user-friendly interface for document signing with comprehensive error handling, real-time status updates, and a responsive design that works across modern browsers and devices.
