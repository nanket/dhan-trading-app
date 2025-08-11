#!/usr/bin/env python3
"""
Dhan AI Trader - Application Startup Script
Starts both backend (FastAPI) and frontend (React) services automatically.
"""

import os
import sys
import time
import signal
import subprocess
import threading
from pathlib import Path
import webbrowser
from typing import List, Optional

class Colors:
    """ANSI color codes for terminal output."""
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

class AppStarter:
    """Main application starter class."""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.absolute()
        self.backend_process: Optional[subprocess.Popen] = None
        self.frontend_process: Optional[subprocess.Popen] = None
        self.backend_port = 8000
        self.frontend_port = 3001
        
    def print_banner(self):
        """Print application banner."""
        banner = f"""
{Colors.HEADER}{Colors.BOLD}
╔══════════════════════════════════════════════════════════════╗
║                    🚀 DHAN AI TRADER 🚀                     ║
║              Enhanced AI Chat & Dynamic OI Analysis          ║
╚══════════════════════════════════════════════════════════════╝
{Colors.ENDC}
"""
        print(banner)
    
    def check_dependencies(self) -> bool:
        """Check if required dependencies are available."""
        print(f"{Colors.OKCYAN}🔍 Checking dependencies...{Colors.ENDC}")
        
        # Check Python
        try:
            python_version = sys.version_info
            if python_version.major < 3 or (python_version.major == 3 and python_version.minor < 8):
                print(f"{Colors.FAIL}❌ Python 3.8+ required. Current: {python_version.major}.{python_version.minor}{Colors.ENDC}")
                return False
            print(f"{Colors.OKGREEN}✅ Python {python_version.major}.{python_version.minor}.{python_version.micro}{Colors.ENDC}")
        except Exception as e:
            print(f"{Colors.FAIL}❌ Python check failed: {e}{Colors.ENDC}")
            return False
        
        # Check Node.js
        try:
            result = subprocess.run(['node', '--version'], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                node_version = result.stdout.strip()
                print(f"{Colors.OKGREEN}✅ Node.js {node_version}{Colors.ENDC}")
            else:
                print(f"{Colors.FAIL}❌ Node.js not found{Colors.ENDC}")
                return False
        except (subprocess.TimeoutExpired, FileNotFoundError):
            print(f"{Colors.FAIL}❌ Node.js not found or not accessible{Colors.ENDC}")
            return False
        
        # Check npm
        try:
            result = subprocess.run(['npm', '--version'], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                npm_version = result.stdout.strip()
                print(f"{Colors.OKGREEN}✅ npm {npm_version}{Colors.ENDC}")
            else:
                print(f"{Colors.FAIL}❌ npm not found{Colors.ENDC}")
                return False
        except (subprocess.TimeoutExpired, FileNotFoundError):
            print(f"{Colors.FAIL}❌ npm not found or not accessible{Colors.ENDC}")
            return False
        
        return True
    
    def check_project_structure(self) -> bool:
        """Check if project structure is correct."""
        print(f"{Colors.OKCYAN}📁 Checking project structure...{Colors.ENDC}")
        
        required_paths = [
            self.project_root / "src" / "dhan_trader" / "api" / "server.py",
            self.project_root / "frontend" / "package.json",
            self.project_root / "frontend" / "src",
        ]
        
        for path in required_paths:
            if not path.exists():
                print(f"{Colors.FAIL}❌ Missing: {path}{Colors.ENDC}")
                return False
            print(f"{Colors.OKGREEN}✅ Found: {path.name}{Colors.ENDC}")
        
        return True
    
    def install_dependencies(self):
        """Install missing dependencies."""
        print(f"{Colors.OKCYAN}📦 Installing dependencies...{Colors.ENDC}")
        
        # Install Python dependencies
        try:
            print(f"{Colors.OKBLUE}Installing Python dependencies...{Colors.ENDC}")
            subprocess.run([
                sys.executable, "-m", "pip", "install", "-r", "requirements.txt"
            ], cwd=self.project_root, check=True)
            
            # Install ML dependencies for dynamic OI analysis
            subprocess.run([
                sys.executable, "-m", "pip", "install", 
                "scikit-learn", "scipy", "pandas", "numpy"
            ], cwd=self.project_root, check=True)
            
            print(f"{Colors.OKGREEN}✅ Python dependencies installed{Colors.ENDC}")
        except subprocess.CalledProcessError as e:
            print(f"{Colors.WARNING}⚠️  Python dependencies installation failed: {e}{Colors.ENDC}")
        
        # Install Node.js dependencies
        try:
            print(f"{Colors.OKBLUE}Installing Node.js dependencies...{Colors.ENDC}")
            subprocess.run([
                "npm", "install"
            ], cwd=self.project_root / "frontend", check=True)
            print(f"{Colors.OKGREEN}✅ Node.js dependencies installed{Colors.ENDC}")
        except subprocess.CalledProcessError as e:
            print(f"{Colors.WARNING}⚠️  Node.js dependencies installation failed: {e}{Colors.ENDC}")
    
    def start_backend(self):
        """Start the backend FastAPI server."""
        print(f"{Colors.OKBLUE}🚀 Starting backend server...{Colors.ENDC}")
        
        try:
            # Change to src directory and start the server
            env = os.environ.copy()
            env['PYTHONPATH'] = str(self.project_root / "src")
            
            self.backend_process = subprocess.Popen([
                sys.executable, "-m", "dhan_trader.api.server"
            ], cwd=self.project_root / "src", env=env)
            
            # Wait a moment to check if it started successfully
            time.sleep(3)
            if self.backend_process.poll() is None:
                print(f"{Colors.OKGREEN}✅ Backend started on http://localhost:{self.backend_port}{Colors.ENDC}")
                return True
            else:
                print(f"{Colors.FAIL}❌ Backend failed to start{Colors.ENDC}")
                return False
                
        except Exception as e:
            print(f"{Colors.FAIL}❌ Backend startup error: {e}{Colors.ENDC}")
            return False
    
    def start_frontend(self):
        """Start the frontend React development server."""
        print(f"{Colors.OKBLUE}🚀 Starting frontend server...{Colors.ENDC}")
        
        try:
            # Set environment variables for frontend
            env = os.environ.copy()
            env['REACT_APP_API_URL'] = f'http://localhost:{self.backend_port}'
            env['PORT'] = str(self.frontend_port)
            
            self.frontend_process = subprocess.Popen([
                "npm", "run", "start"
            ], cwd=self.project_root / "frontend", env=env)
            
            # Wait a moment to check if it started successfully
            time.sleep(5)
            if self.frontend_process.poll() is None:
                print(f"{Colors.OKGREEN}✅ Frontend started on http://localhost:{self.frontend_port}{Colors.ENDC}")
                return True
            else:
                print(f"{Colors.FAIL}❌ Frontend failed to start{Colors.ENDC}")
                return False
                
        except Exception as e:
            print(f"{Colors.FAIL}❌ Frontend startup error: {e}{Colors.ENDC}")
            return False
    
    def open_browser(self):
        """Open browser with the application URLs."""
        print(f"{Colors.OKCYAN}🌐 Opening browser...{Colors.ENDC}")
        
        try:
            # Wait a bit more for services to be fully ready
            time.sleep(3)
            
            # Open frontend
            webbrowser.open(f'http://localhost:{self.frontend_port}')
            
            # Open API docs in a new tab after a short delay
            threading.Timer(2.0, lambda: webbrowser.open(f'http://localhost:{self.backend_port}/docs')).start()
            
            print(f"{Colors.OKGREEN}✅ Browser opened{Colors.ENDC}")
        except Exception as e:
            print(f"{Colors.WARNING}⚠️  Could not open browser: {e}{Colors.ENDC}")
    
    def print_status(self):
        """Print current application status."""
        status = f"""
{Colors.OKGREEN}{Colors.BOLD}🎉 Dhan AI Trader is now running!{Colors.ENDC}

{Colors.OKCYAN}📍 Access URLs:{Colors.ENDC}
  • Frontend App:     http://localhost:{self.frontend_port}
  • Backend API:      http://localhost:{self.backend_port}
  • API Documentation: http://localhost:{self.backend_port}/docs

{Colors.OKCYAN}🎯 Key Features Available:{Colors.ENDC}
  • Enhanced AI Chat with Dynamic OI Analysis
  • Real-time Options Chain Data
  • Machine Learning Pattern Recognition
  • Statistical Anomaly Detection
  • Natural Language Trading Queries

{Colors.OKCYAN}💬 Try these AI chat queries:{Colors.ENDC}
  • "Provide comprehensive dynamic OI analysis"
  • "Analyze current OI patterns using machine learning"
  • "What's the market sentiment based on OI data?"

{Colors.WARNING}⚠️  Press Ctrl+C to stop both services{Colors.ENDC}
"""
        print(status)
    
    def cleanup(self):
        """Clean up processes on exit."""
        print(f"\n{Colors.WARNING}🛑 Shutting down services...{Colors.ENDC}")
        
        if self.frontend_process:
            try:
                self.frontend_process.terminate()
                self.frontend_process.wait(timeout=5)
                print(f"{Colors.OKGREEN}✅ Frontend stopped{Colors.ENDC}")
            except subprocess.TimeoutExpired:
                self.frontend_process.kill()
                print(f"{Colors.WARNING}⚠️  Frontend force killed{Colors.ENDC}")
        
        if self.backend_process:
            try:
                self.backend_process.terminate()
                self.backend_process.wait(timeout=5)
                print(f"{Colors.OKGREEN}✅ Backend stopped{Colors.ENDC}")
            except subprocess.TimeoutExpired:
                self.backend_process.kill()
                print(f"{Colors.WARNING}⚠️  Backend force killed{Colors.ENDC}")
        
        print(f"{Colors.OKGREEN}👋 Goodbye!{Colors.ENDC}")
    
    def run(self):
        """Main run method."""
        self.print_banner()
        
        # Check dependencies
        if not self.check_dependencies():
            print(f"{Colors.FAIL}❌ Dependency check failed. Please install required dependencies.{Colors.ENDC}")
            return False
        
        # Check project structure
        if not self.check_project_structure():
            print(f"{Colors.FAIL}❌ Project structure check failed.{Colors.ENDC}")
            return False
        
        # Install dependencies
        self.install_dependencies()
        
        # Start services
        if not self.start_backend():
            return False
        
        if not self.start_frontend():
            self.cleanup()
            return False
        
        # Open browser
        self.open_browser()
        
        # Print status
        self.print_status()
        
        # Wait for user interrupt
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
        finally:
            self.cleanup()
        
        return True

def main():
    """Main entry point."""
    app_starter = AppStarter()
    
    # Handle Ctrl+C gracefully
    def signal_handler(sig, frame):
        app_starter.cleanup()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    success = app_starter.run()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
