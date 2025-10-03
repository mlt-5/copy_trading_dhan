# Critical Issues - Detailed Breakdown with Code Fixes

## Issue #4 & #15: Critical Typo - `availablBalance` → `availableBalance`

**File**: `src/position_sizing/position_sizer.py`  
**Line**: 118  
**Severity**: 🔴 **CRITICAL - PRODUCTION BLOCKER**

### Current Broken Code
```python
def _parse_funds_response(self, funds_data: dict, account_type: str) -> Funds:
    import json
    
    # Extract available balance (field names may vary, check docs)
    available = funds_data.get('availablBalance', 0.0)  # ❌ TYPO: Missing 'e'
    if available == 0.0:
        available = funds_data.get('available_balance', 0.0)
```

### Why This Is Critical
- **ALL position sizing calculations use this value**
- Due to typo, `available` is ALWAYS 0.0 for primary field
- Falls back to `available_balance` which may also be wrong
- Results in:
  - Capital ratio = 0 (follower balance / leader balance)
  - All calculated quantities = 0
  - Orders fail or are never placed
  - System appears to work but does nothing

### Actual Impact Analysis
```python
# Scenario: Leader has ₹100,000, Follower has ₹50,000
# DhanHQ API returns:
{
    'availableBalance': 50000.0,  # ← Correct field name
    # NO 'availablBalance' field exists
}

# Current code gets:
available = funds_data.get('availablBalance', 0.0)  # Returns 0.0 (default)
available = funds_data.get('available_balance', 0.0)  # Also returns 0.0

# Result:
follower_funds.available_balance = 0.0  # ← WRONG!

# Position sizing calculation:
ratio = 50000.0 / 100000.0  # Should be 0.5
ratio = 0.0 / 100000.0  # Actually 0.0

# Order quantity:
follower_qty = leader_qty * 0.0 = 0  # ← NO ORDERS PLACED!
```

### Correct Fix
```python
def _parse_funds_response(self, funds_data: dict, account_type: str) -> Funds:
    import json
    
    # ✅ FIXED: Correct field name per DhanHQ v2 API docs
    available = funds_data.get('availableBalance', 0.0)
    
    # Try alternative field names as fallback
    if available == 0.0:
        # Check snake_case variant
        available = funds_data.get('available_balance', 0.0)
    
    # Still 0? Log warning and check raw response
    if available == 0.0:
        logger.warning(f"Could not extract balance for {account_type}", extra={
            'funds_keys': list(funds_data.keys()),
            'raw_response': json.dumps(funds_data)
        })
    
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
```

### Verification Test
```python
def test_funds_parsing():
    # Test with real DhanHQ v2 response format
    api_response = {
        'availableBalance': 50000.0,
        'collateralAmount': 10000.0,
        'utilizedAmount': 15000.0
    }
    
    sizer = PositionSizer(...)
    funds = sizer._parse_funds_response(api_response, 'follower')
    
    assert funds.available_balance == 50000.0, "Failed to parse balance!"
    assert funds.collateral == 10000.0
    assert funds.margin_used == 15000.0
```

### Recommended Action
1. ✅ Fix typo immediately
2. ✅ Add unit test with real API response format
3. ✅ Verify exact field names from DhanHQ v2 docs
4. ✅ Add fallback logic for alternative field names
5. ✅ Add logging when balance extraction fails

---

## Issue #6: Bracket Order Leg Tracking NOT Implemented

**File**: `src/orders/order_manager.py`  
**Location**: After Line 451  
**Severity**: 🔴 **CRITICAL - FEATURE BROKEN**

### The Problem
Task-006 audit claimed: "✅ BO leg tracking fully implemented"

**Reality**: 
- Database method `save_bracket_order_leg()` exists
- Method is **NEVER CALLED** anywhere in the code
- BO legs are never saved after order placement
- OCO logic cannot work without leg tracking

