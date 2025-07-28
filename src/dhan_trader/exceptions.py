"""Custom exceptions for Dhan AI Trader."""


class DhanTraderError(Exception):
    """Base exception for Dhan AI Trader."""
    pass


class APIError(DhanTraderError):
    """API related errors."""
    
    def __init__(self, message: str, status_code: int = None, response_data: dict = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_data = response_data


class AuthenticationError(APIError):
    """Authentication related errors."""
    pass


class RateLimitError(APIError):
    """Rate limit exceeded errors."""
    pass


class MarketDataError(DhanTraderError):
    """Market data related errors."""
    pass


class WebSocketError(MarketDataError):
    """WebSocket connection errors."""
    pass


class TradingError(DhanTraderError):
    """Trading related errors."""
    pass


class OrderError(TradingError):
    """Order placement/management errors."""
    pass


class PositionError(TradingError):
    """Position management errors."""
    pass


class RiskManagementError(DhanTraderError):
    """Risk management related errors."""
    pass


class CalculationError(DhanTraderError):
    """Mathematical calculation errors."""
    pass


class GreeksCalculationError(CalculationError):
    """Options Greeks calculation errors."""
    pass


class ImpliedVolatilityError(CalculationError):
    """Implied volatility calculation errors."""
    pass


class DatabaseError(DhanTraderError):
    """Database related errors."""
    pass


class ConfigurationError(DhanTraderError):
    """Configuration related errors."""
    pass


class ValidationError(DhanTraderError):
    """Data validation errors."""
    pass


class StrategyError(DhanTraderError):
    """Trading strategy related errors."""
    pass


class BacktestError(DhanTraderError):
    """Backtesting related errors."""
    pass
