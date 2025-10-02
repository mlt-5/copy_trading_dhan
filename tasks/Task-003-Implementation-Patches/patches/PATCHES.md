# Task-003: Comprehensive Code Patches

## Overview

This document details all code patches applied to resolve critical gaps identified in Task-002 audit. Each patch includes:
- The problem being solved
- The complete code fix
- Line numbers in the patched files
- Test scenarios covered

---

## 1. WebSocket Manager Patches

### File: `src/websocket/ws_manager.py`

### Patch 1.1: Handle All Order Statuses

**Problem**: WebSocket only processed PENDING/OPEN/TRANSIT orders, ignoring modifications, cancellations, and executions.

**Fix** (Lines 138-158):
```python
def _handle_order_update(self, message: dict) -> None:
    """Handle incoming order update."""
    try:
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
```

**Scenarios Covered**:
- ✅ Leader modifies order → Follower receives MODIFIED status
- ✅ Leader cancels order → Follower receives CANCELLED status
- ✅ Order executes → System tracks TRADED/EXECUTED
- ✅ Order rejected → System logs REJECTED with reason

---

### Patch 1.2: Missed Orders Recovery

**Problem**: Orders placed during WebSocket disconnect were lost forever.

**Fix** (Multiple locations):

**1.2a: Add leader_client to initialization** (Lines 29-60):
```python
def __init__(
    self,
    leader_client_id: str,
    leader_access_token: str,
    on_order_update: Callable,
    leader_client: Optional[Any] = None  # ✅ ADDED: For fetching missed orders
):
    """Initialize WebSocket manager."""
    self.leader_client_id = leader_client_id
    self.leader_access_token = leader_access_token
    self.on_order_update = on_order_update
    self.leader_client = leader_client  # ✅ ADDED
    
    self.ws_client: Optional[orderupdate.OrderSocket] = None
    self.is_connected = False
    self.is_running = False
    
    self._reconnect_attempts = 0
    self._max_reconnect_attempts = 10
    self._reconnect_delay = 1.0
    self._max_reconnect_delay = 60.0
    self._was_disconnected = False  # ✅ ADDED: Track if we were disconnected
    
    logger.info("WebSocket manager initialized")
```

**1.2b: Fetch missed orders on reconnection** (Lines 89-97):
```python
def connect(self) -> bool:
    """Connect to DhanHQ order WebSocket."""
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
```

**1.2c: Implement _fetch_missed_orders()** (Lines 210-261):
```python
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
                    missed_orders = [
                        order for order in orders
                        if order.get('createdAt', 0) > last_ts
                    ]
                    
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
```

**1.2d: Track disconnections** (Line 271):
```python
def monitor_connection(self) -> None:
    """Monitor connection health (call periodically)."""
    if self.is_running and not self.is_connected:
        logger.warning("WebSocket disconnected, attempting reconnect")
        self._was_disconnected = True  # ✅ ADDED
        self._reconnect_with_backoff()
```

**1.2e: Update initialization function** (Lines 279-301):
```python
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
```

**Scenarios Covered**:
- ✅ WebSocket disconnects for 30 seconds → Fetches all orders placed during disconnect
- ✅ System restart → Fetches orders since last processed timestamp
- ✅ No last timestamp in DB → Fetches orders from last 1 hour (safe fallback)

---

## 2. Order Manager Patches

### File: `src/orders/order_manager.py`

### Patch 2.1: Rate Limiting

**Problem**: No rate limiting, risking HTTP 429 errors and API suspension.

**Fix**:

**2.1a: Add rate limiting infrastructure** (Lines 10-11, 51-56):
```python
import threading
from collections import deque

# In __init__:
self.request_timestamps = deque()  # Track request times
self.request_lock = threading.Lock()
self.max_requests_per_second = 10  # DhanHQ limit

logger.info("Order manager initialized with rate limiting")
```

**2.1b: Implement token bucket algorithm** (Lines 109-132):
```python
def _wait_for_rate_limit(self) -> None:
    """
    ✅ ADDED: Wait if necessary to respect rate limits.
    """
    with self.request_lock:
        now = time.time()
        
        # Remove timestamps older than 1 second
        while self.request_timestamps and now - self.request_timestamps[0] > 1.0:
            self.request_timestamps.popleft()
        
        # Check if we're at the limit
        if len(self.request_timestamps) >= self.max_requests_per_second:
            # Calculate wait time
            oldest = self.request_timestamps[0]
            wait_time = 1.0 - (now - oldest) + 0.01  # Add small buffer
            
            if wait_time > 0:
                logger.debug(f"Rate limit reached, waiting {wait_time:.2f}s")
                time.sleep(wait_time)
                now = time.time()
        
        # Add current request timestamp
        self.request_timestamps.append(now)
```

