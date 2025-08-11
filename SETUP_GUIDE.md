# 🚀 Dhan AI Trader - Complete Setup Guide

## 📋 Prerequisites

Before starting, ensure you have the following installed:

- **Python 3.8+** (recommended: 3.12)
- **Node.js 16+** and **npm**
- **Git**
- **Dhan HQ API credentials** (Access Token and Client ID)

## 🔧 Environment Setup

### 1. Clone and Navigate to Project
```bash
git clone <repository-url>
cd dhan-ai-trader
```

### 2. Backend Setup (Python/FastAPI)

#### Install Python Dependencies
```bash
# Install required packages
pip install -r requirements.txt

# Install additional ML dependencies for dynamic OI analysis
pip install scikit-learn scipy pandas numpy
```

#### Configure Environment Variables
Create a `.env` file in the project root:
```bash
# Dhan API Configuration
DHAN_ACCESS_TOKEN=your_dhan_access_token_here
DHAN_CLIENT_ID=your_dhan_client_id_here

# Gemini AI Configuration (for AI analysis)
GEMINI_API_KEY=your_gemini_api_key_here

# Optional: Database Configuration
DATABASE_URL=sqlite:///data/dhan_trader.db

# Optional: Logging Configuration
LOG_LEVEL=INFO
```

### 3. Frontend Setup (React/TypeScript)

#### Install Node.js Dependencies
```bash
cd frontend
npm install
cd ..
```

## 🚀 Running the Application

### Method 1: Start Both Services Manually

#### Terminal 1 - Backend API Server
```bash
cd src
python -m dhan_trader.api.server
```
The backend will start on: **http://localhost:8000**

#### Terminal 2 - Frontend Development Server
```bash
cd frontend
npm run start:dev
```
The frontend will start on: **http://localhost:3000**

### Method 2: Quick Start Scripts

#### Start Backend Only
```bash
cd src && python -m dhan_trader.api.server
```

#### Start Frontend Only
```bash
cd frontend && npm run start:dev
```

## 🔍 Verification Steps

### 1. Backend Health Check
Open your browser and visit:
- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health
- **Option Chain**: http://localhost:8000/api/optionchain/13

### 2. Frontend Access
- **Main Application**: http://localhost:3000
- **Options Chain View**: http://localhost:3000/options
- **AI Chat Interface**: http://localhost:3000/chat

### 3. Test Enhanced AI Chat
Visit the chat interface and try these commands:
- "Provide a comprehensive dynamic OI analysis with AI-powered pattern recognition"
- "Analyze current OI patterns using machine learning and statistical methods"
- "What's the current market sentiment based on OI data?"

## 🎯 Key Features Available

### 1. **Dynamic OI Analysis** 🧠
- AI-powered pattern recognition
- Statistical analysis using machine learning
- Real-time anomaly detection
- Momentum and trend analysis

### 2. **Enhanced Chat Interface** 💬
- Natural language queries for OI analysis
- Automatic pattern detection
- Comprehensive trading recommendations
- Risk assessment and key level identification

### 3. **API Endpoints** 🔌
- `/api/chat/enhanced` - Enhanced chat with dynamic OI analysis
- `/api/chat/dynamic-oi-analysis` - Direct OI analysis endpoint
- `/api/optionchain/{scrip_id}` - Real-time option chain data
- `/api/oi-recommendation` - OI-based trading recommendations

### 4. **Real-time Data** 📊
- Live market data from Dhan HQ API
- WebSocket connections for real-time updates
- Change in Open Interest calculations
- Volume and OI ratio analysis

## 🛠️ Development Commands

### Backend Development
```bash
# Run with auto-reload for development
cd src
python -m dhan_trader.api.server --reload

# Run tests
python -m pytest tests/

# Check code quality
flake8 src/
black src/
```

### Frontend Development
```bash
cd frontend

# Start development server
npm start

# Run tests
npm test

# Build for production
npm run build

# Type checking
npx tsc --noEmit
```

## 📱 Production Deployment

### Backend Production
```bash
# Install production dependencies
pip install gunicorn

# Start with Gunicorn
cd src
gunicorn dhan_trader.api.server:app --host 0.0.0.0 --port 8000 --workers 4
```

### Frontend Production
```bash
cd frontend

# Build for production
npm run build:prod

# Serve static files (example with serve)
npx serve -s build -l 3000
```

## 🔧 Troubleshooting

### Common Issues

1. **Rate Limit Exceeded**
   - The Dhan API has rate limits
   - Wait a few minutes between heavy testing
   - Consider implementing caching for production

2. **Import Errors**
   - Ensure you're running from the correct directory
   - Check Python path: `cd src && python -m dhan_trader.api.server`

3. **Frontend Connection Issues**
   - Verify backend is running on port 8000
   - Check CORS settings in the backend
   - Ensure `REACT_APP_API_URL` is set correctly

4. **Missing Dependencies**
   - Backend: `pip install -r requirements.txt`
   - Frontend: `cd frontend && npm install`

### Environment Variables Check
```bash
# Verify environment variables are set
echo $DHAN_ACCESS_TOKEN
echo $DHAN_CLIENT_ID
echo $GEMINI_API_KEY
```

## 📞 Support

For issues or questions:
1. Check the logs in `logs/dhan_trader.log`
2. Verify API credentials are valid
3. Ensure all dependencies are installed
4. Check network connectivity for API calls

---

## 🎉 You're Ready!

Once both services are running:
- **Backend**: http://localhost:8000
- **Frontend**: http://localhost:3000
- **API Docs**: http://localhost:8000/docs

The enhanced AI chatbot with dynamic OI analysis is now ready for use! 🚀
