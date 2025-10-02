# Cover & Bracket Order Support Analysis

## User Question
**"By the way, does the codebase support Cover Orders, Bracket Orders and their modifications and cancellations according to API docs?"**

---

## 🔍 **DhanHQ v2 API Support Confirmed**

Based on official DhanHQ v2 API documentation (dhanhq.co/docs/v2/orders/):

### ✅ **Cover Orders (CO)**
- **Definition**: Two-legged order combining entry order with **compulsory stop-loss**
- **Structure**:
  - Entry Order: Market or Limit order
  - Stop-Loss: Automatically placed when entry executes
- **Use Case**: Risk management with mandatory SL
- **API Parameters**: Special CO-specific parameters required

### ✅ **Bracket Orders (BO)**
- **Definition**: Three-component order for automated risk management
- **Structure**:
  1. **Entry Order**: Initial buy/sell
  2. **Target Order**: Profit booking at specified price
  3. **Stop-Loss Order**: Loss limiting at predetermined price
- **API Parameters**:
  - `boProfitValue`: Target profit level
  - `boStopLossValue`: Stop-loss level
  - Conditionally required when placing BO
- **Behavior**: When entry executes, both Target and SL become active (OCO - One-Cancels-Other)

### ✅ **Modifications & Cancellations**
- **Supported**: Yes, via PUT/DELETE endpoints
- **Modification Limit**: Up to 25 modifications per order
- **Beyond 25**: Must cancel and place new order

---

## 📊 **Current Codebase Support Assessment**

### ❌ **Cover Orders: NOT SUPPORTED**

**Current Code Status**:
```python
# File: src/orders/order_manager.py
# No extraction of CO-specific parameters:
# - coStopLossValue ❌ NOT EXTRACTED
# - coTriggerPrice ❌ NOT EXTRACTED
```

**What's Missing**:
1. ❌ **CO parameters not extracted** from leader order
2. ❌ **CO stop-loss not replicated** to follower
3. ❌ **CO stop-loss modifications not handled**
4. ❌ **CO-specific validation not implemented**

**Impact**: 🔴 **HIGH RISK**
- If leader places CO order → Follower gets regular order (no SL protection)
- Leader's automatic SL → Not replicated
- Follower exposed to unlimited risk

---

### ❌ **Bracket Orders: NOT SUPPORTED**

**Current Code Status**:
```python
# File: src/orders/order_manager.py, Line 103-105
trigger_price = leader_order_data.get('triggerPrice')  # ✅ ADDED
validity = leader_order_data.get('validity', 'DAY')  # ✅ ADDED
disclosed_qty = leader_order_data.get('disclosedQuantity')  # ✅ ADDED

# But BO-specific parameters:
# - boProfitValue ❌ NOT EXTRACTED
# - boStopLossValue ❌ NOT EXTRACTED
# - boOrderType ❌ NOT EXTRACTED
```

**What's Missing**:
1. ❌ **BO parameters not extracted**
   - `boProfitValue` (target level)
   - `boStopLossValue` (SL level)
   - `boOrderType` (identifier for BO)
2. ❌ **BO multi-leg structure not handled**
   - Entry leg
   - Target leg
   - SL leg
3. ❌ **BO leg modifications not handled**
   - Modifying target level
   - Modifying SL level (trailing stop)
4. ❌ **BO leg cancellations not handled**
   - Canceling target leg
   - Canceling SL leg
   - OCO logic not implemented
5. ❌ **BO leg order_id mapping not tracked**
   - No linking between parent BO and child legs
   - Copy mapping only tracks single order_id

**Impact**: 🔴 **CRITICAL RISK**
- If leader places BO → Follower gets only entry order (no Target/SL)
- Leader's automatic Target/SL → Not replicated
- Follower has NO risk management
- Follower has NO profit booking
- Manual intervention required for every BO

---

## 🛠️ **Required Enhancements**

### **Phase 1: Cover Order Support**

#### **1.1 Extract CO Parameters**
```python
# File: src/orders/order_manager.py, Line ~103

# Current:
trigger_price = leader_order_data.get('triggerPrice')
validity = leader_order_data.get('validity', 'DAY')
disclosed_qty = leader_order_data.get('disclosedQuantity')

# ADD:
co_stop_loss_value = leader_order_data.get('coStopLossValue')  # ✅ ADD
co_trigger_price = leader_order_data.get('coTriggerPrice')  # ✅ ADD (if supported)
is_cover_order = leader_order_data.get('orderType') == 'CO'  # ✅ ADD detection
```

#### **1.2 Pass CO Parameters to API**
```python
# File: src/orders/order_manager.py, Line ~335

# ✅ MODIFIED: Build API params with CO parameters
api_params = {
    'security_id': security_id,
    'exchange_segment': exchange_segment,
    'transaction_type': transaction_type,
    'quantity': quantity,
    'order_type': order_type,  # May be 'CO'
    'product_type': product_type,
    'price': price if price > 0 else 0,
    'validity': validity
}

# ✅ ADD: Include CO stop-loss if Cover Order
if co_stop_loss_value:
    api_params['coStopLossValue'] = co_stop_loss_value

if co_trigger_price:
    api_params['coTriggerPrice'] = co_trigger_price
```

#### **1.3 Handle CO Stop-Loss Modifications**
```python
# File: src/orders/order_manager.py, modify_order()

# Detect if modifying CO stop-loss leg
new_co_sl = leader_order_data.get('coStopLossValue')

if new_co_sl:
    modify_params['coStopLossValue'] = new_co_sl
```

---

### **Phase 2: Bracket Order Support**

#### **2.1 Extract BO Parameters**
```python
# File: src/orders/order_manager.py, Line ~103

# ADD Bracket Order parameters:
bo_profit_value = leader_order_data.get('boProfitValue')  # ✅ ADD
bo_stop_loss_value = leader_order_data.get('boStopLossValue')  # ✅ ADD
bo_order_type = leader_order_data.get('boOrderType')  # ✅ ADD (e.g., 'MARKET', 'LIMIT')
is_bracket_order = bool(bo_profit_value or bo_stop_loss_value)  # ✅ ADD detection
```

#### **2.2 Calculate Proportional BO Levels**
```python
# File: src/orders/order_manager.py

# Calculate follower BO profit/SL values
# These should be ABSOLUTE values, not adjusted by capital ratio
# Because they're price levels, not quantities

follower_bo_profit = bo_profit_value  # Same absolute profit level
follower_bo_sl = bo_stop_loss_value   # Same absolute SL level

# OR if they're percentage-based:
# follower_bo_profit = (follower_quantity / leader_quantity) * bo_profit_value
```

#### **2.3 Pass BO Parameters to API**
```python
# File: src/orders/order_manager.py, _place_follower_order()

# ✅ ADD: Include BO parameters if Bracket Order
if bo_profit_value:
    api_params['boProfitValue'] = follower_bo_profit

if bo_stop_loss_value:
    api_params['boStopLossValue'] = follower_bo_sl

if bo_order_type:
    api_params['boOrderType'] = bo_order_type
```

#### **2.4 Track BO Leg Order IDs**
```python
# New database table or column to track BO relationships

# Add to Order model:
@dataclass
class Order:
    # ... existing fields ...
    parent_order_id: Optional[str] = None  # ✅ ADD: For BO legs
    leg_type: Optional[str] = None         # ✅ ADD: 'ENTRY', 'TARGET', 'SL'
    
# Or separate table:
CREATE TABLE bracket_order_legs (
    parent_order_id TEXT NOT NULL,
    leg_order_id TEXT NOT NULL,
    leg_type TEXT NOT NULL,  -- 'ENTRY', 'TARGET', 'SL'
    account_type TEXT NOT NULL,  -- 'leader', 'follower'
    created_at INTEGER NOT NULL,
    PRIMARY KEY (parent_order_id, leg_order_id)
);
```

#### **2.5 Handle BO Leg Modifications**
```python
# File: src/orders/order_manager.py, modify_order()

def modify_order(self, leader_order_data: Dict[str, Any]) -> bool:
    """Modify follower order when leader modifies."""
    try:
        leader_order_id = leader_order_data.get('orderId')
        
        # ✅ CURRENT: Find direct mapping
        mapping = self.db.get_copy_mapping_by_leader(leader_order_id)
        
        # ✅ ADD: If no mapping, check if this is a BO leg
        if not mapping:
            # Check if leader_order_id is a BO parent
            bo_legs = self.db.get_bracket_order_legs(leader_order_id)
            
            if bo_legs:
                # Determine which leg is being modified
                leg_type = leader_order_data.get('legType')  # 'TARGET' or 'SL'
                
                # Find corresponding follower leg
                for leg in bo_legs:
                    if leg.leg_type == leg_type and leg.account_type == 'follower':
                        return self._modify_bo_leg(leg.leg_order_id, leader_order_data)
        
        # ... existing logic ...
```