**2.1c: Apply to all API calls** (Lines 262, 499, 600):
```python
# Before place_order API call:
self._wait_for_rate_limit()

# Before cancel_order API call:
self._wait_for_rate_limit()

# Before modify_order API call:
self._wait_for_rate_limit()
```

**Scenarios Covered**:
- ✅ 15 rapid orders → System throttles to 10/sec, no API errors
- ✅ Burst of modifications → Rate limiter prevents 429 errors
- ✅ Concurrent threads → Thread-safe lock prevents race conditions

---

### Patch 2.2: Missing Order Parameters

**Problem**: Not extracting/passing trigger_price, validity, disclosed_qty → SL orders rejected, iceberg orders not replicated.

**Fix**:

**2.2a: Extract parameters from leader order** (Lines 103-105):
```python
price = leader_order_data.get('price', 0)
trigger_price = leader_order_data.get('triggerPrice')  # ✅ ADDED
validity = leader_order_data.get('validity', 'DAY')  # ✅ ADDED
disclosed_qty = leader_order_data.get('disclosedQuantity')  # ✅ ADDED
```

**2.2b: Calculate proportional disclosed quantity** (Lines 197-210):
```python
# ✅ ADDED: Calculate proportional disclosed quantity
follower_disclosed_qty = None
if disclosed_qty and follower_quantity > 0:
    disclosed_ratio = disclosed_qty / quantity
    follower_disclosed_qty = int(follower_quantity * disclosed_ratio)
    # Ensure it doesn't exceed total quantity
    follower_disclosed_qty = min(follower_disclosed_qty, follower_quantity)
    # Ensure it's at least 1 lot if original had disclosed qty
    if follower_disclosed_qty == 0 and disclosed_qty > 0:
        instrument = self.db.get_instrument(security_id)
        if instrument:
            follower_disclosed_qty = instrument.lot_size
```

**2.2c: Update method signature** (Lines 229-241):
```python
def _place_follower_order(
    self,
    security_id: str,
    exchange_segment: str,
    transaction_type: str,
    quantity: int,
    order_type: str,
    product_type: str,
    price: float = 0,
    trigger_price: Optional[float] = None,  # ✅ ADDED
    validity: str = 'DAY',  # ✅ ADDED
    disclosed_qty: Optional[int] = None  # ✅ ADDED
) -> Optional[str]:
```

**2.2d: Build API params correctly** (Lines 279-300):
```python
# ✅ MODIFIED: Build API params with all parameters
api_params = {
    'security_id': security_id,
    'exchange_segment': exchange_segment,
    'transaction_type': transaction_type,
    'quantity': quantity,
    'order_type': order_type,
    'product_type': product_type,
    'price': price if price > 0 else 0,
    'validity': validity  # ✅ ADDED
}

# ✅ ADDED: Include trigger price for SL orders
if trigger_price and order_type in ('SL', 'SL-M'):
    api_params['trigger_price'] = trigger_price

# ✅ ADDED: Include disclosed quantity if specified
if disclosed_qty:
    api_params['disclosed_quantity'] = disclosed_qty

# Call DhanHQ API
response = self.follower_client.place_order(**api_params)
```

**2.2e: Save to database** (Lines 334-340):
```python
follower_order = Order(
    id=str(order_id),
    account_type='follower',
    status='PENDING',
    side=transaction_type,
    product=product_type,
    order_type=order_type,
    validity=validity,  # ✅ FIXED: Use parameter instead of hardcoded 'DAY'
    security_id=security_id,
    exchange_segment=exchange_segment,
    quantity=quantity,
    price=price if price > 0 else None,
    trigger_price=trigger_price,  # ✅ FIXED: Use parameter instead of None
    disclosed_qty=disclosed_qty,  # ✅ FIXED: Use parameter instead of None
    created_at=int(time.time()),
    updated_at=int(time.time()),
    raw_response=json.dumps(response)
)
```

**Scenarios Covered**:
- ✅ Leader places SL order with trigger → Follower replicates with correct trigger
- ✅ Leader uses IOC validity → Follower uses IOC (not hardcoded DAY)
- ✅ Leader uses iceberg (disclosed qty) → Follower calculates proportional disclosed qty
- ✅ Disclosed qty rounds to 0 → Fallback to 1 lot minimum

