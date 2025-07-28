"""Basic tests for Dhan AI Trader."""

import pytest
import os
from unittest.mock import Mock, patch

from src.dhan_trader.config import Config
from src.dhan_trader.api.client import DhanAPIClient
from src.dhan_trader.api.models import UserProfile
from src.dhan_trader.exceptions import AuthenticationError


class TestConfig:
    """Test configuration management."""
    
    def test_config_initialization(self):
        """Test config initialization."""
        config = Config()
        assert config.api.base_url == "https://api.dhan.co"
        assert config.api.timeout == 30
    
    def test_config_with_env_token(self):
        """Test config with environment token."""
        with patch.dict(os.environ, {"DHAN_TOKEN": "test_token"}):
            config = Config()
            assert config.api.token == "test_token"


class TestDhanAPIClient:
    """Test Dhan API client."""
    
    @patch('src.dhan_trader.api.client.requests.Session')
    def test_client_initialization(self, mock_session):
        """Test API client initialization."""
        with patch.dict(os.environ, {"DHAN_TOKEN": "test_token"}):
            # Mock the profile response
            mock_response = Mock()
            mock_response.ok = True
            mock_response.json.return_value = {
                "dhanClientId": "1100000001",
                "tokenValidity": "2024-12-31 23:59",
                "activeSegment": "Equity, Derivative",
                "ddpi": "Active",
                "mtf": "Active",
                "dataPlan": "Active",
                "dataValidity": "2024-12-31 23:59"
            }
            mock_session.return_value.get.return_value = mock_response
            
            client = DhanAPIClient()
            assert client.access_token == "test_token"
            assert client.client_id == "1100000001"
    
    def test_client_without_token(self):
        """Test client initialization without token."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(AuthenticationError):
                DhanAPIClient()
    
    @patch('src.dhan_trader.api.client.requests.Session')
    def test_get_user_profile(self, mock_session):
        """Test getting user profile."""
        with patch.dict(os.environ, {"DHAN_TOKEN": "test_token"}):
            # Mock the profile response
            mock_response = Mock()
            mock_response.ok = True
            mock_response.json.return_value = {
                "dhanClientId": "1100000001",
                "tokenValidity": "2024-12-31 23:59",
                "activeSegment": "Equity, Derivative",
                "ddpi": "Active",
                "mtf": "Active",
                "dataPlan": "Active",
                "dataValidity": "2024-12-31 23:59"
            }
            mock_session.return_value.get.return_value = mock_response
            
            client = DhanAPIClient()
            profile = client.get_user_profile()
            
            assert isinstance(profile, UserProfile)
            assert profile.dhan_client_id == "1100000001"
            assert profile.active_segment == "Equity, Derivative"


class TestMarketDataModels:
    """Test market data models."""
    
    def test_user_profile_creation(self):
        """Test UserProfile model creation."""
        profile = UserProfile(
            dhan_client_id="1100000001",
            token_validity="2024-12-31 23:59",
            active_segment="Equity, Derivative",
            ddpi="Active",
            mtf="Active",
            data_plan="Active",
            data_validity="2024-12-31 23:59"
        )
        
        assert profile.dhan_client_id == "1100000001"
        assert profile.active_segment == "Equity, Derivative"


class TestIntegration:
    """Integration tests (require valid API token)."""
    
    @pytest.mark.api
    def test_real_api_connection(self):
        """Test real API connection (requires valid token)."""
        # Skip if no token available
        if not os.getenv("DHAN_TOKEN"):
            pytest.skip("No DHAN_TOKEN environment variable")
        
        try:
            client = DhanAPIClient()
            profile = client.get_user_profile()
            
            assert profile.dhan_client_id
            assert profile.token_validity
            print(f"Connected as: {profile.dhan_client_id}")
            
        except Exception as e:
            pytest.fail(f"Real API connection failed: {e}")
    
    @pytest.mark.api
    def test_option_chain_retrieval(self):
        """Test option chain retrieval (requires valid token)."""
        if not os.getenv("DHAN_TOKEN"):
            pytest.skip("No DHAN_TOKEN environment variable")
        
        try:
            client = DhanAPIClient()
            
            # Get NIFTY option expiry list
            expiry_list = client.get_option_expiry_list(13, "IDX_I")
            assert len(expiry_list) > 0
            
            # Get option chain for nearest expiry
            option_chain = client.get_option_chain(13, "IDX_I", expiry_list[0])
            assert option_chain.underlying_price > 0
            assert len(option_chain.strikes) > 0
            
            print(f"NIFTY Price: {option_chain.underlying_price}")
            print(f"Strikes available: {len(option_chain.strikes)}")
            
        except Exception as e:
            pytest.fail(f"Option chain retrieval failed: {e}")


if __name__ == "__main__":
    # Run basic tests
    pytest.main([__file__, "-v"])
