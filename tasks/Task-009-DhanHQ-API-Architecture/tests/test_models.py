"""
Unit tests for data models.
"""

import pytest
from dataclasses import asdict
from core.models import (
    Order,
    OrderEvent,
    Trade,
    Position,
    Funds,
    Instrument,
    CopyMapping,
    BracketOrderLeg
)


@pytest.mark.unit
class TestOrder:
    """Test Order data model."""
    
    def test_order_creation(self):
        """Test creating Order."""
        order = Order(
            order_id="12345",
            dhan_order_id="12345",
            correlation_id="corr_123",
            order_status="PENDING",
            transaction_type="BUY",
            exchange_segment="NSE_EQ",
            product_type="INTRADAY",
            order_type="LIMIT",
            validity="DAY",
            security_id="11536",
            quantity=100,
            disclosed_quantity=0,
            price=1500.50,
            trigger_price=None,
            trading_symbol="RELIANCE",
            created_at=1696348800,
            updated_at=1696348800
        )
        
        assert order.order_id == "12345"
        assert order.quantity == 100
        assert order.price == 1500.50
    
    def test_order_to_dict(self):
        """Test converting Order to dictionary."""
        order = Order(
            order_id="12345",
            dhan_order_id="12345",
            order_status="PENDING",
            transaction_type="BUY",
            exchange_segment="NSE_EQ",
            product_type="INTRADAY",
            order_type="LIMIT",
            security_id="11536",
            quantity=100,
            price=1500.50,
            created_at=1696348800,
            updated_at=1696348800
        )
        
        order_dict = asdict(order)
        assert order_dict['order_id'] == "12345"
        assert order_dict['quantity'] == 100


@pytest.mark.unit
class TestCopyMapping:
    """Test CopyMapping data model."""
    
    def test_copy_mapping_success(self):
        """Test creating successful CopyMapping."""
        mapping = CopyMapping(
            leader_order_id="12345",
            follower_order_id="67890",
            leader_quantity=100,
            follower_quantity=50,
            sizing_strategy="CAPITAL_PROPORTIONAL",
            capital_ratio=0.5,
            status="placed",
            error_message=None,
            created_at=1696348800,
            updated_at=1696348800
        )
        
        assert mapping.leader_order_id == "12345"
        assert mapping.follower_order_id == "67890"
        assert mapping.leader_quantity == 100
        assert mapping.follower_quantity == 50
        assert mapping.status == "placed"
        assert mapping.error_message is None
    
    def test_copy_mapping_failed(self):
        """Test creating failed CopyMapping."""
        mapping = CopyMapping(
            leader_order_id="12345",
            follower_order_id=None,
            leader_quantity=100,
            follower_quantity=0,
            sizing_strategy="CAPITAL_PROPORTIONAL",
            capital_ratio=0.5,
            status="failed",
            error_message="Insufficient margin",
            created_at=1696348800,
            updated_at=1696348800
        )
        
        assert mapping.status == "failed"
        assert mapping.error_message == "Insufficient margin"
        assert mapping.follower_order_id is None


@pytest.mark.unit
class TestBracketOrderLeg:
    """Test BracketOrderLeg data model."""
    
    def test_bracket_order_leg_creation(self):
        """Test creating BracketOrderLeg."""
        leg = BracketOrderLeg(
            parent_order_id="12345",
            leg_name="SL",
            leg_order_id="12346",
            order_status="PENDING",
            price=1490.0,
            trigger_price=1495.0,
            quantity=25,
            created_at=1696348800,
            updated_at=1696348800
        )
        
        assert leg.parent_order_id == "12345"
        assert leg.leg_name == "SL"
        assert leg.leg_order_id == "12346"
        assert leg.price == 1490.0
    
    def test_bracket_order_leg_optional_fields(self):
        """Test BracketOrderLeg with optional fields."""
        leg = BracketOrderLeg(
            parent_order_id="12345",
            leg_name="TARGET",
            leg_order_id=None,
            order_status="PENDING",
            price=1520.0,
            trigger_price=None,
            quantity=25,
            created_at=1696348800,
            updated_at=1696348800
        )
        
        assert leg.leg_order_id is None
        assert leg.trigger_price is None


@pytest.mark.unit
class TestFunds:
    """Test Funds data model."""
    
    def test_funds_creation(self):
        """Test creating Funds."""
        funds = Funds(
            client_id="test_123",
            available_balance=100000.0,
            sod_limit=150000.0,
            collateral_amount=0.0,
            received_amount=0.0,
            blocked_payout_amount=0.0,
            utilized_amount=50000.0,
            timestamp=1696348800
        )
        
        assert funds.client_id == "test_123"
        assert funds.available_balance == 100000.0
        assert funds.utilized_amount == 50000.0
    
    def test_funds_calculations(self):
        """Test funds balance calculations."""
        funds = Funds(
            client_id="test_123",
            available_balance=50000.0,
            sod_limit=100000.0,
            collateral_amount=0.0,
            received_amount=10000.0,
            blocked_payout_amount=5000.0,
            utilized_amount=50000.0,
            timestamp=1696348800
        )
        
        # Available balance should be positive
        assert funds.available_balance > 0
        
        # Utilized + available should approximately equal sod_limit
        # (may not be exact due to other factors)
        total = funds.utilized_amount + funds.available_balance
        assert total <= funds.sod_limit + funds.received_amount


@pytest.mark.unit
class TestInstrument:
    """Test Instrument data model."""
    
    def test_instrument_creation(self):
        """Test creating Instrument."""
        instrument = Instrument(
            security_id="11536",
            trading_symbol="RELIANCE",
            exchange_segment="NSE_EQ",
            instrument_type="EQUITY",
            lot_size=1,
            tick_size=0.05,
            expiry_date=None,
            strike_price=None,
            option_type=None,
            last_updated=1696348800
        )
        
        assert instrument.security_id == "11536"
        assert instrument.trading_symbol == "RELIANCE"
        assert instrument.lot_size == 1
        assert instrument.tick_size == 0.05
    
    def test_instrument_derivative(self):
        """Test creating derivative Instrument."""
        instrument = Instrument(
            security_id="45678",
            trading_symbol="NIFTY23OCT18000CE",
            exchange_segment="NSE_FO",
            instrument_type="OPTIDX",
            lot_size=50,
            tick_size=0.05,
            expiry_date="2023-10-26",
            strike_price=18000.0,
            option_type="CE",
            last_updated=1696348800
        )
        
        assert instrument.instrument_type == "OPTIDX"
        assert instrument.strike_price == 18000.0
        assert instrument.option_type == "CE"
        assert instrument.expiry_date == "2023-10-26"