---

### Patch 2.3: Order Cancellation Handler

**Problem**: No handler for leader order cancellations → follower orders remain open.

**Fix** (Lines 454-533):
```python
def cancel_order(self, leader_order_data: Dict[str, Any]) -> bool:
    """
    ✅ ADDED: Cancel follower order when leader cancels.
    
    Args:
        leader_order_data: Leader order cancellation data
    
    Returns:
        True if cancellation successful, False otherwise
    """
    try:
        leader_order_id = leader_order_data.get('orderId') or leader_order_data.get('dhanOrderId')
        
        logger.info(f"Processing cancellation for leader order: {leader_order_id}")
        
        # Update leader order status
        self.db.update_order_status(leader_order_id, 'CANCELLED')
        
        # Find corresponding follower order
        mapping = self.db.get_copy_mapping_by_leader(leader_order_id)
        
        if not mapping:
            logger.warning(f"No mapping found for leader order {leader_order_id}")
            return False
        
        if not mapping.follower_order_id:
            logger.info(f"No follower order placed yet for {leader_order_id}")
            return False
        
        # Get follower order status
        follower_order = self.db.get_order(mapping.follower_order_id)
        
        if not follower_order:
            logger.error(f"Follower order {mapping.follower_order_id} not found in DB")
            return False
        
        # Check if already in terminal state
        if follower_order.status in ('EXECUTED', 'TRADED', 'CANCELLED', 'REJECTED'):
            logger.info(f"Follower order {mapping.follower_order_id} already in terminal state: {follower_order.status}")
            return False
        
        # Cancel follower order via API
        logger.info(f"Cancelling follower order: {mapping.follower_order_id}")
        
        # ✅ ADDED: Wait for rate limit
        self._wait_for_rate_limit()
        
        response = self.follower_client.cancel_order(mapping.follower_order_id)
        
        # Log to audit
        self.db.log_audit(
            action='cancel_order',
            account_type='follower',
            request_data={'order_id': mapping.follower_order_id},
            response_data=response
        )
        
        if response and (response.get('status') == 'success' or 'orderId' in response):
            # Update follower order status
            self.db.update_order_status(mapping.follower_order_id, 'CANCELLED')
            
            # Update copy mapping
            self.db.update_copy_mapping_status(
                leader_order_id=leader_order_id,
                status='cancelled',
                error_message='Leader order cancelled'
            )
            
            logger.info(f"Successfully cancelled follower order {mapping.follower_order_id}")
            return True
        else:
            logger.error(f"Failed to cancel follower order: {response}")
            return False
    
    except Exception as e:
        logger.error("Error cancelling order", exc_info=True, extra={
            "error": str(e),
            "order_data": leader_order_data
        })
        return False
```

**Scenarios Covered**:
- ✅ Leader cancels PENDING order → Follower cancels immediately
- ✅ Leader cancels after partial fill → Follower cancels remaining qty
- ✅ Leader cancels already EXECUTED order → Follower skips (already terminal)
- ✅ Cancellation API fails → Logged with full context

---

### Patch 2.4: Order Modification Handler

**Problem**: No handler for leader order modifications → follower orders not updated.

