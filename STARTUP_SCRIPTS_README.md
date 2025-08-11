# 🚀 Dhan AI Trader - Startup Scripts

This directory contains automated startup scripts that will launch both the backend (FastAPI) and frontend (React) services with a single command.

## 📁 Available Scripts

### 1. **Python Script** (Recommended) - `start_app.py`
**Cross-platform Python script with advanced features**

```bash
python start_app.py
```

**Features:**
- ✅ Cross-platform (Windows, macOS, Linux)
- ✅ Dependency checking
- ✅ Automatic dependency installation
- ✅ Process management
- ✅ Graceful shutdown (Ctrl+C)
- ✅ Browser auto-opening
- ✅ Colored terminal output
- ✅ Error handling and recovery

### 2. **Shell Script** (Unix/Linux/macOS) - `start_app.sh`
**Bash script for Unix-like systems**

```bash
./start_app.sh
```

**Features:**
- ✅ Native shell performance
- ✅ Process monitoring
- ✅ Signal handling
- ✅ Browser auto-opening
- ✅ Colored output

### 3. **Batch File** (Windows) - `start_app.bat`
**Windows batch file**

```cmd
start_app.bat
```

**Features:**
- ✅ Windows native
- ✅ Dependency checking
- ✅ Separate console windows
- ✅ Browser auto-opening

## 🚀 Quick Start

### Option 1: Python Script (Recommended)
```bash
# Navigate to project directory
cd dhan-ai-trader

# Run the Python startup script
python start_app.py
```

### Option 2: Shell Script (macOS/Linux)
```bash
# Navigate to project directory
cd dhan-ai-trader

# Make executable (first time only)
chmod +x start_app.sh

# Run the script
./start_app.sh
```

### Option 3: Batch File (Windows)
```cmd
# Navigate to project directory
cd dhan-ai-trader

# Run the batch file
start_app.bat
```
 
## 📋 What the Scripts Do

1. **🔍 Check Dependencies**
   - Verify Python 3.8+ is installed
   - Verify Node.js and npm are installed
   - Check project structure

2. **📦 Install Dependencies**
   - Install Python packages from `requirements.txt`
   - Install ML packages: `scikit-learn`, `scipy`, `pandas`, `numpy`
   - Install Node.js packages with `npm install`

3. **🚀 Start Services**
   - Launch FastAPI backend on `http://localhost:8000`
   - Launch React frontend on `http://localhost:3001`
   - Monitor both processes

4. **🌐 Open Browser**
   - Automatically open frontend app
   - Open API documentation in separate tab

5. **📊 Display Status**
   - Show access URLs
   - List available features
   - Provide sample AI chat queries

## 🛑 Stopping the Application

### Python Script & Shell Script
- Press `Ctrl+C` in the terminal
- Both services will be gracefully stopped

### Windows Batch File
- Close the separate console windows that opened
- Or press `Ctrl+C` in each window

## 🔧 Troubleshooting

### Common Issues

1. **Permission Denied (macOS/Linux)**
   ```bash
   chmod +x start_app.sh
   ```

2. **Python Not Found**
   - Install Python 3.8+ from [python.org](https://python.org)
   - Ensure Python is in your PATH

3. **Node.js Not Found**
   - Install Node.js from [nodejs.org](https://nodejs.org)
   - Ensure Node.js and npm are in your PATH

4. **Port Already in Use**
   - The scripts will automatically handle port conflicts
   - Frontend will use an alternative port if 3001 is busy

5. **Dependencies Installation Failed**
   - Check internet connection
   - Try running manually:
     ```bash
     pip install -r requirements.txt
     cd frontend && npm install
     ```

### Manual Verification

If scripts fail, you can start services manually:

**Backend:**
```bash
cd src
python -m dhan_trader.api.server
```

**Frontend:**
```bash
cd frontend
npm run start:dev
```

## 🎯 Expected Output

When successful, you should see:
- ✅ Dependency checks passed
- ✅ Backend started on http://localhost:8000
- ✅ Frontend started on http://localhost:3001
- 🌐 Browser windows opened automatically
- 📊 Status information displayed

## 🔗 Access URLs

After successful startup:
- **Frontend Application**: http://localhost:3001
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

## 🎉 Features Available

Once running, you can:
- Use the enhanced AI chat interface
- Try dynamic OI analysis queries
- View real-time options chain data
- Access comprehensive API documentation
- Test machine learning pattern recognition

## 💡 Tips

1. **First Run**: May take longer due to dependency installation
2. **Subsequent Runs**: Much faster as dependencies are cached
3. **Development**: Use the Python script for best experience
4. **Production**: Consider using proper process managers like PM2 or systemd

---

**Need Help?** Check the main `SETUP_GUIDE.md` for detailed setup instructions.
