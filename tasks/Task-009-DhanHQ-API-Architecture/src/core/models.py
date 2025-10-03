"""
Data models for database entities.

Core business logic data structures. Does NOT include DhanHQ API-specific code.
"""

from dataclasses import dataclass
from typing import Optional, Literal


@dataclass
class Order:
    """Represents an order in the database."""
    id: str  # DhanHQ orderId
    account_type: Literal['leader', 'follower']
    status: str  # Internal status (PENDING/TRANSIT/OPEN/PARTIAL/EXECUTED/CANCELLED/REJECTED)
    side: str
    product: str
    order_type: str
    validity: str
    security_id: str
    exchange_segment: str
    quantity: int
    price: Optional[float]
    trigger_price: Optional[float]
    disclosed_qty: Optional[int]
    created_at: int
    updated_at: int
    # Response fields from DhanHQ API
    traded_qty: int = 0  # Quantity filled (filledQty)
    remaining_qty: Optional[int] = None  # Remaining quantity (remainingQuantity)
    avg_price: Optional[float] = None  # Average execution price (averageTradedPrice)
    exchange_order_id: Optional[str] = None  # Exchange order ID
    exchange_time: Optional[int] = None  # Exchange timestamp
    completed_at: Optional[int] = None  # Order completion timestamp
    trading_symbol: Optional[str] = None  # Trading symbol (e.g., "RELIANCE", "NIFTY24DEC19500CE")
    algo_id: Optional[str] = None  # Exchange Algo ID for Dhan
    # Derivatives info (F&O)
    drv_expiry_date: Optional[int] = None  # For F&O, expiry date of contract (epoch)
    drv_option_type: Optional[str] = None  # Type of Option: CALL or PUT
    drv_strike_price: Optional[float] = None  # For Options, Strike Price
    # Error tracking
    oms_error_code: Optional[str] = None  # Error code if order is rejected/failed
    oms_error_description: Optional[str] = None  # Error description if order is rejected/failed
    correlation_id: Optional[str] = None
    order_status: Optional[str] = None  # DhanHQ orderStatus from API response
    raw_request: Optional[str] = None
    raw_response: Optional[str] = None
    # Cover Order (CO) parameters
    co_stop_loss_value: Optional[float] = None
    co_trigger_price: Optional[float] = None
    # Bracket Order (BO) parameters
    bo_profit_value: Optional[float] = None
    bo_stop_loss_value: Optional[float] = None
    bo_order_type: Optional[str] = None
    # Multi-leg order tracking
    parent_order_id: Optional[str] = None
    leg_type: Optional[str] = None  # 'ENTRY', 'TARGET', 'SL'
    # AMO (After Market Order) flags
    after_market_order: bool = False
    amo_time: Optional[str] = None  # 'PRE_OPEN', 'OPEN', 'OPEN_30', 'OPEN_60'
    # Order Slicing tracking
    is_sliced_order: bool = False  # Order created via slicing API
    slice_order_id: Optional[str] = None  # Common ID for all orders from same slice request
    slice_index: Optional[int] = None  # Order number within slice (1, 2, 3, etc.)
    total_slice_quantity: Optional[int] = None  # Original total quantity before slicing
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'id': self.id,
            'account_type': self.account_type,
            'correlation_id': self.correlation_id,
            'status': self.status,
            'order_status': self.order_status,
            'side': self.side,
            'product': self.product,
            'order_type': self.order_type,
            'validity': self.validity,
            'security_id': self.security_id,
            'exchange_segment': self.exchange_segment,
            'quantity': self.quantity,
            'price': self.price,
            'trigger_price': self.trigger_price,
            'disclosed_qty': self.disclosed_qty,
            'traded_qty': self.traded_qty,
            'remaining_qty': self.remaining_qty,
            'avg_price': self.avg_price,
            'exchange_order_id': self.exchange_order_id,
            'exchange_time': self.exchange_time,
            'completed_at': self.completed_at,
            'trading_symbol': self.trading_symbol,
            'algo_id': self.algo_id,
            'drv_expiry_date': self.drv_expiry_date,
            'drv_option_type': self.drv_option_type,
            'drv_strike_price': self.drv_strike_price,
            'oms_error_code': self.oms_error_code,
            'oms_error_description': self.oms_error_description,
            'co_stop_loss_value': self.co_stop_loss_value,
            'co_trigger_price': self.co_trigger_price,
            'bo_profit_value': self.bo_profit_value,
            'bo_stop_loss_value': self.bo_stop_loss_value,
            'bo_order_type': self.bo_order_type,
            'parent_order_id': self.parent_order_id,
            'leg_type': self.leg_type,
            'after_market_order': self.after_market_order,
            'amo_time': self.amo_time,
            'is_sliced_order': self.is_sliced_order,
            'slice_order_id': self.slice_order_id,
            'slice_index': self.slice_index,
            'total_slice_quantity': self.total_slice_quantity,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'raw_request': self.raw_request,
            'raw_response': self.raw_response
        }


