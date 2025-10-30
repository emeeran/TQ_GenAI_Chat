#!/bin/bash

# TQ GenAI Chat - Reorganized Structure Startup Script
# Runs the frontend/backend separated structure

set -e

echo "🏗️ Starting TQ GenAI Chat (Reorganized Frontend/Backend)"
echo "================================================"

# Set environment variables
export BASIC_AUTH_USERNAME=emeeran
export BASIC_AUTH_PASSWORD=3u0qL1lizU19WE

# Activate virtual environment
source .venv/bin/activate

# Check if application is already running
if curl -s http://127.0.0.1:5005/health >/dev/null 2>&1; then
    echo "✅ Original application is running on http://127.0.0.1:5005"
    echo "🔄 Starting reorganized version on port 5006..."
elif curl -s http://127.0.0.1:5006/health >/dev/null 2>&1; then
    echo "✅ Reorganized application is already running on http://127.0.0.1:5006"
    echo "🔐 Login credentials:"
    echo "   Username: $BASIC_AUTH_USERNAME"
    echo "   Password: $BASIC_AUTH_PASSWORD"
    echo ""
    echo "📊 Performance metrics: http://127.0.0.1:5006/metrics"
    exit 0
fi

echo "🔧 Starting FastAPI application..."
echo "   Mode: Frontend/Backend Separated"
echo "   Port: 5005 (or 5006 if original is running)"
echo "   Environment: Development"
echo ""

# Start the application (original port if available, otherwise port 5006)
if curl -s http://127.0.0.1:5005/health >/dev/null 2>&1; then
    echo "🟢 Original detected, starting reorganized on port 5006..."
    python -m uvicorn backend.main:app --host 127.0.0.1 --port 5006 --reload
    APP_PORT=5006
else
    echo "🟢 Starting reorganized on default port 5005..."
    python -m uvicorn backend.main:app --host 127.0.0.1 --port 5005 --reload
    APP_PORT=5005
fi

echo ""
echo "🎉 Application started successfully!"
echo "📱 Access it at: http://127.0.0.1:$APP_PORT"
echo "🔐 Login with: $BASIC_AUTH_USERNAME / $BASIC_AUTH_PASSWORD"
echo "📊 Performance metrics: http://127.0.0.1:$APP_PORT/metrics"
echo ""
echo "🏗️ Architecture: Frontend/Backend Separated"
echo "📁 Frontend: ./frontend/"
echo "📁 Backend:  ./backend/"