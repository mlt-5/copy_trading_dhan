"""
Data models for database entities.
"""

from dataclasses import dataclass
from typing import Optional, Literal
import json


@dataclass
class Order:
    """Represents an order in the database."""
    id: str
    account_type: Literal['leader', 'follower']
    status: str
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
    correlation_id: Optional[str] = None
    raw_request: Optional[str] = None
    raw_response: Optional[str] = None
    # ✅ ADDED: Cover Order (CO) parameters
    co_stop_loss_value: Optional[float] = None
    co_trigger_price: Optional[float] = None
    # ✅ ADDED: Bracket Order (BO) parameters
    bo_profit_value: Optional[float] = None
    bo_stop_loss_value: Optional[float] = None
    bo_order_type: Optional[str] = None
    # ✅ ADDED: Multi-leg order tracking
    parent_order_id: Optional[str] = None
    leg_type: Optional[str] = None  # 'ENTRY', 'TARGET', 'SL'
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'id': self.id,
            'account_type': self.account_type,
            'correlation_id': self.correlation_id,
            'status': self.status,
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
            # ✅ ADDED: CO/BO parameters
            'co_stop_loss_value': self.co_stop_loss_value,
            'co_trigger_price': self.co_trigger_price,
            'bo_profit_value': self.bo_profit_value,
            'bo_stop_loss_value': self.bo_stop_loss_value,
            'bo_order_type': self.bo_order_type,
            'parent_order_id': self.parent_order_id,
            'leg_type': self.leg_type,
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
    """Represents a trade execution."""
    id: str
    order_id: str
    account_type: Literal['leader', 'follower']
    trade_ts: int
    quantity: int
    price: float
    exchange_segment: Optional[str] = None
    security_id: Optional[str] = None
    raw_data: Optional[str] = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'id': self.id,
            'order_id': self.order_id,
            'account_type': self.account_type,
            'trade_ts': self.trade_ts,
            'quantity': self.quantity,
            'price': self.price,
            'exchange_segment': self.exchange_segment,
            'security_id': self.security_id,
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
    ✅ ADDED: Represents a bracket order leg relationship.
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
