#!/bin/bash

# Document Signing Portal - Stop Script
# This script stops both the Docker container and frontend server

echo "Stopping Document Signing Portal..."

# Stop Docker container
if docker ps -q -f name=document-signing-container > /dev/null 2>&1; then
    echo "Stopping backend container..."
    docker stop document-signing-container
    docker rm document-signing-container
    echo "Backend stopped"
else
    echo "ℹBackend container not running"
fi

# Stop frontend server
if [ -f .frontend.pid ]; then
    FRONTEND_PID=$(cat .frontend.pid)
    if kill -0 $FRONTEND_PID 2>/dev/null; then
        echo "Stopping frontend server (PID: $FRONTEND_PID)..."
        kill $FRONTEND_PID
        echo "Frontend stopped"
    else
        echo "Frontend server not running"
    fi
    rm -f .frontend.pid
else
    # Fallback: kill any process on port 3000
    if lsof -ti:3000 > /dev/null 2>&1; then
        echo "Stopping process on port 3000..."
        kill -9 $(lsof -ti:3000) 2>/dev/null || true
        echo "Port 3000 freed"
    else
        echo "No process running on port 3000"
    fi
fi

echo ""
echo "Document Signing Portal stopped successfully!"
