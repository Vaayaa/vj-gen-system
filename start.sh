#!/bin/bash

# VJ-Gen System Startup Script
# Starts both the FastAPI backend and React frontend

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}VJ-Gen System${NC} - Starting services..."

# Check if we're in the right directory
if [ ! -d "api" ] || [ ! -d "frontend" ]; then
    echo -e "${YELLOW}Warning: Not in project root. Attempting to find it...${NC}"
    SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
    cd "$SCRIPT_DIR"
fi

# Function to cleanup background jobs on exit
cleanup() {
    echo -e "\n${YELLOW}Shutting down services...${NC}"
    kill $API_PID $FRONTEND_PID 2>/dev/null || true
    exit 0
}

trap cleanup SIGINT SIGTERM

# Start FastAPI backend
echo -e "${GREEN}[1/2]${NC} Starting FastAPI backend on port 8000..."
cd api
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000 &
API_PID=$!
cd ..

# Wait a moment for backend to initialize
sleep 2

# Start React frontend
echo -e "${GREEN}[2/2]${NC} Starting React frontend on port 3000..."
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..

echo ""
echo -e "${GREEN}VJ-Gen System is running!${NC}"
echo -e "  - API:       http://localhost:8000"
echo -e "  - API Docs:  http://localhost:8000/docs"
echo -e "  - Frontend:  http://localhost:3000"
echo ""
echo "Press Ctrl+C to stop all services"

# Wait for any process to exit
wait