#### **2.6 Handle BO Leg Cancellations**
```python
# File: src/orders/order_manager.py, cancel_order()

def cancel_order(self, leader_order_data: Dict[str, Any]) -> bool:
    """Cancel follower order when leader cancels."""
    try:
        leader_order_id = leader_order_data.get('orderId')
        
        # ✅ ADD: Check if this is a BO parent cancellation
        bo_legs = self.db.get_bracket_order_legs(leader_order_id)
        
        if bo_legs:
            # Cancel all follower legs
            success = True
            for leg in bo_legs:
                if leg.account_type == 'follower':
                    leg_success = self._cancel_bo_leg(leg.leg_order_id)
                    success = success and leg_success
            return success
        
        # ... existing single order cancellation logic ...
```

#### **2.7 Handle OCO Logic**
```python
# When one BO leg executes, the other should be auto-cancelled

def handle_execution(self, execution_data: Dict[str, Any]) -> None:
    """Handle order execution event."""
    try:
        order_id = execution_data.get('orderId')
        order_status = execution_data.get('orderStatus')
        
        # ✅ ADD: Check if this is a BO leg execution
        bo_leg = self.db.get_bracket_order_leg(order_id)
        
        if bo_leg and order_status in ('EXECUTED', 'TRADED'):
            # Get other legs of same BO parent
            sibling_legs = self.db.get_bracket_order_legs(
                bo_leg.parent_order_id,
                exclude_leg_id=order_id
            )
            
            # For OCO: If TARGET executes, cancel SL (and vice versa)
            if bo_leg.leg_type in ('TARGET', 'SL'):
                for sibling in sibling_legs:
                    if sibling.leg_type in ('TARGET', 'SL') and sibling.leg_type != bo_leg.leg_type:
                        # Auto-cancel the other leg (OCO behavior)
                        self._cancel_bo_leg(sibling.leg_order_id)
                        logger.info(f"OCO: Cancelled {sibling.leg_type} leg after {bo_leg.leg_type} execution")
        
        # ... existing execution handling ...
```

---

## 📋 **Database Schema Changes Required**

### **New Table: bracket_order_legs**
```sql
-- Track Bracket Order leg relationships
CREATE TABLE IF NOT EXISTS bracket_order_legs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    parent_order_id TEXT NOT NULL,     -- BO parent order ID
    leg_order_id TEXT NOT NULL,        -- Individual leg order ID
    leg_type TEXT NOT NULL,            -- 'ENTRY', 'TARGET', 'SL'
    account_type TEXT NOT NULL,        -- 'leader', 'follower'
    status TEXT DEFAULT 'PENDING',     -- Track leg status
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL,
    
    UNIQUE(parent_order_id, leg_order_id, account_type)
);

CREATE INDEX idx_bo_legs_parent ON bracket_order_legs(parent_order_id);
CREATE INDEX idx_bo_legs_leg ON bracket_order_legs(leg_order_id);
```

### **Extend Orders Table**
```sql
-- Add CO/BO specific columns to orders table
ALTER TABLE orders ADD COLUMN co_stop_loss_value REAL;
ALTER TABLE orders ADD COLUMN bo_profit_value REAL;
ALTER TABLE orders ADD COLUMN bo_stop_loss_value REAL;
ALTER TABLE orders ADD COLUMN parent_order_id TEXT;
ALTER TABLE orders ADD COLUMN leg_type TEXT;  -- 'ENTRY', 'TARGET', 'SL', NULL for regular orders
```

---

## 🧪 **Testing Required**

### **Cover Order Tests**

#### **Test 1: CO Order Placement**
```python
# Leader places Cover Order
co_order = leader_client.place_order(
    security_id="52175",
    exchange_segment="NSE_FNO",
    transaction_type="BUY",
    quantity=50,
    order_type="CO",  # Cover Order
    product_type="MIS",
    price=100,
    coStopLossValue=95  # Mandatory SL
)

# Expected:
# ✅ Follower also places CO with adjusted qty
# ✅ Follower CO has same coStopLossValue=95
# ✅ When entry executes, both have SL auto-placed
```

#### **Test 2: CO Stop-Loss Modification**
```python
# Leader modifies CO stop-loss (trailing)
modify_response = leader_client.modify_order(
    order_id=co_order['orderId'],
    coStopLossValue=98  # Trail SL up
)

# Expected:
# ✅ Follower CO stop-loss also modified to 98
```

