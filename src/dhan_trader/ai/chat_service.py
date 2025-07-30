"""Chat service for handling AI-powered trading conversations."""

import uuid
import logging
import json
import os
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import asyncio
import time

from .trading_advisor import TradingAdvisor
from ..api.chat_models import (
    ChatMessage, ChatMessageType, ChatSession, 
    ChatRequest, ChatResponse, AnalysisRequest, AnalysisResponse,
    StrategyRequest, StrategyResponse
)

logger = logging.getLogger(__name__)


class ChatService:
    """Service for managing AI-powered trading chat conversations."""
    
    def __init__(self, trading_advisor: TradingAdvisor):
        """
        Initialize the chat service.

        Args:
            trading_advisor: Trading advisor instance
        """
        self.trading_advisor = trading_advisor
        self.sessions: Dict[str, ChatSession] = {}
        self.session_timeout = timedelta(hours=2)

        # Setup persistent storage
        self.storage_dir = "data/chat_history"
        os.makedirs(self.storage_dir, exist_ok=True)

        # Predefined quick responses for common queries
        self.quick_responses = {
            "market_status": "Let me check the current market conditions for you.",
            "option_chain": "I'll analyze the current option chain data.",
            "strategies": "Let me suggest some trading strategies based on current market conditions.",
            "portfolio": "I'll review your current portfolio and positions.",
            "risk": "Let me assess the risk factors in the current market."
        }

        # Load existing sessions from storage
        self._load_sessions_from_storage()

        logger.info("Chat service initialized with persistent storage")
    
    def _generate_session_id(self) -> str:
        """Generate a unique session ID."""
        return str(uuid.uuid4())
    
    def _generate_message_id(self) -> str:
        """Generate a unique message ID."""
        return str(uuid.uuid4())
    
    def _load_sessions_from_storage(self):
        """Load chat sessions from persistent storage."""
        try:
            for filename in os.listdir(self.storage_dir):
                if filename.endswith('.json'):
                    session_id = filename[:-5]  # Remove .json extension
                    session_path = os.path.join(self.storage_dir, filename)

                    with open(session_path, 'r', encoding='utf-8') as f:
                        session_data = json.load(f)

                    # Convert datetime strings back to datetime objects
                    session_data['created_at'] = datetime.fromisoformat(session_data['created_at'])
                    session_data['last_activity'] = datetime.fromisoformat(session_data['last_activity'])

                    for message in session_data['messages']:
                        message['timestamp'] = datetime.fromisoformat(message['timestamp'])

                    # Convert to ChatSession object
                    session = ChatSession(**session_data)

                    # Only load recent sessions (within timeout period)
                    if datetime.now() - session.last_activity < self.session_timeout:
                        self.sessions[session_id] = session
                        logger.debug(f"Loaded session: {session_id}")
                    else:
                        # Remove expired session file
                        os.remove(session_path)
                        logger.debug(f"Removed expired session: {session_id}")

        except Exception as e:
            logger.error(f"Error loading sessions from storage: {e}")

    def _save_session_to_storage(self, session: ChatSession):
        """Save a chat session to persistent storage."""
        try:
            session_path = os.path.join(self.storage_dir, f"{session.session_id}.json")

            # Convert session to dict for JSON serialization
            session_dict = session.dict()

            # Convert datetime objects to ISO strings
            session_dict['created_at'] = session.created_at.isoformat()
            session_dict['last_activity'] = session.last_activity.isoformat()

            for message in session_dict['messages']:
                message['timestamp'] = message['timestamp'].isoformat() if isinstance(message['timestamp'], datetime) else message['timestamp']

            with open(session_path, 'w', encoding='utf-8') as f:
                json.dump(session_dict, f, indent=2, ensure_ascii=False)

            logger.debug(f"Saved session to storage: {session.session_id}")

        except Exception as e:
            logger.error(f"Error saving session to storage: {e}")

    def _cleanup_expired_sessions(self):
        """Remove expired chat sessions."""
        current_time = datetime.now()
        expired_sessions = [
            session_id for session_id, session in self.sessions.items()
            if current_time - session.last_activity > self.session_timeout
        ]

        for session_id in expired_sessions:
            # Remove from storage
            session_path = os.path.join(self.storage_dir, f"{session_id}.json")
            if os.path.exists(session_path):
                os.remove(session_path)

            del self.sessions[session_id]
            logger.info(f"Cleaned up expired session: {session_id}")
    
    def _get_or_create_session(self, session_id: Optional[str] = None) -> ChatSession:
        """Get existing session or create a new one."""
        self._cleanup_expired_sessions()
        
        if session_id and session_id in self.sessions:
            session = self.sessions[session_id]
            session.last_activity = datetime.now()
            return session
        
        # Create new session
        new_session_id = session_id or self._generate_session_id()
        session = ChatSession(
            session_id=new_session_id,
            messages=[],
            created_at=datetime.now(),
            last_activity=datetime.now()
        )
        
        # Add welcome message
        welcome_message = ChatMessage(
            id=self._generate_message_id(),
            type=ChatMessageType.ASSISTANT,
            content="Hello! I'm your AI trading advisor. I can help you with options trading analysis, strategy suggestions, and market insights. What would you like to know?",
            timestamp=datetime.now()
        )
        session.messages.append(welcome_message)
        
        self.sessions[new_session_id] = session

        # Save new session to storage
        self._save_session_to_storage(session)

        logger.info(f"Created new chat session: {new_session_id}")

        return session
    
    async def process_chat_message(self, request: ChatRequest) -> ChatResponse:
        """
        Process a chat message and generate AI response.
        
        Args:
            request: Chat request
            
        Returns:
            Chat response with AI-generated content
        """
        start_time = time.time()
        
        try:
            # Get or create session
            session = self._get_or_create_session(request.session_id)
            
            # Add user message to session
            user_message = ChatMessage(
                id=self._generate_message_id(),
                type=ChatMessageType.USER,
                content=request.message,
                timestamp=datetime.now(),
                metadata=request.context
            )
            session.messages.append(user_message)
            
            # Determine if this requires market data
            market_data_used = request.use_market_data or self._requires_market_data(request.message)
            
            # Generate AI response
            ai_response_content = await self._generate_ai_response(
                request.message, 
                session,
                market_data_used
            )
            
            # Create assistant message
            assistant_message = ChatMessage(
                id=self._generate_message_id(),
                type=ChatMessageType.ASSISTANT,
                content=ai_response_content,
                timestamp=datetime.now(),
                metadata={"market_data_used": market_data_used}
            )
            session.messages.append(assistant_message)
            
            # Update session
            session.last_activity = datetime.now()

            # Save updated session to storage
            self._save_session_to_storage(session)

            processing_time = time.time() - start_time
            
            return ChatResponse(
                message=assistant_message,
                session_id=session.session_id,
                processing_time=processing_time,
                market_data_used=market_data_used
            )
            
        except Exception as e:
            logger.error(f"Error processing chat message: {e}")
            
            # Create error response
            error_message = ChatMessage(
                id=self._generate_message_id(),
                type=ChatMessageType.ASSISTANT,
                content=f"I apologize, but I encountered an error processing your request: {str(e)}",
                timestamp=datetime.now()
            )
            
            processing_time = time.time() - start_time
            session_id = request.session_id or self._generate_session_id()
            
            return ChatResponse(
                message=error_message,
                session_id=session_id,
                processing_time=processing_time,
                market_data_used=False
            )
    
    def _requires_market_data(self, message: str) -> bool:
        """Determine if the message requires real-time market data."""
        market_keywords = [
            "current", "now", "today", "price", "option chain", "strikes", 
            "volume", "open interest", "implied volatility", "greeks",
            "market", "nifty", "expiry", "premium", "call", "put"
        ]
        
        message_lower = message.lower()
        return any(keyword in message_lower for keyword in market_keywords)
    
    async def _generate_ai_response(
        self,
        message: str,
        session: ChatSession,
        use_market_data: bool
    ) -> str:
        """Generate AI response based on the message and context."""
        try:
            # Check for quick response patterns
            quick_response = self._get_quick_response(message)
            if quick_response and not use_market_data:
                return quick_response

            # Check for specific OI queries (e.g., "OI for 25600", "open interest 25600")
            import re
            oi_pattern = r'(?:oi|open interest).*?(\d{4,5})'
            oi_match = re.search(oi_pattern, message.lower())

            if oi_match and use_market_data:
                strike_price = float(oi_match.group(1))
                response = await self.trading_advisor.get_specific_oi_data(strike_price)
                return response

            # Check for OI-based trading recommendation queries
            oi_recommendation_patterns = [
                r'oi recommendation', r'oi based', r'oi trading', r'oi signal',
                r'trading recommendation', r'should i buy', r'should i sell',
                r'bullish.*bearish', r'market direction', r'trading signal',
                r'what to trade', r'trading advice', r'market outlook'
            ]

            if any(re.search(pattern, message.lower()) for pattern in oi_recommendation_patterns) and use_market_data:
                response = await self.trading_advisor.get_oi_based_recommendation()
                return response

            # Check for OI change analysis queries
            oi_change_patterns = [
                r'oi chang', r'open interest chang', r'institutional activity',
                r'oi build', r'oi unwinding', r'oi analysis'
            ]

            if any(re.search(pattern, message.lower()) for pattern in oi_change_patterns) and use_market_data:
                response = await self.trading_advisor.analyze_oi_changes()
                return response

            # Use trading advisor for market-related queries
            if use_market_data:
                response = await self.trading_advisor.get_trading_recommendation(message)
            else:
                # For general trading questions without market data
                response = await self.trading_advisor.ai_client.answer_trading_question(
                    question=message,
                    market_context=None,
                    portfolio_context=None
                )

            return response
            
        except Exception as e:
            logger.error(f"Error generating AI response: {e}")
            return "I'm sorry, I'm having trouble processing your request right now. Please try again."
    
    def _get_quick_response(self, message: str) -> Optional[str]:
        """Get quick response for common queries."""
        message_lower = message.lower()
        
        if any(word in message_lower for word in ["hello", "hi", "hey"]):
            return "Hello! I'm here to help you with options trading. What would you like to analyze today?"
        
        if any(word in message_lower for word in ["help", "what can you do"]):
            return """I can help you with REAL-TIME market data and AI-powered trading recommendations:

🎯 **OI-BASED TRADING RECOMMENDATIONS:**
• Ask "trading recommendation" or "should I buy/sell" for AI-powered signals
• Bullish/Bearish/Neutral signals based on PE vs CE OI analysis
• Confidence levels and risk warnings included
• Real-time analysis of nearest strike prices

📊 **MARKET ANALYSIS:**
• Live option chain analysis with current prices & OI
• Greeks analysis (Delta, Gamma, Theta, Vega) - real-time
• Implied volatility insights - current levels
• Market sentiment analysis
• Specific OI data for any strike (e.g., "OI for 25600")

💡 **TRADING STRATEGIES:**
• Strategy suggestions based on live data
• Risk assessment with live market conditions
• Portfolio recommendations
• OI change analysis and institutional activity tracking

**Try asking:**
• "What's your trading recommendation?"
• "Should I buy or sell NIFTY options?"
• "Give me an OI-based signal"
• "Analyze current market direction"

I have access to live market data and provide AI-powered trading insights with confidence levels and risk warnings!"""
        
        return None
    
    async def get_market_analysis(self, request: AnalysisRequest) -> AnalysisResponse:
        """Get detailed market analysis."""
        try:
            if request.analysis_type == "option_chain":
                analysis = await self.trading_advisor.analyze_option_chain_ai(
                    request.underlying_scrip, 
                    request.expiry
                )
            elif request.analysis_type == "unusual_activity":
                analysis = await self.trading_advisor.detect_unusual_activity()
            else:
                analysis = await self.trading_advisor.get_trading_recommendation(
                    f"Provide {request.analysis_type} analysis"
                )
            
            return AnalysisResponse(
                analysis=analysis,
                data_timestamp=datetime.now(),
                analysis_type=request.analysis_type,
                metadata=request.parameters
            )
            
        except Exception as e:
            logger.error(f"Error in market analysis: {e}")
            return AnalysisResponse(
                analysis=f"Error generating analysis: {str(e)}",
                data_timestamp=datetime.now(),
                analysis_type=request.analysis_type
            )
    
    async def get_strategy_suggestions(self, request: StrategyRequest) -> StrategyResponse:
        """Get trading strategy suggestions."""
        try:
            strategies = await self.trading_advisor.suggest_strategies(
                request.market_outlook,
                request.risk_tolerance
            )
            
            # Get current market conditions
            market_analysis = await self.trading_advisor.analyze_current_market(
                request.underlying_scrip
            )
            
            risk_assessment = f"""
Risk Assessment for {request.market_outlook} outlook with {request.risk_tolerance} risk tolerance:
- Market volatility should be considered
- Position sizing should align with risk tolerance
- Always use stop-losses and profit targets
- Monitor Greeks exposure, especially Theta decay
"""
            
            return StrategyResponse(
                strategies=strategies,
                market_conditions=market_analysis,
                risk_assessment=risk_assessment,
                timestamp=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"Error generating strategies: {e}")
            return StrategyResponse(
                strategies=f"Error generating strategies: {str(e)}",
                market_conditions={},
                risk_assessment="Unable to assess risk due to error",
                timestamp=datetime.now()
            )
    
    def get_session_history(self, session_id: str) -> Optional[ChatSession]:
        """Get chat session history by session ID."""
        # First check in-memory sessions
        if session_id in self.sessions:
            return self.sessions[session_id]

        # If not in memory, try to load from storage
        try:
            session_path = os.path.join(self.storage_dir, f"{session_id}.json")
            if os.path.exists(session_path):
                with open(session_path, 'r', encoding='utf-8') as f:
                    session_data = json.load(f)

                # Convert datetime strings back to datetime objects
                session_data['created_at'] = datetime.fromisoformat(session_data['created_at'])
                session_data['last_activity'] = datetime.fromisoformat(session_data['last_activity'])

                for message in session_data['messages']:
                    message['timestamp'] = datetime.fromisoformat(message['timestamp'])

                # Convert to ChatSession object
                session = ChatSession(**session_data)

                # Add to in-memory cache if not expired
                if datetime.now() - session.last_activity < self.session_timeout:
                    self.sessions[session_id] = session
                    return session

        except Exception as e:
            logger.error(f"Error loading session {session_id} from storage: {e}")

        return None

    def get_all_sessions(self) -> List[ChatSession]:
        """Get all available chat sessions."""
        all_sessions = []

        # Get sessions from storage
        try:
            for filename in os.listdir(self.storage_dir):
                if filename.endswith('.json'):
                    session_id = filename[:-5]  # Remove .json extension
                    session = self.get_session_history(session_id)
                    if session:
                        all_sessions.append(session)
        except Exception as e:
            logger.error(f"Error getting all sessions: {e}")

        # Sort by last activity (most recent first)
        all_sessions.sort(key=lambda s: s.last_activity, reverse=True)

        return all_sessions
    
    def get_active_sessions_count(self) -> int:
        """Get count of active sessions."""
        self._cleanup_expired_sessions()
        return len(self.sessions)
