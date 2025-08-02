#!/bin/bash

# Document Signing Portal - Run Script
# This script builds and runs the Docker container for the backend
# and serves the frontend on port 3000

set -e  # Exit on any error

echo "🚀 Starting Document Signing Portal..."

# Build Docker image
echo "📦 Building Docker image..."
docker build -t document-signing-app .

# Check if container is already running and stop it
if docker ps -a -q -f name=document-signing-container | grep -q .; then
    echo "Stopping existing container..."
    docker stop document-signing-container > /dev/null 2>&1 || true
    docker rm document-signing-container > /dev/null 2>&1 || true
    echo "Existing container stopped"
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

# Wait a moment for the container to start
sleep 2

# Check if Python is available, if not try python3
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    echo "Python not found. Please install Python to serve the frontend."
    exit 1
fi

# Start frontend server on port 3000
echo "Starting frontend server on port 3000..."
echo "Serving index.html from current directory..."

# Kill any existing process on port 3000
if lsof -ti:3000 > /dev/null 2>&1; then
    echo "Killing existing process on port 3000..."
    kill -9 $(lsof -ti:3000) 2>/dev/null || true
fi

# Start the frontend server in the background
$PYTHON_CMD -m http.server 3000 > /dev/null 2>&1 &
FRONTEND_PID=$!

# Wait a moment for the server to start
sleep 1

echo ""
echo "Document Signing Portal is now running!"
echo ""
echo "Services:"
echo "   Backend API: http://localhost:8000"
echo "   Frontend:    http://localhost:3000"
echo "   Health:      http://localhost:8000/health"
echo ""
echo "Logs:"
echo "   Backend:     docker logs -f document-signing-container"
echo "   Frontend:    PID $FRONTEND_PID"
echo ""
echo "To stop:"
echo "   Backend:     docker stop document-signing-container"
echo "   Frontend:    kill $FRONTEND_PID"
echo "   Or run:      ./stop.sh"
echo ""

# Save PIDs for cleanup script
echo $FRONTEND_PID > .frontend.pid

echo "🎉 Ready! Open http://localhost:3000 in your browser."
