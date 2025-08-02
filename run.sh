#!/bin/bash

# Document Signing Portal - Run Script
# This script builds and runs the Docker container
# Everything is served from port 8000

set -e  # Exit on any error

echo "Starting Document Signing Portal..."

# Set Dropbox Sign configuration
export DROPBOX_SIGN_CLIENT_ID=f42ce491701f35b55f1ee089d6a7c89c
export DROPBOX_SIGN_TEMPLATE_ID=b502b0a6237b9b84a2fe49fcb54de180cfb8e811

# Prompt for API key
echo ""
echo "Please enter your Dropbox Sign API key:"
echo "(You can find this in your Dropbox Sign account settings)"
read -p "API Key: " DROPBOX_SIGN_API_KEY

if [ -z "$DROPBOX_SIGN_API_KEY" ]; then
    echo "Error: API key cannot be empty!"
    exit 1
fi

export DROPBOX_SIGN_API_KEY

# Build Docker image
echo "Building Docker image..."
docker build -t document-signing-app .

# Check if container is already running and stop it
if docker ps -a -q -f name=document-signing-container | grep -q .; then
    echo "Stopping existing container..."
    docker stop document-signing-container > /dev/null 2>&1 || true
    docker rm document-signing-container > /dev/null 2>&1 || true
else
    echo "No existing container to stop"
fi

# Run the Docker container
echo "Starting backend container on port 8000..."
docker run -d \
    --name document-signing-container \
    -p 8000:8000 \
    -e DROPBOX_SIGN_API_KEY="$DROPBOX_SIGN_API_KEY" \
    -e DROPBOX_SIGN_CLIENT_ID="$DROPBOX_SIGN_CLIENT_ID" \
    -e DROPBOX_SIGN_TEMPLATE_ID="$DROPBOX_SIGN_TEMPLATE_ID" \
    document-signing-app

echo "Container started successfully"

echo ""
echo "Document Signing Portal is now running!"
echo ""
echo "Services:"
echo "   Application: http://localhost:8000"
echo "   Health:      http://localhost:8000/health"
echo ""
echo "Logs:"
echo "   View logs:   docker logs -f document-signing-container"
echo ""
echo "To stop:"
echo "   Run:         ./stop.sh"
echo "   Or:          docker stop document-signing-container"
echo ""
echo "Ready! Open http://localhost:8000 in your browser."
