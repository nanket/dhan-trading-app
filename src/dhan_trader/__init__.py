"""
Dhan AI Trader - Comprehensive Options Trading Platform

A sophisticated trading platform built on the Dhan HQ API, featuring:
- Real-time market data streaming
- Advanced options analytics and Greeks calculations
- Risk management and position sizing
- Automated trading strategies
- Performance analytics and backtesting
"""

__version__ = "0.1.0"
__author__ = "Aniket Nagapure"
__email__ = "nanket.dev@gmail.com"

from .config import Config
from .exceptions import DhanTraderError

__all__ = [
    "Config",
    "DhanTraderError",
    "__version__",
]