### **Bracket Order Tests**

#### **Test 3: BO Order Placement**
```python
# Leader places Bracket Order
bo_order = leader_client.place_order(
    security_id="52175",
    exchange_segment="NSE_FNO",
    transaction_type="BUY",
    quantity=50,
    order_type="LIMIT",
    product_type="MIS",
    price=100,
    boProfitValue=10,     # Target: ₹110
    boStopLossValue=5     # SL: ₹95
)

# Expected:
# ✅ Follower places BO with adjusted qty (e.g., 25)
# ✅ Follower BO has same boProfitValue=10, boStopLossValue=5
# ✅ When entry executes, follower gets Target & SL legs
```

#### **Test 4: BO Target Modification**
```python
# Leader modifies BO target (book profit early)
modify_response = leader_client.modify_order(
    order_id=target_leg_id,
    price=105  # Reduce target from ₹110 to ₹105
)

# Expected:
# ✅ Follower BO target also modified to ₹105
```

#### **Test 5: BO Stop-Loss Trail**
```python
# Leader trails BO stop-loss
modify_response = leader_client.modify_order(
    order_id=sl_leg_id,
    trigger_price=98  # Trail SL from ₹95 to ₹98
)

# Expected:
# ✅ Follower BO SL also trailed to ₹98
```

#### **Test 6: BO OCO Behavior**
```python
# Entry executes, price moves to target
# Target leg executes

# Expected:
# ✅ Leader SL leg auto-cancelled (OCO)
# ✅ Follower SL leg also auto-cancelled
```

---

## 🎯 **Current Status Summary**

| Feature | DhanHQ API Support | Current Code Support | Gap Severity |
|---------|-------------------|---------------------|--------------|
| **Cover Orders (CO)** | ✅ Fully Supported | ❌ Not Implemented | 🔴 **CRITICAL** |
| - CO Placement | ✅ Yes | ❌ No | 🔴 CRITICAL |
| - CO SL Parameters | ✅ Yes | ❌ Not extracted | 🔴 CRITICAL |
| - CO SL Modification | ✅ Yes | ❌ Not handled | 🔴 CRITICAL |
| - CO SL Cancellation | ✅ Yes | ❌ Not handled | 🔴 CRITICAL |
| **Bracket Orders (BO)** | ✅ Fully Supported | ❌ Not Implemented | 🔴 **CRITICAL** |
| - BO Placement | ✅ Yes | ❌ No | 🔴 CRITICAL |
| - BO Profit/SL Parameters | ✅ Yes | ❌ Not extracted | 🔴 CRITICAL |
| - BO Leg Tracking | ✅ Yes | ❌ Not implemented | 🔴 CRITICAL |
| - BO Leg Modification | ✅ Yes (25 limit) | ❌ Not handled | 🔴 CRITICAL |
| - BO Leg Cancellation | ✅ Yes | ❌ Not handled | 🔴 CRITICAL |
| - BO OCO Logic | ✅ Yes | ❌ Not implemented | 🔴 CRITICAL |

---

## ⚠️ **Risk Assessment**

### **Production Deployment WITHOUT CO/BO Support**

**Risk Level**: 🔴 **EXTREMELY HIGH** if users trade with CO/BO orders

**Scenarios**:

#### **Scenario 1: Leader Uses Cover Order**
```
Leader:
- Places CO (Entry + mandatory SL)
- Entry executes
- SL auto-placed for protection

Follower:
- Places regular order (no SL) ❌
- Entry executes
- NO SL PROTECTION ❌
- Exposed to unlimited loss ❌
```
**Impact**: 💰 **CATASTROPHIC** - Follower has zero risk management

#### **Scenario 2: Leader Uses Bracket Order**
```
Leader:
- Places BO (Entry + Target + SL)
- Entry executes
- Target at ₹110, SL at ₹95

Follower:
- Places only entry order ❌
- Entry executes
- NO TARGET (no profit booking) ❌
- NO SL (no loss protection) ❌
- Requires manual intervention for every trade ❌
```
**Impact**: 💰 **CATASTROPHIC** - System completely non-functional for BO users

---

## 💡 **Recommendations**

### **Immediate (BEFORE Production)**

1. **🚨 CRITICAL: Determine if users will use CO/BO**
   - Survey trading strategy
   - If CO/BO are used → MUST implement support
   - If NOT used → Document limitation clearly

