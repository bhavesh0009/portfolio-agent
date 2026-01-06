#!/bin/bash
# Restart Backend API to Apply Performance Calculator Fix

echo "=========================================="
echo "Restarting Backend API"
echo "=========================================="
echo ""

# Kill existing backend process
echo "Stopping existing price_service.py..."
pkill -f "python.*price_service.py" || echo "(No running process found)"
sleep 2

# Start fresh backend
echo "Starting fresh price_service.py..."
cd /Users/bhaveshghodasara/Development/portfolio-agent
source env/bin/activate
nohup python api/price_service.py > /dev/null 2>&1 &
BACKEND_PID=$!
echo "Backend restarted (PID: $BACKEND_PID)"
sleep 2

echo ""
echo "=========================================="
echo "Backend Restarted Successfully"
echo "=========================================="
echo ""
echo "Next steps:"
echo "  1. Hard refresh browser (Cmd+Shift+R)"
echo "  2. Verify dashboard shows:"
echo "     - Current Value: ₹4,94,535"
echo "     - Total P&L: -₹5,465 (-1.09%)"
echo "     - Holdings: 14 stocks"
echo "     - Cash Balance: ₹70,241"
echo ""
echo "API endpoint: http://localhost:8000"
echo "=========================================="