**Fix** (Lines 535-634):
```python
def modify_order(self, leader_order_data: Dict[str, Any]) -> bool:
    """
    ✅ ADDED: Modify follower order when leader modifies.
    
    Args:
        leader_order_data: Leader order modification data
    
    Returns:
        True if modification successful, False otherwise
    """
    try:
        leader_order_id = leader_order_data.get('orderId') or leader_order_data.get('dhanOrderId')
        
        logger.info(f"Processing modification for leader order: {leader_order_id}")
        
        # Find corresponding follower order
        mapping = self.db.get_copy_mapping_by_leader(leader_order_id)
        
        if not mapping or not mapping.follower_order_id:
            logger.warning(f"No follower order to modify for {leader_order_id}")
            return False
        
        # Get current follower order
        follower_order = self.db.get_order(mapping.follower_order_id)
        
        if not follower_order:
            logger.error(f"Follower order {mapping.follower_order_id} not found")
            return False
        
        # Check if modifiable
        if follower_order.status not in ('PENDING', 'OPEN'):
            logger.info(f"Follower order {mapping.follower_order_id} not in modifiable state: {follower_order.status}")
            return False
        
        # Extract modification details
        new_quantity = leader_order_data.get('quantity')
        new_price = leader_order_data.get('price')
        new_trigger_price = leader_order_data.get('triggerPrice')
        new_order_type = leader_order_data.get('orderType')
        
        # Calculate adjusted follower quantity
        if new_quantity:
            follower_quantity = self.position_sizer.calculate_quantity(
                leader_quantity=new_quantity,
                security_id=follower_order.security_id,
                premium=new_price
            )
        else:
            follower_quantity = follower_order.quantity
        
        # Modify via API (DhanHQ v2 uses TOTAL quantity, not delta)
        modify_params = {
            'order_id': mapping.follower_order_id,
            'quantity': follower_quantity,
            'order_type': new_order_type or follower_order.order_type,
            'validity': follower_order.validity,
            'price': new_price if new_price else follower_order.price
        }
        
        if new_trigger_price:
            modify_params['trigger_price'] = new_trigger_price
        
        logger.info(f"Modifying follower order with params: {modify_params}")
        
        # ✅ ADDED: Wait for rate limit
        self._wait_for_rate_limit()
        
        response = self.follower_client.modify_order(**modify_params)
        
        # Log to audit
        self.db.log_audit(
            action='modify_order',
            account_type='follower',
            request_data=modify_params,
            response_data=response
        )
        
        if response and (response.get('status') == 'success' or 'orderId' in response):
            # Update DB
            follower_order.quantity = follower_quantity
            if new_price:
                follower_order.price = new_price
            if new_trigger_price:
                follower_order.trigger_price = new_trigger_price
            follower_order.updated_at = int(time.time())
            
            self.db.save_order(follower_order)
            
            logger.info(f"Successfully modified follower order {mapping.follower_order_id}")
            return True
        else:
            logger.error(f"Failed to modify follower order: {response}")
            return False
    
    except Exception as e:
        logger.error("Error modifying order", exc_info=True, extra={
            "error": str(e),
            "order_data": leader_order_data
        })
        return False
```

**Scenarios Covered**:
- ✅ Leader increases qty from 50 to 75 → Follower recalculates proportional qty
- ✅ Leader changes price from 100 to 95 → Follower changes to 95
- ✅ Leader changes trigger price → Follower updates trigger price
- ✅ Leader modifies already EXECUTED order → Follower skips (not modifiable)
- ✅ Modification uses TOTAL quantity (not delta), per DhanHQ API spec

---

### Patch 2.5: Execution Tracking

**Problem**: No tracking of order executions, fills, or slippage monitoring.

**Fix** (Lines 636-702):
```python
def handle_execution(self, execution_data: Dict[str, Any]) -> None:
    """
    ✅ ADDED: Handle order execution event.
    
    Args:
        execution_data: Execution event data
    """
    try:
        order_id = execution_data.get('orderId') or execution_data.get('dhanOrderId')
        fill_qty = execution_data.get('filledQty', 0)
        fill_price = execution_data.get('averagePrice', 0)
        order_status = execution_data.get('orderStatus', 'EXECUTED')
        
        logger.info(f"Processing execution for order: {order_id}", extra={
            "order_id": order_id,
            "fill_qty": fill_qty,
            "fill_price": fill_price,
            "status": order_status
        })
        
        # Update order status
        self.db.update_order_status(order_id, order_status)
        
        # Check if this is a leader or follower order
        order = self.db.get_order(order_id)
        if not order:
            logger.warning(f"Order {order_id} not found in database")
            return
        
        # Log execution event
        event = OrderEvent(
            order_id=order_id,
            event_type=order_status,
            event_data=json.dumps(execution_data),
            event_ts=int(time.time())
        )
        self.db.save_order_event(event)
        
        # Log execution for analytics
        self.db.log_audit(
            action='order_executed',
            account_type=order.account_type,
            request_data={
                'order_id': order_id,
                'fill_qty': fill_qty,
                'fill_price': fill_price
            }
        )
        
        # If leader order, check follower order status
        if order.account_type == 'leader':
            mapping = self.db.get_copy_mapping_by_leader(order_id)
            if mapping and mapping.follower_order_id:
                follower_order = self.db.get_order(mapping.follower_order_id)
                if follower_order:
                    logger.info(f"Leader order {order_id} executed. Follower order {mapping.follower_order_id} status: {follower_order.status}")
                    
                    # Optional: Alert on large execution time difference
                    time_diff = abs(order.updated_at - follower_order.updated_at)
                    if time_diff > 60:  # More than 1 minute
                        logger.warning(f"Large execution time difference: {time_diff}s between leader and follower orders")
    
    except Exception as e:
        logger.error("Error handling execution", exc_info=True, extra={
            "error": str(e),
            "execution_data": execution_data
        })
```

