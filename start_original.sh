#!/bin/bash

# TQ GenAI Chat - Original Structure Startup Script
# Runs the original application structure

set -e

echo "🚀 Starting TQ GenAI Chat (Original Structure)"
echo "================================================"

# Set environment variables
export BASIC_AUTH_USERNAME=emeeran
export BASIC_AUTH_PASSWORD=3u0qL1lizU19WE

# Activate virtual environment
source .venv/bin/activate

# Check if application is already running
if curl -s http://127.0.0.1:5005/health >/dev/null 2>&1; then
    echo "✅ Application is already running on http://127.0.0.1:5005"
    echo "🔐 Login credentials:"
    echo "   Username: $BASIC_AUTH_USERNAME"
    echo "   Password: $BASIC_AUTH_PASSWORD"
    echo ""
    echo "📊 Performance metrics: http://127.0.0.1:5005/metrics"
    exit 0
fi

echo "🔧 Starting FastAPI application..."
echo "   Mode: Original Structure"
echo "   Port: 5005"
echo "   Environment: Development"
echo ""

# Start the application
python -m uvicorn main:app --host 127.0.0.1 --port 5005 --reload

echo ""
echo "🎉 Application started successfully!"
echo "📱 Access it at: http://127.0.0.1:5005"
echo "🔐 Login with: $BASIC_AUTH_USERNAME / $BASIC_AUTH_PASSWORD"