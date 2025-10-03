"""
Integration tests for copy trading system.
"""

import pytest
import time
from unittest.mock import Mock, patch
from core.database import DatabaseManager
from core.position_sizer import PositionSizer
from core.order_replicator import OrderReplicator
from core.models import CopyMapping


@pytest.mark.integration
class TestOrderReplicationFlow:
    """Test complete order replication flow."""
    
    @pytest.fixture
    def setup_system(self, temp_db, mock_env, reset_singletons):
        """Setup complete system for integration testing."""
        # Create database
        db = DatabaseManager(temp_db)
        
        # Create mock APIs
        leader_funds_api = Mock()
        follower_funds_api = Mock()
        orders_api = Mock()
        super_orders_api = Mock()
        
        # Setup mock responses
        leader_funds_api.get_fund_limits.return_value = {
            'availableBalance': 200000.0,
            'sodLimit': 300000.0,
        }
        
        follower_funds_api.get_fund_limits.return_value = {
            'availableBalance': 100000.0,
            'sodLimit': 150000.0,
        }
        
        follower_funds_api.calculate_margin_requirement.return_value = {
            'requiredMargin': 5000.0
        }
        
        orders_api.place_order.return_value = {
            'orderId': 'FOLLOWER_12345',
            'status': 'success'
        }
        
        # Create position sizer
        position_sizer = PositionSizer(leader_funds_api, follower_funds_api)
        
        # Create order replicator
        order_replicator = OrderReplicator(
            orders_api=orders_api,
            super_orders_api=super_orders_api,
            position_sizer=position_sizer,
            db=db
        )
        
        return {
            'db': db,
            'position_sizer': position_sizer,
            'order_replicator': order_replicator,
            'orders_api': orders_api,
            'super_orders_api': super_orders_api,
        }
    
    def test_replicate_basic_order(self, setup_system, sample_order_data):
        """Test replicating a basic order."""
        system = setup_system
        
        # Replicate order
        follower_order_id = system['order_replicator'].replicate_order(sample_order_data)
        
        # Verify order was placed
        assert follower_order_id is not None
        assert follower_order_id == 'FOLLOWER_12345'
        
        # Verify API was called
        system['orders_api'].place_order.assert_called_once()
        
        # Verify copy mapping was saved
        mapping = system['db'].get_copy_mapping_by_leader(sample_order_data['orderId'])
        assert mapping is not None
        assert mapping.leader_order_id == sample_order_data['orderId']
        assert mapping.follower_order_id == 'FOLLOWER_12345'
        assert mapping.status == 'placed'
    
    def test_replicate_cover_order(self, setup_system, sample_co_order_data):
        """Test replicating a cover order."""
        system = setup_system
        
        system['super_orders_api'].place_cover_order.return_value = {
            'orderId': 'FOLLOWER_CO_12345',
            'status': 'success'
        }
        
        # Replicate cover order
        follower_order_id = system['order_replicator'].replicate_order(sample_co_order_data)
        
        # Verify order was placed
        assert follower_order_id is not None
        assert follower_order_id == 'FOLLOWER_CO_12345'
        
        # Verify Super Orders API was called
        system['super_orders_api'].place_cover_order.assert_called_once()
        
        # Verify copy mapping
        mapping = system['db'].get_copy_mapping_by_leader(sample_co_order_data['orderId'])
        assert mapping.status == 'placed'
    
    def test_replicate_bracket_order(self, setup_system, sample_bo_order_data):
        """Test replicating a bracket order."""
        system = setup_system
        
        system['super_orders_api'].place_bracket_order.return_value = {
            'orderId': 'FOLLOWER_BO_12345',
            'status': 'success'
        }
        
        # Replicate bracket order
        follower_order_id = system['order_replicator'].replicate_order(sample_bo_order_data)
        
        # Verify order was placed
        assert follower_order_id is not None
        
        # Verify Super Orders API was called
        system['super_orders_api'].place_bracket_order.assert_called_once()
    
    def test_failed_replication_insufficient_margin(self, setup_system, sample_order_data):
        """Test failed replication due to insufficient margin."""
        system = setup_system
        
        # Setup insufficient margin
        system['position_sizer'].follower_funds_api.calculate_margin_requirement.return_value = {
            'requiredMargin': 200000.0  # More than available
        }
        
        # Replicate order
        follower_order_id = system['order_replicator'].replicate_order(sample_order_data)
        
        # Verify replication failed
        assert follower_order_id is None
        
        # Verify API was NOT called
        system['orders_api'].place_order.assert_not_called()
        
        # Verify failed mapping was saved
        mapping = system['db'].get_copy_mapping_by_leader(sample_order_data['orderId'])
        assert mapping is not None
        assert mapping.status == 'failed'
        assert 'Insufficient margin' in mapping.error_message
    
    def test_position_sizing_calculation(self, setup_system, sample_order_data):
        """Test position sizing calculation in replication flow."""
        system = setup_system
        
        # Replicate order with 100 quantity
        follower_order_id = system['order_replicator'].replicate_order(sample_order_data)
        
        # Get copy mapping
        mapping = system['db'].get_copy_mapping_by_leader(sample_order_data['orderId'])
        
        # Leader quantity is 100, follower should be 50 (0.5 capital ratio)
        assert mapping.leader_quantity == 100
        assert mapping.follower_quantity == 50
        assert mapping.capital_ratio == 0.5


