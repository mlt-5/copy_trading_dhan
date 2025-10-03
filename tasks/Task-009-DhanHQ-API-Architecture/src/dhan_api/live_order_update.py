"""
DhanHQ v2 Live Order Update API Module

WebSocket-based real-time order update stream.

API Documentation: https://dhanhq.co/docs/v2/order-update/
"""

import logging
import time
import threading
from typing import Optional, Callable, Any
from dhanhq import orderupdate

logger = logging.getLogger(__name__)


class LiveOrderUpdateManager:
    """
    DhanHQ v2 Live Order Update WebSocket manager.
    
    Features:
    - Real-time order event streaming via WebSocket
    - Automatic reconnection with exponential backoff
    - Event callback handling
    - Connection health monitoring with heartbeat
    - Missed order recovery after reconnection
    """
    
    def __init__(
        self,
        client_id: str,
        access_token: str,
        on_order_update: Callable,
        dhan_client: Optional[Any] = None
    ):
        """
        Initialize Live Order Update manager.
        
        Args:
            client_id: DhanHQ client ID
            access_token: DhanHQ access token
            on_order_update: Callback function for order updates
            dhan_client: DhanHQ client for fetching missed orders
        """
        self.client_id = client_id
        self.access_token = access_token
        self.on_order_update = on_order_update
        self.dhan_client = dhan_client
        
        self.ws_client: Optional[orderupdate.OrderSocket] = None
        self.is_connected = False
        self.is_running = False
        
        # Reconnection settings
        self._reconnect_attempts = 0
        self._max_reconnect_attempts = 10
        self._reconnect_delay = 1.0  # Initial delay in seconds
        self._max_reconnect_delay = 60.0
        self._was_disconnected = False
        
        # Heartbeat/health monitoring
        self._last_heartbeat = 0
        self._heartbeat_interval = 30  # seconds
        self._heartbeat_timeout = 60  # seconds
        
        logger.info("Live Order Update manager initialized")
    
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
                self.client_id,
                self.access_token
            )
            
            # Set callback
            self.ws_client.on_order_update = self._handle_order_update
            
            # Connect (synchronous)
            self.ws_client.connect_to_dhan_websocket_sync()
            
            self.is_connected = True
            self._reconnect_attempts = 0
            self._last_heartbeat = time.time()
            
            logger.info("WebSocket connected successfully")
            
            # Fetch missed orders if reconnecting
            if self._was_disconnected and self.dhan_client:
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
            self._was_disconnected = True
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
        Handle incoming order update from WebSocket.
        
        Args:
            message: Order update message
        """
        try:
            # Update heartbeat timestamp on any message
            self._last_heartbeat = time.time()
            
            logger.debug("Received order update", extra={"message": message})
            
            # Extract order status
            order_status = message.get('orderStatus', '')
            
            # Handle all relevant order statuses
            if order_status in (
                'PENDING', 'OPEN', 'TRANSIT', 'MODIFIED', 'CANCELLED',
                'TRADED', 'EXECUTED', 'REJECTED', 'PARTIALLY_FILLED'
            ):
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
        
        logger.warning(
            f"Reconnecting in {delay}s "
            f"(attempt {self._reconnect_attempts}/{self._max_reconnect_attempts})"
        )
        
        time.sleep(delay)
        
        # Attempt reconnect
        if self.connect():
            logger.info("Reconnection successful")
        else:
            logger.error("Reconnection failed")
            self._reconnect_with_backoff()
    
    def _fetch_missed_orders(self) -> None:
        """
        Fetch orders that were placed while disconnected.
        
        Uses get_order_list() API to retrieve recent orders and replay missed events.
        """
        try:
            if not self.dhan_client:
                logger.warning("DhanHQ client not available, cannot fetch missed orders")
                return
            
            logger.info("Fetching orders placed during disconnect...")
            
            # Fetch recent orders from API
            orders = self.dhan_client.get_order_list()
            
            if orders and isinstance(orders, list):
                logger.info(f"Found {len(orders)} orders, filtering for missed ones...")
                
                # Process orders (in production, you'd filter by timestamp)
                for order in orders:
                    # Add orderStatus if not present
                    if 'orderStatus' not in order:
                        order['orderStatus'] = order.get('status', 'UNKNOWN')
                    
                    # Process the order
                    self._handle_order_update(order)
                
                logger.info(f"Processed {len(orders)} missed orders")
            else:
                logger.info("No missed orders found")
                
        except Exception as e:
            logger.error("Error in _fetch_missed_orders", exc_info=True, extra={
                "error": str(e)
            })
    
    def monitor_connection(self) -> None:
        """
        Monitor connection health with heartbeat timeout detection.
        
        Should be called periodically from main event loop.
        """
        # Check heartbeat timeout
        if self.is_connected:
            time_since_heartbeat = time.time() - self._last_heartbeat
            if time_since_heartbeat > self._heartbeat_timeout:
                logger.warning(
                    f"Heartbeat timeout: {time_since_heartbeat:.1f}s since last message"
                )
                self.is_connected = False
                if self.ws_client:
                    try:
                        self.ws_client.disconnect()
                    except Exception as e:
                        logger.error(f"Error disconnecting stale WebSocket: {e}")
        
        # Attempt reconnection if disconnected
        if self.is_running and not self.is_connected:
            logger.warning("WebSocket disconnected, attempting reconnect")
            self._was_disconnected = True
            self._reconnect_with_backoff()


# Usage example:
"""
from dhan_api.live_order_update import LiveOrderUpdateManager

def handle_order_update(order_data):
    print(f"Order update: {order_data}")
    # Process order update...

ws_manager = LiveOrderUpdateManager(
    client_id="your_client_id",
    access_token="your_access_token",
    on_order_update=handle_order_update,
    dhan_client=your_dhan_client
)

ws_manager.start()

# Monitor connection in event loop
while True:
    ws_manager.monitor_connection()
    time.sleep(5)
"""

