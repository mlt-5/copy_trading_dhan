"""
Pytest configuration and fixtures for test suite.
"""

import pytest
import os
import sys
import tempfile
import sqlite3
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent.parent / 'src'
sys.path.insert(0, str(src_path))


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    fd, path = tempfile.mkstemp(suffix='.db')
    yield path
    os.close(fd)
    os.unlink(path)


@pytest.fixture
def mock_env(monkeypatch):
    """Mock environment variables for testing."""
    env_vars = {
        'LEADER_CLIENT_ID': 'test_leader_123',
        'LEADER_ACCESS_TOKEN': 'test_leader_token',
        'FOLLOWER_CLIENT_ID': 'test_follower_456',
        'FOLLOWER_ACCESS_TOKEN': 'test_follower_token',
        'SIZING_STRATEGY': 'CAPITAL_PROPORTIONAL',
        'CAPITAL_RATIO': '0.5',
        'FIXED_RATIO': '1.0',
        'RISK_PER_TRADE_PCT': '2.0',
        'MAX_DAILY_LOSS': '10000.0',
        'MAX_POSITION_SIZE': '500000.0',
        'MAX_OPEN_POSITIONS': '10',
        'DB_PATH': ':memory:',
        'LOG_LEVEL': 'DEBUG',
    }
    
    for key, value in env_vars.items():
        monkeypatch.setenv(key, value)
    
    return env_vars


@pytest.fixture
def sample_order_data():
    """Sample order data for testing."""
    return {
        'orderId': '12345678',
        'dhanOrderId': '12345678',
        'securityId': '11536',
        'exchangeSegment': 'NSE_EQ',
        'transactionType': 'BUY',
        'quantity': 100,
        'orderType': 'LIMIT',
        'productType': 'INTRADAY',
        'price': 1500.50,
        'triggerPrice': None,
        'validity': 'DAY',
        'disclosedQuantity': 0,
        'orderStatus': 'PENDING',
        'tradingSymbol': 'RELIANCE',
    }


@pytest.fixture
def sample_co_order_data():
    """Sample Cover Order data for testing."""
    return {
        'orderId': '87654321',
        'dhanOrderId': '87654321',
        'securityId': '11536',
        'exchangeSegment': 'NSE_EQ',
        'transactionType': 'BUY',
        'quantity': 50,
        'orderType': 'LIMIT',
        'productType': 'CO',
        'price': 1500.00,
        'stopLossValue': 10.0,
        'validity': 'DAY',
        'orderStatus': 'PENDING',
        'tradingSymbol': 'RELIANCE',
    }


@pytest.fixture
def sample_bo_order_data():
    """Sample Bracket Order data for testing."""
    return {
        'orderId': '11223344',
        'dhanOrderId': '11223344',
        'securityId': '11536',
        'exchangeSegment': 'NSE_EQ',
        'transactionType': 'BUY',
        'quantity': 25,
        'orderType': 'LIMIT',
        'productType': 'BO',
        'price': 1500.00,
        'boStopLossValue': 10.0,
        'boProfitValue': 20.0,
        'validity': 'DAY',
        'orderStatus': 'PENDING',
        'tradingSymbol': 'RELIANCE',
    }


@pytest.fixture
def sample_funds_data():
    """Sample funds data for testing."""
    return {
        'availableBalance': 100000.0,
        'sodLimit': 150000.0,
        'collateralAmount': 0.0,
        'receivedAmount': 0.0,
        'blockedPayoutAmount': 0.0,
        'utilizedAmount': 50000.0,
    }


@pytest.fixture
def mock_dhan_client():
    """Mock DhanHQ client for testing."""
    class MockDhanClient:
        def __init__(self, client_id, access_token):
            self.client_id = client_id
            self.access_token = access_token
            self.base_url = "https://api.dhan.co"
        
        def place_order(self, **kwargs):
            return {'orderId': '99999999', 'status': 'success'}
        
        def get_order_by_id(self, order_id):
            return {'orderId': order_id, 'orderStatus': 'COMPLETE'}
        
        def get_fund_limits(self):
            return {
                'availableBalance': 100000.0,
                'sodLimit': 150000.0,
            }
    
    return MockDhanClient


@pytest.fixture
def reset_singletons():
    """Reset singleton instances between tests."""
    # Import here to avoid circular imports
    from core.database import DatabaseManager
    from core.position_sizer import PositionSizer
    
    # Reset singleton instances
    DatabaseManager._instance = None
    PositionSizer._instance = None
    
    yield
    
    # Reset again after test
    DatabaseManager._instance = None
    PositionSizer._instance = None


# Pytest markers
def pytest_configure(config):
    """Configure custom pytest markers."""
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers", "unit: mark test as unit test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )

