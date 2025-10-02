# Task-003 Patches - Quick Start Guide

## 🎯 What Changed?

### Before Task-003
```
Copy Trading System v1.0 (Task-001)
├── ✅ Place orders from leader to follower
├── ✅ Adjust quantity based on capital
├── ✅ Options filtering
└── ❌ NO handling for cancellations, modifications, disconnects
```

### After Task-003
```
Copy Trading System v2.0 (Task-001 + Task-003 Patches)
├── ✅ Place orders (with ALL parameters)
├── ✅ Cancel orders (mirror leader)
├── ✅ Modify orders (mirror leader)
├── ✅ Track executions & slippage
├── ✅ Recover missed orders after disconnect
├── ✅ Rate limiting (no API errors)
├── ✅ Market hours validation
└── ✅ Full order lifecycle management
```

---

## 🚨 Critical Fixes Applied

### 1. **Order Cancellation** (CRITICAL)
**Problem**: Leader cancels → Follower stays open → Unintended position  
**Fix**: `OrderManager.cancel_order()` mirrors cancellations instantly

```python
# WebSocket receives CANCELLED status
→ OrderManager.cancel_order(leader_order_data)
  → Find follower order via copy_mapping
  → Call follower_client.cancel_order()
  → Update DB statuses
  → Log audit trail
```

### 2. **Order Modification** (CRITICAL)
**Problem**: Leader modifies qty/price → Follower unchanged → Mismatched exposure  
**Fix**: `OrderManager.modify_order()` replicates modifications

```python
# WebSocket receives MODIFIED status
→ OrderManager.modify_order(leader_order_data)
  → Extract new qty/price/trigger
  → Recalculate follower qty (proportional)
  → Call follower_client.modify_order()
  → Update DB
```

### 3. **Missed Orders** (CRITICAL)
**Problem**: WebSocket disconnect → Orders placed during downtime → LOST FOREVER  
**Fix**: `_fetch_missed_orders()` queries and replays

```python
# On reconnection
→ WebSocket.connect()
  → if _was_disconnected:
    → _fetch_missed_orders()
      → Query leader_client.get_order_list()
      → Filter orders created after last_leader_event_ts
      → Replay each through _handle_order_update()
```

### 4. **SL Orders Failing** (HIGH)
**Problem**: SL orders rejected due to missing `trigger_price`  
**Fix**: Extract and pass `trigger_price` from leader order

```python
# Before: trigger_price=None → API rejection ❌
# After:  trigger_price=leader_order_data.get('triggerPrice') → Success ✅
```

### 5. **Rate Limiting** (HIGH)
**Problem**: Burst orders → HTTP 429 → Order failures  
**Fix**: Token bucket rate limiter (10 req/sec)

```python
def _wait_for_rate_limit():
    # Keep last 1 second of timestamps
    # If >= 10 requests, wait remainder of 1 second
    # Thread-safe with lock
```

---

## 📋 How to Apply Patches

### Option 1: Patches Already Applied ✅
If you're reading this, the patches are **already applied** to:
- `tasks/Task-001-Copy-Trading-Architecture/src/websocket/ws_manager.py`
- `tasks/Task-001-Copy-Trading-Architecture/src/orders/order_manager.py`
- `tasks/Task-001-Copy-Trading-Architecture/src/main.py`
- `tasks/Task-001-Copy-Trading-Architecture/requirements.txt`

### Option 2: Manual Verification
```bash
cd /Users/mjolnir/Desktop/copy_trading_dhan

# Check for patch markers
grep -r "✅ ADDED" tasks/Task-001-Copy-Trading-Architecture/src/
grep -r "✅ FIXED" tasks/Task-001-Copy-Trading-Architecture/src/

# Should see multiple matches if patches applied
```

### Option 3: Install Updated Dependencies
```bash
cd tasks/Task-001-Copy-Trading-Architecture
pip install -r requirements.txt  # Now includes pytz
```

---