### Current Code (Broken)
```python
def _place_follower_order(self, ...):
    # ... place order via API ...
    
    # Line 418-419:
    if response and 'orderId' in response:
        order_id = response['orderId']
        
        # Save follower order
        follower_order = Order(
            id=str(order_id),
            # ... fields ...
        )
        self.db.save_order(follower_order)  # ← Only saves main order
        
        # ❌ MISSING: No call to save BO legs!
        # ❌ BUG: BO parameters exist but legs never tracked
        
        # Log order event
        event = OrderEvent(...)
        self.db.save_order_event(event)
        
        return str(order_id)
```

### What Should Happen
Per DhanHQ v2 API docs, Bracket Order response includes:
```json
{
    "orderId": "12345",           // Parent BO order ID
    "status": "success",
    "data": {
        "entryOrderId": "12346",   // Entry leg order ID
        "targetOrderId": "12347",  // Target leg order ID  
        "stopLossOrderId": "12348" // Stop-loss leg order ID
    }
}
```

### Required Fix
```python
def _place_follower_order(
    self,
    # ... existing params ...
    bo_profit_value: Optional[float] = None,
    bo_stop_loss_value: Optional[float] = None,
    bo_order_type: Optional[str] = None
) -> Optional[str]:
    try:
        # ... existing API call ...
        
        response = self.follower_client.place_order(**api_params)
        
        if response and 'orderId' in response:
            order_id = response['orderId']
            
            # Save main order
            follower_order = Order(...)
            self.db.save_order(follower_order)
            
            # ✅ NEW: Save BO legs if this is a bracket order
            if bo_profit_value is not None or bo_stop_loss_value is not None:
                self._save_bracket_order_legs(
                    parent_order_id=str(order_id),
                    response=response,
                    quantity=quantity,
                    price=price,
                    trigger_price=trigger_price
                )
            
            return str(order_id)
```

### New Method to Add
```python
def _save_bracket_order_legs(
    self,
    parent_order_id: str,
    response: dict,
    quantity: int,
    price: float,
    trigger_price: Optional[float]
) -> None:
    """
    Save bracket order legs to database for tracking and OCO logic.
    
    Args:
        parent_order_id: Parent BO order ID
        response: API response containing leg order IDs
        quantity: Order quantity
        price: Entry price
        trigger_price: Stop-loss trigger price
    """
    try:
        # Extract leg order IDs from response
        # NOTE: Verify exact response structure from DhanHQ v2 docs
        data = response.get('data', {})
        
        entry_leg_id = data.get('entryOrderId') or response.get('entryOrderId')
        target_leg_id = data.get('targetOrderId') or response.get('targetOrderId')
        sl_leg_id = data.get('stopLossOrderId') or response.get('stopLossOrderId')
        
        current_time = int(time.time())
        
        # Save entry leg
        if entry_leg_id:
            self.db.save_bracket_order_leg({
                'parent_order_id': parent_order_id,
                'leg_type': 'entry',
                'leg_order_id': str(entry_leg_id),  # ← Correct field name
                'status': 'PENDING',
                'quantity': quantity,
                'price': price,
                'trigger_price': None,
                'created_at': current_time,
                'updated_at': current_time
            })
            logger.info(f"Saved BO entry leg: {entry_leg_id}")
        
        # Save target leg
        if target_leg_id:
            self.db.save_bracket_order_leg({
                'parent_order_id': parent_order_id,
                'leg_type': 'target',
                'leg_order_id': str(target_leg_id),
                'status': 'PENDING',
                'quantity': quantity,
                'price': None,  # Target price set by BO
                'trigger_price': None,
                'created_at': current_time,
                'updated_at': current_time
            })
            logger.info(f"Saved BO target leg: {target_leg_id}")
        
        # Save stop-loss leg
        if sl_leg_id:
            self.db.save_bracket_order_leg({
                'parent_order_id': parent_order_id,
                'leg_type': 'stop_loss',
                'leg_order_id': str(sl_leg_id),
                'status': 'PENDING',
                'quantity': quantity,
                'price': None,
                'trigger_price': trigger_price,
                'created_at': current_time,
                'updated_at': current_time
            })
            logger.info(f"Saved BO SL leg: {sl_leg_id}")
        
        # Verify legs were saved
        saved_legs = self.db.get_bracket_order_legs(parent_order_id)
        if len(saved_legs) != 3:
            logger.error(f"Expected 3 BO legs, saved {len(saved_legs)}", extra={
                'parent_order_id': parent_order_id,
                'response': response
            })
    
    except Exception as e:
        logger.error("Failed to save BO legs", exc_info=True, extra={
            'parent_order_id': parent_order_id,
            'error': str(e)
        })
```

