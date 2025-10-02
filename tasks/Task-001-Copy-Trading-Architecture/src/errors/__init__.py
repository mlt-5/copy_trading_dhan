"""
✅ TASK-006: Typed Error Classes for DhanHQ Copy Trading

Strongly typed exceptions for better error handling and debugging.
"""

from typing import Optional, Dict, Any


class DhanCopyTradingError(Exception):
    """Base exception for all copy trading errors."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)
    
    def __str__(self) -> str:
        if self.details:
            return f"{self.message} | Details: {self.details}"
        return self.message


class ConfigurationError(DhanCopyTradingError):
    """Configuration-related errors (missing env vars, invalid config)."""
    pass


class AuthenticationError(DhanCopyTradingError):
    """Authentication failures (invalid tokens, expired credentials)."""
    pass


class OrderPlacementError(DhanCopyTradingError):
    """Order placement failures."""
    
    def __init__(
        self,
        message: str,
        order_id: Optional[str] = None,
        security_id: Optional[str] = None,
        api_error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, details)
        self.order_id = order_id
        self.security_id = security_id
        self.api_error_code = api_error_code


class OrderModificationError(DhanCopyTradingError):
    """Order modification failures."""
    
    def __init__(
        self,
        message: str,
        order_id: Optional[str] = None,
        api_error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, details)
        self.order_id = order_id
        self.api_error_code = api_error_code


class OrderCancellationError(DhanCopyTradingError):
    """Order cancellation failures."""
    
    def __init__(
        self,
        message: str,
        order_id: Optional[str] = None,
        api_error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, details)
        self.order_id = order_id
        self.api_error_code = api_error_code


class PositionSizingError(DhanCopyTradingError):
    """Position sizing calculation errors."""
    
    def __init__(
        self,
        message: str,
        leader_quantity: Optional[int] = None,
        follower_capital: Optional[float] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, details)
        self.leader_quantity = leader_quantity
        self.follower_capital = follower_capital


class InsufficientFundsError(DhanCopyTradingError):
    """Insufficient funds in follower account."""
    
    def __init__(
        self,
        message: str,
        required: Optional[float] = None,
        available: Optional[float] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, details)
        self.required = required
        self.available = available


class WebSocketConnectionError(DhanCopyTradingError):
    """WebSocket connection errors."""
    pass


class WebSocketTimeoutError(DhanCopyTradingError):
    """WebSocket timeout/heartbeat errors."""
    pass


class DatabaseError(DhanCopyTradingError):
    """Database operation errors."""
    pass


class ValidationError(DhanCopyTradingError):
    """Input/data validation errors."""
    
    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        value: Optional[Any] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, details)
        self.field = field
        self.value = value


class RateLimitError(DhanCopyTradingError):
    """Rate limiting errors."""
    
    def __init__(
        self,
        message: str,
        retry_after: Optional[float] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, details)
        self.retry_after = retry_after


class MarketClosedError(DhanCopyTradingError):
    """Market closed errors."""
    pass


class CoverOrderError(DhanCopyTradingError):
    """Cover Order specific errors."""
    
    def __init__(
        self,
        message: str,
        order_id: Optional[str] = None,
        stop_loss_value: Optional[float] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, details)
        self.order_id = order_id
        self.stop_loss_value = stop_loss_value


class BracketOrderError(DhanCopyTradingError):
    """Bracket Order specific errors."""
    
    def __init__(
        self,
        message: str,
        parent_order_id: Optional[str] = None,
        leg_type: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, details)
        self.parent_order_id = parent_order_id
        self.leg_type = leg_type


__all__ = [
    'DhanCopyTradingError',
    'ConfigurationError',
    'AuthenticationError',
    'OrderPlacementError',
    'OrderModificationError',
    'OrderCancellationError',
    'PositionSizingError',
    'InsufficientFundsError',
    'WebSocketConnectionError',
    'WebSocketTimeoutError',
    'DatabaseError',
    'ValidationError',
    'RateLimitError',
    'MarketClosedError',
    'CoverOrderError',
    'BracketOrderError',
]

