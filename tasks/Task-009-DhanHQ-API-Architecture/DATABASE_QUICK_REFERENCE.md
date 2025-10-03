# Database Quick Reference Guide

**Version**: 3.0  
**Date**: October 3, 2025  
**For**: Copy Trading System - DhanHQ v2

---

## Quick Start

### Initialize Database
```python
from src.core.database import init_database, get_db

# Initialize (creates schema if needed)
db = init_database()

# Get existing connection
db = get_db()
```

### Check Schema Version
```python
version = db.get_schema_version()
print(f"Schema version: {version}")  # Should be 3
```

---

## Common Operations

### 1. Orders

#### Save Order
```python
from src.core.models import Order
import time

order = Order(
    id="order123",
    account_type="leader",
    status="OPEN",
    side="BUY",
    product="INTRADAY",
    order_type="LIMIT",
    validity="DAY",
    security_id="1234",
    exchange_segment="NSE_EQ",
    quantity=100,
    price=1500.0,
    created_at=int(time.time()),
    updated_at=int(time.time())
)

db.save_order(order)
```

#### Get Order
```python
order = db.get_order("order123")
```

#### Update Order Status
```python
db.update_order_status("order123", "EXECUTED")
```

#### Get Recent Orders
```python
orders = db.get_orders_by_account("leader", limit=50)
```

### 2. Positions

#### Save Position Snapshot
```python
from src.core.models import Position

positions = [
    Position(
        snapshot_ts=int(time.time()),
        account_type="leader",
        security_id="1234",
        exchange_segment="NSE_EQ",
        quantity=100,
        avg_price=1500.0,
        realized_pl=0.0,
        unrealized_pl=250.0,
        product="INTRADAY"
    )
]

db.save_positions_snapshot(positions)
```

#### Get Latest Positions
```python
positions = db.get_latest_positions("leader")
```

### 3. Funds

#### Save Funds Snapshot
```python
from src.core.models import Funds

funds = Funds(
    snapshot_ts=int(time.time()),
    account_type="follower",
    available_balance=50000.0,
    collateral=10000.0,
    margin_used=5000.0
)

db.save_funds_snapshot(funds)
```

#### Get Latest Funds
```python
funds = db.get_latest_funds("follower")
print(f"Available: {funds.available_balance}")
```

### 4. Copy Mappings

#### Save Copy Mapping
```python
from src.core.models import CopyMapping

mapping = CopyMapping(
    leader_order_id="leader_order_123",
    follower_order_id="follower_order_456",
    leader_quantity=100,
    follower_quantity=50,
    status="placed",
    sizing_strategy="capital_proportional",
    capital_ratio=0.5,
    created_at=int(time.time()),
    updated_at=int(time.time())
)

mapping_id = db.save_copy_mapping(mapping)
```

#### Get Copy Mapping
```python
mapping = db.get_copy_mapping_by_leader("leader_order_123")
```

#### Update Copy Mapping Status
```python
db.update_copy_mapping_status(
    leader_order_id="leader_order_123",
    status="failed",
    error_message="Insufficient funds"
)
```

### 5. Order Events

#### Save Order Event
```python
from src.core.models import OrderEvent

event = OrderEvent(
    order_id="order123",
    event_type="EXECUTED",
    event_data='{"filled_qty": 100, "price": 1500.0}',
    event_ts=int(time.time()),
    sequence=1
)

db.save_order_event(event)
```

#### Get Order Events
```python
events = db.get_order_events("order123")
for event in events:
    print(f"{event.event_type} at {event.event_ts}")
```

### 6. Instruments

#### Save Instrument
```python
from src.core.models import Instrument

instrument = Instrument(
    security_id="1234",
    exchange_segment="NSE_EQ",
    symbol="RELIANCE",
    lot_size=1,
    tick_size=0.05,
    updated_at=int(time.time())
)

db.save_instrument(instrument)
```

#### Get Instrument
```python
instrument = db.get_instrument("1234")
print(f"{instrument.symbol} - Lot size: {instrument.lot_size}")
```

### 7. Audit Log

#### Log API Interaction
```python
db.log_audit(
    action="place_order",
    account_type="leader",
    request_data={"order_type": "LIMIT", "quantity": 100},
    response_data={"order_id": "order123", "status": "success"},
    status_code=200,
    duration_ms=150
)
```

### 8. Configuration

