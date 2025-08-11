#!/bin/bash

# Dhan AI Trader - Application Startup Script
# Starts both backend (FastAPI) and frontend (React) services automatically.

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Configuration
BACKEND_PORT=8000
FRONTEND_PORT=3001
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Process IDs
BACKEND_PID=""
FRONTEND_PID=""

# Print banner
print_banner() {
    echo -e "${CYAN}${BOLD}"
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║                    🚀 DHAN AI TRADER 🚀                     ║"
    echo "║              Enhanced AI Chat & Dynamic OI Analysis          ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check dependencies
check_dependencies() {
    echo -e "${CYAN}🔍 Checking dependencies...${NC}"
    
    # Check Python
    if command_exists python3; then
        PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2)
        echo -e "${GREEN}✅ Python ${PYTHON_VERSION}${NC}"
    else
        echo -e "${RED}❌ Python 3 not found${NC}"
        return 1
    fi
    
    # Check Node.js
    if command_exists node; then
        NODE_VERSION=$(node --version)
        echo -e "${GREEN}✅ Node.js ${NODE_VERSION}${NC}"
    else
        echo -e "${RED}❌ Node.js not found${NC}"
        return 1
    fi
    
    # Check npm
    if command_exists npm; then
        NPM_VERSION=$(npm --version)
        echo -e "${GREEN}✅ npm ${NPM_VERSION}${NC}"
    else
        echo -e "${RED}❌ npm not found${NC}"
        return 1
    fi
    
    return 0
}

# Install dependencies
install_dependencies() {
    echo -e "${CYAN}📦 Installing dependencies...${NC}"
    
    # Install Python dependencies
    echo -e "${BLUE}Installing Python dependencies...${NC}"
    cd "$PROJECT_ROOT"
    python3 -m pip install -r requirements.txt
    python3 -m pip install scikit-learn scipy pandas numpy
    
    # Install Node.js dependencies
    echo -e "${BLUE}Installing Node.js dependencies...${NC}"
    cd "$PROJECT_ROOT/frontend"
    npm install
    
    echo -e "${GREEN}✅ Dependencies installed${NC}"
}

# Start backend
start_backend() {
    echo -e "${BLUE}🚀 Starting backend server...${NC}"
    
    cd "$PROJECT_ROOT/src"
    export PYTHONPATH="$PROJECT_ROOT/src"
    
    # Start backend in background
    python3 -m dhan_trader.api.server > ../logs/backend.log 2>&1 &
    BACKEND_PID=$!
    
    # Wait and check if it started
    sleep 3
    if kill -0 $BACKEND_PID 2>/dev/null; then
        echo -e "${GREEN}✅ Backend started on http://localhost:${BACKEND_PORT} (PID: ${BACKEND_PID})${NC}"
        return 0
    else
        echo -e "${RED}❌ Backend failed to start${NC}"
        return 1
    fi
}

# Start frontend
start_frontend() {
    echo -e "${BLUE}🚀 Starting frontend server...${NC}"
    
    cd "$PROJECT_ROOT/frontend"
    
    # Set environment variables
    export REACT_APP_API_URL="http://localhost:${BACKEND_PORT}"
    export PORT="${FRONTEND_PORT}"
    
    # Start frontend in background
    npm start > ../logs/frontend.log 2>&1 &
    FRONTEND_PID=$!
    
    # Wait and check if it started
    sleep 8
    if kill -0 $FRONTEND_PID 2>/dev/null; then
        echo -e "${GREEN}✅ Frontend started on http://localhost:${FRONTEND_PORT} (PID: ${FRONTEND_PID})${NC}"
        return 0
    else
        echo -e "${RED}❌ Frontend failed to start${NC}"
        return 1
    fi
}