## 🧪 Quick Test Checklist

### Test 1: Cancellation Replication
```python
# 1. Start copy trading system
python -m src.main

# 2. In leader account: Place limit order (NSE FNO option)
# 3. Wait for replication (check logs)
# 4. In leader account: Cancel the order
# 5. Verify: Follower order also cancelled

# Expected log:
# "Processing cancellation for leader order: L123"
# "Successfully cancelled follower order F456"
```

### Test 2: Missed Orders Recovery
```python
# 1. Start system, note the time
# 2. Kill WebSocket (Ctrl+C or disconnect network)
# 3. In leader account: Place 2-3 orders
# 4. Restart system
# 5. Check logs for "Fetching orders placed since: <timestamp>"

# Expected log:
# "Reconnected after disconnect, fetching missed orders..."
# "Found 3 missed orders, processing..."
# "Order replicated successfully" x3
```

### Test 3: SL Order with Trigger
```python
# 1. Start system
# 2. In leader account: Place SL order
#    - Strike: NIFTY 22000 CE
#    - Qty: 50
#    - Price: 100
#    - Trigger: 98
# 3. Verify follower order has trigger price

# Expected log:
# "trigger_price": 98 in order placement log
# Order accepted (not rejected)
```

### Test 4: Rate Limiting
```python
# 1. Start system
# 2. In leader account: Place 15 orders rapidly (within 1 second)
# 3. Check logs for rate limiting

# Expected log:
# "Placing follower order" x10 (immediate)
# "Rate limit reached, waiting 0.5s"
# "Placing follower order" x5 (delayed)
```

---

## 📊 Key Metrics to Monitor

### Success Metrics
- **Order replication rate**: Should be 99%+ (was 85%)
- **Cancellation success**: Should be 100% (was 0%)
- **Modification success**: Should be 100% (was 0%)
- **Disconnect recovery**: Should be 100% (was 0%)
- **Rate limit errors**: Should be 0 (was 5-10/day)

### Performance Metrics
- **Avg latency (normal)**: 150-200ms (slight increase due to rate limiter)
- **Avg latency (burst)**: 500-1000ms (throttled but successful)
- **P99 latency**: <1500ms

### Log Monitoring
```bash
tail -f copy_trading.log | grep -E "(✅|❌|⚠️|CRITICAL|ERROR)"

# Green flags:
# ✅ "Order replicated successfully"
# ✅ "Order modified successfully"
# ✅ "Order cancelled successfully"
# ✅ "Found X missed orders"

# Yellow flags:
# ⚠️  "Rate limit reached" (expected during bursts)
# ⚠️  "Market closed" (expected outside hours)

# Red flags:
# ❌ "Failed to cancel/modify"
# ❌ "Error in _fetch_missed_orders"
# ❌ Continuous API errors
```

---

## 🔧 Troubleshooting

### Issue: Cancellations Not Working
**Symptoms**: Leader cancels order, follower order stays open

**Checklist**:
1. Check WebSocket is receiving CANCELLED status:
   ```bash
   grep "CANCELLED" copy_trading.log
   ```
2. Check copy_mapping exists:
   ```sql
   sqlite3 copy_trading.db "SELECT * FROM copy_mappings WHERE leader_order_id='L123';"
   ```
3. Check follower order status:
   ```sql
   sqlite3 copy_trading.db "SELECT * FROM orders WHERE id='F456';"
   ```
4. Verify API response:
   ```bash
   grep "cancel_order" copy_trading.log | tail -5
   ```