@dataclass
class OrderEvent:
    """Represents an order lifecycle event."""
    order_id: str
    event_type: str
    event_data: Optional[str]
    event_ts: int
    sequence: Optional[int] = None
    id: Optional[int] = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'id': self.id,
            'order_id': self.order_id,
            'event_type': self.event_type,
            'event_data': self.event_data,
            'event_ts': self.event_ts,
            'sequence': self.sequence
        }


@dataclass
class Trade:
    """
    Represents a trade execution from DhanHQ Trade Book API.
    
    Covers all fields from GET /trades and GET /trades/{order-id} endpoints.
    API Reference: https://dhanhq.co/docs/v2/orders/ (Trade Book section)
    """
    # Primary identification
    id: str  # Trade ID (use exchange_trade_id if available)
    order_id: str  # DhanHQ orderId
    account_type: Literal['leader', 'follower']
    
    # Exchange identifiers
    exchange_order_id: Optional[str] = None  # exchangeOrderId
    exchange_trade_id: Optional[str] = None  # exchangeTradeId
    
    # Instrument details
    security_id: str = ''  # securityId
    exchange_segment: str = ''  # exchangeSegment
    trading_symbol: Optional[str] = None  # tradingSymbol
    
    # Transaction details
    transaction_type: str = ''  # transactionType (BUY/SELL)
    product_type: str = ''  # productType (CNC/INTRADAY/MARGIN/MTF/CO/BO)
    order_type: str = ''  # orderType (LIMIT/MARKET/STOP_LOSS/STOP_LOSS_MARKET)
    
    # Quantity and pricing
    quantity: int = 0  # tradedQuantity
    price: float = 0.0  # tradedPrice
    
    # Timestamps
    trade_ts: int = 0  # Trade timestamp (internal)
    created_at: int = 0  # createTime (epoch)
    updated_at: Optional[int] = None  # updateTime (epoch)
    exchange_time: Optional[int] = None  # exchangeTime (epoch)
    
    # F&O derivatives info
    drv_expiry_date: Optional[int] = None  # drvExpiryDate (epoch)
    drv_option_type: Optional[str] = None  # drvOptionType (CALL/PUT)
    drv_strike_price: Optional[float] = None  # drvStrikePrice
    
    # Raw data
    raw_data: Optional[str] = None  # JSON
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'id': self.id,
            'order_id': self.order_id,
            'account_type': self.account_type,
            'exchange_order_id': self.exchange_order_id,
            'exchange_trade_id': self.exchange_trade_id,
            'security_id': self.security_id,
            'exchange_segment': self.exchange_segment,
            'trading_symbol': self.trading_symbol,
            'transaction_type': self.transaction_type,
            'product_type': self.product_type,
            'order_type': self.order_type,
            'quantity': self.quantity,
            'price': self.price,
            'trade_ts': self.trade_ts,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'exchange_time': self.exchange_time,
            'drv_expiry_date': self.drv_expiry_date,
            'drv_option_type': self.drv_option_type,
            'drv_strike_price': self.drv_strike_price,
            'raw_data': self.raw_data
        }