# Open browser
open_browser() {
    echo -e "${CYAN}🌐 Opening browser...${NC}"
    
    sleep 2
    
    # Try different browser opening commands
    if command_exists open; then
        # macOS
        open "http://localhost:${FRONTEND_PORT}"
        sleep 2
        open "http://localhost:${BACKEND_PORT}/docs"
    elif command_exists xdg-open; then
        # Linux
        xdg-open "http://localhost:${FRONTEND_PORT}"
        sleep 2
        xdg-open "http://localhost:${BACKEND_PORT}/docs"
    elif command_exists start; then
        # Windows (if running in Git Bash or similar)
        start "http://localhost:${FRONTEND_PORT}"
        sleep 2
        start "http://localhost:${BACKEND_PORT}/docs"
    else
        echo -e "${YELLOW}⚠️  Could not auto-open browser. Please manually open:${NC}"
        echo -e "   Frontend: http://localhost:${FRONTEND_PORT}"
        echo -e "   API Docs: http://localhost:${BACKEND_PORT}/docs"
    fi
}

# Print status
print_status() {
    echo -e "${GREEN}${BOLD}🎉 Dhan AI Trader is now running!${NC}"
    echo ""
    echo -e "${CYAN}📍 Access URLs:${NC}"
    echo -e "  • Frontend App:       http://localhost:${FRONTEND_PORT}"
    echo -e "  • Backend API:        http://localhost:${BACKEND_PORT}"
    echo -e "  • API Documentation:  http://localhost:${BACKEND_PORT}/docs"
    echo ""
    echo -e "${CYAN}🎯 Key Features Available:${NC}"
    echo -e "  • Enhanced AI Chat with Dynamic OI Analysis"
    echo -e "  • Real-time Options Chain Data"
    echo -e "  • Machine Learning Pattern Recognition"
    echo -e "  • Statistical Anomaly Detection"
    echo -e "  • Natural Language Trading Queries"
    echo ""
    echo -e "${CYAN}💬 Try these AI chat queries:${NC}"
    echo -e "  • \"Provide comprehensive dynamic OI analysis\""
    echo -e "  • \"Analyze current OI patterns using machine learning\""
    echo -e "  • \"What's the market sentiment based on OI data?\""
    echo ""
    echo -e "${YELLOW}⚠️  Press Ctrl+C to stop both services${NC}"
}

# Cleanup function
cleanup() {
    echo -e "\n${YELLOW}🛑 Shutting down services...${NC}"
    
    # Stop frontend
    if [ ! -z "$FRONTEND_PID" ] && kill -0 $FRONTEND_PID 2>/dev/null; then
        kill $FRONTEND_PID
        echo -e "${GREEN}✅ Frontend stopped${NC}"
    fi
    
    # Stop backend
    if [ ! -z "$BACKEND_PID" ] && kill -0 $BACKEND_PID 2>/dev/null; then
        kill $BACKEND_PID
        echo -e "${GREEN}✅ Backend stopped${NC}"
    fi
    
    echo -e "${GREEN}👋 Goodbye!${NC}"
    exit 0
}

# Set up signal handlers
trap cleanup SIGINT SIGTERM

# Main execution
main() {
    print_banner
    
    # Create logs directory
    mkdir -p "$PROJECT_ROOT/logs"
    
    # Check dependencies
    if ! check_dependencies; then
        echo -e "${RED}❌ Dependency check failed. Please install required dependencies.${NC}"
        exit 1
    fi
    
    # Install dependencies
    install_dependencies
    
    # Start services
    if ! start_backend; then
        exit 1
    fi
    
    if ! start_frontend; then
        cleanup
        exit 1
    fi
    
    # Open browser
    open_browser
    
    # Print status
    print_status
    
    # Wait for user interrupt
    echo -e "${CYAN}Waiting for services... (Press Ctrl+C to stop)${NC}"
    while true; do
        sleep 1
        
        # Check if processes are still running
        if [ ! -z "$BACKEND_PID" ] && ! kill -0 $BACKEND_PID 2>/dev/null; then
            echo -e "${RED}❌ Backend process died${NC}"
            cleanup
            exit 1
        fi
        
        if [ ! -z "$FRONTEND_PID" ] && ! kill -0 $FRONTEND_PID 2>/dev/null; then
            echo -e "${RED}❌ Frontend process died${NC}"
            cleanup
            exit 1
        fi
    done
}

# Run main function
main "$@"
