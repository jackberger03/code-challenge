#!/bin/bash

# Document Signing Portal - Run Script
# This script builds and runs the Docker container
# Everything is served from port 8000

set -e  # Exit on any error

echo "🚀 Starting Document Signing Portal..."

# Check for .env file and API key
if [ ! -f .env ]; then
    echo "❌ .env file not found!"
    echo "Please create a .env file with your Dropbox Sign API key:"
    echo "DROPBOX_SIGN_API_KEY=your_api_key_here"
    exit 1
fi

# Check if API key exists
if ! grep -q "DROPBOX_SIGN_API_KEY=" .env; then
    echo "❌ DROPBOX_SIGN_API_KEY not found in .env file!"
    echo "Please add your Dropbox Sign API key to the .env file:"
    echo "DROPBOX_SIGN_API_KEY=your_api_key_here"
    exit 1
else
    echo "✅ Using existing API key from .env file"
fi

# Build Docker image
echo "📦 Building Docker image..."
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
    --env-file .env \
    document-signing-app

echo "✅ Container started successfully"

echo ""
echo "🎉 Document Signing Portal is now running!"
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
echo "🎉 Ready! Open http://localhost:8000 in your browser."