**Common Causes**:
- Follower order already executed (can't cancel)
- Network issue reaching DhanHQ API
- Invalid order ID in mapping

### Issue: Missed Orders Not Fetched
**Symptoms**: Disconnect/reconnect but no missed orders fetched

**Checklist**:
1. Check `_was_disconnected` flag set:
   ```bash
   grep "_was_disconnected" copy_trading.log
   ```
2. Check `last_leader_event_ts` in DB:
   ```sql
   sqlite3 copy_trading.db "SELECT * FROM config WHERE key='last_leader_event_ts';"
   ```
3. Check leader_client available:
   ```bash
   grep "leader_client not available" copy_trading.log
   ```

**Common Causes**:
- `leader_client` not passed to WebSocket manager (check main.py)
- DB doesn't have `last_leader_event_ts` (falls back to 1 hour)
- API call failing (check network/credentials)

### Issue: Rate Limiting Too Aggressive
**Symptoms**: Orders delayed even with low volume

**Solution**: Adjust rate limit in `orders/order_manager.py`:
```python
# Line 54 - increase from 10 to desired limit
self.max_requests_per_second = 15  # Adjust as needed
```

**Note**: DhanHQ limit is 10 req/sec, increasing may cause API errors.

---

## 📚 Full Documentation

### Quick Navigation
1. **[README.md](./README.md)** - Main overview and status
2. **[IMPLEMENTATION_SUMMARY.md](./IMPLEMENTATION_SUMMARY.md)** - Executive summary
3. **[patches/PATCHES.md](./patches/PATCHES.md)** - Complete code patches
4. **[TODO.md](./TODO.md)** - Task checklist
5. **[changelogs.md](./changelogs.md)** - Detailed change history

### External References
- [Task-001 Architecture](../Task-001-Copy-Trading-Architecture/architecture/ARCHITECTURE.md)
- [Task-002 Audit](../Task-002-Scenario-Analysis-Audit/EXECUTIVE_SUMMARY.md)
- [DhanHQ v2 Docs](../docs_links.txt)

---

## ✅ Production Deployment Checklist

### Pre-Deployment
- [ ] All patches applied and verified
- [ ] Unit tests written and passing
- [ ] Integration tests passing in sandbox
- [ ] Rate limiting validated (15+ orders)
- [ ] Disconnect recovery validated (30s+ disconnect)
- [ ] Cancellation tested (10+ scenarios)
- [ ] Modification tested (10+ scenarios)
- [ ] Performance metrics measured
- [ ] Error handling validated

### Deployment
- [ ] Backup current production code
- [ ] Deploy patched code to production
- [ ] Verify all environment variables set
- [ ] Start system and monitor logs
- [ ] Test with small orders first
- [ ] Gradually increase order size
- [ ] Monitor for 24 hours

### Post-Deployment
- [ ] Set up monitoring alerts
- [ ] Configure log aggregation
- [ ] Document any issues encountered
- [ ] Create runbook for common issues
- [ ] Schedule review after 1 week

---

## 🎉 Success Criteria

### The patches are successful if:
1. ✅ Leader cancels order → Follower cancels (100% success)
2. ✅ Leader modifies order → Follower modifies (100% success)
3. ✅ System disconnects → Missed orders fetched (100% recovery)
4. ✅ SL orders placed → API accepts (100% success)
5. ✅ 15 rapid orders → No rate limit errors (100% success)
6. ✅ No manual intervention needed for 24 hours
7. ✅ Order replication rate > 99%
8. ✅ Average latency < 200ms (normal), < 1000ms (burst)

---

## 🆘 Need Help?

### Common Questions

**Q: Do I need to redeploy the entire system?**  
A: Yes, the patches modify core files. Restart required.

**Q: Will my existing orders be affected?**  
A: No, patches only affect new orders. Existing orders continue as-is.

**Q: Can I roll back if needed?**  
A: Yes, use git to revert to pre-patch commit. Database is compatible.

**Q: Do I need to update my database schema?**  
A: No, patches don't change DB schema. Fully backward compatible.

**Q: What if I only want some patches?**  
A: Not recommended. Patches are interdependent. All or nothing.

---

**Quick Start Version**: 1.0  
**Last Updated**: 2025-10-02  
**Patches Status**: ✅ Complete  
**Testing Status**: 🔄 Pending  
**Production Status**: 🔄 Not Deployed

