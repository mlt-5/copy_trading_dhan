"""
Unit tests for database module.
"""

import pytest
import sqlite3
from core.database import DatabaseManager, init_database
from core.models import Order, CopyMapping, BracketOrderLeg


@pytest.mark.unit
class TestDatabaseManager:
    """Test DatabaseManager class."""
    
    def test_database_initialization(self, temp_db, reset_singletons):
        """Test database initialization."""
        db = DatabaseManager(temp_db)
        
        # Check if tables were created
        cursor = db.conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        tables = [row[0] for row in cursor.fetchall()]
        
        assert 'orders' in tables
        assert 'copy_mappings' in tables
        assert 'order_events' in tables
    
    def test_singleton_pattern(self, temp_db, reset_singletons):
        """Test DatabaseManager singleton pattern."""
        db1 = DatabaseManager(temp_db)
        db2 = DatabaseManager(temp_db)
        
        assert db1 is db2
    
    def test_save_and_get_order(self, temp_db, reset_singletons, sample_order_data):
        """Test saving and retrieving order."""
        db = DatabaseManager(temp_db)
        
        order = Order(
            order_id=sample_order_data['orderId'],
            dhan_order_id=sample_order_data['dhanOrderId'],
            order_status=sample_order_data['orderStatus'],
            transaction_type=sample_order_data['transactionType'],
            exchange_segment=sample_order_data['exchangeSegment'],
            product_type=sample_order_data['productType'],
            order_type=sample_order_data['orderType'],
            security_id=sample_order_data['securityId'],
            quantity=sample_order_data['quantity'],
            price=sample_order_data['price'],
            created_at=1696348800,
            updated_at=1696348800
        )
        
        db.save_order(order)
        
        retrieved_order = db.get_order_by_id(sample_order_data['orderId'])
        assert retrieved_order is not None
        assert retrieved_order.order_id == sample_order_data['orderId']
        assert retrieved_order.quantity == sample_order_data['quantity']
    
    def test_save_copy_mapping(self, temp_db, reset_singletons):
        """Test saving copy mapping."""
        db = DatabaseManager(temp_db)
        
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
        
        db.save_copy_mapping(mapping)
        
        retrieved = db.get_copy_mapping_by_leader("12345")
        assert retrieved is not None
        assert retrieved.follower_order_id == "67890"
        assert retrieved.leader_quantity == 100
        assert retrieved.follower_quantity == 50
    
    def test_save_bracket_order_leg(self, temp_db, reset_singletons):
        """Test saving bracket order leg."""
        db = DatabaseManager(temp_db)
        
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
        
        db.save_bracket_order_leg(leg)
        
        legs = db.get_bracket_order_legs("12345")
        assert len(legs) == 1
        assert legs[0].leg_name == "SL"
        assert legs[0].price == 1490.0
    
    def test_config_key_value_store(self, temp_db, reset_singletons):
        """Test configuration key-value store."""
        db = DatabaseManager(temp_db)
        
        # Set value
        db.set_config_value('test_key', 'test_value')
        
        # Get value
        value = db.get_config_value('test_key')
        assert value == 'test_value'
        
        # Update value
        db.set_config_value('test_key', 'updated_value')
        value = db.get_config_value('test_key')
        assert value == 'updated_value'
        
        # Get non-existent key
        value = db.get_config_value('non_existent', default='default_val')
        assert value == 'default_val'
    
    def test_database_wal_mode(self, temp_db, reset_singletons):
        """Test database WAL mode is enabled."""
        db = DatabaseManager(temp_db)
        
        cursor = db.conn.cursor()
        cursor.execute("PRAGMA journal_mode")
        mode = cursor.fetchone()[0]
        
        assert mode.lower() == 'wal'
    
    def test_connection_context_manager(self, temp_db, reset_singletons):
        """Test database connection context manager."""
        db = DatabaseManager(temp_db)
        
        with db.get_connection() as conn:
            assert conn is not None
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            assert result[0] == 1


@pytest.mark.unit
class TestInitDatabase:
    """Test init_database function."""
    
    def test_init_database(self, temp_db, monkeypatch, reset_singletons):
        """Test init_database function."""
        monkeypatch.setenv('DB_PATH', temp_db)
        
        db = init_database()
        
        assert db is not None
        assert isinstance(db, DatabaseManager)

