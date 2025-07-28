"""Configuration management for Dhan AI Trader."""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


@dataclass
class APIConfig:
    """API configuration settings."""
    base_url: str = "https://api.dhan.co"
    websocket_url: str = "wss://api-feed.dhan.co"
    timeout: int = 30
    max_retries: int = 3
    retry_delay: float = 1.0
    token: Optional[str] = None
    
    def __post_init__(self):
        """Load token from environment if not provided."""
        if not self.token:
            self.token = os.getenv("DHAN_TOKEN")
            if not self.token:
                raise ValueError("DHAN_TOKEN environment variable is required")


@dataclass
class DatabaseConfig:
    """Database configuration settings."""
    url: str = "sqlite:///data/trading.db"
    echo: bool = False
    pool_size: int = 10
    max_overflow: int = 20
    pool_timeout: int = 30


@dataclass
class RiskConfig:
    """Risk management configuration."""
    max_position_size_percent: float = 5.0
    max_daily_loss_percent: float = 2.0
    max_drawdown_percent: float = 10.0
    default_stop_loss_percent: float = 20.0
    default_take_profit_percent: float = 50.0
    kelly_criterion: bool = True
    max_kelly_fraction: float = 0.25


@dataclass
class OptionsConfig:
    """Options trading configuration."""
    default_expiry_days: int = 30
    max_strike_range: int = 20
    risk_free_rate: float = 0.06
    dividend_yield: float = 0.0
    calculation_frequency: float = 1.0
    iv_initial_guess: float = 0.2
    iv_max_iterations: int = 100
    iv_tolerance: float = 1e-6


@dataclass
class DashboardConfig:
    """Dashboard configuration."""
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    auto_reload: bool = True
    refresh_interval: float = 1.0
    max_chart_points: int = 1000


class Config:
    """Main configuration class for Dhan AI Trader."""
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize configuration.
        
        Args:
            config_path: Path to YAML configuration file
        """
        self.config_path = config_path or self._get_default_config_path()
        self._config_data = self._load_config()
        
        # Initialize configuration sections
        api_config = self._config_data.get("api", {})
        # Remove nested sections that aren't part of APIConfig
        api_config_clean = {k: v for k, v in api_config.items() if k not in ['rate_limit']}
        self.api = APIConfig(**api_config_clean)

        self.database = DatabaseConfig(**self._config_data.get("database", {}))

        risk_config = self._config_data.get("risk_management", {})
        # Remove nested sections that aren't part of RiskConfig
        risk_config_clean = {k: v for k, v in risk_config.items() if k not in ['position_sizing', 'stop_loss', 'take_profit']}
        self.risk = RiskConfig(**risk_config_clean)

        options_config = self._config_data.get("options", {})
        # Remove nested sections that aren't part of OptionsConfig
        options_config_clean = {k: v for k, v in options_config.items() if k not in ['greeks_calculation', 'implied_volatility']}
        self.options = OptionsConfig(**options_config_clean)

        self.dashboard = DashboardConfig(**self._config_data.get("dashboard", {}))
        
        # Additional configuration sections
        self.market_data = self._config_data.get("market_data", {})
        self.trading = self._config_data.get("trading", {})
        self.analytics = self._config_data.get("analytics", {})
        self.logging = self._config_data.get("logging", {})
        self.security = self._config_data.get("security", {})
        self.development = self._config_data.get("development", {})
    
    def _get_default_config_path(self) -> str:
        """Get default configuration file path."""
        current_dir = Path(__file__).parent.parent.parent
        return str(current_dir / "config" / "config.yaml")
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        try:
            with open(self.config_path, 'r') as file:
                return yaml.safe_load(file) or {}
        except FileNotFoundError:
            print(f"Warning: Configuration file {self.config_path} not found. Using defaults.")
            return {}
        except yaml.YAMLError as e:
            raise ValueError(f"Error parsing configuration file: {e}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by key.
        
        Args:
            key: Configuration key (supports dot notation)
            default: Default value if key not found
            
        Returns:
            Configuration value
        """
        keys = key.split('.')
        value = self._config_data
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def update(self, key: str, value: Any) -> None:
        """Update configuration value.
        
        Args:
            key: Configuration key (supports dot notation)
            value: New value
        """
        keys = key.split('.')
        config = self._config_data
        
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        config[keys[-1]] = value
    
    def save(self, path: Optional[str] = None) -> None:
        """Save configuration to file.
        
        Args:
            path: Optional path to save to (defaults to current config path)
        """
        save_path = path or self.config_path
        
        with open(save_path, 'w') as file:
            yaml.dump(self._config_data, file, default_flow_style=False, indent=2)


# Global configuration instance
config = Config()
