# Comprehensive Test Scenarios

## Document Purpose

This document provides detailed test scenarios for validating all functionality identified in the scenario analysis.

---

## Test Category 1: Order Placement

### TC-1.1: Basic Market Order Replication

**Objective**: Verify market order is replicated correctly

**Pre-conditions**:
- System running and connected
- Leader and follower authenticated
- Sufficient margin in follower account

**Test Steps**:
1. Place MARKET BUY order in leader account for NIFTY 25000 CE, qty 50
2. Wait for WebSocket event
3. Verify follower order placed

**Expected Results**:
- ✅ Follower order placed within 2 seconds
- ✅ Order type = MARKET
- ✅ Transaction type = BUY
- ✅ Security ID = same as leader
- ✅ Quantity = proportionally adjusted (e.g., 25 if 50% capital)
- ✅ Copy mapping created in database
- ✅ Both orders logged in audit_log

**Test Data**:
```python
leader_order = {
    'orderId': 'L001',
    'securityId': '67890',
    'exchangeSegment': 'NSE_FO',
    'transactionType': 'BUY',
    'quantity': 50,
    'orderType': 'MARKET',
    'productType': 'MIS',
    'orderStatus': 'PENDING'
}
```

**Validation Queries**:
```sql
-- Check copy mapping
SELECT * FROM copy_mappings WHERE leader_order_id = 'L001';

-- Check follower order
SELECT * FROM orders WHERE id = '<follower_order_id>';

-- Check audit log
SELECT * FROM audit_log WHERE action = 'place_order' AND account_type = 'follower';
```

---

### TC-1.2: Limit Order with Price

**Objective**: Verify limit order replicates with correct price

**Test Steps**:
1. Place LIMIT BUY order @ ₹100 in leader account
2. Verify follower places LIMIT @ ₹100 (same price)

**Expected Results**:
- ✅ Follower order type = LIMIT
- ✅ Follower price = ₹100 (same as leader)
- ✅ Quantity adjusted proportionally

---

### TC-1.3: Stop-Loss Order with Trigger (AFTER FIX)

**Objective**: Verify SL order includes trigger price

**Test Steps**:
1. Place SL order with trigger=₹95, limit=₹94 in leader
2. Verify follower replicates with same triggers

**Expected Results**:
- ✅ Follower order type = SL
- ✅ Follower trigger_price = ₹95
- ✅ Follower price = ₹94
- ✅ Quantity adjusted

**Current Status**: ❌ WILL FAIL (trigger price not implemented)

---

### TC-1.4: IOC Order Validity (AFTER FIX)

**Objective**: Verify IOC validity is preserved

**Test Steps**:
1. Place IOC order in leader
2. Verify follower order has IOC validity

**Expected Results**:
- ✅ Follower validity = IOC (not DAY)

**Current Status**: ❌ WILL FAIL (validity hardcoded to DAY)

---

### TC-1.5: Options-Only Filter

**Objective**: Verify non-options orders are skipped

**Test Steps**:
1. Place equity order in leader (e.g., RELIANCE stock)
2. Verify follower order NOT placed

**Expected Results**:
- ✅ No follower order created
- ✅ Log message: "not an option, skipping"
- ✅ No copy mapping created

---

### TC-1.6: Insufficient Margin

**Objective**: Verify orders skip when follower lacks margin

**Test Steps**:
1. Reduce follower margin to very low
2. Place large order in leader
3. Verify order skipped with clear reason

**Expected Results**:
- ✅ No follower order placed
- ✅ Copy mapping created with status='failed'
- ✅ Error message: "Insufficient margin"

---

### TC-1.7: Duplicate Order Prevention

**Objective**: Verify duplicate events don't create duplicate orders

**Test Steps**:
1. Place order in leader
2. Simulate receiving same WebSocket event twice
3. Verify only one follower order created

**Expected Results**:
- ✅ Only one follower order
- ✅ Second event logs: "already replicated"

---

## Test Category 2: Order Modification (AFTER IMPLEMENTATION)

### TC-2.1: Modify Order Quantity

**Objective**: Verify quantity modifications are replicated

**Pre-conditions**:
- Order already placed in both accounts
- Order in OPEN status

**Test Steps**:
1. Modify leader order quantity from 50 to 100
2. Verify follower order quantity updated proportionally

