"""
DhanHQ API v2 Module

Aligned with DhanHQ v2 API documentation structure.
Each sub-module maps to a specific API category.

API Documentation: https://dhanhq.co/docs/v2/
"""

from .authentication import DhanAuthManager, authenticate_accounts, get_leader_client, get_follower_client
from .orders import OrdersAPI
from .super_order import SuperOrderAPI
from .forever_order import ForeverOrderAPI
from .portfolio import PortfolioAPI
from .edis import EDISAPI
from .traders_control import TradersControlAPI
from .funds import FundsAPI
from .statement import StatementAPI
from .postback import PostbackHandler
from .live_order_update import LiveOrderUpdateManager

__all__ = [
    # Authentication
    'DhanAuthManager',
    'authenticate_accounts',
    'get_leader_client',
    'get_follower_client',
    
    # API Modules
    'OrdersAPI',
    'SuperOrderAPI',
    'ForeverOrderAPI',
    'PortfolioAPI',
    'EDISAPI',
    'TradersControlAPI',
    'FundsAPI',
    'StatementAPI',
    'PostbackHandler',
    'LiveOrderUpdateManager',
]

__version__ = '2.0.0'

