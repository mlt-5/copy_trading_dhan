"""
Unit tests for position sizer module.
"""

import pytest
from unittest.mock import Mock, patch
from core.position_sizer import PositionSizer, initialize_position_sizer
from core.config import SizingStrategy


@pytest.mark.unit
class TestPositionSizer:
    """Test PositionSizer class."""
    
    @pytest.fixture
    def mock_funds_apis(self):
        """Create mock funds APIs."""
        leader_funds_api = Mock()
        follower_funds_api = Mock()
        
        leader_funds_api.get_fund_limits.return_value = {
            'availableBalance': 200000.0,
            'sodLimit': 300000.0,
        }
        
        follower_funds_api.get_fund_limits.return_value = {
            'availableBalance': 100000.0,
            'sodLimit': 150000.0,
        }
        
        return leader_funds_api, follower_funds_api
    
    def test_capital_proportional_strategy(self, mock_funds_apis, mock_env, reset_singletons, monkeypatch):
        """Test CAPITAL_PROPORTIONAL sizing strategy."""
        monkeypatch.setenv('SIZING_STRATEGY', 'CAPITAL_PROPORTIONAL')
        monkeypatch.setenv('CAPITAL_RATIO', '0.5')
        
        leader_api, follower_api = mock_funds_apis
        sizer = PositionSizer(leader_api, follower_api)
        
        # Leader trades 100 qty
        follower_qty = sizer.calculate_quantity(
            leader_quantity=100,
            security_id="11536",
            premium=None
        )
        
        # Follower should trade 50 (100 * 0.5)
        assert follower_qty == 50
    
    def test_fixed_ratio_strategy(self, mock_funds_apis, mock_env, reset_singletons, monkeypatch):
        """Test FIXED_RATIO sizing strategy."""
        monkeypatch.setenv('SIZING_STRATEGY', 'FIXED_RATIO')
        monkeypatch.setenv('FIXED_RATIO', '2.0')
        
        leader_api, follower_api = mock_funds_apis
        sizer = PositionSizer(leader_api, follower_api)
        
        # Leader trades 50 qty
        follower_qty = sizer.calculate_quantity(
            leader_quantity=50,
            security_id="11536",
            premium=None
        )
        
        # Follower should trade 100 (50 * 2.0)
        assert follower_qty == 100
    
    def test_lot_size_rounding(self, mock_funds_apis, mock_env, reset_singletons):
        """Test lot size rounding."""
        leader_api, follower_api = mock_funds_apis
        sizer = PositionSizer(leader_api, follower_api)
        
        # Test with lot size of 50
        result = sizer._round_to_lot_size(123, 50)
        assert result == 100  # Rounded down to 2 lots
        
        result = sizer._round_to_lot_size(175, 50)
        assert result == 150  # Rounded down to 3 lots
    
    def test_zero_quantity_when_too_small(self, mock_funds_apis, mock_env, reset_singletons):
        """Test returns zero when quantity too small for lot size."""
        leader_api, follower_api = mock_funds_apis
        sizer = PositionSizer(leader_api, follower_api)
        
        # With lot size 50, quantity 25 should become 0
        result = sizer._round_to_lot_size(25, 50)
        assert result == 0
    
    def test_get_capital_ratio(self, mock_funds_apis, mock_env, reset_singletons):
        """Test get_capital_ratio calculation."""
        leader_api, follower_api = mock_funds_apis
        sizer = PositionSizer(leader_api, follower_api)
        
        # Follower has 100k available, leader has 200k
        # Ratio should be 0.5
        ratio = sizer.get_capital_ratio()
        assert ratio == 0.5
    
    def test_validate_sufficient_margin_success(self, mock_funds_apis, mock_env, reset_singletons):
        """Test margin validation passes with sufficient funds."""
        leader_api, follower_api = mock_funds_apis
        follower_api.calculate_margin_requirement.return_value = {
            'requiredMargin': 5000.0
        }
        
        sizer = PositionSizer(leader_api, follower_api)
        
        # Available balance is 100k, required is 5k
        is_valid, error_msg = sizer.validate_sufficient_margin(
            quantity=50,
            security_id="11536",
            premium=100.0
        )
        
        assert is_valid is True
        assert error_msg is None
    
    def test_validate_sufficient_margin_failure(self, mock_funds_apis, mock_env, reset_singletons):
        """Test margin validation fails with insufficient funds."""
        leader_api, follower_api = mock_funds_apis
        follower_api.calculate_margin_requirement.return_value = {
            'requiredMargin': 150000.0  # More than available
        }
        
        sizer = PositionSizer(leader_api, follower_api)
        
        is_valid, error_msg = sizer.validate_sufficient_margin(
            quantity=1000,
            security_id="11536",
            premium=150.0
        )
        
        assert is_valid is False
        assert "Insufficient margin" in error_msg


@pytest.mark.unit
class TestInitializePositionSizer:
    """Test initialize_position_sizer function."""
    
    def test_initialize_position_sizer(self, mock_env, reset_singletons):
        """Test initializing position sizer."""
        leader_api = Mock()
        follower_api = Mock()
        
        leader_api.get_fund_limits.return_value = {'availableBalance': 200000.0}
        follower_api.get_fund_limits.return_value = {'availableBalance': 100000.0}
        
        sizer = initialize_position_sizer(leader_api, follower_api)
        
        assert sizer is not None
        assert isinstance(sizer, PositionSizer)