### Verification Test
```python
def test_bo_leg_tracking():
    # Place a BO order
    order_data = {
        'orderId': 'BO123',
        'securityId': '1333',
        'exchangeSegment': 'NSE_FO',
        'transactionType': 'BUY',
        'quantity': 50,
        'orderType': 'MARKET',
        'productType': 'INTRADAY',
        'boProfitValue': 10.0,
        'boStopLossValue': 5.0,
        'boOrderType': 'MARKET'
    }
    
    follower_order_id = order_manager.replicate_order(order_data)
    
    # Verify legs were saved
    legs = db.get_bracket_order_legs(follower_order_id)
    
    assert len(legs) == 3, f"Expected 3 BO legs, got {len(legs)}"
    
    leg_types = [leg['leg_type'] for leg in legs]
    assert 'entry' in leg_types
    assert 'target' in leg_types
    assert 'stop_loss' in leg_types
    
    print("✅ BO leg tracking works!")
```

---

## Issue #7 & #17: Database Schema Field Name Mismatch

**Files**: 
- `src/database/database.py` Line 153-165
- `src/database/schema_v2_co_bo.sql` Line 28

**Severity**: 🔴 **CRITICAL - DATA CORRUPTION RISK**

### The Problem
Schema defines column as `leg_order_id`, code inserts as `order_id`

### Schema Definition (Correct)
```sql
-- schema_v2_co_bo.sql Line 24-37
CREATE TABLE IF NOT EXISTS bracket_order_legs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    parent_order_id TEXT NOT NULL,
    leg_order_id TEXT NOT NULL,  -- ✅ Correct column name
    leg_type TEXT NOT NULL,
    account_type TEXT NOT NULL,
    status TEXT DEFAULT 'PENDING',
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL,
    
    UNIQUE(parent_order_id, leg_order_id, account_type),
    CHECK (account_type IN ('leader', 'follower')),
    CHECK (leg_type IN ('ENTRY', 'TARGET', 'SL'))
);
```

### Python Code (Wrong)
```python
# database.py Line 150-165
def save_bracket_order_leg(self, leg_data: Dict[str, Any]) -> bool:
    try:
        self.conn.execute('''
            INSERT OR REPLACE INTO bracket_order_legs (
                parent_order_id, leg_type, order_id, status,  -- ❌ Wrong: order_id
                quantity, price, trigger_price, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            leg_data.get('parent_order_id'),
            leg_data.get('leg_type'),
            leg_data.get('order_id'),  -- ❌ Wrong key name
            # ... rest
        ))
```

### Impact
- SQL INSERT will fail with "no such column: order_id"
- OR if SQL succeeds, will insert NULL (data loss)
- BO leg tracking completely broken at database level

### Required Fix
```python
def save_bracket_order_leg(self, leg_data: Dict[str, Any]) -> bool:
    """
    ✅ FIXED: Save bracket order leg to tracking table.
    
    Args:
        leg_data: Dictionary with:
            - parent_order_id: Parent BO order ID
            - leg_type: 'entry', 'target', 'stop_loss'
            - leg_order_id: Individual leg order ID (FIXED field name)
            - status: Order status
            - quantity, price, trigger_price: Order params
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
            leg_data.get('leg_order_id'),  # ✅ Fixed: correct field name
            leg_data.get('status', 'PENDING'),
            leg_data.get('quantity', 0),
            leg_data.get('price', 0),
            leg_data.get('trigger_price', 0),
            leg_data.get('created_at', int(time.time())),
            leg_data.get('updated_at', int(time.time()))
        ))
        self.conn.commit()
        
        logger.debug(f"BO leg saved: parent={leg_data.get('parent_order_id')}, "
                    f"leg={leg_data.get('leg_type')}, "
                    f"id={leg_data.get('leg_order_id')}")
        return True
        
    except sqlite3.Error as e:
        logger.error(f"Database error saving BO leg: {e}", extra={
            'leg_data': leg_data
        })
        return False
    except Exception as e:
        logger.error(f"Error saving BO leg: {e}", exc_info=True)
        return False
```