**Expected Results**:
- ✅ Follower order modified via API
- ✅ New quantity = adjusted to 50 (if 50% capital ratio)
- ✅ Order status remains OPEN
- ✅ Modification logged in order_events

**Current Status**: ❌ NOT IMPLEMENTED

---

### TC-2.2: Modify Limit Price

**Objective**: Verify price modifications are replicated

**Test Steps**:
1. Modify leader limit price from ₹100 to ₹105
2. Verify follower price updated to ₹105

**Expected Results**:
- ✅ Follower price = ₹105
- ✅ Quantity unchanged
- ✅ API modify_order called

**Current Status**: ❌ NOT IMPLEMENTED

---

### TC-2.3: Modify to Market Order

**Objective**: Verify order type change replicated

**Test Steps**:
1. Modify leader from LIMIT to MARKET
2. Verify follower changed to MARKET

**Expected Results**:
- ✅ Follower order_type = MARKET
- ✅ Price removed (not applicable to MARKET)

**Current Status**: ❌ NOT IMPLEMENTED

---

### TC-2.4: Modify After Partial Fill

**Objective**: Verify modification after partial execution

**Test Steps**:
1. Leader order 50% filled
2. Modify remaining quantity
3. Verify follower modifies remaining portion only

**Expected Results**:
- ✅ Only unfilled portion modified
- ✅ Filled portion unchanged

**Current Status**: ❌ NOT IMPLEMENTED

---

## Test Category 3: Order Cancellation (AFTER IMPLEMENTATION)

### TC-3.1: Cancel Pending Order

**Objective**: Verify pending order cancellation

**Test Steps**:
1. Place order in both accounts (not yet filled)
2. Cancel leader order
3. Verify follower order cancelled

**Expected Results**:
- ✅ Follower order cancelled via API
- ✅ Follower order status = CANCELLED
- ✅ Copy mapping status = 'cancelled'
- ✅ Event logged

**Current Status**: ❌ NOT IMPLEMENTED

---

### TC-3.2: Cancel Partially Filled Order

**Objective**: Verify cancellation after partial fill

**Test Steps**:
1. Leader order 30% filled
2. Cancel leader order
3. Verify follower cancels remaining 70%

