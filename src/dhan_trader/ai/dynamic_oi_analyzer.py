"""
Dynamic OI Analysis Service using AI-powered pattern recognition.

This service analyzes Change in Open Interest (OI) data using machine learning
and statistical analysis to identify meaningful patterns and generate trading
recommendations without relying on fixed rules.
"""

import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from scipy import stats
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans

from ..market_data.manager import MarketDataManager
from .gemini_client import GeminiAIClient

logger = logging.getLogger(__name__)


@dataclass
class OIPattern:
    """Represents a detected OI pattern."""
    pattern_type: str
    confidence: float
    description: str
    strikes_involved: List[float]
    magnitude: float
    direction: str  # bullish, bearish, neutral
    time_horizon: str  # short, medium, long
    risk_level: str  # low, medium, high


@dataclass
class DynamicOIAnalysis:
    """Dynamic OI analysis result."""
    timestamp: datetime
    underlying_price: float
    patterns: List[OIPattern]
    overall_sentiment: str
    confidence_score: float
    recommendation: str
    reasoning: str
    risk_assessment: str
    key_levels: List[float]
    statistical_summary: Dict[str, Any]


class DynamicOIAnalyzer:
    """AI-powered dynamic OI analysis service."""
    
    def __init__(self, market_data_manager: MarketDataManager, ai_client: GeminiAIClient):
        """Initialize the dynamic OI analyzer."""
        self.market_data_manager = market_data_manager
        self.ai_client = ai_client
        self.scaler = StandardScaler()
        
    async def analyze_oi_patterns(
        self,
        underlying_scrip: int = 13,
        expiry: Optional[str] = None,
        lookback_periods: int = 5
    ) -> DynamicOIAnalysis:
        """
        Perform dynamic OI pattern analysis using AI and statistical methods.
        
        Args:
            underlying_scrip: Underlying instrument ID
            expiry: Option expiry date
            lookback_periods: Number of time periods to analyze for trends
            
        Returns:
            DynamicOIAnalysis with patterns and recommendations
        """
        try:
            # Get current option chain data
            option_chain = self.market_data_manager.get_option_chain_with_oi_changes(
                underlying_scrip, "IDX_I", expiry, use_cache=False
            )
            
            current_price = option_chain.underlying_price
            
            # Extract and prepare OI data for analysis
            oi_data = self._extract_oi_data(option_chain.strikes, current_price)
            
            # Perform statistical analysis
            statistical_patterns = self._detect_statistical_patterns(oi_data)
            
            # Perform clustering analysis
            cluster_patterns = self._detect_cluster_patterns(oi_data)
            
            # Analyze OI momentum and trends
            momentum_patterns = self._analyze_oi_momentum(oi_data)
            
            # Detect anomalies and unusual activity
            anomaly_patterns = self._detect_anomalies(oi_data)
            
            # Combine all patterns
            all_patterns = (
                statistical_patterns + cluster_patterns + 
                momentum_patterns + anomaly_patterns
            )
            
            # Generate overall sentiment and confidence
            overall_sentiment, confidence_score = self._calculate_overall_sentiment(all_patterns)
            
            # Identify key support/resistance levels
            key_levels = self._identify_key_levels(oi_data, current_price)
            
            # Generate AI-powered recommendation
            recommendation, reasoning, risk_assessment = await self._generate_ai_recommendation(
                oi_data, all_patterns, current_price, overall_sentiment
            )
            
            # Create statistical summary
            statistical_summary = self._create_statistical_summary(oi_data)
            
            return DynamicOIAnalysis(
                timestamp=datetime.now(),
                underlying_price=current_price,
                patterns=all_patterns,
                overall_sentiment=overall_sentiment,
                confidence_score=confidence_score,
                recommendation=recommendation,
                reasoning=reasoning,
                risk_assessment=risk_assessment,
                key_levels=key_levels,
                statistical_summary=statistical_summary
            )
            
        except Exception as e:
            logger.error(f"Error in dynamic OI analysis: {e}")
            raise
    
    def _extract_oi_data(self, strikes: Dict, current_price: float) -> pd.DataFrame:
        """Extract and structure OI data for analysis."""
        data = []
        
        for strike_key, strike_data in strikes.items():
            strike_price = float(strike_key)
            
            # Calculate distance from current price
            distance = strike_price - current_price
            distance_pct = (distance / current_price) * 100
            
            # Extract CE data
            ce_oi = strike_data.ce.oi if strike_data.ce else 0
            ce_volume = strike_data.ce.volume if strike_data.ce else 0
            ce_oi_change = 0
            ce_oi_change_pct = 0
            
            if strike_data.ce and strike_data.ce.oi_change:
                ce_oi_change = strike_data.ce.oi_change.absolute_change
                ce_oi_change_pct = strike_data.ce.oi_change.percentage_change
            
            # Extract PE data
            pe_oi = strike_data.pe.oi if strike_data.pe else 0
            pe_volume = strike_data.pe.volume if strike_data.pe else 0
            pe_oi_change = 0
            pe_oi_change_pct = 0
            
            if strike_data.pe and strike_data.pe.oi_change:
                pe_oi_change = strike_data.pe.oi_change.absolute_change
                pe_oi_change_pct = strike_data.pe.oi_change.percentage_change
            
            # Calculate derived metrics
            total_oi = ce_oi + pe_oi
            total_volume = ce_volume + pe_volume
            pe_ce_ratio = pe_oi / ce_oi if ce_oi > 0 else 0
            volume_oi_ratio = total_volume / total_oi if total_oi > 0 else 0
            
            data.append({
                'strike': strike_price,
                'distance': distance,
                'distance_pct': distance_pct,
                'ce_oi': ce_oi,
                'pe_oi': pe_oi,
                'total_oi': total_oi,
                'ce_volume': ce_volume,
                'pe_volume': pe_volume,
                'total_volume': total_volume,
                'ce_oi_change': ce_oi_change,
                'pe_oi_change': pe_oi_change,
                'ce_oi_change_pct': ce_oi_change_pct,
                'pe_oi_change_pct': pe_oi_change_pct,
                'pe_ce_ratio': pe_ce_ratio,
                'volume_oi_ratio': volume_oi_ratio,
                'is_itm_call': distance < 0,
                'is_itm_put': distance > 0,
                'is_atm': abs(distance_pct) < 2.0  # Within 2% of current price
            })
        
        df = pd.DataFrame(data)
        df = df.sort_values('strike').reset_index(drop=True)
        return df
    
    def _detect_statistical_patterns(self, oi_data: pd.DataFrame) -> List[OIPattern]:
        """Detect patterns using statistical analysis."""
        patterns = []
        
        try:
            # Pattern 1: Significant OI concentration
            total_oi = oi_data['total_oi'].sum()
            if total_oi > 0:
                oi_data['oi_concentration'] = oi_data['total_oi'] / total_oi
                
                # Find strikes with unusually high OI concentration
                concentration_threshold = oi_data['oi_concentration'].quantile(0.9)
                high_concentration_strikes = oi_data[
                    oi_data['oi_concentration'] > concentration_threshold
                ]
                
                if len(high_concentration_strikes) > 0:
                    patterns.append(OIPattern(
                        pattern_type="oi_concentration",
                        confidence=0.8,
                        description=f"High OI concentration at {len(high_concentration_strikes)} strikes",
                        strikes_involved=high_concentration_strikes['strike'].tolist(),
                        magnitude=high_concentration_strikes['oi_concentration'].sum(),
                        direction="neutral",
                        time_horizon="medium",
                        risk_level="medium"
                    ))
            
            # Pattern 2: Asymmetric OI changes
            ce_change_sum = oi_data['ce_oi_change'].sum()
            pe_change_sum = oi_data['pe_oi_change'].sum()
            
            if abs(ce_change_sum) > 0 or abs(pe_change_sum) > 0:
                asymmetry_ratio = (pe_change_sum - ce_change_sum) / (abs(pe_change_sum) + abs(ce_change_sum) + 1)
                
                if abs(asymmetry_ratio) > 0.3:  # Significant asymmetry
                    direction = "bullish" if asymmetry_ratio > 0 else "bearish"
                    patterns.append(OIPattern(
                        pattern_type="asymmetric_oi_change",
                        confidence=min(0.9, abs(asymmetry_ratio) * 2),
                        description=f"Asymmetric OI changes: {direction} bias",
                        strikes_involved=[],
                        magnitude=abs(asymmetry_ratio),
                        direction=direction,
                        time_horizon="short",
                        risk_level="medium"
                    ))
            
        except Exception as e:
            logger.error(f"Error in statistical pattern detection: {e}")
        
        return patterns

    def _detect_cluster_patterns(self, oi_data: pd.DataFrame) -> List[OIPattern]:
        """Detect patterns using clustering analysis."""
        patterns = []

        try:
            if len(oi_data) < 5:  # Need minimum data for clustering
                return patterns

            # Prepare features for clustering
            features = ['ce_oi', 'pe_oi', 'ce_oi_change', 'pe_oi_change', 'volume_oi_ratio']
            cluster_data = oi_data[features].fillna(0)

            if cluster_data.sum().sum() == 0:  # No meaningful data
                return patterns

            # Normalize features
            normalized_data = self.scaler.fit_transform(cluster_data)

            # Perform K-means clustering
            n_clusters = min(3, len(oi_data) // 2)
            if n_clusters >= 2:
                kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
                clusters = kmeans.fit_predict(normalized_data)
                oi_data['cluster'] = clusters

                # Analyze cluster characteristics
                for cluster_id in range(n_clusters):
                    cluster_strikes = oi_data[oi_data['cluster'] == cluster_id]

                    if len(cluster_strikes) >= 2:
                        avg_distance = cluster_strikes['distance'].mean()
                        total_oi_change = cluster_strikes['ce_oi_change'].sum() + cluster_strikes['pe_oi_change'].sum()

                        if abs(total_oi_change) > 1000000:  # Significant OI change (10 lakh+)
                            direction = "bullish" if total_oi_change > 0 else "bearish"
                            patterns.append(OIPattern(
                                pattern_type="cluster_activity",
                                confidence=0.7,
                                description=f"Clustered activity at {len(cluster_strikes)} strikes",
                                strikes_involved=cluster_strikes['strike'].tolist(),
                                magnitude=abs(total_oi_change) / 1000000,  # In lakhs
                                direction=direction,
                                time_horizon="medium",
                                risk_level="medium"
                            ))

        except Exception as e:
            logger.error(f"Error in cluster pattern detection: {e}")

        return patterns

    def _analyze_oi_momentum(self, oi_data: pd.DataFrame) -> List[OIPattern]:
        """Analyze OI momentum and trends."""
        patterns = []

        try:
            # Calculate momentum indicators
            oi_data['ce_momentum'] = oi_data['ce_oi_change_pct'].rolling(window=3, center=True).mean()
            oi_data['pe_momentum'] = oi_data['pe_oi_change_pct'].rolling(window=3, center=True).mean()

            # Find strikes with strong momentum
            ce_momentum_threshold = oi_data['ce_momentum'].quantile(0.8)
            pe_momentum_threshold = oi_data['pe_momentum'].quantile(0.8)

            strong_ce_momentum = oi_data[oi_data['ce_momentum'] > ce_momentum_threshold]
            strong_pe_momentum = oi_data[oi_data['pe_momentum'] > pe_momentum_threshold]

            if len(strong_ce_momentum) > 0:
                patterns.append(OIPattern(
                    pattern_type="ce_momentum",
                    confidence=0.75,
                    description=f"Strong CE momentum at {len(strong_ce_momentum)} strikes",
                    strikes_involved=strong_ce_momentum['strike'].tolist(),
                    magnitude=strong_ce_momentum['ce_momentum'].mean(),
                    direction="bearish",  # High CE activity often bearish
                    time_horizon="short",
                    risk_level="medium"
                ))

            if len(strong_pe_momentum) > 0:
                patterns.append(OIPattern(
                    pattern_type="pe_momentum",
                    confidence=0.75,
                    description=f"Strong PE momentum at {len(strong_pe_momentum)} strikes",
                    strikes_involved=strong_pe_momentum['strike'].tolist(),
                    magnitude=strong_pe_momentum['pe_momentum'].mean(),
                    direction="bullish",  # High PE activity often bullish
                    time_horizon="short",
                    risk_level="medium"
                ))

        except Exception as e:
            logger.error(f"Error in momentum analysis: {e}")

        return patterns

    def _detect_anomalies(self, oi_data: pd.DataFrame) -> List[OIPattern]:
        """Detect anomalies and unusual activity."""
        patterns = []

        try:
            # Detect volume-to-OI ratio anomalies
            if oi_data['volume_oi_ratio'].std() > 0:
                z_scores = np.abs(stats.zscore(oi_data['volume_oi_ratio'].fillna(0)))
                anomalous_strikes = oi_data[z_scores > 2]  # 2 standard deviations

                if len(anomalous_strikes) > 0:
                    patterns.append(OIPattern(
                        pattern_type="volume_anomaly",
                        confidence=0.8,
                        description=f"Unusual volume-to-OI ratios at {len(anomalous_strikes)} strikes",
                        strikes_involved=anomalous_strikes['strike'].tolist(),
                        magnitude=z_scores.max(),
                        direction="neutral",
                        time_horizon="short",
                        risk_level="high"
                    ))

            # Detect extreme OI changes
            extreme_ce_changes = oi_data[abs(oi_data['ce_oi_change_pct']) > 100]  # >100% change
            extreme_pe_changes = oi_data[abs(oi_data['pe_oi_change_pct']) > 100]  # >100% change

            if len(extreme_ce_changes) > 0:
                patterns.append(OIPattern(
                    pattern_type="extreme_ce_change",
                    confidence=0.9,
                    description=f"Extreme CE OI changes at {len(extreme_ce_changes)} strikes",
                    strikes_involved=extreme_ce_changes['strike'].tolist(),
                    magnitude=extreme_ce_changes['ce_oi_change_pct'].abs().mean(),
                    direction="bearish",
                    time_horizon="short",
                    risk_level="high"
                ))

            if len(extreme_pe_changes) > 0:
                patterns.append(OIPattern(
                    pattern_type="extreme_pe_change",
                    confidence=0.9,
                    description=f"Extreme PE OI changes at {len(extreme_pe_changes)} strikes",
                    strikes_involved=extreme_pe_changes['strike'].tolist(),
                    magnitude=extreme_pe_changes['pe_oi_change_pct'].abs().mean(),
                    direction="bullish",
                    time_horizon="short",
                    risk_level="high"
                ))

        except Exception as e:
            logger.error(f"Error in anomaly detection: {e}")

        return patterns

    def _calculate_overall_sentiment(self, patterns: List[OIPattern]) -> Tuple[str, float]:
        """Calculate overall market sentiment from detected patterns."""
        if not patterns:
            return "neutral", 0.5

        # Weight patterns by confidence and magnitude
        bullish_score = 0
        bearish_score = 0
        total_weight = 0

        for pattern in patterns:
            weight = pattern.confidence * (1 + pattern.magnitude * 0.1)
            total_weight += weight

            if pattern.direction == "bullish":
                bullish_score += weight
            elif pattern.direction == "bearish":
                bearish_score += weight

        if total_weight == 0:
            return "neutral", 0.5

        # Calculate sentiment scores
        bullish_ratio = bullish_score / total_weight
        bearish_ratio = bearish_score / total_weight

        # Determine overall sentiment
        if bullish_ratio > bearish_ratio + 0.2:
            sentiment = "bullish"
            confidence = bullish_ratio
        elif bearish_ratio > bullish_ratio + 0.2:
            sentiment = "bearish"
            confidence = bearish_ratio
        else:
            sentiment = "neutral"
            confidence = 1 - abs(bullish_ratio - bearish_ratio)

        return sentiment, min(0.95, confidence)

    def _identify_key_levels(self, oi_data: pd.DataFrame, current_price: float) -> List[float]:
        """Identify key support and resistance levels based on OI data."""
        key_levels = []

        try:
            # Find strikes with highest total OI (potential support/resistance)
            oi_threshold = oi_data['total_oi'].quantile(0.8)
            high_oi_strikes = oi_data[oi_data['total_oi'] > oi_threshold]

            # Add strikes with significant OI
            key_levels.extend(high_oi_strikes['strike'].tolist())

            # Find strikes with highest OI changes (active levels)
            oi_data['total_oi_change'] = abs(oi_data['ce_oi_change']) + abs(oi_data['pe_oi_change'])
            change_threshold = oi_data['total_oi_change'].quantile(0.8)
            active_strikes = oi_data[oi_data['total_oi_change'] > change_threshold]

            # Add active strikes
            key_levels.extend(active_strikes['strike'].tolist())

            # Remove duplicates and sort
            key_levels = sorted(list(set(key_levels)))

            # Keep only levels within reasonable range of current price (±10%)
            price_range = current_price * 0.1
            key_levels = [
                level for level in key_levels
                if abs(level - current_price) <= price_range
            ]

        except Exception as e:
            logger.error(f"Error identifying key levels: {e}")

        return key_levels[:10]  # Limit to top 10 levels

    async def _generate_ai_recommendation(
        self,
        oi_data: pd.DataFrame,
        patterns: List[OIPattern],
        current_price: float,
        overall_sentiment: str
    ) -> Tuple[str, str, str]:
        """Generate AI-powered trading recommendation."""
        try:
            # Prepare data summary for AI
            data_summary = {
                "current_price": current_price,
                "total_strikes_analyzed": len(oi_data),
                "patterns_detected": len(patterns),
                "overall_sentiment": overall_sentiment,
                "total_ce_oi": oi_data['ce_oi'].sum(),
                "total_pe_oi": oi_data['pe_oi'].sum(),
                "total_ce_change": oi_data['ce_oi_change'].sum(),
                "total_pe_change": oi_data['pe_oi_change'].sum(),
                "avg_volume_oi_ratio": oi_data['volume_oi_ratio'].mean(),
                "patterns": [
                    {
                        "type": p.pattern_type,
                        "confidence": p.confidence,
                        "direction": p.direction,
                        "magnitude": p.magnitude,
                        "description": p.description
                    }
                    for p in patterns
                ]
            }

            # Create AI prompt for recommendation
            prompt = f"""
            As an expert options trading analyst, analyze this real-time Open Interest (OI) data and provide a trading recommendation.

            MARKET DATA SUMMARY:
            - Current Price: {current_price}
            - Total CE OI: {oi_data['ce_oi'].sum():,.0f}
            - Total PE OI: {oi_data['pe_oi'].sum():,.0f}
            - Total CE OI Change: {oi_data['ce_oi_change'].sum():,.0f}
            - Total PE OI Change: {oi_data['pe_oi_change'].sum():,.0f}
            - Overall Sentiment: {overall_sentiment}

            DETECTED PATTERNS:
            {chr(10).join([f"- {p.description} (Confidence: {p.confidence:.1%}, Direction: {p.direction})" for p in patterns])}

            STATISTICAL INSIGHTS:
            - Average Volume/OI Ratio: {oi_data['volume_oi_ratio'].mean():.3f}
            - Strikes with High Activity: {len(oi_data[oi_data['total_oi'] > oi_data['total_oi'].quantile(0.8)])}

            Please provide:
            1. A clear trading recommendation (BUY/SELL/HOLD with specific strikes if applicable)
            2. Detailed reasoning based on the OI patterns and data
            3. Risk assessment and position sizing guidance
            4. Time horizon for the recommendation

            Focus on actionable insights derived from the OI data patterns rather than generic advice.
            """

            # Get AI response
            ai_response = await self.ai_client.answer_trading_question(
                question="Provide a trading recommendation based on this OI analysis",
                market_context=data_summary,
                portfolio_context=None
            )

            # Parse AI response into components
            lines = ai_response.split('\n')
            recommendation = "HOLD"  # Default
            reasoning = ai_response
            risk_assessment = "Medium risk - monitor position closely"

            # Try to extract recommendation from AI response
            for line in lines:
                line_lower = line.lower()
                if any(word in line_lower for word in ['buy', 'long', 'bullish']):
                    recommendation = "BUY"
                    break
                elif any(word in line_lower for word in ['sell', 'short', 'bearish']):
                    recommendation = "SELL"
                    break

            return recommendation, reasoning, risk_assessment

        except Exception as e:
            logger.error(f"Error generating AI recommendation: {e}")
            return "HOLD", f"Error generating recommendation: {str(e)}", "High risk due to analysis error"

    def _create_statistical_summary(self, oi_data: pd.DataFrame) -> Dict[str, Any]:
        """Create statistical summary of OI data."""
        try:
            return {
                "total_strikes": len(oi_data),
                "total_ce_oi": int(oi_data['ce_oi'].sum()),
                "total_pe_oi": int(oi_data['pe_oi'].sum()),
                "total_volume": int(oi_data['total_volume'].sum()),
                "avg_pe_ce_ratio": float(oi_data['pe_ce_ratio'].mean()),
                "max_oi_strike": float(oi_data.loc[oi_data['total_oi'].idxmax(), 'strike']),
                "max_volume_strike": float(oi_data.loc[oi_data['total_volume'].idxmax(), 'strike']),
                "oi_change_distribution": {
                    "ce_positive": int((oi_data['ce_oi_change'] > 0).sum()),
                    "ce_negative": int((oi_data['ce_oi_change'] < 0).sum()),
                    "pe_positive": int((oi_data['pe_oi_change'] > 0).sum()),
                    "pe_negative": int((oi_data['pe_oi_change'] < 0).sum())
                },
                "volatility_indicators": {
                    "ce_oi_std": float(oi_data['ce_oi'].std()),
                    "pe_oi_std": float(oi_data['pe_oi'].std()),
                    "volume_oi_ratio_std": float(oi_data['volume_oi_ratio'].std())
                }
            }
        except Exception as e:
            logger.error(f"Error creating statistical summary: {e}")
            return {}