#### Get Config Value
```python
copy_enabled = db.get_config_value("copy_enabled")
print(f"Copy trading enabled: {copy_enabled}")
```

#### Set Config Value
```python
db.set_config_value(
    key="daily_loss_limit",
    value="10000",
    description="Daily loss limit in INR"
)
```

---

## Advanced Queries

### Active Orders with Copy Mappings
```sql
SELECT * FROM v_active_orders 
WHERE account_type = 'leader'
ORDER BY created_at DESC;
```

### Latest Positions with P&L
```sql
SELECT 
    security_id,
    net_qty,
    realized_pl,
    unrealized_pl,
    total_pl
FROM v_latest_positions
WHERE account_type = 'follower'
AND net_qty != 0
ORDER BY total_pl DESC;
```

### Risk Violations (Last 24 Hours)
```sql
SELECT 
    violation_type,
    actual_value,
    limit_value,
    action_taken,
    datetime(violated_at, 'unixepoch', 'localtime') as violated_time
FROM risk_violations
WHERE violated_at > (strftime('%s', 'now') - 86400)
AND account_type = 'follower'
ORDER BY violated_at DESC;
```

### WebSocket Connection Health
```sql
SELECT 
    account_type,
    status,
    seconds_since_heartbeat,
    connect_attempts,
    datetime(last_heartbeat_at, 'unixepoch', 'localtime') as last_heartbeat
FROM v_active_websocket_connections;
```

### Daily P&L Summary
```sql
SELECT 
    date(trade_ts, 'unixepoch', 'localtime') as trade_date,
    account_type,
    side,
    SUM(quantity) as total_qty,
    SUM(trade_value) as total_value,
    SUM(total_charges) as total_charges,
    SUM(net_amount) as net_amount
FROM trades
WHERE trade_ts > (strftime('%s', 'now') - 86400 * 30)  -- Last 30 days
GROUP BY trade_date, account_type, side
ORDER BY trade_date DESC;
```

### Recent Errors by Type
```sql
SELECT * FROM v_recent_errors
ORDER BY error_count DESC, last_occurred DESC
LIMIT 20;
```

### Forever Orders (GTT) Status
```sql
SELECT 
    id,
    security_id,
    trigger_type,
    trigger_price_above,
    trigger_price_below,
    status,
    datetime(created_at, 'unixepoch', 'localtime') as created_time
FROM forever_orders
WHERE account_type = 'leader'
AND status = 'ACTIVE'
ORDER BY created_at DESC;
```

### Order Execution Rate
```sql
SELECT 
    account_type,
    COUNT(CASE WHEN status = 'EXECUTED' THEN 1 END) as executed,
    COUNT(CASE WHEN status = 'CANCELLED' THEN 1 END) as cancelled,
    COUNT(CASE WHEN status = 'REJECTED' THEN 1 END) as rejected,
    COUNT(*) as total,
    ROUND(COUNT(CASE WHEN status = 'EXECUTED' THEN 1 END) * 100.0 / COUNT(*), 2) as execution_rate
FROM orders
WHERE created_at > (strftime('%s', 'now') - 86400)  -- Last 24 hours
GROUP BY account_type;
```

---

## Database Maintenance

### Daily Tasks

#### Check Database Size
```python
import os
db_size = os.path.getsize(db.db_path)
print(f"Database size: {db_size / (1024*1024):.2f} MB")
```

#### Verify Schema Version
```python
version = db.get_schema_version()
assert version == 3, f"Expected schema v3, got v{version}"
```

### Weekly Tasks

#### Archive Old Data
```sql
-- Archive audit logs older than 90 days
DELETE FROM audit_log WHERE ts < (strftime('%s', 'now') - 86400 * 90);

-- Archive order events older than 90 days
DELETE FROM order_events WHERE event_ts < (strftime('%s', 'now') - 86400 * 90);

-- Archive trades older than 1 year
DELETE FROM trades WHERE trade_ts < (strftime('%s', 'now') - 86400 * 365);
```

#### Optimize Database
```sql
-- Rebuild indexes and reclaim space
VACUUM;

-- Update statistics for query optimizer
ANALYZE;
```

#### Check WAL Size
```sql
PRAGMA wal_checkpoint(TRUNCATE);
```

### Monthly Tasks

#### Database Integrity Check
```sql
PRAGMA integrity_check;
```

