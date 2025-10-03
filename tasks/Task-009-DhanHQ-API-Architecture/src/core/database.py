"""
Database Manager Module

SQLite database operations with WAL mode, prepared statements, and connection pooling.
Updated for new architecture with proper imports from core.models.
"""

import sqlite3
import logging
import time
import json
from typing import Optional, List, Dict, Any
from pathlib import Path

from .config import get_config
from .models import Order, OrderEvent, Trade, Position, Funds, Instrument, CopyMapping

logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    Manage SQLite database operations.
    
    Features:
    - WAL mode for concurrent reads
    - Prepared statements for performance
    - Transaction support
    - Automatic schema initialization
    - Migration support
    """
    
    def __init__(self, db_path: str):
        """
        Initialize database manager.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.conn: Optional[sqlite3.Connection] = None
        self._busy_timeout = 5000  # 5 seconds
    
    def connect(self) -> sqlite3.Connection:
        """
        Establish database connection with optimized settings.
        
        Returns:
            SQLite connection object
        """
        if self.conn is not None:
            return self.conn
        
        logger.info(f"Connecting to database: {self.db_path}")
        
        # Create directory if it doesn't exist
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        
        self.conn = sqlite3.connect(
            self.db_path,
            timeout=self._busy_timeout / 1000,
            check_same_thread=False  # Allow multi-threaded access (with care)
        )
        
        # Enable row factory for dict-like access
        self.conn.row_factory = sqlite3.Row
        
        # Enable foreign keys
        self.conn.execute("PRAGMA foreign_keys = ON")
        
        # Enable WAL mode for better concurrency
        self.conn.execute("PRAGMA journal_mode = WAL")
        
        # Set synchronous mode
        self.conn.execute("PRAGMA synchronous = NORMAL")
        
        logger.info("Database connection established")
        
        return self.conn
    
    def initialize_schema(self) -> None:
        """Initialize database schema from SQL file."""
        schema_path = Path(__file__).parent / "database" / "schema.sql"
        
        logger.info("Initializing database schema")
        
        with open(schema_path, 'r') as f:
            schema_sql = f.read()
        
        self.conn.executescript(schema_sql)
        self.conn.commit()
        
        logger.info("Database schema initialized successfully")
    
    def get_schema_version(self) -> int:
        """
        Get current database schema version.
        
        Returns:
            Schema version number
        """
        cursor = self.conn.execute(
            "SELECT value FROM config WHERE key = 'schema_version'"
        )
        row = cursor.fetchone()
        return int(row['value']) if row else 0
    
    def close(self) -> None:
        """Close database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None
            logger.info("Database connection closed")
    
    # =========================================================================
    # Order Operations
    # =========================================================================
    
    def save_order(self, order: Order) -> None:
        """
        Save or update an order.
        
        Args:
            order: Order object to save
        """
        self.conn.execute("""
            INSERT OR REPLACE INTO orders (
                id, account_type, correlation_id, status, order_status, side, product, order_type,
                validity, security_id, exchange_segment, trading_symbol, quantity, price, trigger_price,
                disclosed_qty, traded_qty, remaining_qty, avg_price, exchange_order_id, exchange_time,
                algo_id, drv_expiry_date, drv_option_type, drv_strike_price,
                oms_error_code, oms_error_description,
                co_stop_loss_value, co_trigger_price, bo_profit_value,
                bo_stop_loss_value, bo_order_type, parent_order_id, leg_type,
                after_market_order, amo_time, is_sliced_order, slice_order_id, slice_index, total_slice_quantity,
                created_at, updated_at, completed_at, raw_request, raw_response
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            order.id, order.account_type, order.correlation_id, order.status,
            order.order_status, order.side, order.product, order.order_type, order.validity,
            order.security_id, order.exchange_segment, order.trading_symbol, order.quantity,
            order.price, order.trigger_price, order.disclosed_qty,
            order.traded_qty, order.remaining_qty, order.avg_price, order.exchange_order_id, order.exchange_time,
            order.algo_id, order.drv_expiry_date, order.drv_option_type, order.drv_strike_price,
            order.oms_error_code, order.oms_error_description,
            order.co_stop_loss_value, order.co_trigger_price, order.bo_profit_value,
            order.bo_stop_loss_value, order.bo_order_type, order.parent_order_id,
            order.leg_type, 1 if order.after_market_order else 0, order.amo_time,
            1 if order.is_sliced_order else 0, order.slice_order_id, order.slice_index, order.total_slice_quantity,
            order.created_at, order.updated_at, order.completed_at, order.raw_request, order.raw_response
        ))
        self.conn.commit()
        
        logger.debug(f"Saved order: {order.id} ({order.account_type})")
    
    def save_bracket_order_leg(self, leg_data: Dict[str, Any]) -> bool:
        """
        Save bracket order leg to tracking table.
        
        Args:
            leg_data: Dictionary with parent_order_id, leg_type, leg_order_id, status, etc.
        """
        try:
            self.conn.execute('''
                INSERT OR REPLACE INTO bracket_order_legs (
                    parent_order_id, leg_type, leg_order_id, status,
                    quantity, price, trigger_price, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                leg_data.get('parent_order_id'),
                leg_data.get('leg_type'),
                leg_data.get('leg_order_id'),
                leg_data.get('status', 'PENDING'),
                leg_data.get('quantity', 0),
                leg_data.get('price', 0),
                leg_data.get('trigger_price', 0),
                leg_data.get('created_at', int(time.time())),
                leg_data.get('updated_at', int(time.time()))
            ))
            self.conn.commit()
            logger.debug(f"BO leg saved: parent={leg_data.get('parent_order_id')}, leg={leg_data.get('leg_type')}")
            return True
        except Exception as e:
            logger.error(f"Error saving BO leg: {e}")
            return False
    
    def get_bracket_order_legs(self, parent_order_id: str) -> List[Dict[str, Any]]:
        """
        Retrieve all legs for a bracket order.
        
        Args:
            parent_order_id: The parent BO order ID
        
        Returns:
            List of leg dictionaries
        """
        try:
            cursor = self.conn.execute('''
                SELECT * FROM bracket_order_legs WHERE parent_order_id = ?
            ''', (parent_order_id,))
            rows = cursor.fetchall()
            
            legs = []
            for row in rows:
                legs.append({
                    'id': row[0],
                    'parent_order_id': row[1],
                    'leg_type': row[2],
                    'leg_order_id': row[3],
                    'status': row[4],
                    'quantity': row[5],
                    'price': row[6],
                    'trigger_price': row[7],
                    'created_at': row[8],
                    'updated_at': row[9]
                })
            return legs
        except Exception as e:
            logger.error(f"Error fetching BO legs: {e}")
            return []
    
    def update_bracket_order_leg_status(self, leg_id: int, status: str) -> bool:
        """
        Update status of a bracket order leg.
        
        Args:
            leg_id: Database ID of the leg
            status: New status
        """
        try:
            self.conn.execute('''
                UPDATE bracket_order_legs 
                SET status = ?, updated_at = ?
                WHERE id = ?
            ''', (status, int(time.time()), leg_id))
            self.conn.commit()
            logger.debug(f"BO leg {leg_id} status updated to {status}")
            return True
        except Exception as e:
            logger.error(f"Error updating BO leg status: {e}")
            return False
    
    def get_order(self, order_id: str) -> Optional[Order]:
        """
        Get order by ID.
        
        Args:
            order_id: Order ID
        
        Returns:
            Order object or None
        """
        cursor = self.conn.execute(
            "SELECT * FROM orders WHERE id = ?", (order_id,)
        )
        row = cursor.fetchone()
        
        if row:
            return Order(**dict(row))
        return None
    
    def get_orders_by_account(self, account_type: str, limit: int = 100) -> List[Order]:
        """
        Get recent orders for an account.
        
        Args:
            account_type: 'leader' or 'follower'
            limit: Maximum number of orders to return
        
        Returns:
            List of Order objects
        """
        cursor = self.conn.execute("""
            SELECT * FROM orders 
            WHERE account_type = ?
            ORDER BY created_at DESC
            LIMIT ?
        """, (account_type, limit))
        
        return [Order(**dict(row)) for row in cursor.fetchall()]
    
    def get_order_by_correlation_id(self, correlation_id: str) -> Optional[Order]:
        """
        Get order by correlation ID.
        
        Per DhanHQ v2 Orders API:
        GET /orders/external/{correlation-id}
        
        Args:
            correlation_id: User/partner generated tracking ID
        
        Returns:
            Order object or None (returns most recent if multiple matches)
        """
        cursor = self.conn.execute("""
            SELECT * FROM orders 
            WHERE correlation_id = ?
            ORDER BY created_at DESC
            LIMIT 1
        """, (correlation_id,))
        
        row = cursor.fetchone()
        
        if row:
            return Order(**dict(row))
        return None
    
    def update_order_status(self, order_id: str, status: str) -> None:
        """
        Update order status.
        
        Args:
            order_id: Order ID
            status: New status
        """
        self.conn.execute("""
            UPDATE orders 
            SET status = ?, updated_at = ?
            WHERE id = ?
        """, (status, int(time.time()), order_id))
        self.conn.commit()
        
        logger.debug(f"Updated order {order_id} status to {status}")
    
    def save_order_modification(
        self,
        order_id: str,
        modification_type: str,
        old_value: Optional[str] = None,
        new_value: Optional[str] = None,
        status: str = 'PENDING',
        error_message: Optional[str] = None
    ) -> None:
        """
        Save order modification record.
        
        Args:
            order_id: Order ID being modified
            modification_type: Type of modification (QUANTITY, PRICE, TRIGGER_PRICE, VALIDITY, ORDER_TYPE)
            old_value: Previous value (JSON string)
            new_value: New value (JSON string)
            status: Modification status (PENDING, SUCCESS, FAILED)
            error_message: Error message if failed
        """
        self.conn.execute("""
            INSERT INTO order_modifications (
                order_id, modification_type, old_value, new_value,
                status, error_message, modified_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            order_id, modification_type, old_value, new_value,
            status, error_message, int(time.time())
        ))
        self.conn.commit()
        
        logger.debug(f"Saved modification for order {order_id}: {modification_type}")
    
    def get_order_modifications(self, order_id: str) -> List[Dict[str, Any]]:
        """
        Get all modifications for an order.
        
        Args:
            order_id: Order ID
        
        Returns:
            List of modification records
        """
        cursor = self.conn.execute("""
            SELECT * FROM order_modifications
            WHERE order_id = ?
            ORDER BY modified_at DESC
        """, (order_id,))
        
        return [dict(row) for row in cursor.fetchall()]
    
    # =========================================================================
    # Order Event Operations
    # =========================================================================
    
    def save_order_event(self, event: OrderEvent) -> None:
        """
        Save order event.
        
        Args:
            event: OrderEvent object
        """
        self.conn.execute("""
            INSERT OR IGNORE INTO order_events (
                order_id, event_type, event_data, event_ts, sequence
            ) VALUES (?, ?, ?, ?, ?)
        """, (
            event.order_id, event.event_type, event.event_data,
            event.event_ts, event.sequence
        ))
        self.conn.commit()
        
        logger.debug(f"Saved order event: {event.event_type} for order {event.order_id}")
    
    def get_order_events(self, order_id: str) -> List[OrderEvent]:
        """
        Get all events for an order.
        
        Args:
            order_id: Order ID
        
        Returns:
            List of OrderEvent objects
        """
        cursor = self.conn.execute("""
            SELECT * FROM order_events
            WHERE order_id = ?
            ORDER BY event_ts ASC
        """, (order_id,))
        
        return [OrderEvent(**dict(row)) for row in cursor.fetchall()]
    
    # =========================================================================
    # Copy Mapping Operations
    # =========================================================================
    
    def save_copy_mapping(self, mapping: CopyMapping) -> int:
        """
        Save copy mapping.
        
        Args:
            mapping: CopyMapping object
        
        Returns:
            Mapping ID
        """
        cursor = self.conn.execute("""
            INSERT OR REPLACE INTO copy_mappings (
                leader_order_id, follower_order_id, leader_quantity, follower_quantity,
                sizing_strategy, capital_ratio, status, error_message, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            mapping.leader_order_id, mapping.follower_order_id,
            mapping.leader_quantity, mapping.follower_quantity,
            mapping.sizing_strategy, mapping.capital_ratio,
            mapping.status, mapping.error_message,
            mapping.created_at, mapping.updated_at
        ))
        self.conn.commit()
        
        mapping_id = cursor.lastrowid
        logger.debug(f"Saved copy mapping: {mapping.leader_order_id} -> {mapping.follower_order_id}")
        
        return mapping_id
    
    def get_copy_mapping_by_leader(self, leader_order_id: str) -> Optional[CopyMapping]:
        """
        Get copy mapping by leader order ID.
        
        Args:
            leader_order_id: Leader order ID
        
        Returns:
            CopyMapping object or None
        """
        cursor = self.conn.execute(
            "SELECT * FROM copy_mappings WHERE leader_order_id = ?",
            (leader_order_id,)
        )
        row = cursor.fetchone()
        
        if row:
            return CopyMapping(**dict(row))
        return None
    
    def update_copy_mapping_status(self, leader_order_id: str, status: str, 
                                   follower_order_id: Optional[str] = None,
                                   error_message: Optional[str] = None) -> None:
        """
        Update copy mapping status.
        
        Args:
            leader_order_id: Leader order ID
            status: New status
            follower_order_id: Follower order ID (optional)
            error_message: Error message if failed (optional)
        """
        if follower_order_id:
            self.conn.execute("""
                UPDATE copy_mappings
                SET status = ?, follower_order_id = ?, error_message = ?, updated_at = ?
                WHERE leader_order_id = ?
            """, (status, follower_order_id, error_message, int(time.time()), leader_order_id))
        else:
            self.conn.execute("""
                UPDATE copy_mappings
                SET status = ?, error_message = ?, updated_at = ?
                WHERE leader_order_id = ?
            """, (status, error_message, int(time.time()), leader_order_id))
        
        self.conn.commit()
        
        logger.debug(f"Updated copy mapping {leader_order_id} status to {status}")
    
    # =========================================================================
    # Trade Operations
    # =========================================================================
    
    def save_trade(self, trade: Trade) -> None:
        """
        Save a trade to database.
        
        Args:
            trade: Trade object with all fields from Trade Book API
        """
        self.conn.execute("""
            INSERT OR REPLACE INTO trades (
                id, order_id, account_type, exchange_order_id, exchange_trade_id,
                security_id, exchange_segment, trading_symbol,
                side, product, order_type,
                quantity, price, trade_value,
                trade_ts, created_at, updated_at, exchange_time,
                drv_expiry_date, drv_option_type, drv_strike_price,
                raw_data
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            trade.id, trade.order_id, trade.account_type,
            trade.exchange_order_id, trade.exchange_trade_id,
            trade.security_id, trade.exchange_segment, trade.trading_symbol,
            trade.transaction_type, trade.product_type, trade.order_type,
            trade.quantity, trade.price, trade.quantity * trade.price if trade.quantity and trade.price else None,
            trade.trade_ts, trade.created_at, trade.updated_at, trade.exchange_time,
            trade.drv_expiry_date, trade.drv_option_type, trade.drv_strike_price,
            trade.raw_data
        ))
        self.conn.commit()
        
        logger.debug(f"Saved trade: {trade.id} for order {trade.order_id}")
    
    def get_trade_by_id(self, trade_id: str) -> Optional[Trade]:
        """
        Get trade by ID.
        
        Args:
            trade_id: Trade ID
            
        Returns:
            Trade object or None
        """
        cursor = self.conn.execute("""
            SELECT * FROM trades WHERE id = ?
        """, (trade_id,))
        
        row = cursor.fetchone()
        
        if row:
            return Trade(**dict(row))
        return None
    
    def get_trades_by_order_id(self, order_id: str) -> List[Trade]:
        """
        Get all trades for an order (Trades of an Order).
        
        This method implements the database query for the "Trades of an Order" API.
        API Endpoint: GET /trades/{order-id}
        Reference: https://dhanhq.co/docs/v2/orders/#trades-of-an-order
        
        Critical for:
        - Tracking partial fills (one order → multiple trades)
        - Multi-leg orders (BO/CO where each leg has multiple trades)
        - Order execution analysis
        
        Args:
            order_id: Order ID to get trades for
            
        Returns:
            List of Trade objects ordered by trade_ts (chronological)
        """
        cursor = self.conn.execute("""
            SELECT * FROM trades 
            WHERE order_id = ? 
            ORDER BY trade_ts
        """, (order_id,))
        
        return [Trade(**dict(row)) for row in cursor.fetchall()]
    
    def get_trades(
        self,
        account_type: Optional[str] = None,
        from_ts: Optional[int] = None,
        to_ts: Optional[int] = None,
        security_id: Optional[str] = None,
        exchange_segment: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Trade]:
        """
        Get trades with optional filters.
        
        Args:
            account_type: Filter by account type ('leader' or 'follower')
            from_ts: Filter trades from this timestamp
            to_ts: Filter trades up to this timestamp
            security_id: Filter by security ID
            exchange_segment: Filter by exchange segment
            limit: Maximum number of trades to return
            
        Returns:
            List of Trade objects
        """
        conditions = []
        params = []
        
        if account_type:
            conditions.append("account_type = ?")
            params.append(account_type)
        
        if from_ts:
            conditions.append("trade_ts >= ?")
            params.append(from_ts)
        
        if to_ts:
            conditions.append("trade_ts <= ?")
            params.append(to_ts)
        
        if security_id:
            conditions.append("security_id = ?")
            params.append(security_id)
        
        if exchange_segment:
            conditions.append("exchange_segment = ?")
            params.append(exchange_segment)
        
        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        limit_clause = f"LIMIT {limit}" if limit else ""
        
        cursor = self.conn.execute(f"""
            SELECT * FROM trades 
            {where_clause}
            ORDER BY trade_ts DESC
            {limit_clause}
        """, params)
        
        return [Trade(**dict(row)) for row in cursor.fetchall()]
    
    def get_trades_summary(
        self,
        account_type: str,
        from_ts: Optional[int] = None,
        to_ts: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Get trades summary with aggregated statistics.
        
        Args:
            account_type: Account type ('leader' or 'follower')
            from_ts: From timestamp
            to_ts: To timestamp
            
        Returns:
            Dict with summary statistics
        """
        conditions = ["account_type = ?"]
        params = [account_type]
        
        if from_ts:
            conditions.append("trade_ts >= ?")
            params.append(from_ts)
        
        if to_ts:
            conditions.append("trade_ts <= ?")
            params.append(to_ts)
        
        where_clause = f"WHERE {' AND '.join(conditions)}"
        
        cursor = self.conn.execute(f"""
            SELECT 
                COUNT(*) as total_trades,
                SUM(CASE WHEN side = 'BUY' THEN quantity ELSE 0 END) as total_buy_qty,
                SUM(CASE WHEN side = 'SELL' THEN quantity ELSE 0 END) as total_sell_qty,
                SUM(trade_value) as total_value,
                AVG(price) as avg_price
            FROM trades
            {where_clause}
        """, params)
        
        row = cursor.fetchone()
        
        if row:
            return dict(row)
        
        return {
            'total_trades': 0,
            'total_buy_qty': 0,
            'total_sell_qty': 0,
            'total_value': 0,
            'avg_price': 0
        }
    
    # =========================================================================
    # Position Operations
    # =========================================================================
    
    def save_positions_snapshot(self, positions: List[Position]) -> None:
        """
        Save position snapshot.
        
        Args:
            positions: List of Position objects
        """
        for pos in positions:
            self.conn.execute("""
                INSERT OR REPLACE INTO positions (
                    snapshot_ts, account_type, security_id, exchange_segment,
                    quantity, avg_price, realized_pl, unrealized_pl, product, raw_data
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                pos.snapshot_ts, pos.account_type, pos.security_id,
                pos.exchange_segment, pos.quantity, pos.avg_price,
                pos.realized_pl, pos.unrealized_pl, pos.product, pos.raw_data
            ))
        
        self.conn.commit()
        logger.debug(f"Saved {len(positions)} positions")
    
    def get_latest_positions(self, account_type: str) -> List[Position]:
        """
        Get latest positions for an account.
        
        Args:
            account_type: 'leader' or 'follower'
        
        Returns:
            List of Position objects
        """
        cursor = self.conn.execute("""
            SELECT * FROM v_latest_positions
            WHERE account_type = ?
        """, (account_type,))
        
        return [Position(**dict(row)) for row in cursor.fetchall()]
    
    # =========================================================================
    # Funds Operations
    # =========================================================================
    
    def save_funds_snapshot(self, funds: Funds) -> None:
        """
        Save funds snapshot.
        
        Args:
            funds: Funds object
        """
        self.conn.execute("""
            INSERT OR REPLACE INTO funds (
                snapshot_ts, account_type, available_balance, collateral, margin_used, raw_data
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (
            funds.snapshot_ts, funds.account_type, funds.available_balance,
            funds.collateral, funds.margin_used, funds.raw_data
        ))
        self.conn.commit()
        
        logger.debug(f"Saved funds snapshot for {funds.account_type}")
    
    def get_latest_funds(self, account_type: str) -> Optional[Funds]:
        """
        Get latest funds for an account.
        
        Args:
            account_type: 'leader' or 'follower'
        
        Returns:
            Funds object or None
        """
        cursor = self.conn.execute("""
            SELECT * FROM v_latest_funds
            WHERE account_type = ?
        """, (account_type,))
        
        row = cursor.fetchone()
        if row:
            return Funds(**dict(row))
        return None
    
    # =========================================================================
    # Instrument Operations
    # =========================================================================
    
    def save_instrument(self, instrument: Instrument) -> None:
        """
        Save instrument metadata.
        
        Args:
            instrument: Instrument object
        """
        self.conn.execute("""
            INSERT OR REPLACE INTO instruments (
                security_id, exchange_segment, symbol, name, instrument_type,
                expiry_date, strike_price, option_type, lot_size, tick_size,
                underlying_security_id, meta, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            instrument.security_id, instrument.exchange_segment, instrument.symbol,
            instrument.name, instrument.instrument_type, instrument.expiry_date,
            instrument.strike_price, instrument.option_type, instrument.lot_size,
            instrument.tick_size, instrument.underlying_security_id, instrument.meta,
            instrument.updated_at
        ))
        self.conn.commit()
        
        logger.debug(f"Saved instrument: {instrument.symbol} ({instrument.security_id})")
    
    def get_instrument(self, security_id: str) -> Optional[Instrument]:
        """
        Get instrument by security ID.
        
        Args:
            security_id: Security ID
        
        Returns:
            Instrument object or None
        """
        cursor = self.conn.execute(
            "SELECT * FROM instruments WHERE security_id = ?",
            (security_id,)
        )
        row = cursor.fetchone()
        
        if row:
            return Instrument(**dict(row))
        return None
    
    # =========================================================================
    # Audit Operations
    # =========================================================================
    
    def log_audit(self, action: str, account_type: str, request_data: Optional[Dict] = None,
                  response_data: Optional[Dict] = None, status_code: Optional[int] = None,
                  error_message: Optional[str] = None, duration_ms: Optional[int] = None) -> None:
        """
        Log API interaction to audit trail.
        
        Args:
            action: API action name
            account_type: 'leader' or 'follower'
            request_data: Request payload (will be redacted)
            response_data: Response payload (will be redacted)
            status_code: HTTP status code
            error_message: Error message if applicable
            duration_ms: Request duration in milliseconds
        """
        request_json = json.dumps(request_data) if request_data else None
        response_json = json.dumps(response_data) if response_data else None
        
        self.conn.execute("""
            INSERT INTO audit_log (
                action, account_type, request_data, response_data,
                status_code, error_message, duration_ms, ts
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            action, account_type, request_json, response_json,
            status_code, error_message, duration_ms, int(time.time())
        ))
        self.conn.commit()
    
    # =========================================================================
    # Configuration Operations
    # =========================================================================
    
    def get_config_value(self, key: str) -> Optional[str]:
        """
        Get configuration value.
        
        Args:
            key: Configuration key
        
        Returns:
            Configuration value or None
        """
        cursor = self.conn.execute(
            "SELECT value FROM config WHERE key = ?", (key,)
        )
        row = cursor.fetchone()
        return row['value'] if row else None
    
    def set_config_value(self, key: str, value: str, description: Optional[str] = None) -> None:
        """
        Set configuration value.
        
        Args:
            key: Configuration key
            value: Configuration value
            description: Optional description
        """
        self.conn.execute("""
            INSERT OR REPLACE INTO config (key, value, description, updated_at)
            VALUES (?, ?, ?, ?)
        """, (key, value, description, int(time.time())))
        self.conn.commit()


# Global database manager instance
_db_manager: Optional[DatabaseManager] = None


def init_database() -> DatabaseManager:
    """
    Initialize database (singleton pattern).
    
    Returns:
        DatabaseManager instance
    """
    global _db_manager
    
    if _db_manager is None:
        _, _, system_config = get_config()
        _db_manager = DatabaseManager(system_config.sqlite_path)
        _db_manager.connect()
        _db_manager.initialize_schema()
    
    return _db_manager


def get_db() -> DatabaseManager:
    """
    Get database manager instance.
    
    Returns:
        DatabaseManager instance
    
    Raises:
        ValueError: If database not initialized
    """
    if _db_manager is None:
        raise ValueError("Database not initialized. Call init_database() first.")
    return _db_manager

