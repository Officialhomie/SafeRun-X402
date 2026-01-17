#!/bin/bash

echo "🛡️  SafeRun X402 Demo"
echo "===================="
echo ""

# Activate virtual environment
source venv/bin/activate

# Run demo
python demo_scenario.py

echo ""
echo "Demo complete!"
echo ""
echo "To run the API server:"
echo "  python -m saferun.api.server"
echo ""
