"""
Position Sizing Engine

Calculate appropriate order quantities for follower account based on:
- Capital ratio between accounts
- Risk management limits
- Options lot sizes
- Configured sizing strategy
"""

import logging
import math
import time
from typing import Optional
from dhanhq import dhanhq

from ..config import SizingStrategy, get_config
from ..database import DatabaseManager, get_db, Funds, Instrument

logger = logging.getLogger(__name__)


class PositionSizer:
    """
    Calculate position sizes for follower orders.
    
    Supports multiple sizing strategies:
    - Capital proportional: Scale by capital ratio
    - Fixed ratio: Fixed multiplier
    - Risk-based: Based on % of capital at risk
    """
    
    def __init__(
        self,
        leader_client: dhanhq,
        follower_client: dhanhq,
        db: DatabaseManager,
        strategy: SizingStrategy,
        copy_ratio: Optional[float] = None,
        max_position_size_pct: float = 10.0
    ):
        """
        Initialize position sizer.
        
        Args:
            leader_client: DhanHQ client for leader account
            follower_client: DhanHQ client for follower account
            db: Database manager
            strategy: Position sizing strategy
            copy_ratio: Fixed ratio (required for fixed_ratio strategy)
            max_position_size_pct: Max position size as % of capital
        """
        self.leader_client = leader_client
        self.follower_client = follower_client
        self.db = db
        self.strategy = strategy
        self.copy_ratio = copy_ratio
        self.max_position_size_pct = max_position_size_pct
        
        # Cache for funds (refresh periodically)
        self._leader_funds: Optional[Funds] = None
        self._follower_funds: Optional[Funds] = None
        self._funds_last_updated: int = 0
        self._funds_ttl: int = 30  # Refresh every 30 seconds
        
        logger.info(f"Position sizer initialized with strategy: {strategy.value}")
    
    def _refresh_funds(self, force: bool = False) -> tuple[Funds, Funds]:
        """
        Refresh fund limits for both accounts.
        
        Args:
            force: Force refresh even if within TTL
        
        Returns:
            Tuple of (leader_funds, follower_funds)
        """
        current_time = int(time.time())
        
        if force or (current_time - self._funds_last_updated) > self._funds_ttl:
            logger.debug("Refreshing fund limits")
            
            # Fetch from API
            leader_funds_data = self.leader_client.get_fund_limits()
            follower_funds_data = self.follower_client.get_fund_limits()
            
            # Parse and create Funds objects
            self._leader_funds = self._parse_funds_response(leader_funds_data, 'leader')
            self._follower_funds = self._parse_funds_response(follower_funds_data, 'follower')
            
            # Save to database
            self.db.save_funds_snapshot(self._leader_funds)
            self.db.save_funds_snapshot(self._follower_funds)
            
            self._funds_last_updated = current_time
            
            logger.info("Fund limits refreshed", extra={
                "leader_balance": self._leader_funds.available_balance,
                "follower_balance": self._follower_funds.available_balance
            })
        
        return self._leader_funds, self._follower_funds
    
    def _parse_funds_response(self, funds_data: dict, account_type: str) -> Funds:
        """
        Parse DhanHQ funds response into Funds object.
        
        Args:
            funds_data: API response
            account_type: 'leader' or 'follower'
        
        Returns:
            Funds object
        """
        import json
        
        # ✅ PATCH-001: Fixed typo - availableBalance (per DhanHQ v2 Funds API)
        available = funds_data.get('availableBalance', 0.0)
        if available == 0.0:
            available = funds_data.get('available_balance', 0.0)
        
        collateral = funds_data.get('collateralAmount', 0.0)
        margin_used = funds_data.get('utilizedAmount', 0.0)
        
        return Funds(
            snapshot_ts=int(time.time()),
            account_type=account_type,
            available_balance=float(available),
            collateral=float(collateral) if collateral else None,
            margin_used=float(margin_used) if margin_used else None,
            raw_data=json.dumps(funds_data)
        )
    
    def get_capital_ratio(self) -> float:
        """
        Calculate capital ratio between follower and leader.
        
        Returns:
            Ratio (follower_capital / leader_capital)
        """
        leader_funds, follower_funds = self._refresh_funds()
        
        if leader_funds.available_balance == 0:
            logger.warning("Leader available balance is 0, returning ratio 0")
            return 0.0
        
        ratio = follower_funds.available_balance / leader_funds.available_balance
        
        logger.debug(f"Capital ratio: {ratio:.4f}", extra={
            "leader_balance": leader_funds.available_balance,
            "follower_balance": follower_funds.available_balance
        })
        
        return ratio
    
    def calculate_quantity(
        self,
        leader_quantity: int,
        security_id: str,
        premium: Optional[float] = None
    ) -> int:
        """
        Calculate appropriate quantity for follower order.
        
        Args:
            leader_quantity: Quantity in leader order
            security_id: Security ID for instrument lookup
            premium: Option premium (for risk-based sizing)
        
        Returns:
            Adjusted quantity for follower (rounded to lot size)
        """
        # Get instrument metadata
        instrument = self.db.get_instrument(security_id)
        
        if not instrument:
            logger.warning(f"Instrument {security_id} not found in cache, using leader quantity")
            return leader_quantity
        
        # Calculate raw quantity based on strategy
        if self.strategy == SizingStrategy.CAPITAL_PROPORTIONAL:
            raw_qty = self._calculate_capital_proportional(leader_quantity)
        elif self.strategy == SizingStrategy.FIXED_RATIO:
            raw_qty = self._calculate_fixed_ratio(leader_quantity)
        elif self.strategy == SizingStrategy.RISK_BASED:
            raw_qty = self._calculate_risk_based(leader_quantity, instrument, premium)
        else:
            logger.warning(f"Unknown strategy {self.strategy}, using leader quantity")
            raw_qty = float(leader_quantity)
        
        # Round to lot size
        adjusted_qty = self._round_to_lot_size(raw_qty, instrument.lot_size)
        
        # Apply risk limits
        final_qty = self._apply_risk_limits(adjusted_qty, instrument, premium)
        
        logger.info("Quantity calculated", extra={
            "leader_qty": leader_quantity,
            "raw_qty": raw_qty,
            "adjusted_qty": adjusted_qty,
            "final_qty": final_qty,
            "lot_size": instrument.lot_size,
            "strategy": self.strategy.value
        })
        
        return final_qty
    
    def _calculate_capital_proportional(self, leader_quantity: int) -> float:
        """
        Calculate quantity based on capital ratio.
        
        Args:
            leader_quantity: Leader order quantity
        
        Returns:
            Proportional quantity (float)
        """
        capital_ratio = self.get_capital_ratio()
        return float(leader_quantity) * capital_ratio
    
    def _calculate_fixed_ratio(self, leader_quantity: int) -> float:
        """
        Calculate quantity based on fixed ratio.
        
        Args:
            leader_quantity: Leader order quantity
        
        Returns:
            Scaled quantity (float)
        """
        if self.copy_ratio is None:
            logger.warning("copy_ratio not set, falling back to capital proportional")
            return self._calculate_capital_proportional(leader_quantity)
        
        return float(leader_quantity) * self.copy_ratio
    
    def _calculate_risk_based(
        self,
        leader_quantity: int,
        instrument: Instrument,
        premium: Optional[float]
    ) -> float:
        """
        Calculate quantity based on risk as % of capital.
        
        Args:
            leader_quantity: Leader order quantity
            instrument: Instrument metadata
            premium: Option premium
        
        Returns:
            Risk-adjusted quantity (float)
        """
        _, follower_funds = self._refresh_funds()
        
        # Maximum position value based on % of capital
        max_position_value = follower_funds.available_balance * (self.max_position_size_pct / 100.0)
        
        if premium is None or premium == 0:
            logger.warning("Premium not provided for risk-based sizing, using capital proportional")
            return self._calculate_capital_proportional(leader_quantity)
        
        # Calculate maximum lots
        value_per_lot = premium * instrument.lot_size
        max_lots = max_position_value / value_per_lot
        
        # Calculate leader lots
        leader_lots = leader_quantity / instrument.lot_size
        
        # Take minimum
        follower_lots = min(max_lots, leader_lots)
        
        return follower_lots * instrument.lot_size
    
    def _round_to_lot_size(self, quantity: float, lot_size: int) -> int:
        """
        Round quantity to nearest lot size.
        
        Args:
            quantity: Raw quantity
            lot_size: Lot size
        
        Returns:
            Rounded quantity
        """
        if quantity <= 0:
            return 0
        
        num_lots = math.floor(quantity / lot_size)
        
        # Minimum 1 lot
        if num_lots < 1:
            num_lots = 1
        
        return num_lots * lot_size
    
    def _apply_risk_limits(
        self,
        quantity: int,
        instrument: Instrument,
        premium: Optional[float]
    ) -> int:
        """
        Apply risk management limits to quantity.
        
        Args:
            quantity: Proposed quantity
            instrument: Instrument metadata
            premium: Option premium
        
        Returns:
            Risk-limited quantity
        """
        if quantity == 0:
            return 0
        
        _, follower_funds = self._refresh_funds()
        
        # Calculate position value
        if premium:
            position_value = quantity * premium
        else:
            # Conservative estimate if premium not available
            position_value = quantity * 100  # Arbitrary, should fetch quote
        
        # Check if within max position size
        max_position_value = follower_funds.available_balance * (self.max_position_size_pct / 100.0)
        
        if position_value > max_position_value:
            logger.warning(f"Position value {position_value} exceeds limit {max_position_value}, reducing")
            
            # Reduce to max lots
            if premium:
                max_lots = int(max_position_value / (premium * instrument.lot_size))
            else:
                max_lots = int(quantity / instrument.lot_size) - 1
            
            quantity = max_lots * instrument.lot_size
        
        return quantity
    
    def validate_sufficient_margin(
        self,
        quantity: int,
        security_id: str,
        premium: Optional[float]
    ) -> tuple[bool, str]:
        """
        Validate that follower has sufficient margin for order.
        
        Args:
            quantity: Order quantity
            security_id: Security ID
            premium: Option premium
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        if quantity == 0:
            return False, "Quantity is 0"
        
        _, follower_funds = self._refresh_funds()
        
        instrument = self.db.get_instrument(security_id)
        
        if not instrument:
            return False, f"Instrument {security_id} not found"
        
        # Rough margin estimate (actual margin depends on broker rules)
        if premium:
            estimated_margin = quantity * premium
        else:
            # Very rough estimate
            estimated_margin = quantity * 50  # Should use margin calculator API
        
        if estimated_margin > follower_funds.available_balance:
            return False, f"Insufficient margin: need {estimated_margin}, have {follower_funds.available_balance}"
        
        return True, ""


# Global position sizer instance
_position_sizer: Optional[PositionSizer] = None


def get_position_sizer() -> PositionSizer:
    """
    Get position sizer instance (singleton).
    
    Returns:
        PositionSizer instance
    
    Raises:
        ValueError: If not initialized
    """
    global _position_sizer
    
    if _position_sizer is None:
        raise ValueError("Position sizer not initialized")
    
    return _position_sizer


def initialize_position_sizer(
    leader_client: dhanhq,
    follower_client: dhanhq
) -> PositionSizer:
    """
    Initialize position sizer (call after auth and db init).
    
    Args:
        leader_client: Leader DhanHQ client
        follower_client: Follower DhanHQ client
    
    Returns:
        PositionSizer instance
    """
    global _position_sizer
    
    _, _, system_config = get_config()
    db = get_db()
    
    _position_sizer = PositionSizer(
        leader_client=leader_client,
        follower_client=follower_client,
        db=db,
        strategy=system_config.sizing_strategy,
        copy_ratio=system_config.copy_ratio,
        max_position_size_pct=system_config.max_position_size_pct
    )
    
    return _position_sizer