@dataclass
class Position:
    """Represents a position snapshot."""
    snapshot_ts: int
    account_type: Literal['leader', 'follower']
    security_id: str
    exchange_segment: str
    quantity: int
    avg_price: float
    realized_pl: Optional[float] = None
    unrealized_pl: Optional[float] = None
    product: Optional[str] = None
    raw_data: Optional[str] = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'snapshot_ts': self.snapshot_ts,
            'account_type': self.account_type,
            'security_id': self.security_id,
            'exchange_segment': self.exchange_segment,
            'quantity': self.quantity,
            'avg_price': self.avg_price,
            'realized_pl': self.realized_pl,
            'unrealized_pl': self.unrealized_pl,
            'product': self.product,
            'raw_data': self.raw_data
        }


@dataclass
class Funds:
    """Represents fund limits snapshot."""
    snapshot_ts: int
    account_type: Literal['leader', 'follower']
    available_balance: float
    collateral: Optional[float] = None
    margin_used: Optional[float] = None
    raw_data: Optional[str] = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'snapshot_ts': self.snapshot_ts,
            'account_type': self.account_type,
            'available_balance': self.available_balance,
            'collateral': self.collateral,
            'margin_used': self.margin_used,
            'raw_data': self.raw_data
        }


@dataclass
class Instrument:
    """Represents instrument metadata."""
    security_id: str
    exchange_segment: str
    symbol: str
    lot_size: int
    tick_size: float
    updated_at: int
    name: Optional[str] = None
    instrument_type: Optional[str] = None
    expiry_date: Optional[str] = None
    strike_price: Optional[float] = None
    option_type: Optional[str] = None
    underlying_security_id: Optional[str] = None
    meta: Optional[str] = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'security_id': self.security_id,
            'exchange_segment': self.exchange_segment,
            'symbol': self.symbol,
            'name': self.name,
            'instrument_type': self.instrument_type,
            'expiry_date': self.expiry_date,
            'strike_price': self.strike_price,
            'option_type': self.option_type,
            'lot_size': self.lot_size,
            'tick_size': self.tick_size,
            'underlying_security_id': self.underlying_security_id,
            'meta': self.meta,
            'updated_at': self.updated_at
        }
    
    def is_option(self) -> bool:
        """Check if instrument is an option."""
        return self.instrument_type in ('OPTIDX', 'OPTSTK')
    
    def is_future(self) -> bool:
        """Check if instrument is a future."""
        return self.instrument_type in ('FUTIDX', 'FUTSTK')


@dataclass
class CopyMapping:
    """Represents a mapping between leader and follower orders."""
    leader_order_id: str
    leader_quantity: int
    follower_quantity: int
    status: Literal['pending', 'placed', 'failed', 'cancelled']
    created_at: int
    updated_at: int
    id: Optional[int] = None
    follower_order_id: Optional[str] = None
    sizing_strategy: Optional[str] = None
    capital_ratio: Optional[float] = None
    error_message: Optional[str] = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'id': self.id,
            'leader_order_id': self.leader_order_id,
            'follower_order_id': self.follower_order_id,
            'leader_quantity': self.leader_quantity,
            'follower_quantity': self.follower_quantity,
            'sizing_strategy': self.sizing_strategy,
            'capital_ratio': self.capital_ratio,
            'status': self.status,
            'error_message': self.error_message,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }


@dataclass
class BracketOrderLeg:
    """
    Represents a bracket order leg relationship.
    Tracks Entry, Target, and SL legs of a bracket order.
    """
    parent_order_id: str  # BO parent order ID
    leg_order_id: str     # Individual leg order ID
    leg_type: Literal['ENTRY', 'TARGET', 'SL']
    account_type: Literal['leader', 'follower']
    status: str           # Track leg status
    created_at: int
    updated_at: int
    id: Optional[int] = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'id': self.id,
            'parent_order_id': self.parent_order_id,
            'leg_order_id': self.leg_order_id,
            'leg_type': self.leg_type,
            'account_type': self.account_type,
            'status': self.status,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }

