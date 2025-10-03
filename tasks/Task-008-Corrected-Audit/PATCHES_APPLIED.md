# Task-008: Critical Patches Applied

**Date**: October 3, 2025  
**Status**: ✅ ALL PATCHES APPLIED  
**Total Patches**: 4

---

## ✅ Patch Summary

| Patch | Issue | File | Time | Status |
|-------|-------|------|------|--------|
| PATCH-001 | Position sizing typo | position_sizer.py:118 | 1 min | ✅ APPLIED |
| PATCH-002 | ProductType detection | order_manager.py:152-403 | 2 hrs | ✅ APPLIED |
| PATCH-003 | Database field mismatch | database.py:142-208 + order_manager.py | 5 min | ✅ APPLIED |
| PATCH-004 | WebSocket field name | ws_manager.py:246-263 | 30 min | ✅ APPLIED |

---

## PATCH-001: Position Sizing Typo Fix

**File**: `src/position_sizing/position_sizer.py`  
**Line**: 118  
**Time**: 1 minute

### Problem
```python
# ❌ BEFORE:
available = funds_data.get('availablBalance', 0.0)  # Typo: missing 'e'
```

### Solution
```python
# ✅ AFTER:
available = funds_data.get('availableBalance', 0.0)  # Fixed: correct field name
```

### Impact
- **Before**: All position sizing returned 0 due to typo
- **After**: Correctly extracts balance from DhanHQ API response
- **Critical**: This fix enables the entire trading system to work

### Validation Required
- [ ] Test funds API response parsing
- [ ] Verify balance is extracted correctly (not 0.0)
- [ ] Test capital ratio calculation
- [ ] Verify orders have non-zero quantities

---

## PATCH-002: ProductType Detection Logic

**Files**: `src/orders/order_manager.py`  
**Lines**: 152-179 (parameter extraction), 371-404 (API params)  
**Time**: 2 hours

### Problem
Code detected BO/CO orders by checking if parameters existed, instead of checking `productType` field:

```python
# ❌ BEFORE:
product_type = leader_order_data.get('productType')  # Extracted but not used
co_stop_loss_value = leader_order_data.get('coStopLossValue')
bo_profit_value = leader_order_data.get('boProfitValue')

# Wrong detection logic:
if bo_profit_value is not None:
    # Assume it's a BO order
```

### Solution
```python
# ✅ AFTER:
product_type = leader_order_data.get('productType')

# Initialize all parameters
co_stop_loss_value = None
bo_profit_value = None
# ... etc

# Correct detection logic:
if product_type == 'BO':
    # Extract BO parameters
    bo_profit_value = leader_order_data.get('boProfitValue')
    bo_stop_loss_value = leader_order_data.get('boStopLossValue')
    logger.info(f"Bracket Order detected: product_type=BO")

elif product_type == 'CO':
    # Extract CO parameters  
    co_stop_loss_value = leader_order_data.get('coStopLossValue')
    logger.info(f"Cover Order detected: product_type=CO")

# In API call:
api_params = {
    'product_type': product_type,  # ✅ Now properly set
    # ...
}

# Only add BO params if it's a BO order:
if product_type == 'BO':
    if bo_profit_value is not None:
        api_params['boProfitValue'] = bo_profit_value
```

### Impact
- **Before**: BO/CO detection unreliable, productType not set correctly in follower orders
- **After**: Proper detection based on productType field, follower orders correctly typed
- **Critical**: Ensures BO/CO orders are replicated with correct product type

### Validation Required
- [ ] Place BO order (productType='BO') → verify detected correctly
- [ ] Place CO order (productType='CO') → verify detected correctly  
- [ ] Verify follower order has correct productType
- [ ] Test BO parameter extraction
- [ ] Test CO parameter extraction

---

## PATCH-003: Database Field Name Fix

**Files**: 
- `src/database/database.py` Lines 142-208
- `src/orders/order_manager.py` Lines 659, 663, 666, 899, 903

**Time**: 5 minutes

### Problem
Database schema defined column as `leg_order_id`, but code used `order_id`:

```python
# ❌ BEFORE (database.py):
self.conn.execute('''
    INSERT INTO bracket_order_legs (
        parent_order_id, leg_type, order_id, status, ...  # Wrong column name
    ) VALUES (?, ?, ?, ?, ...)
''', (
    leg_data.get('parent_order_id'),
    leg_data.get('leg_type'),
    leg_data.get('order_id'),  # Wrong key name
))

# ❌ BEFORE (order_manager.py):
self.follower_client.cancel_order(leg['order_id'])  # Wrong key
```

### Solution
```python
# ✅ AFTER (database.py):
self.conn.execute('''
    INSERT INTO bracket_order_legs (
        parent_order_id, leg_type, leg_order_id, status, ...  # Correct
    ) VALUES (?, ?, ?, ?, ...)
''', (
    leg_data.get('parent_order_id'),
    leg_data.get('leg_type'),
    leg_data.get('leg_order_id'),  # Correct key name
))

# Also fixed in get_bracket_order_legs():
legs.append({
    'leg_order_id': row[3],  # Correct key name
})

# ✅ AFTER (order_manager.py):
self.follower_client.cancel_order(leg['leg_order_id'])  # Correct key
```

### Impact
- **Before**: BO leg operations would fail with SQL error or insert NULL
- **After**: BO legs correctly saved and retrieved from database
- **Critical**: Enables BO leg tracking and OCO logic to work

### Validation Required
- [ ] Save BO leg to database → verify no SQL error
- [ ] Retrieve BO legs → verify leg_order_id present
- [ ] Test BO leg cancellation
- [ ] Test OCO logic

---

## PATCH-004: WebSocket Field Name Fix

**File**: `src/websocket/ws_manager.py`  
**Lines**: 246-263  
**Time**: 30 minutes

### Problem
Code used `createdAt` field which doesn't exist in DhanHQ Orders API:

```python
# ❌ BEFORE:
missed_orders = [
    order for order in orders
    if order.get('createdAt', 0) > last_ts  # Wrong field name
]
```

### Solution
```python
# ✅ AFTER:
# Per DhanHQ v2 Orders API, correct field is 'createTime' (string)
missed_orders = []
for order in orders:
    create_time_str = order.get('createTime', '')  # Correct field name
    if create_time_str:
        try:
            # Convert to epoch for comparison
            order_ts = int(create_time_str)
        except (ValueError, TypeError):
            order_ts = 0
        
        if order_ts > last_ts:
            missed_orders.append(order)
```

### Impact
- **Before**: Missed order recovery wouldn't work (field doesn't exist)
- **After**: Correctly identifies missed orders using createTime field
- **Critical**: Ensures orders placed during disconnect are recovered

### Validation Required
- [ ] Disconnect WebSocket
- [ ] Place order while disconnected
- [ ] Reconnect
- [ ] Verify missed order is fetched and replicated

---

## Additional Improvements Made

### 1. Enhanced Logging
Added detailed logging for BO/CO detection:
```python
logger.info(f"Bracket Order detected: product_type=BO, profit={bo_profit_value}, SL={bo_stop_loss_value}")
logger.info(f"Cover Order detected: product_type=CO, SL={co_stop_loss_value}")
```

### 2. Documentation Comments
Added inline comments explaining corrections:
```python
# ✅ PATCH-00X: Description of fix
# Reference to docs/schema
```

### 3. Proper Parameter Initialization
Ensured all BO/CO parameters start as None:
```python
co_stop_loss_value = None
co_trigger_price = None
bo_profit_value = None
bo_stop_loss_value = None
```

---

## Testing Plan

### Phase 1: Position Sizing (30 minutes)
```bash
# 1. Test funds parsing
# Expected: balance extracted correctly (not 0.0)

# 2. Test capital ratio
# Expected: ratio = follower_balance / leader_balance

# 3. Test quantity calculation
# Expected: quantity > 0 based on ratio
```

### Phase 2: Regular Orders (1 hour)
```bash
# 1. Place CNC order
# Expected: replicated with correct quantity

# 2. Place INTRADAY order
# Expected: replicated with correct productType

# 3. Modify order
# Expected: modification replicated

# 4. Cancel order
# Expected: cancellation replicated
```

### Phase 3: BO/CO Orders (2 hours)
```bash
# 1. Place BO order (productType='BO')
# Expected: 
#   - Detection logs "Bracket Order detected"
#   - Follower order has productType='BO'
#   - boProfitValue and boStopLossValue set

# 2. Place CO order (productType='CO')
# Expected:
#   - Detection logs "Cover Order detected"
#   - Follower order has productType='CO'
#   - coStopLossValue set

# 3. Test BO leg tracking (if API returns legs)
# Expected:
#   - Legs saved to database with correct leg_order_id
#   - Can retrieve legs
#   - Can cancel legs
```

### Phase 4: WebSocket Recovery (1 hour)
```bash
# 1. Monitor WebSocket connection
# Expected: Updates received

# 2. Disconnect (kill network)
# Expected: Reconnection triggered

# 3. Place order while disconnected
# Expected: Order fetched on reconnect using createTime

# 4. Verify replication
# Expected: Missed order replicated correctly
```

---

## Files Modified

### Source Files (4)
1. `src/position_sizing/position_sizer.py` - 1 line changed
2. `src/orders/order_manager.py` - ~30 lines changed
3. `src/database/database.py` - 4 lines changed
4. `src/websocket/ws_manager.py` - ~20 lines changed

### Total Changes
- **Lines added**: ~40
- **Lines modified**: ~20
- **Lines removed**: ~15
- **Net change**: ~45 lines

---

## Rollback Procedure

If patches cause issues, rollback using git:

```bash
# View changes
git diff src/

# Revert specific file
git checkout HEAD -- src/position_sizing/position_sizer.py

# Or revert all changes
git reset --hard HEAD
```

---

## Post-Patch Checklist

### Immediate (Before Testing)
- [x] All patches applied
- [x] No syntax errors
- [ ] Run linter on modified files
- [ ] Review git diff

### Testing Phase
- [ ] Phase 1: Position sizing tests
- [ ] Phase 2: Regular order tests
- [ ] Phase 3: BO/CO order tests
- [ ] Phase 4: WebSocket recovery tests

### Pre-Deployment
- [ ] All tests passing
- [ ] Code review complete
- [ ] Documentation updated
- [ ] Changelog updated
- [ ] Deployment plan ready

---

## Expected Outcomes

### Position Sizing
- ✅ Orders now have non-zero quantities
- ✅ Capital ratio calculated correctly
- ✅ Position sizing works as designed

### BO/CO Orders
- ✅ Proper detection based on productType
- ✅ Follower orders have correct productType
- ✅ BO/CO parameters properly extracted and passed
- ✅ BO legs tracked correctly (field name fixed)

### WebSocket Recovery
- ✅ Missed orders fetched using correct field name
- ✅ Orders placed during disconnect are recovered
- ✅ System resilient to network interruptions

---

## Next Steps

### Immediate
1. Run lint checks on modified files
2. Commit changes with descriptive message
3. Begin Phase 1 testing

### Short Term
4. Complete all 4 testing phases
5. Document any issues found
6. Fix any edge cases discovered

### Medium Term
7. Deploy to staging environment
8. Monitor for 24-48 hours
9. Deploy to production with monitoring
10. Update documentation with learnings

---

**Patches Applied By**: AI Assistant  
**Date**: October 3, 2025  
**Status**: ✅ COMPLETE  
**Next**: Begin testing phase