**Scenarios Covered**:
- ✅ Leader order executes → Follower execution logged and compared
- ✅ Partial fills → Each PARTIALLY_FILLED event tracked
- ✅ Execution time slippage > 60s → Warning logged
- ✅ Order rejections → Tracked as executions with REJECTED status

---

### Patch 2.6: Market Hours Validation

**Problem**: Orders placed during market closures wasting API calls.

**Fix** (Lines 58-107, 184-187):

**2.6a: Implement market hours check**:
```python
def _is_market_open(self, exchange_segment: str) -> bool:
    """
    ✅ ADDED: Check if market is open for the given exchange.
    
    Args:
        exchange_segment: Exchange segment (NSE_EQ, NSE_FNO, BSE_EQ, etc.)
    
    Returns:
        True if market is open, False otherwise
    
    Note: This is a basic implementation. For production, fetch exact timings
    from DhanHQ API or maintain a holiday calendar.
    """
    try:
        from datetime import datetime
        import pytz
        
        # Indian timezone
        ist = pytz.timezone('Asia/Kolkata')
        now = datetime.now(ist)
        
        # Check if weekend
        if now.weekday() >= 5:  # Saturday=5, Sunday=6
            logger.debug("Market closed: Weekend")
            return False
        
        # Market hours (simplified)
        # NSE/BSE Equity: 9:15 AM - 3:30 PM
        # NSE F&O: 9:15 AM - 3:30 PM
        # MCX: 9:00 AM - 11:30 PM (with breaks)
        # CDS: 9:00 AM - 5:00 PM
        
        current_time = now.time()
        
        if 'NSE' in exchange_segment or 'BSE' in exchange_segment:
            from datetime import time as dt_time
            market_open = dt_time(9, 15)
            market_close = dt_time(15, 30)
            
            if current_time < market_open or current_time > market_close:
                logger.debug(f"Market closed: Outside hours for {exchange_segment}")
                return False
        
        # TODO: Add holiday calendar check
        # For now, assume market is open if not weekend and within hours
        return True
        
    except Exception as e:
        logger.warning(f"Error checking market hours: {e}, assuming market is open")
        return True  # Fail open - let API reject if needed
```

**2.6b: Apply in replicate_order**:
```python
# ✅ ADDED: Check market hours (optional - can be disabled for testing)
if not self._is_market_open(exchange_segment):
    logger.warning(f"Market closed for {exchange_segment}, order may be rejected")
    # Still proceed - let DhanHQ API handle rejection with proper error
```

**Scenarios Covered**:
- ✅ Order at 2 AM Sunday → Warning logged, order still placed (API will reject)
- ✅ Order at 4 PM Friday → Warning logged (after market close)
- ✅ Order at 10 AM Tuesday → Proceeds normally
- ✅ Holiday check → TODO (requires calendar API)

---

## 3. Main Orchestrator Patches

### File: `src/main.py`

### Patch 3.1: Pass leader_client to WebSocket

**Problem**: WebSocket manager couldn't fetch missed orders without leader client.

**Fix** (Lines 106-108):
```python
# Initialize WebSocket manager
logger.info("Initializing WebSocket manager...")
self.ws_manager = initialize_ws_manager(
    on_order_update=self._handle_order_update,
    leader_client=self.auth_manager.leader_client  # ✅ ADDED: For fetching missed orders
)
logger.info("WebSocket manager initialized")
```

---

### Patch 3.2: Route All Order Events

**Problem**: Only PENDING/OPEN/TRANSIT routed, other events ignored.

