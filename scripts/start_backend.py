#!/usr/bin/env python3
"""
Startup script for Dhan AI Trader backend server.
"""

import os
import sys
import subprocess
import logging
from pathlib import Path

# Add the src directory to Python path
project_root = Path(__file__).parent.parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def check_dependencies():
    """Check if required dependencies are installed."""
    try:
        import fastapi
        import uvicorn
        import dhan_trader
        logger.info("✅ All dependencies are installed")
        return True
    except ImportError as e:
        logger.error(f"❌ Missing dependency: {e}")
        logger.error("Please run: pip install -r requirements.txt")
        return False

def check_environment():
    """Check if environment variables are set."""
    if not os.getenv("DHAN_TOKEN"):
        logger.error("❌ DHAN_TOKEN environment variable is not set")
        logger.error("Please set your Dhan API token in the .env file")
        return False
    
    logger.info("✅ Environment variables are set")
    return True

def create_directories():
    """Create necessary directories."""
    directories = ["logs", "data"]
    
    for directory in directories:
        dir_path = project_root / directory
        dir_path.mkdir(exist_ok=True)
        logger.info(f"✅ Created directory: {directory}")

def start_server():
    """Start the FastAPI server."""
    try:
        logger.info("🚀 Starting Dhan AI Trader backend server...")
        logger.info("📊 Dashboard will be available at: http://localhost:8000")
        logger.info("📖 API documentation at: http://localhost:8000/docs")
        logger.info("🔄 Press Ctrl+C to stop the server")
        
        # Change to project root directory
        os.chdir(project_root)
        
        # Start the server
        subprocess.run([
            sys.executable, "-m", "uvicorn",
            "src.dhan_trader.api.server:app",
            "--host", "0.0.0.0",
            "--port", "8000",
            "--reload",
            "--log-level", "info"
        ])
        
    except KeyboardInterrupt:
        logger.info("🛑 Server stopped by user")
    except Exception as e:
        logger.error(f"❌ Failed to start server: {e}")
        sys.exit(1)

def main():
    """Main function."""
    logger.info("🔧 Initializing Dhan AI Trader backend...")
    
    # Check dependencies
    if not check_dependencies():
        sys.exit(1)
    
    # Check environment
    if not check_environment():
        sys.exit(1)
    
    # Create directories
    create_directories()
    
    # Start server
    start_server()

if __name__ == "__main__":
    main()
