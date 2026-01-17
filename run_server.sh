#!/bin/bash

echo "🛡️  Starting SafeRun X402 API Server"
echo "===================================="
echo ""

# Activate virtual environment
source venv/bin/activate

# Run server
echo "Starting server at http://localhost:8000"
echo "API docs at http://localhost:8000/docs"
echo ""
python -m saferun.api.server