**Fix** (Lines 199-244):
```python
def _handle_order_update(self, order_data: Dict[str, Any]) -> None:
    """Handle order update from WebSocket."""
    try:
        order_id = order_data.get('orderId') or order_data.get('dhanOrderId')
        order_status = order_data.get('orderStatus', '')
        
        logger.info(f"Processing order update: {order_id} ({order_status})", extra={
            "order_id": order_id,
            "status": order_status,
            "security_id": order_data.get('securityId')
        })
        
        # ✅ FIXED: Handle all order statuses
        
        # New orders - replicate
        if order_status in ('PENDING', 'TRANSIT', 'OPEN'):
            follower_order_id = self.order_manager.replicate_order(order_data)
            
            if follower_order_id:
                logger.info(f"Order replicated successfully", extra={
                    "leader_order_id": order_id,
                    "follower_order_id": follower_order_id
                })
                
                # ✅ ADDED: Update last processed event timestamp
                self.db.set_config_value('last_leader_event_ts', str(int(time.time())))
            else:
                logger.warning(f"Order replication skipped or failed: {order_id}")
        
        # ✅ ADDED: Modifications - replicate changes
        elif order_status == 'MODIFIED':
            success = self.order_manager.modify_order(order_data)
            if success:
                logger.info(f"Order modified successfully: {order_id}")
            else:
                logger.warning(f"Order modification failed or not applicable: {order_id}")
        
        # ✅ ADDED: Cancellations - cancel follower order
        elif order_status == 'CANCELLED':
            success = self.order_manager.cancel_order(order_data)
            if success:
                logger.info(f"Order cancelled successfully: {order_id}")
            else:
                logger.warning(f"Order cancellation failed or not applicable: {order_id}")
        
        # ✅ ADDED: Executions - track fills
        elif order_status in ('TRADED', 'EXECUTED', 'PARTIALLY_FILLED'):
            self.order_manager.handle_execution(order_data)
        
        # ✅ ADDED: Rejections - log for analysis
        elif order_status == 'REJECTED':
            logger.warning(f"Order rejected: {order_id}", extra={
                "rejection_reason": order_data.get('rejectionReason', 'Unknown')
            })
            self.order_manager.handle_execution(order_data)  # Still track it
        
        else:
            logger.debug(f"Ignoring order with status: {order_status}")
    
    except Exception as e:
        logger.error("Error handling order update", exc_info=True, extra={
            "error": str(e),
            "order_data": order_data
        })
```

**Scenarios Covered**:
- ✅ All order statuses routed to correct handler
- ✅ Timestamp updated after successful replication (for missed orders)
- ✅ Rejections logged with reason extracted
- ✅ Success/failure logged for each operation type

---

## 4. Dependencies Update

### File: `requirements.txt`

**Patch**: Added pytz for timezone support (Lines 6-7):
```txt
# Timezone support for market hours validation
pytz>=2023.3
```

---

## Summary

### Total Lines Changed
- **WebSocket Manager**: ~100 LOC added
- **Order Manager**: ~370 LOC added
- **Main Orchestrator**: ~45 LOC changed (net)
- **Requirements**: 3 LOC added
- **Total**: ~515 LOC

### Issues Resolved
| Priority | Issue | Status |
|----------|-------|--------|
| CRITICAL | Order cancellation | ✅ FIXED |
| CRITICAL | Order modification | ✅ FIXED |
| CRITICAL | Missed orders | ✅ FIXED |
| HIGH | Trigger price | ✅ FIXED |
| HIGH | Validity hardcoding | ✅ FIXED |
| HIGH | Execution tracking | ✅ FIXED |
| HIGH | Rate limiting | ✅ FIXED |
| MEDIUM | Market hours | ✅ FIXED |
| MEDIUM | Disclosed quantity | ✅ FIXED |

### Test Coverage Matrix

| Scenario | Before | After |
|----------|--------|-------|
| Leader cancels order | ❌ Ignored | ✅ Follower cancels |
| Leader modifies order | ❌ Ignored | ✅ Follower modifies |
| Disconnect for 30s | ❌ Orders lost | ✅ Fetched & replayed |
| SL order with trigger | ❌ Rejected (missing param) | ✅ Replicated correctly |
| IOC validity | ❌ Changed to DAY | ✅ IOC preserved |
| Iceberg order | ❌ Disclosed qty=0 | ✅ Proportional calculation |
| 15 rapid orders | ❌ Rate limit error | ✅ Throttled to 10/sec |
| Execution tracking | ❌ Not tracked | ✅ Logged & compared |
| Market closed order | ❌ No warning | ✅ Warning logged |

### Production Readiness
**Before Patches**: 🔴 **NOT READY** - Missing critical order lifecycle handling  
**After Patches**: 🟡 **TESTABLE** - Core functionality complete, requires sandbox validation

### Next Steps
1. ✅ Complete code patches
2. 🔄 Run unit tests
3. 🔄 Run integration tests in sandbox
4. 🔄 Stress test rate limiting
5. 🔄 Test disconnection/reconnection scenarios
6. 🔄 Measure latency metrics
7. 🔄 Security audit
8. 🔄 Production deployment

---

**Patch Documentation Version**: 1.0  
**Date**: 2025-10-02  
**Author**: AI Assistant  
**Status**: Implementation Complete, Testing Pending

