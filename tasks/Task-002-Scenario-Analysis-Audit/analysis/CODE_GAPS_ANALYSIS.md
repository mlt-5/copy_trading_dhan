# Code Gaps Analysis & Fix Recommendations

## Document Purpose

This document provides detailed code-level analysis of gaps identified in the comprehensive scenario audit, with specific recommendations for fixes.

---

## Gap Category 1: Order Cancellation (CRITICAL 🔴)

### Current State
```python
# File: src/websocket/ws_manager.py, Line 139-143
if order_status in ('PENDING', 'OPEN', 'TRANSIT'):
    self.on_order_update(message)
else:
    logger.debug(f"Ignoring order update with status: {order_status}")
    # ❌ CANCELLED status is completely ignored
```

### Problem
- Follower orders remain active even after leader cancels
- Creates unwanted positions and financial risk
- No mapping between leader cancellation and follower orders

### Recommended Fix

#### Step 1: Add CANCELLED status handling to WebSocket manager

```python
# File: src/websocket/ws_manager.py, Line 139-150
def _handle_order_update(self, message: dict) -> None:
    """Handle incoming order update."""
    try:
        logger.debug("Received order update", extra={"message": message})
        
        order_status = message.get('orderStatus', '')
        
        # Handle new orders
        if order_status in ('PENDING', 'OPEN', 'TRANSIT'):
            self.on_order_update(message)
        
        # ✅ ADD: Handle order cancellations
        elif order_status == 'CANCELLED':
            self.on_order_update(message)  # Pass to main handler
        
        # ✅ ADD: Handle order modifications
        elif order_status == 'MODIFIED':
            self.on_order_update(message)
        
        # ✅ ADD: Handle order executions
        elif order_status in ('TRADED', 'EXECUTED'):
            self.on_order_update(message)
        
        else:
            logger.debug(f"Ignoring order update with status: {order_status}")
            
    except Exception as e:
        logger.error("Error handling order update", exc_info=True, extra={
            "error": str(e),
            "message": message
        })
```

#### Step 2: Add cancel_order method to OrderManager

```python
# File: src/orders/order_manager.py - ADD NEW METHOD

def cancel_order(self, leader_order_data: Dict[str, Any]) -> bool:
    """
    Cancel follower order when leader cancels.
    
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
        
        response = self.follower_client.cancel_order(mapping.follower_order_id)
        
        # Log to audit
        self.db.log_audit(
            action='cancel_order',
            account_type='follower',
            request_data={'order_id': mapping.follower_order_id},
            response_data=response
        )
        
        if response and response.get('status') == 'success':
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

#### Step 3: Update main orchestrator to handle cancellations

```python
# File: src/main.py, Line 179-217 - MODIFY _handle_order_update

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
        
        # Handle new orders
        if order_status in ('PENDING', 'TRANSIT', 'OPEN'):
            follower_order_id = self.order_manager.replicate_order(order_data)
            
            if follower_order_id:
                logger.info(f"Order replicated successfully", extra={
                    "leader_order_id": order_id,
                    "follower_order_id": follower_order_id
                })
            else:
                logger.warning(f"Order replication skipped or failed: {order_id}")
        
        # ✅ ADD: Handle cancellations
        elif order_status == 'CANCELLED':
            success = self.order_manager.cancel_order(order_data)
            if success:
                logger.info(f"Order cancelled successfully: {order_id}")
            else:
                logger.warning(f"Order cancellation failed or not applicable: {order_id}")
        
        # ✅ ADD: Handle modifications
        elif order_status == 'MODIFIED':
            success = self.order_manager.modify_order(order_data)
            if success:
                logger.info(f"Order modified successfully: {order_id}")
            else:
                logger.warning(f"Order modification failed or not applicable: {order_id}")
        
        # ✅ ADD: Handle executions
        elif order_status in ('TRADED', 'EXECUTED'):
            self.order_manager.handle_execution(order_data)
        
        else:
            logger.debug(f"Ignoring order with status: {order_status}")
            
    except Exception as e:
        logger.error("Error handling order update", exc_info=True, extra={
            "error": str(e),
            "order_data": order_data
        })
