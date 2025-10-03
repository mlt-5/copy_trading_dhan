# Fix Checklist - Task-007 Findings

## P0 - Critical Production Blockers (MUST FIX IMMEDIATELY)

### ☐ Issue #4 & #15: Fix `availablBalance` Typo
**File**: `src/position_sizing/position_sizer.py`  
**Line**: 118  
**Estimated Time**: 1 minute  
**Complexity**: ⭐ Trivial

**Action**:
```python
# Change Line 118 from:
available = funds_data.get('availablBalance', 0.0)

# To:
available = funds_data.get('availableBalance', 0.0)
```

**Verification**:
- [ ] Run unit test with real API response
- [ ] Verify balance is correctly extracted (not 0.0)
- [ ] Test capital ratio calculation
- [ ] Verify orders have non-zero quantity

---

### ☐ Issue #7 & #17: Fix Database Field Name Mismatch
**File**: `src/database/database.py`  
**Lines**: 153-165, 192-206  
**Estimated Time**: 5 minutes  
**Complexity**: ⭐ Trivial

**Actions**:
1. **Fix INSERT statement (Line 153-157)**:
```python
# Change from:
INSERT OR REPLACE INTO bracket_order_legs (
    parent_order_id, leg_type, order_id, status, ...

# To:
INSERT OR REPLACE INTO bracket_order_legs (
    parent_order_id, leg_type, leg_order_id, status, ...
```

2. **Fix parameter binding (Line 156)**:
```python
# Change from:
leg_data.get('order_id'),

# To:
leg_data.get('leg_order_id'),
```

3. **Fix return dict keys (Line 191-203)**:
```python
# Change all instances of:
'order_id': row[3],

# To:
'leg_order_id': row[3],
```

**Verification**:
- [ ] Run SQL INSERT test
- [ ] Verify no SQL errors
- [ ] Check data is correctly stored
- [ ] Test retrieval returns correct field names

---

### ☐ Issue #6: Implement BO Leg Tracking
**File**: `src/orders/order_manager.py`  
**Location**: After Line 451  
**Estimated Time**: 2-3 hours  
**Complexity**: ⭐⭐⭐ Medium

**Actions**:

1. **Add helper method** (add after line 476):
```python
def _save_bracket_order_legs(
    self,
    parent_order_id: str,
    response: dict,
    quantity: int,
    price: float,
    trigger_price: Optional[float]
) -> None:
    """Save BO legs to database for tracking."""
    # Implementation per CRITICAL_ISSUES_DETAILED.md
```

2. **Call helper in _place_follower_order** (after line 451):
```python
# After saving main order:
if bo_profit_value is not None or bo_stop_loss_value is not None:
    self._save_bracket_order_legs(
        parent_order_id=str(order_id),
        response=response,
        quantity=quantity,
        price=price,
        trigger_price=trigger_price
    )
```

3. **Verify DhanHQ API response structure**:
- [ ] Check actual API response for BO order placement
- [ ] Identify field names for leg order IDs
- [ ] Update code to match actual response structure

**Verification**:
- [ ] Place test BO order in sandbox
- [ ] Verify 3 legs saved to database
- [ ] Check leg_type values are correct ('entry', 'target', 'stop_loss')
- [ ] Verify leg_order_id fields populated
- [ ] Test retrieval with get_bracket_order_legs()

---

### ☐ Issue #10: Rewrite OCO Logic
**File**: `src/orders/order_manager.py`  
**Lines**: 855-899  
**Estimated Time**: 2-3 hours  
**Complexity**: ⭐⭐⭐ Medium

**Actions**:

1. **Replace _handle_bracket_order_oco method** (lines 855-899):
```python
def _handle_bracket_order_oco(self, parent_order_id: str, execution_data: Dict[str, Any]) -> None:
    """
    ✅ FIXED: Detect executed leg by matching order ID, then cancel opposite leg.
    """
    # Implementation per CRITICAL_ISSUES_DETAILED.md Issue #10
```

2. **Update handle_execution to detect BO legs** (around line 810):
```python
# Add database query to find if executed order is a BO leg:
cursor = self.db.conn.execute('''
    SELECT parent_order_id FROM bracket_order_legs
    WHERE leg_order_id = ?
''', (order_id,))

row = cursor.fetchone()
if row:
    parent_order_id = row[0]
    self._handle_bracket_order_oco(parent_order_id, execution_data)
```

**Verification**:
- [ ] Place BO order with target + SL
- [ ] Simulate target execution via WebSocket
- [ ] Verify SL leg is cancelled automatically
- [ ] Simulate SL execution
- [ ] Verify target leg is cancelled automatically
- [ ] Check database status updates correctly
- [ ] Verify rate limiting applied to cancellation