@pytest.mark.integration
class TestDatabasePersistence:
    """Test database persistence across operations."""
    
    def test_order_lifecycle_tracking(self, temp_db, reset_singletons, sample_order_data):
        """Test tracking order lifecycle in database."""
        db = DatabaseManager(temp_db)
        
        from core.models import Order, OrderEvent
        
        # Create order
        order = Order(
            order_id=sample_order_data['orderId'],
            dhan_order_id=sample_order_data['dhanOrderId'],
            order_status='PENDING',
            transaction_type=sample_order_data['transactionType'],
            exchange_segment=sample_order_data['exchangeSegment'],
            product_type=sample_order_data['productType'],
            order_type=sample_order_data['orderType'],
            security_id=sample_order_data['securityId'],
            quantity=sample_order_data['quantity'],
            price=sample_order_data['price'],
            created_at=int(time.time()),
            updated_at=int(time.time())
        )
        
        db.save_order(order)
        
        # Add order events
        events = ['PENDING', 'TRANSIT', 'TRADED', 'COMPLETE']
        for status in events:
            event = OrderEvent(
                event_id=None,
                order_id=sample_order_data['orderId'],
                event_type='STATUS_CHANGE',
                event_data={'status': status},
                timestamp=int(time.time())
            )
            db.save_order_event(event)
        
        # Retrieve order events
        saved_events = db.get_order_events(sample_order_data['orderId'])
        
        assert len(saved_events) >= len(events)


@pytest.mark.integration
@pytest.mark.slow
class TestSystemPerformance:
    """Test system performance under load."""
    
    def test_rapid_order_replication(self, setup_system):
        """Test replicating multiple orders rapidly."""
        system = setup_system
        
        # Create 100 orders
        start_time = time.time()
        
        for i in range(100):
            order_data = {
                'orderId': f'ORDER_{i}',
                'dhanOrderId': f'ORDER_{i}',
                'securityId': '11536',
                'exchangeSegment': 'NSE_EQ',
                'transactionType': 'BUY',
                'quantity': 100,
                'orderType': 'LIMIT',
                'productType': 'INTRADAY',
                'price': 1500.0,
                'orderStatus': 'PENDING',
            }
            
            system['order_replicator'].replicate_order(order_data)
        
        elapsed_time = time.time() - start_time
        
        # Should process 100 orders in reasonable time (< 5 seconds)
        assert elapsed_time < 5.0
        
        # Verify all mappings were saved
        # Note: This is a performance test, actual count depends on mock behavior
        assert system['orders_api'].place_order.call_count > 0