```

### Testing Checklist
- [ ] Leader cancels pending order → Follower order cancelled
- [ ] Leader cancels partially filled order → Follower remaining qty cancelled
- [ ] Cancel request for non-existent follower order → Graceful handling
- [ ] Cancel request for already-executed order → No error
- [ ] Multiple rapid cancellations → No duplicate cancel requests

---

## Gap Category 2: Order Modification (CRITICAL 🔴)

### Current State
- No modification handling at all
- Follower orders don't reflect leader's changes

### Recommended Fix

```python
# File: src/orders/order_manager.py - ADD NEW METHOD

def modify_order(self, leader_order_data: Dict[str, Any]) -> bool:
    """
    Modify follower order when leader modifies.
    
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
        
        # Modify via API
        # Note: DhanHQ v2 modify_order uses TOTAL quantity, not delta
        modify_params = {
            'order_id': mapping.follower_order_id,
            'quantity': follower_quantity,  # Total quantity
            'order_type': new_order_type or follower_order.order_type,
            'validity': follower_order.validity,
            'price': new_price if new_price else follower_order.price
        }
        
        if new_trigger_price:
            modify_params['trigger_price'] = new_trigger_price
        
        logger.info(f"Modifying follower order with params: {modify_params}")
        
        response = self.follower_client.modify_order(**modify_params)
        
        # Log to audit
        self.db.log_audit(
            action='modify_order',
            account_type='follower',
            request_data=modify_params,
            response_data=response
        )
        
        if response and response.get('status') == 'success':
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

---

## Gap Category 3: Missing Order Parameters (HIGH 🔴)

### Gap 3.1: Trigger Price for SL Orders

**Current Code**:
```python
# File: src/orders/order_manager.py, Line 70
price = leader_order_data.get('price', 0)
# ❌ trigger_price extracted but never used

# Line 178-187
def _place_follower_order(
    self,
    security_id: str,
    exchange_segment: str,
    transaction_type: str,
    quantity: int,
    order_type: str,
    product_type: str,
    price: float = 0  # ❌ No trigger_price parameter
) -> Optional[str]:
```

**Fix**:
```python
# File: src/orders/order_manager.py

# Line 70 - Extract trigger price
price = leader_order_data.get('price', 0)
trigger_price = leader_order_data.get('triggerPrice')  # ✅ KEEP extraction

# Line 137-145 - Pass trigger price
follower_order_id = self._place_follower_order(
    security_id=security_id,
    exchange_segment=exchange_segment,
    transaction_type=transaction_type,
    quantity=follower_quantity,
    order_type=order_type,
    product_type=product_type,
    price=price,
    trigger_price=trigger_price  # ✅ ADD parameter
)

# Line 178-190 - Add trigger_price parameter
def _place_follower_order(
    self,
    security_id: str,
    exchange_segment: str,
    transaction_type: str,
    quantity: int,
    order_type: str,
    product_type: str,
    price: float = 0,
    trigger_price: Optional[float] = None  # ✅ ADD parameter
) -> Optional[str]:
    """Place order in follower account."""
    try:
        start_time = time.time()
        
        logger.info("Placing follower order", extra={
            "security_id": security_id,
            "exchange": exchange_segment,
            "side": transaction_type,
            "quantity": quantity,
            "order_type": order_type,
            "product": product_type,
            "price": price,
            "trigger_price": trigger_price  # ✅ ADD to log
        })
        
        # Build API params
        api_params = {
            'security_id': security_id,
            'exchange_segment': exchange_segment,
            'transaction_type': transaction_type,
            'quantity': quantity,
            'order_type': order_type,
            'product_type': product_type,
            'price': price if price > 0 else 0
        }
        
        # ✅ ADD: Include trigger price for SL orders
        if trigger_price and order_type in ('SL', 'SL-M'):
            api_params['trigger_price'] = trigger_price
        
        # Call DhanHQ API
        response = self.follower_client.place_order(**api_params)
        
        # ... rest of the method
```

### Gap 3.2: Order Validity (Hardcoded to DAY)

**Current Code**:
```python
# File: src/orders/order_manager.py, Line 258
validity='DAY',  # ❌ HARDCODED
```

**Fix**:
```python
# File: src/orders/order_manager.py

# Line 71 - Extract validity
validity = leader_order_data.get('validity', 'DAY')  # ✅ ADD extraction

# Line 137-146 - Pass validity
follower_order_id = self._place_follower_order(
    security_id=security_id,
    exchange_segment=exchange_segment,
    transaction_type=transaction_type,
    quantity=follower_quantity,
    order_type=order_type,
    product_type=product_type,
    price=price,
    trigger_price=trigger_price,
    validity=validity  # ✅ ADD parameter
)

# Line 178-192 - Add validity parameter
def _place_follower_order(
    self,
    security_id: str,
    exchange_segment: str,
    transaction_type: str,
    quantity: int,
    order_type: str,
    product_type: str,
    price: float = 0,
    trigger_price: Optional[float] = None,
    validity: str = 'DAY'  # ✅ ADD parameter with default
) -> Optional[str]:
    """Place order in follower account."""
    # ... existing code ...
    
    # Use validity in API call and when saving order
    response = self.follower_client.place_order(
        security_id=security_id,
        exchange_segment=exchange_segment,
        transaction_type=transaction_type,
        quantity=quantity,
        order_type=order_type,
        product_type=product_type,
        price=price if price > 0 else 0,
        validity=validity  # ✅ ADD to API call
    )
    
    # ... when creating follower_order object ...
    follower_order = Order(
        id=str(order_id),
        account_type='follower',
        status='PENDING',
        side=transaction_type,
        product=product_type,
        order_type=order_type,
        validity=validity,  # ✅ Use parameter instead of hardcoded 'DAY'
        # ... rest of fields ...
    )
```

### Gap 3.3: Disclosed Quantity

**Fix**:
```python
# File: src/orders/order_manager.py

# Line 72 - Extract disclosed quantity
disclosed_qty = leader_order_data.get('disclosedQuantity')

# Calculate proportional disclosed quantity
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
else:
    follower_disclosed_qty = None

# Pass to _place_follower_order
follower_order_id = self._place_follower_order(
    # ... other params ...
    disclosed_qty=follower_disclosed_qty  # ✅ ADD
)

# Add to _place_follower_order signature and API call
def _place_follower_order(
    self,
    # ... other params ...
    disclosed_qty: Optional[int] = None  # ✅ ADD
) -> Optional[str]:
    
    api_params = {
        # ... other params ...
    }
    
    if disclosed_qty:
        api_params['disclosed_quantity'] = disclosed_qty
    
    response = self.follower_client.place_order(**api_params)
```

---

## Gap Category 4: Execution Tracking (HIGH 🔴)

### Recommended Fix

```python
# File: src/orders/order_manager.py - ADD NEW METHOD

def handle_execution(self, execution_data: Dict[str, Any]) -> None:
    """
    Handle order execution event.
    
    Args:
        execution_data: Execution event data
    """
    try:
        order_id = execution_data.get('orderId') or execution_data.get('dhanOrderId')
        fill_qty = execution_data.get('filledQty', 0)
        fill_price = execution_data.get('averagePrice', 0)
        
        logger.info(f"Processing execution for order: {order_id}", extra={
            "order_id": order_id,
            "fill_qty": fill_qty,
            "fill_price": fill_price
        })
        
        # Update order status
        self.db.update_order_status(order_id, 'EXECUTED')
        
        # Check if this is a leader or follower order
        order = self.db.get_order(order_id)
        if not order:
            logger.warning(f"Order {order_id} not found in database")
            return
        
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

---

## Gap Category 5: Rate Limiting (HIGH 🔴)

### Recommended Fix

```python
# File: src/orders/order_manager.py - ADD at class level

from collections import deque
import threading

class OrderManager:
    def __init__(
        self,
        follower_client: dhanhq,
        db: DatabaseManager,
        position_sizer: PositionSizer
    ):
        self.follower_client = follower_client
        self.db = db
        self.position_sizer = position_sizer
        
        # ✅ ADD: Rate limiting
        self.request_timestamps = deque()  # Track request times
        self.request_lock = threading.Lock()
        self.max_requests_per_second = 10  # DhanHQ limit
        self.min_request_interval = 0.1  # 100ms between requests
        
        logger.info("Order manager initialized")
    
    def _wait_for_rate_limit(self) -> None:
        """Wait if necessary to respect rate limits."""
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
    
    def _place_follower_order(
        self,
        # ... parameters ...
    ) -> Optional[str]:
        """Place order in follower account."""
        try:
            # ✅ ADD: Wait for rate limit
            self._wait_for_rate_limit()
            
            start_time = time.time()
            
            # ... existing code ...
```

---

## Gap Category 6: Missed Orders During Disconnect (CRITICAL 🔴)

### Recommended Fix

```python
# File: src/websocket/ws_manager.py - ADD NEW METHOD

def fetch_missed_orders(self) -> List[Dict[str, Any]]:
    """
    Fetch orders that were placed while disconnected.
    
    Returns:
        List of order events
    """
    try:
        # Get last processed order timestamp from DB
        from ..database import get_db
        db = get_db()
        last_ts = db.get_config_value('last_leader_event_ts')
        
        if not last_ts:
            logger.warning("No last event timestamp found, fetching recent orders")
            last_ts = str(int(time.time()) - 3600)  # Last hour
        
        logger.info(f"Fetching orders since timestamp: {last_ts}")
        
        # This requires leader_client access - need to pass it in
        # For now, return empty list and log warning
        logger.warning("fetch_missed_orders not fully implemented - requires API access")
        return []
    
    except Exception as e:
        logger.error("Error fetching missed orders", exc_info=True, extra={
            "error": str(e)
        })
        return []

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
        
        # ✅ ADD: Fetch missed orders after reconnection
        if self._reconnect_attempts > 0:
            logger.info("Reconnected, fetching missed orders...")
            missed_orders = self.fetch_missed_orders()
            
            if missed_orders:
                logger.info(f"Found {len(missed_orders)} missed orders, processing...")
                for order in missed_orders:
                    self._handle_order_update(order)
        
        return True
        
    except Exception as e:
        logger.error("WebSocket connection failed", exc_info=True, extra={
            "error": str(e)
        })
        self.is_connected = False
        return False
```

---

## Summary of Required Code Changes

| File | Method/Area | Change Type | Priority | LOC |
|------|-------------|-------------|----------|-----|
| `src/websocket/ws_manager.py` | `_handle_order_update` | Modify | 🔴 Critical | ~20 |
| `src/orders/order_manager.py` | `cancel_order` | Add | 🔴 Critical | ~80 |
| `src/orders/order_manager.py` | `modify_order` | Add | 🔴 Critical | ~100 |
| `src/orders/order_manager.py` | `handle_execution` | Add | 🔴 High | ~50 |
| `src/orders/order_manager.py` | `_place_follower_order` | Modify | 🔴 High | ~30 |
| `src/orders/order_manager.py` | `replicate_order` | Modify | 🔴 High | ~20 |
| `src/orders/order_manager.py` | Rate limiting | Add | 🔴 High | ~40 |
| `src/main.py` | `_handle_order_update` | Modify | 🔴 Critical | ~30 |
| `src/websocket/ws_manager.py` | `fetch_missed_orders` | Add | 🔴 Critical | ~40 |
| **TOTAL** | | | | **~410 LOC** |

---

## Implementation Plan

### Phase 1: Critical Fixes (Week 1)
1. ✅ Add order cancellation handling
2. ✅ Add order modification handling
3. ✅ Fix trigger price for SL orders
4. ✅ Fix validity hardcoding
5. ✅ Add rate limiting

### Phase 2: High Priority (Week 2)
6. ✅ Add execution tracking
7. ✅ Add missed orders recovery
8. ✅ Add disclosed quantity handling
9. ✅ Add market hours validation
10. ✅ Add better error categorization

### Phase 3: Medium Priority (Week 3)
11. ✅ Add position reconciliation
12. ✅ Add slippage tracking
13. ✅ Add multi-leg strategy handling
14. ✅ Add circuit breaker detection
15. ✅ Add comprehensive testing

---

**Next**: See [RECOMMENDATIONS.md](RECOMMENDATIONS.md) for architecture improvements and long-term enhancements.