#### Backup Database
```bash
# Create backup with timestamp
sqlite3 copy_trading.db ".backup 'backup_$(date +%Y%m%d_%H%M%S).db'"

# Or use cp with WAL checkpoint
sqlite3 copy_trading.db "PRAGMA wal_checkpoint(TRUNCATE);"
cp copy_trading.db backup_$(date +%Y%m%d_%H%M%S).db
```

---

## Migration

### Migrate from v1/v2 to v3
```bash
# Backup first!
cp copy_trading.db copy_trading_backup.db

# Run migration
sqlite3 copy_trading.db < src/core/database/migrate_to_v3.sql
```

### Create Fresh v3 Database
```python
from src.core.database import DatabaseManager

db = DatabaseManager("copy_trading.db")
db.connect()
db.initialize_schema()  # Uses schema.sql (v1)

# Then run migration to v3
with open("src/core/database/migrate_to_v3.sql", "r") as f:
    db.conn.executescript(f.read())
```

### Use v3 Directly
```python
# For new installations, use schema_v3_comprehensive.sql directly
from src.core.database import DatabaseManager

db = DatabaseManager("copy_trading.db")
db.connect()

# Initialize with v3 schema
with open("src/core/database/schema_v3_comprehensive.sql", "r") as f:
    db.conn.executescript(f.read())
```

---

## Troubleshooting

### Database Locked
```python
# Increase timeout
db.conn.execute("PRAGMA busy_timeout = 10000")

# Or use WAL mode (already enabled by default)
db.conn.execute("PRAGMA journal_mode = WAL")
```

### Corrupted Database
```bash
# Check integrity
sqlite3 copy_trading.db "PRAGMA integrity_check;"

# If corrupted, restore from backup
cp copy_trading_backup.db copy_trading.db

# Or export and reimport
sqlite3 copy_trading.db ".dump" > dump.sql
sqlite3 copy_trading_new.db < dump.sql
```

### Slow Queries
```sql
-- Analyze query performance
EXPLAIN QUERY PLAN SELECT ...;

-- Rebuild indexes
REINDEX;

-- Update statistics
ANALYZE;
```

---

## Performance Tips

1. **Use Transactions**: Batch multiple writes in a single transaction
   ```python
   db.conn.execute("BEGIN TRANSACTION")
   try:
       # Multiple writes
       db.save_order(order1)
       db.save_order(order2)
       db.conn.commit()
   except Exception as e:
       db.conn.rollback()
       raise
   ```

2. **Use Prepared Statements**: Already handled by DatabaseManager methods

3. **Index Usage**: Queries should use indexes - check with EXPLAIN QUERY PLAN

4. **WAL Mode**: Already enabled by default for concurrent reads

5. **Regular Maintenance**: Run VACUUM and ANALYZE weekly

---

## Schema Reference

For complete schema details, see:
- **DATABASE_SCHEMA_V3.md** - Full documentation
- **schema_v3_comprehensive.sql** - SQL schema
- **migrate_to_v3.sql** - Migration script

---

## Python API Reference

### DatabaseManager Methods

#### Order Operations
- `save_order(order: Order) -> None`
- `get_order(order_id: str) -> Optional[Order]`
- `get_orders_by_account(account_type: str, limit: int) -> List[Order]`
- `update_order_status(order_id: str, status: str) -> None`

#### Order Event Operations
- `save_order_event(event: OrderEvent) -> None`
- `get_order_events(order_id: str) -> List[OrderEvent]`

#### Copy Mapping Operations
- `save_copy_mapping(mapping: CopyMapping) -> int`
- `get_copy_mapping_by_leader(leader_order_id: str) -> Optional[CopyMapping]`
- `update_copy_mapping_status(leader_order_id: str, status: str, ...) -> None`

#### Position Operations
- `save_positions_snapshot(positions: List[Position]) -> None`
- `get_latest_positions(account_type: str) -> List[Position]`

#### Funds Operations
- `save_funds_snapshot(funds: Funds) -> None`
- `get_latest_funds(account_type: str) -> Optional[Funds]`

#### Instrument Operations
- `save_instrument(instrument: Instrument) -> None`
- `get_instrument(security_id: str) -> Optional[Instrument]`

#### Audit Operations
- `log_audit(action: str, account_type: str, ...) -> None`

#### Configuration Operations
- `get_config_value(key: str) -> Optional[str]`
- `set_config_value(key: str, value: str, description: Optional[str]) -> None`

---

**Last Updated**: October 3, 2025  
**Version**: 1.0  
**Schema Version**: 3.0

