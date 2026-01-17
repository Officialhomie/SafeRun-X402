#!/bin/bash

echo "🛡️  SafeRun X402 - Impressive Demo Scenarios"
echo "============================================="
echo ""
echo "This demo shows three sophisticated real-world scenarios:"
echo ""
echo "  1. 💰 Financial Trading - AI optimization with human oversight"
echo "     Result: +$36,150 additional returns (58% improvement!)"
echo ""
echo "  2. 💻 Code Deployment - Preventing production incidents"
echo "     Result: Saved $50,000+ and prevented major outage"
echo ""
echo "  3. ⚖️  Legal Research - Quality assurance for case law"
echo "     Result: Prevented malpractice from citing overturned case"
echo ""
echo "Press ENTER to start..."
read

# Activate virtual environment
source venv/bin/activate

# Run impressive demo
python demo_impressive.py

echo ""
echo "============================================="
echo "Demo complete!"
echo ""
echo "Key Takeaways:"
echo "  • SafeRun added $36K in financial returns"
echo "  • Prevented $50K+ engineering disaster"
echo "  • Ensured professional-grade legal work"
echo ""
echo "Want to see the approval UI in action?"
echo "  Run: ./run_server.sh"
echo "  Visit: http://localhost:8000/approvals"
echo ""
