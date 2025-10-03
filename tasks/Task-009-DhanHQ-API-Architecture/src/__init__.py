"""
Copy Trading System v2.0 - DhanHQ API-Aligned Architecture

Main package initialization.
"""

__version__ = '2.0.0'
__author__ = 'Copy Trading Team'
__description__ = 'Options copy trading system aligned with DhanHQ v2 API'

# Import key components for easy access
from .dhan_api import (
    authenticate_accounts,
    OrdersAPI,
    SuperOrderAPI,
    LiveOrderUpdateManager,
    FundsAPI,
    PortfolioAPI
)

from .core import (
    get_config,
    DatabaseManager,
    init_database,
    PositionSizer
)

__all__ = [
    # Version info
    '__version__',
    '__author__',
    '__description__',
    
    # DhanHQ API
    'authenticate_accounts',
    'OrdersAPI',
    'SuperOrderAPI',
    'LiveOrderUpdateManager',
    'FundsAPI',
    'PortfolioAPI',
    
    # Core
    'get_config',
    'DatabaseManager',
    'init_database',
    'PositionSizer',
]