### Also Fix Return Data
```python
def get_bracket_order_legs(self, parent_order_id: str) -> List[Dict[str, Any]]:
    """
    ✅ FIXED: Retrieve all legs for a bracket order.
    """
    try:
        cursor = self.conn.execute('''
            SELECT 
                id,
                parent_order_id,
                leg_type,
                leg_order_id,  -- ✅ Fixed: correct column name
                status,
                quantity,
                price,
                trigger_price,
                created_at,
                updated_at
            FROM bracket_order_legs 
            WHERE parent_order_id = ?
            ORDER BY leg_type
        ''', (parent_order_id,))
        
        legs = []
        for row in cursor.fetchall():
            legs.append({
                'id': row[0],
                'parent_order_id': row[1],
                'leg_type': row[2],
                'leg_order_id': row[3],  # ✅ Fixed: correct key name
                'status': row[4],
                'quantity': row[5],
                'price': row[6],
                'trigger_price': row[7],
                'created_at': row[8],
                'updated_at': row[9]
            })
        
        return legs
        
    except Exception as e:
        logger.error(f"Error fetching BO legs: {e}", exc_info=True)
        return []
```

---

## Issue #10: OCO Logic Cannot Execute

**File**: `src/orders/order_manager.py`  
**Location**: Lines 855-899  
**Severity**: 🔴 **CRITICAL - FEATURE BROKEN**

### The Problem
OCO logic expects `legType` field in WebSocket execution data, but DhanHQ v2 API **does NOT provide this field**.

### Current Broken Code
```python
def _handle_bracket_order_oco(self, parent_order_id: str, execution_data: Dict[str, Any]) -> None:
    """
    ✅ TASK-006: Implement One-Cancels-Other (OCO) logic for Bracket Orders.
    When one leg (target or stop-loss) executes, automatically cancel the other.
    """
    legs = self.db.get_bracket_order_legs(parent_order_id)
    
    if not legs:
        logger.debug(f"No BO legs found for order {parent_order_id}")
        return
    
    # ❌ BROKEN: This field does not exist in DhanHQ WebSocket updates
    executed_leg_type = execution_data.get('legType')  # Always None!
    
    if not executed_leg_type:
        logger.warning(f"No leg type in execution data for BO {parent_order_id}, skipping OCO")
        return  # ← ALWAYS RETURNS HERE, OCO NEVER EXECUTES!
    
    # This code is NEVER reached
    logger.info(f"BO {parent_order_id}: {executed_leg_type} leg executed, cancelling other leg")
    # ...
```

### What Actually Happens
```python
# WebSocket order update for BO leg execution:
{
    'orderId': '12347',  # ← Leg order ID (not parent ID)
    'dhanOrderId': '12347',
    'orderStatus': 'EXECUTED',
    'quantity': 50,
    'averagePrice': 105.5,
    # ❌ NO 'legType' field exists!
}

# Code tries:
executed_leg_type = execution_data.get('legType')  # Returns None
if not executed_leg_type:
    return  # Exits immediately, OCO never happens
```

### Impact
- BO orders have **NO OCO protection**
- Both target AND stop-loss can execute
- Double capital exposure, potential for large losses
- Defeats the entire purpose of bracket orders