---

### ☐ Issue #12: Verify WebSocket Field Names
**File**: `src/websocket/ws_manager.py`  
**Lines**: 246-249  
**Estimated Time**: 30 minutes  
**Complexity**: ⭐⭐ Easy

**Actions**:

1. **Test actual API response structure**:
- [ ] Connect to DhanHQ WebSocket
- [ ] Capture actual order update message
- [ ] Document field names (createdAt vs created_at vs createTime)

2. **Update field name** (line 248):
```python
# Current:
if order.get('createdAt', 0) > last_ts

# Update based on actual API field name:
if order.get('[ACTUAL_FIELD_NAME]', 0) > last_ts
```

3. **Add fallback for multiple field names**:
```python
order_time = (
    order.get('createdAt', 0) or
    order.get('created_at', 0) or
    order.get('createTime', 0) or
    order.get('timestamp', 0)
)
if order_time > last_ts:
    # Process order
```

**Verification**:
- [ ] Disconnect WebSocket
- [ ] Place order while disconnected
- [ ] Reconnect
- [ ] Verify missed order is fetched
- [ ] Check order is replicated

---

## P1 - High Priority (Fix Within 1 Week)

### ☐ Issue #1: Implement Typed Error Handling
**Files**: `src/auth/auth.py`, `src/orders/order_manager.py`, `src/websocket/ws_manager.py`  
**Estimated Time**: 4 hours  
**Complexity**: ⭐⭐⭐ Medium

**Actions**:
1. [ ] Create typed error classes (if not exists in `src/errors/__init__.py`)
2. [ ] Map DhanHQ error codes to exception types
3. [ ] Add retry logic for transient errors (ConnectionError, TimeoutError, 5xx)
4. [ ] Replace generic `except Exception` with specific error types
5. [ ] Add exponential backoff with jitter

**Files to update**:
- [ ] `src/auth/auth.py` Lines 73-78, 114-119
- [ ] `src/orders/order_manager.py` Line 394-395
- [ ] `src/websocket/ws_manager.py` Error handling

---

### ☐ Issue #2: Add API Response Validation
**File**: `src/auth/auth.py`  
**Lines**: 62-65, 103-106  
**Estimated Time**: 2 hours  
**Complexity**: ⭐⭐ Easy

