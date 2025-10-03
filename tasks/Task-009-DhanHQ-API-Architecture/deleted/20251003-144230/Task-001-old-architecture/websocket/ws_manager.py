"""
WebSocket Manager Module

Manage real-time order update stream from leader account via DhanHQ WebSocket.
"""

import logging
import time
import threading
from typing import Optional, Callable, Any
from dhanhq import orderupdate

from ..config import get_config

logger = logging.getLogger(__name__)


class OrderStreamManager:
    """
    Manage WebSocket connection for leader order updates.
    
    Features:
    - Real-time order event streaming
    - Automatic reconnection with backoff
    - Event callback handling
    - Connection health monitoring
    """
    
    def __init__(
        self,
        leader_client_id: str,
        leader_access_token: str,
        on_order_update: Callable,
        leader_client: Optional[Any] = None  # ✅ ADDED: For fetching missed orders
    ):
        """
        Initialize WebSocket manager.
        
        Args:
            leader_client_id: Leader account client ID
            leader_access_token: Leader account access token
            on_order_update: Callback function for order updates
            leader_client: DhanHQ client for leader account (for fetching missed orders)
        """
        self.leader_client_id = leader_client_id
        self.leader_access_token = leader_access_token
        self.on_order_update = on_order_update
        self.leader_client = leader_client  # ✅ ADDED
        
        self.ws_client: Optional[orderupdate.OrderSocket] = None
        self.is_connected = False
        self.is_running = False
        
        self._reconnect_attempts = 0
        self._max_reconnect_attempts = 10
        self._reconnect_delay = 1.0  # Initial delay in seconds
        self._max_reconnect_delay = 60.0
        self._was_disconnected = False  # ✅ ADDED: Track if we were disconnected
        
        # ✅ TASK-006: Heartbeat/ping-pong for connection health
        self._last_heartbeat = 0
        self._heartbeat_interval = 30  # seconds
        self._heartbeat_timeout = 60  # seconds
        
        logger.info("WebSocket manager initialized")
    
    def connect(self) -> bool:
        """
        Connect to DhanHQ order WebSocket.
        
        Returns:
            True if connected successfully, False otherwise
        """
        try:
            logger.info("Connecting to DhanHQ order WebSocket")
            
            # Initialize WebSocket client
            self.ws_client = orderupdate.OrderSocket(
                self.leader_client_id,
                self.leader_access_token
            )
            
            # Set callback
            self.ws_client.on_order_update = self._handle_order_update
            
            # Connect (synchronous)
            self.ws_client.connect_to_dhan_websocket_sync()
            
            self.is_connected = True
            self._reconnect_attempts = 0
            
            # ✅ TASK-006: Initialize heartbeat timestamp
            self._last_heartbeat = time.time()
            
            logger.info("WebSocket connected successfully")
            
            # ✅ FIXED: Fetch missed orders if this is a reconnection
            if self._was_disconnected and self.leader_client:
                logger.info("Reconnected after disconnect, fetching missed orders...")
                try:
                    self._fetch_missed_orders()
                except Exception as e:
                    logger.error(f"Error fetching missed orders: {e}", exc_info=True)
            
            self._was_disconnected = False
            
            return True
            
        except Exception as e:
            logger.error("WebSocket connection failed", exc_info=True, extra={
                "error": str(e)
            })
            self.is_connected = False
            self._was_disconnected = True  # ✅ ADDED: Mark as disconnected
            return False
    
    def disconnect(self) -> None:
        """Disconnect from WebSocket."""
        logger.info("Disconnecting from WebSocket")
        
        self.is_running = False
        
        if self.ws_client:
            try:
                self.ws_client.disconnect()
            except Exception as e:
                logger.warning(f"Error during WebSocket disconnect: {e}")
        
        self.is_connected = False
        logger.info("WebSocket disconnected")
    
    def start(self) -> None:
        """Start WebSocket event loop in background thread."""
        if self.is_running:
            logger.warning("WebSocket already running")
            return
        
        self.is_running = True
        
        # Connect
        if not self.connect():
            logger.error("Failed to connect WebSocket")
            self.is_running = False
            return
        
        logger.info("WebSocket event loop started")
    
    def _handle_order_update(self, message: dict) -> None:
        """
        Handle incoming order update.
        
        Args:
            message: Order update message from WebSocket
        """
        try:
            # ✅ TASK-006: Update heartbeat timestamp on any message
            self._last_heartbeat = time.time()
            
            logger.debug("Received order update", extra={"message": message})
            
            # Extract order status
            order_status = message.get('orderStatus', '')
            
            # ✅ FIXED: Handle all relevant order statuses
            # New orders
            if order_status in ('PENDING', 'OPEN', 'TRANSIT'):
                self.on_order_update(message)
            # Modifications
            elif order_status == 'MODIFIED':
                self.on_order_update(message)
            # Cancellations
            elif order_status == 'CANCELLED':
                self.on_order_update(message)
            # Executions
            elif order_status in ('TRADED', 'EXECUTED'):
                self.on_order_update(message)
            # Rejections
            elif order_status == 'REJECTED':
                self.on_order_update(message)
            # Partial fills
            elif order_status == 'PARTIALLY_FILLED':
                self.on_order_update(message)
            else:
                logger.debug(f"Ignoring order update with status: {order_status}")
            
        except Exception as e:
            logger.error("Error handling order update", exc_info=True, extra={
                "error": str(e),
                "message": message
            })
    
    def _reconnect_with_backoff(self) -> None:
        """Attempt reconnection with exponential backoff."""
        if not self.is_running:
            return
        
        if self._reconnect_attempts >= self._max_reconnect_attempts:
            logger.error("Maximum reconnection attempts reached, stopping")
            self.is_running = False
            return
        
        self._reconnect_attempts += 1
        
        # Calculate backoff delay
        delay = min(
            self._reconnect_delay * (2 ** (self._reconnect_attempts - 1)),
            self._max_reconnect_delay
        )
        
        logger.warning(f"Reconnecting in {delay}s (attempt {self._reconnect_attempts}/{self._max_reconnect_attempts})")
        
        time.sleep(delay)
        
        # Attempt reconnect
        if self.connect():
            logger.info("Reconnection successful")
        else:
            logger.error("Reconnection failed")
            self._reconnect_with_backoff()
    
    def _fetch_missed_orders(self) -> None:
        """
        ✅ ADDED: Fetch orders that were placed while disconnected.
        """
        try:
            from ..database import get_db
            
            db = get_db()
            last_ts_str = db.get_config_value('last_leader_event_ts')
            
            if not last_ts_str:
                # If no last timestamp, fetch orders from last hour
                last_ts = int(time.time()) - 3600
                logger.warning("No last event timestamp, fetching orders from last hour")
            else:
                last_ts = int(last_ts_str)
            
            logger.info(f"Fetching orders placed since: {last_ts}")
            
            # Fetch recent orders from leader account
            if self.leader_client:
                try:
                    orders = self.leader_client.get_order_list()
                    
                    if orders and isinstance(orders, list):
                        # ✅ PATCH-004: Fixed field name per DhanHQ v2 Orders API
                        # API returns 'createTime' (string timestamp), not 'createdAt'
                        missed_orders = []
                        for order in orders:
                            # Get timestamp from correct field name
                            create_time_str = order.get('createTime', '')
                            if create_time_str:
                                # Convert string timestamp to epoch if needed
                                # For now, compare as-is or parse timestamp
                                # TODO: Implement proper timestamp parsing if createTime is not epoch
                                try:
                                    # Try as epoch first
                                    order_ts = int(create_time_str) if isinstance(create_time_str, (int, float)) else 0
                                except (ValueError, TypeError):
                                    order_ts = 0
                                
                                if order_ts > last_ts:
                                    missed_orders.append(order)
                        
                        if missed_orders:
                            logger.info(f"Found {len(missed_orders)} missed orders, processing...")
                            for order in missed_orders:
                                # Add orderStatus if not present
                                if 'orderStatus' not in order:
                                    order['orderStatus'] = order.get('status', 'UNKNOWN')
                                self._handle_order_update(order)
                        else:
                            logger.info("No missed orders found")
                    else:
                        logger.warning(f"Unexpected orders response: {orders}")
                        
                except Exception as e:
                    logger.error(f"Error fetching order list: {e}", exc_info=True)
            else:
                logger.warning("Leader client not available, cannot fetch missed orders")
                
        except Exception as e:
            logger.error("Error in _fetch_missed_orders", exc_info=True, extra={
                "error": str(e)
            })
    
    def monitor_connection(self) -> None:
        """
        ✅ TASK-006: Monitor connection health with heartbeat timeout detection.
        """
        # ✅ TASK-006: Check heartbeat timeout
        if self.is_connected:
            time_since_heartbeat = time.time() - self._last_heartbeat
            if time_since_heartbeat > self._heartbeat_timeout:
                logger.warning(f"Heartbeat timeout: {time_since_heartbeat:.1f}s since last message")
                self.is_connected = False
                if self.ws_client:
                    try:
                        self.ws_client.disconnect()
                    except Exception as e:
                        logger.error(f"Error disconnecting stale WebSocket: {e}")
        
        if self.is_running and not self.is_connected:
            logger.warning("WebSocket disconnected, attempting reconnect")
            self._was_disconnected = True  # ✅ ADDED
            self._reconnect_with_backoff()


# Global WebSocket manager instance
_ws_manager: Optional[OrderStreamManager] = None


def initialize_ws_manager(on_order_update: Callable, leader_client: Optional[Any] = None) -> OrderStreamManager:
    """
    Initialize WebSocket manager (singleton).
    
    Args:
        on_order_update: Callback for order updates
        leader_client: DhanHQ client for leader account (for fetching missed orders)
    
    Returns:
        OrderStreamManager instance
    """
    global _ws_manager
    
    leader_config, _, _ = get_config()
    
    _ws_manager = OrderStreamManager(
        leader_client_id=leader_config.client_id,
        leader_access_token=leader_config.access_token,
        on_order_update=on_order_update,
        leader_client=leader_client  # ✅ ADDED
    )
    
    return _ws_manager


def get_ws_manager() -> OrderStreamManager:
    """
    Get WebSocket manager instance.
    
    Returns:
        OrderStreamManager instance
    
    Raises:
        ValueError: If not initialized
    """
    if _ws_manager is None:
        raise ValueError("WebSocket manager not initialized")
    return _ws_manager