### Required Fix
```python
def _handle_bracket_order_oco(self, parent_order_id: str, execution_data: Dict[str, Any]) -> None:
    """
    ✅ FIXED: Implement OCO logic by matching order ID with stored legs.
    """
    try:
        legs = self.db.get_bracket_order_legs(parent_order_id)
        
        if not legs:
            logger.debug(f"No BO legs found for order {parent_order_id}")
            return
        
        # ✅ NEW LOGIC: Get executed order ID from WebSocket
        executed_order_id = execution_data.get('orderId') or execution_data.get('dhanOrderId')
        
        if not executed_order_id:
            logger.warning(f"No order ID in execution data for BO {parent_order_id}")
            return
        
        # ✅ Find which leg was executed by matching order ID
        executed_leg_type = None
        executed_leg_id = None
        
        for leg in legs:
            if str(leg['leg_order_id']) == str(executed_order_id):
                executed_leg_type = leg['leg_type']
                executed_leg_id = leg['id']
                break
        
        if not executed_leg_type:
            logger.debug(f"Executed order {executed_order_id} is not a BO leg of {parent_order_id}")
            return
        
        logger.info(f"BO {parent_order_id}: {executed_leg_type} leg {executed_order_id} executed, triggering OCO")
        
        # Update executed leg status
        self.db.update_bracket_order_leg_status(executed_leg_id, 'EXECUTED')
        
        # Determine opposite leg type
        if executed_leg_type == 'target':
            opposite_leg_type = 'stop_loss'
        elif executed_leg_type == 'stop_loss':
            opposite_leg_type = 'target'
        else:
            # Entry leg executed - don't cancel anything
            logger.debug(f"Entry leg executed, no OCO action needed")
            return
        
        # Cancel opposite leg
        for leg in legs:
            if (leg['leg_type'] == opposite_leg_type and 
                leg['status'] not in ('EXECUTED', 'TRADED', 'CANCELLED', 'REJECTED')):
                
                opposite_order_id = leg['leg_order_id']
                logger.info(f"OCO: Cancelling {opposite_leg_type} leg {opposite_order_id}")
                
                try:
                    self._wait_for_rate_limit()
                    
                    cancel_response = self.follower_client.cancel_order(opposite_order_id)
                    
                    if cancel_response and (cancel_response.get('status') == 'success' or 'orderId' in cancel_response):
                        self.db.update_bracket_order_leg_status(leg['id'], 'CANCELLED')
                        logger.info(f"OCO: Successfully cancelled {opposite_leg_type} leg {opposite_order_id}")
                    else:
                        logger.error(f"OCO: Failed to cancel {opposite_leg_type} leg: {cancel_response}")
                
                except Exception as e:
                    logger.error(f"OCO: Exception cancelling {opposite_leg_type} leg {opposite_order_id}: {e}")
        
    except Exception as e:
        logger.error(f"Error in BO OCO logic: {e}", exc_info=True, extra={
            'parent_order_id': parent_order_id,
            'execution_data': execution_data
        })
```

### Integration with handle_execution
```python
def handle_execution(self, execution_data: Dict[str, Any]) -> None:
    """
    ✅ FIXED: Handle order execution event with proper BO detection.
    """
    try:
        order_id = execution_data.get('orderId') or execution_data.get('dhanOrderId')
        
        # ... existing logging ...
        
        # ✅ Check if this order is part of a BO
        # Query database to find if this order_id is a BO leg
        legs = []
        cursor = self.db.conn.execute('''
            SELECT parent_order_id FROM bracket_order_legs
            WHERE leg_order_id = ?
        ''', (order_id,))
        
        row = cursor.fetchone()
        if row:
            parent_order_id = row[0]
            logger.info(f"Order {order_id} is a BO leg of parent {parent_order_id}, triggering OCO")
            self._handle_bracket_order_oco(parent_order_id, execution_data)
        
        # ... rest of existing logic ...
        
    except Exception as e:
        logger.error("Error handling execution", exc_info=True)
```

---

## Summary of Critical Fixes

| Issue | File | Line | Fix Complexity | Impact if Not Fixed |
|-------|------|------|----------------|---------------------|
| #4/#15 | position_sizer.py | 118 | ⭐ Easy (1 char) | System doesn't place orders |
| #6 | order_manager.py | After 451 | ⭐⭐⭐ Medium (50 LOC) | BO tracking broken |
| #7/#17 | database.py | 153-165 | ⭐ Easy (3 chars) | Data corruption |
| #10 | order_manager.py | 855-899 | ⭐⭐⭐ Medium (60 LOC) | OCO doesn't work |

**Total Estimated Fix Time**: 4-6 hours for critical issues

---

**Recommendation**: Fix all 4 critical issues in one focused session, then comprehensive testing.


