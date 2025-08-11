"""
Enhanced Chat Service with Dynamic OI Analysis.

This service extends the existing chat functionality with AI-powered
dynamic OI pattern recognition and trading recommendations.
"""

import logging
import re
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from .chat_service import ChatService, ChatMessage, ChatSession
from .dynamic_oi_analyzer import DynamicOIAnalyzer, DynamicOIAnalysis
from .gemini_client import GeminiAIClient
from .trading_advisor import TradingAdvisor
from ..market_data.manager import MarketDataManager

logger = logging.getLogger(__name__)


@dataclass
class EnhancedChatResponse:
    """Enhanced chat response with OI analysis."""
    message: ChatMessage
    oi_analysis: Optional[DynamicOIAnalysis] = None
    analysis_type: str = "general"
    confidence_score: Optional[float] = None


class EnhancedChatService(ChatService):
    """Enhanced chat service with dynamic OI analysis capabilities."""
    
    def __init__(
        self,
        market_data_manager: MarketDataManager,
        ai_client: GeminiAIClient,
        trading_advisor: TradingAdvisor
    ):
        """Initialize enhanced chat service."""
        super().__init__(trading_advisor)
        self.market_data_manager = market_data_manager
        self.ai_client = ai_client
        self.oi_analyzer = DynamicOIAnalyzer(market_data_manager, ai_client)
        
    async def send_message_enhanced(
        self,
        message: str,
        session_id: Optional[str] = None,
        use_market_data: bool = True
    ) -> EnhancedChatResponse:
        """
        Send message with enhanced OI analysis capabilities.
        
        Args:
            message: User message
            session_id: Optional session ID
            use_market_data: Whether to use real-time market data
            
        Returns:
            EnhancedChatResponse with analysis
        """
        try:
            # Get or create session
            session = self._get_or_create_session(session_id)
            
            # Create user message
            user_message = ChatMessage(
                id=str(len(session.messages) + 1),
                type="user",
                content=message,
                timestamp=datetime.now().isoformat()
            )
            session.messages.append(user_message)
            
            # Determine if this requires dynamic OI analysis
            requires_oi_analysis = self._requires_dynamic_oi_analysis(message)
            
            oi_analysis = None
            analysis_type = "general"
            confidence_score = None
            
            if requires_oi_analysis and use_market_data:
                # Perform dynamic OI analysis
                oi_analysis = await self.oi_analyzer.analyze_oi_patterns()
                analysis_type = "dynamic_oi"
                confidence_score = oi_analysis.confidence_score
                
                # Generate response based on OI analysis
                response_content = await self._generate_oi_analysis_response(
                    message, oi_analysis
                )
            else:
                # Use standard chat response
                response_content = await self._generate_ai_response(
                    message, session, use_market_data
                )
            
            # Create assistant message
            assistant_message = ChatMessage(
                id=str(len(session.messages) + 1),
                type="assistant",
                content=response_content,
                timestamp=datetime.now().isoformat()
            )
            session.messages.append(assistant_message)
            
            return EnhancedChatResponse(
                message=assistant_message,
                oi_analysis=oi_analysis,
                analysis_type=analysis_type,
                confidence_score=confidence_score
            )
            
        except Exception as e:
            logger.error(f"Error in enhanced chat service: {e}")
            error_message = ChatMessage(
                id=str(len(session.messages) + 1) if session else "error",
                type="assistant",
                content=f"I encountered an error processing your request: {str(e)}",
                timestamp=datetime.now().isoformat()
            )
            return EnhancedChatResponse(message=error_message)
    
    def _requires_dynamic_oi_analysis(self, message: str) -> bool:
        """Determine if message requires dynamic OI analysis."""
        # Patterns that trigger dynamic OI analysis
        dynamic_patterns = [
            r'dynamic.*oi', r'pattern.*oi', r'ai.*oi', r'machine.*learning.*oi',
            r'statistical.*oi', r'cluster.*oi', r'anomaly.*oi', r'momentum.*oi',
            r'advanced.*oi', r'intelligent.*oi', r'smart.*oi', r'deep.*analysis',
            r'comprehensive.*oi', r'detailed.*oi.*analysis', r'sophisticated.*oi',
            r'analyze.*patterns', r'detect.*patterns', r'oi.*insights',
            r'market.*sentiment.*oi', r'institutional.*activity', r'unusual.*activity',
            r'oi.*trends', r'oi.*momentum', r'oi.*clustering', r'oi.*distribution'
        ]
        
        message_lower = message.lower()
        return any(re.search(pattern, message_lower) for pattern in dynamic_patterns)
    
    async def _generate_oi_analysis_response(
        self,
        user_message: str,
        oi_analysis: DynamicOIAnalysis
    ) -> str:
        """Generate response based on dynamic OI analysis."""
        try:
            # Create comprehensive response
            response_parts = []
            
            # Header with timestamp and confidence
            response_parts.append(
                f"🤖 **Dynamic OI Analysis** (Confidence: {oi_analysis.confidence_score:.1%})\n"
                f"📊 **Analysis Time**: {oi_analysis.timestamp.strftime('%H:%M:%S')}\n"
                f"💹 **Current Price**: ₹{oi_analysis.underlying_price:,.2f}\n"
            )
            
            # Overall sentiment and recommendation
            sentiment_emoji = {"bullish": "🟢", "bearish": "🔴", "neutral": "🟡"}
            response_parts.append(
                f"\n**📈 Market Sentiment**: {sentiment_emoji.get(oi_analysis.overall_sentiment, '🟡')} "
                f"{oi_analysis.overall_sentiment.upper()}\n"
                f"**🎯 Recommendation**: {oi_analysis.recommendation}\n"
            )
            
            # Key patterns detected
            if oi_analysis.patterns:
                response_parts.append("\n**🔍 Detected Patterns:**")
                for i, pattern in enumerate(oi_analysis.patterns[:5], 1):  # Top 5 patterns
                    direction_emoji = {"bullish": "📈", "bearish": "📉", "neutral": "➡️"}
                    response_parts.append(
                        f"{i}. **{pattern.pattern_type.replace('_', ' ').title()}** "
                        f"{direction_emoji.get(pattern.direction, '➡️')} "
                        f"(Confidence: {pattern.confidence:.1%})\n"
                        f"   {pattern.description}"
                    )
            
            # Key levels
            if oi_analysis.key_levels:
                levels_str = ", ".join([f"₹{level:,.0f}" for level in oi_analysis.key_levels[:5]])
                response_parts.append(f"\n**🎯 Key Levels**: {levels_str}")
            
            # Statistical summary
            stats = oi_analysis.statistical_summary
            if stats:
                response_parts.append(
                    f"\n**📊 Market Statistics:**\n"
                    f"• Total CE OI: {stats.get('total_ce_oi', 0):,.0f}\n"
                    f"• Total PE OI: {stats.get('total_pe_oi', 0):,.0f}\n"
                    f"• PE/CE Ratio: {stats.get('avg_pe_ce_ratio', 0):.2f}\n"
                    f"• Max OI Strike: ₹{stats.get('max_oi_strike', 0):,.0f}"
                )
            
            # AI reasoning
            response_parts.append(f"\n**🧠 AI Analysis:**\n{oi_analysis.reasoning}")
            
            # Risk assessment
            response_parts.append(f"\n**⚠️ Risk Assessment:**\n{oi_analysis.risk_assessment}")
            
            # Disclaimer
            response_parts.append(
                "\n---\n"
                "⚠️ **Disclaimer**: This analysis is based on current OI patterns and AI interpretation. "
                "Always conduct your own research and consider your risk tolerance before trading."
            )
            
            return "\n".join(response_parts)
            
        except Exception as e:
            logger.error(f"Error generating OI analysis response: {e}")
            return f"Error generating analysis response: {str(e)}"
    
    async def get_dynamic_oi_analysis(
        self,
        underlying_scrip: int = 13,
        expiry: Optional[str] = None
    ) -> DynamicOIAnalysis:
        """Get dynamic OI analysis directly."""
        return await self.oi_analyzer.analyze_oi_patterns(underlying_scrip, expiry)
    
    async def ask_for_dynamic_oi_recommendation(self) -> EnhancedChatResponse:
        """Quick action for dynamic OI recommendation."""
        return await self.send_message_enhanced(
            "Provide a comprehensive dynamic OI analysis with AI-powered pattern recognition",
            use_market_data=True
        )
    
    async def ask_for_pattern_analysis(self) -> EnhancedChatResponse:
        """Quick action for OI pattern analysis."""
        return await self.send_message_enhanced(
            "Analyze current OI patterns using machine learning and statistical methods",
            use_market_data=True
        )
    
    async def ask_for_anomaly_detection(self) -> EnhancedChatResponse:
        """Quick action for anomaly detection."""
        return await self.send_message_enhanced(
            "Detect any anomalies or unusual activity in current OI data",
            use_market_data=True
        )
    
    async def ask_for_momentum_analysis(self) -> EnhancedChatResponse:
        """Quick action for momentum analysis."""
        return await self.send_message_enhanced(
            "Analyze OI momentum and trends across all strikes",
            use_market_data=True
        )
