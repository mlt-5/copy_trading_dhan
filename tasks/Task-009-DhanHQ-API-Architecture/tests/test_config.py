"""
Unit tests for configuration module.
"""

import pytest
import os
from core.config import (
    Environment,
    SizingStrategy,
    AccountConfig,
    SystemConfig,
    get_config,
)


@pytest.mark.unit
class TestEnvironmentEnum:
    """Test Environment enumeration."""
    
    def test_environment_values(self):
        """Test environment enum values."""
        assert Environment.PRODUCTION.value == "production"
        assert Environment.SANDBOX.value == "sandbox"
    
    def test_environment_from_string(self):
        """Test creating environment from string."""
        assert Environment("production") == Environment.PRODUCTION
        assert Environment("sandbox") == Environment.SANDBOX


@pytest.mark.unit
class TestSizingStrategy:
    """Test SizingStrategy enumeration."""
    
    def test_sizing_strategy_values(self):
        """Test sizing strategy enum values."""
        assert SizingStrategy.CAPITAL_PROPORTIONAL.value == "CAPITAL_PROPORTIONAL"
        assert SizingStrategy.FIXED_RATIO.value == "FIXED_RATIO"
        assert SizingStrategy.RISK_BASED.value == "RISK_BASED"
    
    def test_sizing_strategy_from_string(self):
        """Test creating sizing strategy from string."""
        assert SizingStrategy("CAPITAL_PROPORTIONAL") == SizingStrategy.CAPITAL_PROPORTIONAL
        assert SizingStrategy("FIXED_RATIO") == SizingStrategy.FIXED_RATIO
        assert SizingStrategy("RISK_BASED") == SizingStrategy.RISK_BASED


@pytest.mark.unit
class TestAccountConfig:
    """Test AccountConfig data class."""
    
    def test_account_config_creation(self):
        """Test creating AccountConfig."""
        config = AccountConfig(
            client_id="test_123",
            access_token="test_token",
            environment=Environment.PRODUCTION
        )
        
        assert config.client_id == "test_123"
        assert config.access_token == "test_token"
        assert config.environment == Environment.PRODUCTION
    
    def test_account_config_defaults(self):
        """Test AccountConfig default values."""
        config = AccountConfig(
            client_id="test_123",
            access_token="test_token"
        )
        
        assert config.environment == Environment.PRODUCTION


@pytest.mark.unit
class TestSystemConfig:
    """Test SystemConfig data class."""
    
    def test_system_config_creation(self):
        """Test creating SystemConfig."""
        config = SystemConfig(
            sizing_strategy=SizingStrategy.CAPITAL_PROPORTIONAL,
            capital_ratio=0.5,
            fixed_ratio=1.0,
            risk_per_trade_pct=2.0,
            max_daily_loss=10000.0,
            max_position_size=500000.0,
            max_open_positions=10
        )
        
        assert config.sizing_strategy == SizingStrategy.CAPITAL_PROPORTIONAL
        assert config.capital_ratio == 0.5
        assert config.fixed_ratio == 1.0
        assert config.risk_per_trade_pct == 2.0
        assert config.max_daily_loss == 10000.0
        assert config.max_position_size == 500000.0
        assert config.max_open_positions == 10
    
    def test_system_config_defaults(self):
        """Test SystemConfig default values."""
        config = SystemConfig()
        
        assert config.sizing_strategy == SizingStrategy.CAPITAL_PROPORTIONAL
        assert config.capital_ratio == 0.5
        assert config.fixed_ratio == 1.0
        assert config.risk_per_trade_pct == 2.0
        assert config.max_daily_loss == 10000.0
        assert config.max_position_size == 500000.0
        assert config.max_open_positions == 10


@pytest.mark.unit
class TestGetConfig:
    """Test get_config function."""
    
    def test_get_config_with_env_vars(self, mock_env):
        """Test get_config with environment variables."""
        leader_config, follower_config, system_config = get_config()
        
        # Check leader config
        assert leader_config.client_id == "test_leader_123"
        assert leader_config.access_token == "test_leader_token"
        
        # Check follower config
        assert follower_config.client_id == "test_follower_456"
        assert follower_config.access_token == "test_follower_token"
        
        # Check system config
        assert system_config.sizing_strategy == SizingStrategy.CAPITAL_PROPORTIONAL
        assert system_config.capital_ratio == 0.5
    
    def test_get_config_missing_required(self, monkeypatch):
        """Test get_config raises error when required vars missing."""
        # Remove required env vars
        monkeypatch.delenv('LEADER_CLIENT_ID', raising=False)
        
        with pytest.raises(ValueError, match="LEADER_CLIENT_ID"):
            get_config()
    
    def test_get_config_invalid_strategy(self, mock_env, monkeypatch):
        """Test get_config with invalid sizing strategy."""
        monkeypatch.setenv('SIZING_STRATEGY', 'INVALID_STRATEGY')
        
        with pytest.raises(ValueError):
            get_config()
    
    def test_get_config_invalid_capital_ratio(self, mock_env, monkeypatch):
        """Test get_config with invalid capital ratio."""
        monkeypatch.setenv('CAPITAL_RATIO', '-0.5')
        
        with pytest.raises(ValueError, match="must be between 0 and 1"):
            get_config()
    
    def test_get_config_capital_ratio_too_high(self, mock_env, monkeypatch):
        """Test get_config with capital ratio > 1."""
        monkeypatch.setenv('CAPITAL_RATIO', '1.5')
        
        with pytest.raises(ValueError, match="must be between 0 and 1"):
            get_config()