2. **🚨 If CO/BO are used:**
   - **DO NOT deploy** current code to production
   - Risk is too high (unlimited loss exposure)
   - Implement Phase 1 & 2 enhancements first

3. **✅ If CO/BO are NOT used:**
   - Add validation to REJECT CO/BO orders
   - Log warning when CO/BO detected
   - Alert operator for manual handling

### **Short Term (1-2 Weeks)**

**If CO/BO support needed**:
1. Implement Cover Order support (Phase 1)
   - Extract CO parameters
   - Pass to API
   - Handle CO SL modifications
   - Test thoroughly in sandbox

2. Implement Bracket Order support (Phase 2)
   - Extract BO parameters
   - Track BO leg relationships
   - Handle BO leg modifications/cancellations
   - Implement OCO logic
   - Test thoroughly in sandbox

### **Medium Term (1 Month)**

1. Add CO/BO analytics
   - Track CO SL hit rate
   - Track BO Target vs SL execution
   - Monitor OCO behavior

2. Advanced BO features
   - Trailing brackets (auto-update SL as price moves)
   - Multiple profit targets
   - Partial profit booking

---

## 📝 **Code Implementation Estimate**

| Component | Lines of Code | Complexity | Time Estimate |
|-----------|---------------|------------|---------------|
| **Cover Order Support** | ~150 LOC | Medium | 1-2 days |
| - Parameter extraction | ~30 LOC | Low | 2 hours |
| - API integration | ~50 LOC | Medium | 4 hours |
| - Modification handling | ~40 LOC | Medium | 4 hours |
| - Testing | ~30 LOC | Low | 4 hours |
| **Bracket Order Support** | ~400 LOC | High | 4-5 days |
| - Parameter extraction | ~50 LOC | Medium | 4 hours |
| - Leg tracking (DB + models) | ~100 LOC | High | 1 day |
| - API integration | ~80 LOC | High | 8 hours |
| - Modification handling | ~80 LOC | High | 8 hours |
| - Cancellation handling | ~50 LOC | Medium | 4 hours |
| - OCO logic | ~40 LOC | Medium | 4 hours |
| - Testing | ~100 LOC | High | 1 day |
| **Total** | **~550 LOC** | **High** | **5-7 days** |

---

## 🎯 **Quick Decision Matrix**

### **Question: Do your users trade with Cover/Bracket Orders?**

#### **Answer: YES** → **Action: IMPLEMENT SUPPORT (5-7 days)**
- Risk too high without support
- Follow Phase 1 & 2 implementation
- Test thoroughly before production

#### **Answer: NO** → **Action: ADD VALIDATION & WARNINGS**
```python
# Quick fix: Reject CO/BO orders with clear warning

def replicate_order(self, leader_order_data: Dict[str, Any]) -> Optional[str]:
    """Replicate a leader order to follower account."""
    try:
        # ... existing code ...
        
        # ✅ ADD: Reject CO/BO orders
        order_type = leader_order_data.get('orderType')
        
        if order_type in ('CO', 'BO'):
            logger.error(
                f"❌ UNSUPPORTED ORDER TYPE: {order_type} detected. "
                f"Cover/Bracket Orders are not supported. Order NOT replicated.",
                extra={
                    "leader_order_id": leader_order_id,
                    "order_type": order_type,
                    "security_id": security_id
                }
            )
            
            # Send alert to operator
            self._send_alert(
                severity="CRITICAL",
                message=f"Cover/Bracket Order detected and NOT replicated: {leader_order_id}"
            )
            
            return None
        
        # ... existing replication logic ...
```

#### **Answer: UNKNOWN** → **Action: RESEARCH FIRST**
- Review leader account's order history
- Check if CO/BO orders exist
- Then decide on implementation

---

## 📄 **Summary**

**Question**: Does the codebase support Cover/Bracket Orders?

**Answer**: **❌ NO - Not Currently Supported**

**DhanHQ API**: ✅ Fully supports CO/BO  
**Current Code**: ❌ No CO/BO handling implemented

**Risk if deployed without CO/BO support**: 🔴 **CRITICAL**

**Required Action**:
1. Determine if users need CO/BO support
2. If YES → Implement enhancements (~5-7 days)
3. If NO → Add validation to reject CO/BO orders

---

**Document Version**: 1.0  
**Date**: 2025-10-02  
**Status**: Analysis Complete, Enhancement Needed for CO/BO Support

