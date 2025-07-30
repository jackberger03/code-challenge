# Embedded Document Signing Challenge

## Overview
Build a web application that implements embedded document signing functionality. You may use any e-signature provider of your choice (DocuSign, HelloSign, Adobe Sign, PandaDoc, etc.). The solution should consist of a pure HTML frontend and a backend server that handles all API interactions.

## Requirements

### Frontend
- **Pure HTML**: Create a single `index.html` file with embedded CSS and JavaScript
- **No frameworks**: Vanilla HTML, CSS, and JavaScript only
- **User Interface**: Should include:
  - Signer information input (name, email, phone)
  - Embedded signing interface
  - Status display for signing process

### Backend
- **Language**: Any programming language of your choice
- **Responsibilities**:
  - Handle e-signature provider API authentication
  - Create signing requests with a predefined document template
  - Generate embedded signing URLs
  - Manage signing sessions
  - Provide status updates to frontend
- **API Endpoints**: Design RESTful endpoints to support the frontend functionality

### Core Functionality
1. **Signer Setup**: Collect signer information (name, email, phone) that gets prefilled into the document
2. **Embedded Signing**: Integrate your chosen provider's embedded signing experience directly in the web page with autofilled signer information
3. **Real-time Status**: Show signing progress and completion status
4. **Document Retrieval**: Allow download of completed signed documents

## Technical Specifications

### E-Signature Provider Integration
- Use your chosen provider's REST API
- Implement embedded signing (not email-based)
- Handle authentication securely on the backend
- Manage document/envelope lifecycle properly

### Security Considerations
- Never expose API credentials to the frontend
- Implement proper error handling
- Validate all inputs

### Bonus Features (Optional)
- Multiple signer support
- Document templates
- Signing position customization
- Mobile-responsive design
- Progress indicators
- Email notifications

## Deliverables
1. `index.html` - Complete frontend implementation
2. Backend server code in your chosen language
3. `README.md` with setup and running instructions
4. Any configuration files needed (package.json, requirements.txt, etc.)
5. **One-line command** to start the server for easy testing

## Setup Requirements
- Developer account with your chosen e-signature provider
- API credentials from your chosen provider
- Test environment setup
- Predefined document template for signing

## Testing Process
The application should support this simple test flow:
1. Run one command to start the server
2. Open `index.html` in browser
3. Input signer information (name, email, phone)
4. Press "Next" to proceed to signing
5. Sign the document with autofilled information from step 3

## Evaluation Criteria
- **Functionality**: Does the embedded signing work end-to-end?
- **Code Quality**: Clean, readable, and well-structured code
- **User Experience**: Intuitive and responsive interface
- **Error Handling**: Graceful handling of edge cases and errors
- **Documentation**: Clear setup and usage instructions
- **Security**: Proper handling of sensitive data and API credentials

Good luck! 🚀