**Actions**:
1. [ ] Validate response is dict before accessing keys
2. [ ] Check for required fields per DhanHQ API schema
3. [ ] Sanitize error messages (don't log full response)
4. [ ] Add structured error codes

---

### ☐ Issue #5: Enforce Market Hours Check
**File**: `src/orders/order_manager.py`  
**Lines**: 191-195  
**Estimated Time**: 1 hour  
**Complexity**: ⭐⭐ Easy

**Actions**:
1. [ ] Change warning to error
2. [ ] Return None instead of proceeding
3. [ ] Create failed copy mapping with error message
4. [ ] Add holiday calendar integration (optional)

---

### ☐ Issue #8: Add Correlation ID Generation
**File**: `src/orders/order_manager.py`  
**Throughout file**  
**Estimated Time**: 2 hours  
**Complexity**: ⭐⭐ Easy

**Actions**:
1. [ ] Generate UUID-based correlation IDs
2. [ ] Pass to API if supported (verify in DhanHQ docs)
3. [ ] Store in database
4. [ ] Add to all log messages for tracing

---

### ☐ Issue #9: Add Retry Logic for Order Placement
**File**: `src/orders/order_manager.py`  
**Line**: 394-395  
**Estimated Time**: 1 hour  
**Complexity**: ⭐⭐ Easy

**Actions**:
1. [ ] Wrap place_order in retry loop (max 3 attempts)
2. [ ] Catch ConnectionError, TimeoutError
3. [ ] Exponential backoff: 1s, 2s, 4s
4. [ ] Add jitter: random 0-500ms
5. [ ] Log retry attempts

---

### ☐ Issue #13: Fix Heartbeat Validation Logic
**File**: `src/websocket/ws_manager.py`  
**Lines**: 156-157  
**Estimated Time**: 30 minutes  
**Complexity**: ⭐ Trivial

**Actions**:
1. [ ] Validate message before updating heartbeat
2. [ ] Check for 'orderStatus' field
3. [ ] Don't update heartbeat for invalid/error messages

---

### ☐ Issue #14: Implement WebSocket Ping/Pong
**File**: `src/websocket/ws_manager.py`  
**Throughout file**  
**Estimated Time**: 2 hours  
**Complexity**: ⭐⭐⭐ Medium

**Actions**:
1. [ ] Check if dhanhq SDK supports ping()
2. [ ] Create background ping thread
3. [ ] Send ping every 30 seconds
4. [ ] Handle pong responses
5. [ ] Verify with dhanhq SDK documentation

---

### ☐ Issue #16: Add Follower Balance Validation
**File**: `src/position_sizing/position_sizer.py`  
**Lines**: 147-153  
**Estimated Time**: 15 minutes  
**Complexity**: ⭐ Trivial

**Actions**:
1. [ ] Check if follower_funds.available_balance == 0
2. [ ] Return 0.0 if follower has no funds
3. [ ] Log warning
4. [ ] Prevent division by zero

---

## P2 - Medium Priority (Fix Within 2 Weeks)

### ☐ Issue #3: Configure HTTP Timeout
**File**: `src/auth/auth.py`  
**Lines**: 56-59, 97-100  
**Estimated Time**: 30 minutes  
**Complexity**: ⭐ Trivial

**Actions**:
1. [ ] Check if dhanhq SDK accepts timeout parameter
2. [ ] Pass timeout from system_config
3. [ ] Document in SDK initialization

---

### ☐ Issue #11: Complete Disclosed Quantity Logic
**File**: `src/orders/order_manager.py`  
**Lines**: 215-216  
**Estimated Time**: 10 minutes  
**Complexity**: ⭐ Trivial

**Actions**:
1. [ ] Use fetched instrument
2. [ ] Set follower_disclosed_qty = instrument.lot_size
3. [ ] Add fallback if instrument not found

---

### ☐ Issue #18: Create Safe Migration Script
**File**: `src/database/schema_v2_co_bo.sql`  
**Entire file**  
**Estimated Time**: 2 hours  
**Complexity**: ⭐⭐ Easy

**Actions**:
1. [ ] Add column existence checks
2. [ ] Use ALTER TABLE ... ADD COLUMN IF NOT EXISTS (SQLite 3.35+)
3. [ ] OR create Python migration function
4. [ ] Add rollback mechanism
5. [ ] Test on fresh database
6. [ ] Test on existing database

---

## Testing Requirements

### Unit Tests
- [ ] Test funds parsing with real API response formats
- [ ] Test BO leg saving with mock API response
- [ ] Test OCO logic with different execution scenarios
- [ ] Test field name validation
- [ ] Test retry logic with mock failures
- [ ] Test error mapping

### Integration Tests (Sandbox)
- [ ] Place regular order → verify replication
- [ ] Place BO order → verify all legs tracked
- [ ] Simulate target execution → verify SL cancelled
- [ ] Simulate SL execution → verify target cancelled
- [ ] Disconnect WebSocket → place order → reconnect → verify missed order fetched
- [ ] Test with insufficient funds
- [ ] Test during market closed hours

### Regression Tests
- [ ] All Task-003 scenarios still pass
- [ ] CO orders work correctly
- [ ] BO orders work correctly
- [ ] Order modifications work
- [ ] Order cancellations work

---

## Documentation Updates

- [ ] Update ARCHITECTURE.md with actual implementation details
- [ ] Update QUICKSTART.md with correct setup steps
- [ ] Create KNOWN_ISSUES.md for any unfixed issues
- [ ] Update env.example with all required variables
- [ ] Document DhanHQ API response structures
- [ ] Add troubleshooting guide

---

## Final Verification

### Pre-Production Checklist
- [ ] All P0 issues fixed and tested
- [ ] All P1 issues fixed or documented
- [ ] Unit test coverage >80%
- [ ] Integration tests pass in sandbox
- [ ] Load test with 100+ orders
- [ ] Stress test reconnection scenarios
- [ ] Manual BO/CO testing
- [ ] Code review by second person
- [ ] Documentation updated
- [ ] Deployment runbook created

### Production Readiness Criteria
- [ ] No critical bugs remaining
- [ ] Test coverage adequate
- [ ] Error handling robust
- [ ] Monitoring in place
- [ ] Rollback plan documented
- [ ] Team trained on system
- [ ] Capital limits configured safely
- [ ] Emergency stop mechanism tested

---

## Progress Tracking

**P0 - Critical**: 0 / 5 complete (0%)  
**P1 - High**: 0 / 8 complete (0%)  
**P2 - Medium**: 0 / 3 complete (0%)  
**Testing**: 0 / 15 complete (0%)  
**Documentation**: 0 / 6 complete (0%)

**Overall Progress**: 0 / 37 items (0%)

---

**Last Updated**: October 3, 2025  
**Target Completion**: October 17-24, 2025 (2-3 weeks)