**Expected Results**:
- ✅ Follower order cancelled
- ✅ Filled portion remains (can't cancel executed)
- ✅ Status updated correctly

**Current Status**: ❌ NOT IMPLEMENTED

---

### TC-3.3: Cancel Already Executed Order

**Objective**: Verify graceful handling of cancel for executed order

**Test Steps**:
1. Leader order fully executed
2. (Unlikely but possible) Cancel event arrives
3. Verify no error, graceful handling

**Expected Results**:
- ✅ No API call (order already terminal)
- ✅ Log message: "already in terminal state"
- ✅ No error thrown

**Current Status**: ❌ NOT IMPLEMENTED

---

### TC-3.4: Cancel Before Follower Placement

**Objective**: Verify handling if cancel arrives before placement completes

**Test Steps**:
1. Place order in leader
2. While follower order placing, cancel arrives
3. Verify follower placement aborted or order immediately cancelled

**Expected Results**:
- ✅ Either: placement aborted
- ✅ Or: order placed then immediately cancelled
- ✅ No orphaned orders

**Current Status**: ❌ NOT IMPLEMENTED (race condition)

---

## Test Category 4: Order Execution

### TC-4.1: Full Execution Tracking

**Objective**: Verify execution events are captured

**Test Steps**:
1. Place and execute order in leader
2. Verify execution event processed

**Expected Results**:
- ✅ Leader order status updated to EXECUTED
- ✅ Execution logged in order_events
- ✅ Trade details captured (if available)

**Current Status**: ❌ PARTIALLY IMPLEMENTED

---

### TC-4.2: Partial Fill Tracking

**Objective**: Verify partial fills are tracked

**Test Steps**:
1. Place large order
2. Receive partial fill event (50% executed)
3. Verify partial fill recorded

**Expected Results**:
- ✅ Order status = PARTIALLY_FILLED
- ✅ Filled quantity tracked
- ✅ Remaining quantity known

**Current Status**: ❌ NOT IMPLEMENTED

---

### TC-4.3: Multiple Fills

**Objective**: Verify multiple partial fills handled correctly

**Test Steps**:
1. Place order
2. Receive 3 partial fill events (30%, 40%, 30%)
3. Verify all fills tracked

**Expected Results**:
- ✅ Three fill events stored
- ✅ Total filled qty = 100%
- ✅ Average price calculated

**Current Status**: ❌ NOT IMPLEMENTED

---

## Test Category 5: WebSocket & Connectivity

### TC-5.1: WebSocket Reconnection

**Objective**: Verify automatic reconnection works

**Test Steps**:
1. Disconnect WebSocket (simulate network issue)
2. Wait for reconnection
3. Verify connection restored

**Expected Results**:
- ✅ Reconnection attempted with backoff
- ✅ Connection restored within 60 seconds
- ✅ System resumes normal operation

**Current Status**: ✅ IMPLEMENTED

---

### TC-5.2: Missed Orders During Disconnect

**Objective**: Verify missed orders are recovered

**Test Steps**:
1. Disconnect WebSocket
2. Place 5 orders in leader while disconnected
3. Reconnect
4. Verify all 5 orders are replicated

**Expected Results**:
- ✅ On reconnect, fetch missed orders
- ✅ All 5 orders replicated
- ✅ No orders lost

**Current Status**: ❌ NOT IMPLEMENTED

---

### TC-5.3: Out-of-Order Events

**Objective**: Verify events processed correctly even if out of sequence

**Test Steps**:
1. Simulate events arriving: CANCELLED, MODIFIED, PLACED (wrong order)
2. Verify system reorders based on timestamps

**Expected Results**:
- ✅ Events reordered by timestamp/sequence
- ✅ Processed in correct order
- ✅ Final state correct

**Current Status**: ❌ NOT IMPLEMENTED

---

## Test Category 6: Edge Cases

### TC-6.1: Zero Calculated Quantity

**Objective**: Verify handling when follower qty calculates to 0

**Test Steps**:
1. Set follower capital very low
2. Place order in leader
3. Verify order skipped gracefully

**Expected Results**:
- ✅ No follower order placed
- ✅ Mapping created with status='failed'
- ✅ Error: "Calculated quantity is 0"

**Current Status**: ✅ IMPLEMENTED

---

### TC-6.2: Race Condition - Simultaneous Orders

**Objective**: Test handling of multiple rapid orders

**Test Steps**:
1. Place 10 orders in leader within 1 second
2. Verify all replicated correctly

**Expected Results**:
- ✅ All 10 orders replicated
- ✅ Capital calculations don't overlap
- ✅ Rate limiting applied
- ✅ No duplicate orders

**Current Status**: ⚠️ RISK (no locking, no rate limiting)

---

### TC-6.3: System Restart Recovery

**Objective**: Verify system recovers state after restart

**Test Steps**:
1. Place orders, some pending, some executed
2. Stop system
3. Restart system
4. Verify state recovered from database

**Expected Results**:
- ✅ All orders reloaded from DB
- ✅ Pending orders resume monitoring
- ✅ No data loss

**Current Status**: ⚠️ PARTIAL (DB persists, but no resume logic)

---

## Test Category 7: Performance & Load

### TC-7.1: High Order Volume

**Objective**: Test system under high order load

**Test Steps**:
1. Place 100 orders in leader over 10 minutes
2. Monitor system performance

**Expected Results**:
- ✅ All orders replicated
- ✅ Average latency < 2 seconds
- ✅ No memory leaks
- ✅ No database deadlocks

---

### TC-7.2: Rate Limiting

**Objective**: Verify rate limiting prevents API overload

**Test Steps**:
1. Place 50 orders in 1 second
2. Verify rate limiting applied

**Expected Results**:
- ✅ Orders queued and throttled
- ✅ No 429 errors from API
- ✅ All orders eventually placed

**Current Status**: ❌ NOT IMPLEMENTED

---

## Test Category 8: Integration Tests

### TC-8.1: End-to-End Replication

**Objective**: Full cycle test in sandbox

**Test Steps**:
1. Start system with sandbox credentials
2. Place, modify, and cancel order in leader sandbox
3. Verify all actions replicated to follower sandbox

**Expected Results**:
- ✅ Order placed, modified, cancelled in follower
- ✅ All events tracked in database
- ✅ Audit trail complete

---

### TC-8.2: Multi-Day Operation

**Objective**: Verify system runs continuously

**Test Steps**:
1. Run system for 24 hours
2. Place orders throughout the day
3. Monitor memory, connections, database

**Expected Results**:
- ✅ No memory leaks
- ✅ All orders replicated
- ✅ Database size reasonable
- ✅ WebSocket stable

---

## Test Execution Checklist

### Phase 1: Critical Path (Fix These First)
- [ ] TC-1.1: Basic market order ✅ (Should pass)
- [ ] TC-1.5: Options-only filter ✅ (Should pass)
- [ ] TC-1.6: Insufficient margin ✅ (Should pass)
- [ ] TC-3.1: Cancel pending order ❌ (Will fail, not implemented)
- [ ] TC-2.1: Modify quantity ❌ (Will fail, not implemented)

### Phase 2: Parameter Fixes
- [ ] TC-1.3: Stop-loss with trigger ❌ (Will fail)
- [ ] TC-1.4: IOC validity ❌ (Will fail)

### Phase 3: Advanced Features
- [ ] TC-4.1: Execution tracking
- [ ] TC-4.2: Partial fills
- [ ] TC-5.2: Missed orders
- [ ] TC-6.2: Race conditions

### Phase 4: Load & Stress
- [ ] TC-7.1: High order volume
- [ ] TC-7.2: Rate limiting
- [ ] TC-8.2: Multi-day operation

---

## Test Automation

### Recommended Test Framework

```python
# tests/integration/test_order_replication.py

import pytest
from unittest.mock import Mock, patch
import time

class TestOrderReplication:
    """Integration tests for order replication."""
    
    @pytest.fixture
    def system(self):
        """Setup test system."""
        # Initialize components with test config
        # Use mock DhanHQ clients or sandbox
        pass
    
    def test_market_order_replication(self, system):
        """Test TC-1.1: Basic market order replication."""
        # Given
        leader_order = {
            'orderId': 'TEST001',
            'securityId': '67890',
            'exchangeSegment': 'NSE_FO',
            'transactionType': 'BUY',
            'quantity': 50,
            'orderType': 'MARKET',
            'productType': 'MIS',
            'orderStatus': 'PENDING'
        }
        
        # When
        follower_order_id = system.order_manager.replicate_order(leader_order)
        
        # Then
        assert follower_order_id is not None
        
        # Verify database
        mapping = system.db.get_copy_mapping_by_leader('TEST001')
        assert mapping is not None
        assert mapping.follower_order_id == follower_order_id
        assert mapping.status == 'placed'
        
        # Verify follower order
        follower_order = system.db.get_order(follower_order_id)
        assert follower_order.order_type == 'MARKET'
        assert follower_order.side == 'BUY'
        assert follower_order.quantity > 0
    
    def test_insufficient_margin(self, system):
        """Test TC-1.6: Insufficient margin handling."""
        # Mock position sizer to return insufficient margin
        with patch.object(system.position_sizer, 'validate_sufficient_margin') as mock:
            mock.return_value = (False, "Insufficient margin")
            
            # When
            result = system.order_manager.replicate_order(test_order)
            
            # Then
            assert result is None
            
            mapping = system.db.get_copy_mapping_by_leader(test_order['orderId'])
            assert mapping.status == 'failed'
            assert 'Insufficient margin' in mapping.error_message
```

---

## Manual Testing Checklist

For sandbox/production testing:

### Pre-Deployment
1. ✅ Unit tests pass
2. ✅ Integration tests pass
3. ✅ Linter clean
4. ✅ No security vulnerabilities
5. ✅ Documentation updated

### Sandbox Testing
1. [ ] Basic order replication works
2. [ ] Cancellation works (after implementation)
3. [ ] Modification works (after implementation)
4. [ ] System runs for 1 hour without errors
5. [ ] WebSocket reconnects successfully
6. [ ] Database integrity maintained

### Production Readiness
1. [ ] All critical gaps fixed
2. [ ] Reconciliation service running
3. [ ] Alerting configured
4. [ ] Backups automated
5. [ ] Monitoring dashboard active
6. [ ] Kill switch tested

---

**Test Coverage Goal**: 80% for core functionality, 100% for critical paths

**Regression Testing**: Run full test suite before each release

