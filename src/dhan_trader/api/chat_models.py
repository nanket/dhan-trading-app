"""Pydantic models for chat API endpoints."""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class ChatMessageType(str, Enum):
    """Types of chat messages."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ChatMessage(BaseModel):
    """Chat message model."""
    id: str = Field(..., description="Unique message ID")
    type: ChatMessageType = Field(..., description="Message type")
    content: str = Field(..., description="Message content")
    timestamp: datetime = Field(default_factory=datetime.now, description="Message timestamp")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional message metadata")


class ChatRequest(BaseModel):
    """Request model for chat messages."""
    message: str = Field(..., description="User message", min_length=1, max_length=1000)
    session_id: Optional[str] = Field(None, description="Chat session ID")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context for the request")
    use_market_data: bool = Field(True, description="Whether to use real-time market data for analysis")


class ChatResponse(BaseModel):
    """Response model for chat messages."""
    message: ChatMessage = Field(..., description="Assistant response message")
    session_id: str = Field(..., description="Chat session ID")
    processing_time: float = Field(..., description="Response processing time in seconds")
    market_data_used: bool = Field(False, description="Whether real-time market data was used")


class AnalysisRequest(BaseModel):
    """Request model for market analysis."""
    analysis_type: str = Field(..., description="Type of analysis requested")
    underlying_scrip: int = Field(13, description="Security ID for analysis")
    expiry: Optional[str] = Field(None, description="Specific expiry date")
    parameters: Optional[Dict[str, Any]] = Field(None, description="Additional analysis parameters")


class AnalysisResponse(BaseModel):
    """Response model for market analysis."""
    analysis: str = Field(..., description="AI-generated analysis")
    data_timestamp: datetime = Field(..., description="Timestamp of underlying data")
    analysis_type: str = Field(..., description="Type of analysis performed")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional analysis metadata")


class StrategyRequest(BaseModel):
    """Request model for strategy suggestions."""
    market_outlook: str = Field("neutral", description="Market outlook: bullish/bearish/neutral")
    risk_tolerance: str = Field("moderate", description="Risk tolerance: low/moderate/high")
    underlying_scrip: int = Field(13, description="Security ID")
    capital_allocation: Optional[float] = Field(None, description="Capital to allocate")


class StrategyResponse(BaseModel):
    """Response model for strategy suggestions."""
    strategies: str = Field(..., description="AI-generated strategy suggestions")
    market_conditions: Dict[str, Any] = Field(..., description="Current market conditions")
    risk_assessment: str = Field(..., description="Risk assessment for suggested strategies")
    timestamp: datetime = Field(default_factory=datetime.now, description="Response timestamp")


class ChatSession(BaseModel):
    """Chat session model."""
    session_id: str = Field(..., description="Unique session ID")
    messages: List[ChatMessage] = Field(default_factory=list, description="Session messages")
    created_at: datetime = Field(default_factory=datetime.now, description="Session creation time")
    last_activity: datetime = Field(default_factory=datetime.now, description="Last activity time")
    user_context: Optional[Dict[str, Any]] = Field(None, description="User-specific context")


class QuickAnalysisRequest(BaseModel):
    """Request model for quick market insights."""
    query_type: str = Field(..., description="Type of quick analysis")
    parameters: Optional[Dict[str, Any]] = Field(None, description="Query parameters")


class QuickAnalysisResponse(BaseModel):
    """Response model for quick market insights."""
    insight: str = Field(..., description="Quick market insight")
    confidence: float = Field(..., description="Confidence level (0-1)")
    data_freshness: str = Field(..., description="How fresh the underlying data is")
    timestamp: datetime = Field(default_factory=datetime.now, description="Response timestamp")


# Range OI Strategy Models
class RangeOIRequest(BaseModel):
    """Request model for Range OI Strategy analysis."""
    underlying_scrip: int = Field(default=13, description="Security ID (13 for NIFTY)")
    expiry: Optional[str] = Field(default=None, description="Option expiry date (YYYY-MM-DD)")
    current_price: Optional[float] = Field(default=None, description="Current underlying price")
    lower_strike: Optional[float] = Field(default=None, description="Lower strike price (e.g., 25500)")
    upper_strike: Optional[float] = Field(default=None, description="Upper strike price (e.g., 25600)")


class RangeOIResponse(BaseModel):
    """Response model for Range OI Strategy analysis."""
    current_price: float
    lower_strike: float
    upper_strike: float
    lower_strike_pe_oi: int
    lower_strike_ce_oi: int
    upper_strike_pe_oi: int
    upper_strike_ce_oi: int
    lower_strike_signal: str  # "support", "resistance", "neutral"
    upper_strike_signal: str  # "support", "resistance", "neutral"
    overall_signal: str  # "bullish", "bearish", "neutral"
    confidence: float  # 0.0 to 1.0
    reasoning: str
    timestamp: datetime

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class OIRecommendationRequest(BaseModel):
    """Request model for OI-based trading recommendations."""
    underlying_scrip: int = Field(13, description="Security ID (13 for NIFTY)")
    expiry: Optional[str] = Field(None, description="Option expiry date (uses nearest if None)")
    include_ai_analysis: bool = Field(True, description="Whether to include AI-enhanced analysis")


class OIRecommendationResponse(BaseModel):
    """Response model for OI-based trading recommendations."""
    signal: str = Field(..., description="Trading signal: bullish/bearish/neutral")
    confidence: float = Field(..., description="Confidence level (0.0 to 1.0)")
    current_price: float = Field(..., description="Current underlying price")
    lower_strike: float = Field(..., description="Lower strike price analyzed")
    upper_strike: float = Field(..., description="Upper strike price analyzed")
    lower_strike_analysis: Dict[str, Any] = Field(..., description="Lower strike OI analysis")
    upper_strike_analysis: Dict[str, Any] = Field(..., description="Upper strike OI analysis")
    reasoning: str = Field(..., description="Detailed reasoning for the recommendation")
    risk_warning: str = Field(..., description="Risk warning and disclaimers")
    ai_enhancement: Optional[str] = Field(None, description="AI-enhanced strategy suggestions")
    timestamp: datetime = Field(default_factory=datetime.now, description="Analysis timestamp")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class QuickOISignalResponse(BaseModel):
    """Response model for quick OI signal."""
    signal: str = Field(..., description="Trading signal: bullish/bearish/neutral")
    confidence: float = Field(..., description="Confidence level (0.0 to 1.0)")
    current_price: float = Field(..., description="Current underlying price")
    lower_strike: float = Field(..., description="Lower strike price")
    upper_strike: float = Field(..., description="Upper strike price")
    summary: str = Field(..., description="Quick summary of the signal")
    timestamp: str = Field(..., description="Analysis timestamp")


# Enhanced Chat Models for Dynamic OI Analysis
class OIPatternModel(BaseModel):
    """Model for detected OI patterns."""
    pattern_type: str = Field(..., description="Type of pattern detected")
    confidence: float = Field(..., description="Pattern confidence (0.0 to 1.0)")
    description: str = Field(..., description="Human-readable pattern description")
    strikes_involved: List[float] = Field(..., description="Strike prices involved in pattern")
    magnitude: float = Field(..., description="Pattern magnitude/strength")
    direction: str = Field(..., description="Pattern direction: bullish/bearish/neutral")
    time_horizon: str = Field(..., description="Expected time horizon: short/medium/long")
    risk_level: str = Field(..., description="Risk level: low/medium/high")


class DynamicOIAnalysisModel(BaseModel):
    """Model for dynamic OI analysis results."""
    timestamp: datetime = Field(..., description="Analysis timestamp")
    underlying_price: float = Field(..., description="Current underlying price")
    patterns: List[OIPatternModel] = Field(..., description="Detected OI patterns")
    overall_sentiment: str = Field(..., description="Overall market sentiment")
    confidence_score: float = Field(..., description="Overall confidence (0.0 to 1.0)")
    recommendation: str = Field(..., description="Trading recommendation")
    reasoning: str = Field(..., description="AI reasoning for recommendation")
    risk_assessment: str = Field(..., description="Risk assessment")
    key_levels: List[float] = Field(..., description="Key support/resistance levels")
    statistical_summary: Dict[str, Any] = Field(..., description="Statistical summary of OI data")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class EnhancedChatRequest(BaseModel):
    """Request model for enhanced chat with dynamic OI analysis."""
    message: str = Field(..., description="User message", min_length=1, max_length=1000)
    session_id: Optional[str] = Field(None, description="Chat session ID")
    use_market_data: bool = Field(True, description="Whether to use real-time market data")
    force_oi_analysis: bool = Field(False, description="Force dynamic OI analysis even for general queries")


class EnhancedChatResponse(BaseModel):
    """Response model for enhanced chat with dynamic OI analysis."""
    message: ChatMessage = Field(..., description="Assistant response message")
    session_id: str = Field(..., description="Chat session ID")
    processing_time: float = Field(..., description="Response processing time in seconds")
    analysis_type: str = Field(..., description="Type of analysis performed")
    oi_analysis: Optional[DynamicOIAnalysisModel] = Field(None, description="Dynamic OI analysis if performed")
    confidence_score: Optional[float] = Field(None, description="Overall confidence score")
    market_data_used: bool = Field(False, description="Whether real-time market data was used")
