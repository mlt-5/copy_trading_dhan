# Options Copy Trading System Architecture

## Executive Summary

This document describes a real-time options copy trading system that replicates orders from a leader account (Account A) to a follower account (Account B) using DhanHQ API v2, Python, and SQLite3.

**Key Capabilities:**
- Real-time order detection via WebSocket
- Instant order replication with position sizing
- Options-specific handling (strikes, expiries, Greeks)
- Capital-proportional quantity adjustment
- Resilient state management with SQLite
- Comprehensive audit trail

---

## System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Copy Trading System                          │
└─────────────────────────────────────────────────────────────────────┘

┌──────────────────┐                              ┌──────────────────┐
│   Leader Account │                              │ Follower Account │
│    (Account A)   │                              │   (Account B)    │
└────────┬─────────┘                              └────────▲─────────┘
         │                                                 │
         │ Orders/Updates                                  │ Replicated
         │                                                 │ Orders
         ▼                                                 │
┌─────────────────────────────────────────────────────────┴──────────┐
│                        DhanHQ API v2                                │
│  ┌──────────────────────────┐  ┌──────────────────────────────┐   │
│  │  WebSocket Order Stream  │  │  REST API (Orders/Portfolio)  │   │
│  └──────────────────────────┘  └──────────────────────────────┘   │
└────────────┬───────────────────────────────────▲───────────────────┘
             │                                    │
             │ Real-time Updates                  │ Place Orders
             ▼                                    │
┌────────────────────────────────────────────────┴───────────────────┐
│                     Copy Trading Application                        │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │                    Main Orchestrator                         │  │
│  │              (Event Loop & State Machine)                    │  │
│  └──┬────────────────────────────────────────────────────────┬─┘  │
│     │                                                         │    │
│  ┌──▼──────────────────┐                      ┌──────────────▼──┐ │
│  │  WebSocket Manager  │                      │  Order Manager  │ │
│  │  - Leader stream    │                      │  - Validation   │ │
│  │  - Reconnection     │                      │  - Placement    │ │
│  │  - Heartbeat        │                      │  - Tracking     │ │
│  └──┬──────────────────┘                      └──────────────▲──┘ │
│     │                                                         │    │
│  ┌──▼──────────────────────────────────────────────────────┬─┘    │
│  │              Position Sizing Engine                      │      │
│  │  - Capital calculation                                   │      │
│  │  - Lot size adjustment                                   │      │
│  │  - Risk management                                       │      │
│  └─────────────┬────────────────────────────────────────────┘      │
│                │                                                    │
│  ┌─────────────▼──────────────────────────────────────────────┐   │
│  │                  SQLite Persistence Layer                   │   │
│  │  - Order tracking    - Audit trail    - Position snapshots │   │
│  │  - Instrument cache  - Config storage - Error logs         │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │               Configuration & Authentication                 │  │
│  │  - Multi-account credentials  - Rate limiting               │  │
│  │  - Environment variables      - Circuit breaking            │  │
│  └─────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Component Details

### 1. Configuration Manager

**Purpose**: Centralized configuration, authentication, and environment management

**Responsibilities**:
- Load credentials from environment variables
- Manage leader and follower account configurations
- Provide HTTP/WebSocket client settings
- Handle rate limiting parameters
- Support sandbox vs production environments

**Key Classes**:
- `AccountConfig`: Stores credentials and account metadata
- `SystemConfig`: Global settings (timeouts, retries, etc.)
- `ConfigLoader`: Reads from environment and validates

**Configuration Schema**:
```python
LEADER_CLIENT_ID        # Leader account client ID
LEADER_ACCESS_TOKEN     # Leader account access token
FOLLOWER_CLIENT_ID      # Follower account client ID
FOLLOWER_ACCESS_TOKEN   # Follower account access token
DHAN_ENV                # prod or sandbox
COPY_RATIO              # Quantity adjustment ratio (default: auto-calculate)
MAX_POSITION_SIZE_PCT   # Maximum position size as % of capital (risk limit)
```

---

### 2. Authentication Module

**Purpose**: Handle DhanHQ authentication for both accounts

**Responsibilities**:
- Initialize DhanHQ SDK clients for leader and follower
- Validate credentials on startup
- Support token rotation
- Redact sensitive data in logs

**Key Functions**:
- `authenticate_leader()`: Initialize leader account client
- `authenticate_follower()`: Initialize follower account client
- `validate_credentials()`: Test API connectivity

---

### 3. WebSocket Manager

**Purpose**: Real-time order update stream from leader account

**Responsibilities**:
- Establish WebSocket connection for leader orders
- Handle reconnection with exponential backoff
- Process order lifecycle events
- Maintain connection health (heartbeats)
- Queue messages during reconnection

**Event Flow**:
```
Connect → Authenticate → Subscribe → Process Events
   ↓                                      ↓
Reconnect ←────────── Connection Lost ←───┘
```

**Event Types Monitored**:
- Order placed
- Order executed (full/partial)
- Order cancelled
- Order rejected
- Order modified

**Key Classes**:
- `OrderStreamClient`: WebSocket connection manager
- `OrderEventHandler`: Process incoming order events
- `ReconnectionStrategy`: Backoff logic with jitter

---

### 4. Order Manager

**Purpose**: Place, track, and manage orders in follower account

**Responsibilities**:
- Validate order parameters
- Place orders via DhanHQ REST API
- Track order status and lifecycle
- Handle order modifications and cancellations
- Implement retry logic with idempotency

**Order Validation**:
- Exchange segment validation
- Product type compatibility
- Price band checks
- Margin sufficiency (pre-trade)
- Options-specific validations (expiry, strike, lot size)

**Order Placement Flow**:
```
Leader Order Detected
    ↓
Validate Order Parameters
    ↓
Calculate Adjusted Quantity (Position Sizing Engine)
    ↓
Pre-trade Checks (Margin, Risk Limits)
    ↓
Place Order in Follower Account
    ↓
Track Order ID & Status
    ↓
Update SQLite Audit Trail
```

**Key Classes**:
- `OrderPlacer`: Execute orders via API
- `OrderValidator`: Pre-flight validation
- `OrderTracker`: Monitor order status
- `IdempotencyManager`: Prevent duplicate orders

---

### 5. Position Sizing Engine

**Purpose**: Calculate appropriate order quantities for follower account

**Responsibilities**:
- Fetch real-time fund limits for both accounts
- Calculate capital ratio between accounts
- Adjust quantities based on available capital
- Respect lot sizes for options contracts
- Apply risk management limits

**Sizing Strategies**:

1. **Capital-Proportional** (Default):
   ```
   follower_qty = (leader_qty × follower_capital) / leader_capital
   adjusted_qty = round_to_lot_size(follower_qty)
   ```

2. **Fixed Ratio**:
   ```
   follower_qty = leader_qty × copy_ratio
   adjusted_qty = round_to_lot_size(follower_qty)
   ```

3. **Risk-Based**:
   ```
   max_position_value = follower_capital × max_position_pct
   follower_qty = max_position_value / (premium × lot_size)
   adjusted_qty = round_to_lot_size(follower_qty)
   ```

**Options-Specific Handling**:
- Lot size normalization (e.g., NIFTY = 50, BANKNIFTY = 15)
- Premium calculation for position value
- Strike and expiry matching
- Greeks consideration (optional)

**Key Classes**:
- `PositionSizer`: Core sizing logic
- `CapitalCalculator`: Fetch and compute capital metrics
- `LotSizeMapper`: Instrument-specific lot sizes
- `RiskManager`: Apply position limits

---

### 6. SQLite Persistence Layer

**Purpose**: Durable storage for state, audit, and cache

**Database Schema**:

#### Core Tables

**orders**
```sql
CREATE TABLE orders (
    id TEXT PRIMARY KEY,                    -- DhanHQ order ID
    account_type TEXT NOT NULL,             -- 'leader' or 'follower'
    correlation_id TEXT,                    -- Link leader to follower orders
    status TEXT NOT NULL,                   -- PENDING/OPEN/EXECUTED/CANCELLED/REJECTED
    side TEXT NOT NULL,                     -- BUY/SELL
    product TEXT NOT NULL,                  -- MIS/CNC/NRML
    order_type TEXT NOT NULL,               -- MARKET/LIMIT/SL/SL-M
    validity TEXT NOT NULL,                 -- DAY/IOC
    security_id TEXT NOT NULL,
    exchange_segment TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    price REAL,
    trigger_price REAL,
    disclosed_qty INTEGER,
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL,
    raw_request JSON,
    raw_response JSON
);

CREATE INDEX idx_orders_correlation ON orders(correlation_id);
CREATE INDEX idx_orders_account ON orders(account_type, created_at);
CREATE INDEX idx_orders_status ON orders(status);
```

**order_events**
```sql
CREATE TABLE order_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id TEXT NOT NULL,
    event_type TEXT NOT NULL,              -- PLACED/EXECUTED/CANCELLED/REJECTED/MODIFIED
    event_data JSON,
    event_ts INTEGER NOT NULL,
    sequence INTEGER,
    UNIQUE(order_id, sequence),
    FOREIGN KEY(order_id) REFERENCES orders(id)
);

CREATE INDEX idx_order_events_order_ts ON order_events(order_id, event_ts);
```

**trades**
```sql
CREATE TABLE trades (
    id TEXT PRIMARY KEY,                   -- Trade ID
    order_id TEXT NOT NULL,
    account_type TEXT NOT NULL,
    trade_ts INTEGER NOT NULL,
    quantity INTEGER NOT NULL,
    price REAL NOT NULL,
    exchange_segment TEXT,
    security_id TEXT,
    raw_data JSON,
    FOREIGN KEY(order_id) REFERENCES orders(id)
);

CREATE INDEX idx_trades_order ON trades(order_id);
CREATE INDEX idx_trades_account_ts ON trades(account_type, trade_ts);
```

**positions**
```sql
CREATE TABLE positions (
    snapshot_ts INTEGER NOT NULL,
    account_type TEXT NOT NULL,
    security_id TEXT NOT NULL,
    exchange_segment TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    avg_price REAL NOT NULL,
    realized_pl REAL,
    unrealized_pl REAL,
    product TEXT,
    raw_data JSON,
    PRIMARY KEY(snapshot_ts, account_type, security_id, exchange_segment)
);

CREATE INDEX idx_positions_ts ON positions(snapshot_ts);
CREATE INDEX idx_positions_account ON positions(account_type, snapshot_ts);
```

**funds**
```sql
CREATE TABLE funds (
    snapshot_ts INTEGER NOT NULL,
    account_type TEXT NOT NULL,
    available_balance REAL NOT NULL,
    collateral REAL,
    margin_used REAL,
    raw_data JSON,
    PRIMARY KEY(snapshot_ts, account_type)
);

CREATE INDEX idx_funds_account_ts ON funds(account_type, snapshot_ts);
```

**instruments**
```sql
CREATE TABLE instruments (
    security_id TEXT PRIMARY KEY,
    exchange_segment TEXT NOT NULL,
    symbol TEXT NOT NULL,
    name TEXT,
    instrument_type TEXT,                  -- OPTIDX/OPTSTK/FUTIDX/FUTSTK/EQUITY
    expiry_date TEXT,
    strike_price REAL,
    option_type TEXT,                      -- CE/PE
    lot_size INTEGER NOT NULL,
    tick_size REAL NOT NULL,
    underlying_security_id TEXT,
    meta JSON,
    updated_at INTEGER NOT NULL
);

CREATE INDEX idx_instruments_symbol ON instruments(symbol, exchange_segment);
CREATE INDEX idx_instruments_underlying ON instruments(underlying_security_id, expiry_date);
```

**copy_mappings**
```sql
CREATE TABLE copy_mappings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    leader_order_id TEXT NOT NULL UNIQUE,
    follower_order_id TEXT UNIQUE,
    leader_quantity INTEGER NOT NULL,
    follower_quantity INTEGER NOT NULL,
    sizing_strategy TEXT,                  -- 'capital_proportional', 'fixed_ratio', 'risk_based'
    capital_ratio REAL,
    status TEXT NOT NULL,                  -- 'pending', 'placed', 'failed', 'cancelled'
    error_message TEXT,
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL,
    FOREIGN KEY(leader_order_id) REFERENCES orders(id),
    FOREIGN KEY(follower_order_id) REFERENCES orders(id)
);

CREATE INDEX idx_copy_mappings_leader ON copy_mappings(leader_order_id);
CREATE INDEX idx_copy_mappings_status ON copy_mappings(status, created_at);
```

**audit_log**
```sql
CREATE TABLE audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    action TEXT NOT NULL,                  -- API action (place_order, cancel_order, etc.)
    account_type TEXT NOT NULL,
    request_data JSON,
    response_data JSON,
    status_code INTEGER,
    error_message TEXT,
    duration_ms INTEGER,
    ts INTEGER NOT NULL
);

CREATE INDEX idx_audit_action_ts ON audit_log(action, ts);
CREATE INDEX idx_audit_account ON audit_log(account_type, ts);
```

**config**
```sql
CREATE TABLE config (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    description TEXT,
    updated_at INTEGER NOT NULL
);

-- Initial config entries
INSERT OR REPLACE INTO config VALUES
    ('schema_version', '1', 'Database schema version', strftime('%s', 'now')),
    ('last_leader_event_ts', '0', 'Last processed leader event timestamp', strftime('%s', 'now')),
    ('copy_enabled', 'true', 'Global copy trading enabled flag', strftime('%s', 'now'));
```

**Migrations**:
- Maintain versioned migration scripts in `src/database/migrations/`
- Track current version in `config.schema_version`
- Apply migrations sequentially on startup

**Connection Management**:
- Enable WAL mode for concurrent reads
- Use prepared statements for performance
- Set busy_timeout to 5000ms
- Single connection per process with connection pooling

---

### 7. Main Orchestrator

**Purpose**: Event loop and state machine coordination

**Responsibilities**:
- Initialize all components
- Start WebSocket listeners
- Coordinate order replication workflow
- Handle graceful shutdown
- Monitor system health

**State Machine**:
```
INITIALIZING
    ↓
AUTHENTICATING
    ↓
CONNECTING_WEBSOCKET
    ↓
READY (Monitoring)
    ↓
PROCESSING_ORDER (on event)
    ↓
READY (loop continues)
    ↓
SHUTTING_DOWN (on signal)
    ↓
STOPPED
```

**Event Processing Loop**:
```python
while running:
    # 1. Receive order event from leader WebSocket
    event = await ws_manager.get_next_event()
    
    # 2. Validate event type and extract order details
    if not event.is_relevant():
        continue
    
    # 3. Check if order should be replicated (filters, rules)
    if not should_replicate(event):
        log_skip_reason(event)
        continue
    
    # 4. Calculate follower order quantity
    follower_qty = position_sizer.calculate(event.order)
    
    # 5. Validate and place follower order
    follower_order = await order_manager.place_order(
        leader_order=event.order,
        adjusted_quantity=follower_qty
    )
    
    # 6. Store mapping and audit trail
    db.save_copy_mapping(event.order.id, follower_order.id)
    
    # 7. Track follower order status
    order_tracker.monitor(follower_order.id)
```

**Key Classes**:
- `CopyTradingOrchestrator`: Main coordinator
- `EventProcessor`: Handle incoming events
- `HealthMonitor`: System health checks
- `SignalHandler`: Graceful shutdown

---

## Data Flow Diagrams

### Order Replication Flow

```
Leader Places Order
        ↓
DhanHQ Processes Order
        ↓
WebSocket Event Generated
        ↓
Copy Trading App Receives Event
        ↓
┌───────────────────────────────────────┐
│ 1. Parse & Validate Event             │
│    - Extract order details            │
│    - Validate event type              │
└───────────┬───────────────────────────┘
            ↓
┌───────────────────────────────────────┐
│ 2. Apply Replication Rules            │
│    - Check if options order           │
│    - Check enabled status             │
│    - Apply filters (if any)           │
└───────────┬───────────────────────────┘
            ↓
┌───────────────────────────────────────┐
│ 3. Fetch Capital & Positions          │
│    - Leader funds & positions         │
│    - Follower funds & positions       │
│    - Calculate available capital      │
└───────────┬───────────────────────────┘
            ↓
┌───────────────────────────────────────┐
│ 4. Calculate Adjusted Quantity        │
│    - Apply sizing strategy            │
│    - Round to lot size                │
│    - Validate risk limits             │
└───────────┬───────────────────────────┘
            ↓
┌───────────────────────────────────────┐
│ 5. Pre-trade Validation               │
│    - Sufficient margin check          │
│    - Position limit check             │
│    - Instrument availability          │
└───────────┬───────────────────────────┘
            ↓
┌───────────────────────────────────────┐
│ 6. Place Follower Order               │
│    - Call DhanHQ place_order API      │
│    - Handle API response/errors       │
│    - Store order ID                   │
└───────────┬───────────────────────────┘
            ↓
┌───────────────────────────────────────┐
│ 7. Save to Database                   │
│    - Store both orders                │
│    - Create copy mapping              │
│    - Add audit log entry              │
└───────────┬───────────────────────────┘
            ↓
┌───────────────────────────────────────┐
│ 8. Monitor Execution                  │
│    - Track follower order status      │
│    - Handle partial fills             │
│    - Log final state                  │
└───────────────────────────────────────┘
```

---

## Error Handling & Recovery

### Circuit Breaker Pattern

**States**:
- **CLOSED**: Normal operation, requests flow through
- **OPEN**: Errors exceed threshold, block requests temporarily
- **HALF_OPEN**: Test if service recovered, allow limited requests

**Configuration**:
- Failure threshold: 5 consecutive failures
- Timeout: 60 seconds
- Half-open test requests: 1

**Implementation**:
```python
if circuit_breaker.is_open():
    log_error("Circuit breaker open, skipping replication")
    return

try:
    place_order(...)
    circuit_breaker.record_success()
except Exception as e:
    circuit_breaker.record_failure()
    raise
```

### Retry Strategy

**Idempotent Operations** (retryable):
- Fetch orders, positions, funds
- WebSocket reconnection

**Non-Idempotent Operations** (no automatic retry):
- Place order (without idempotency key)
- Cancel order (unless already executed)

**Retry Configuration**:
- Max retries: 3
- Initial delay: 1 second
- Backoff multiplier: 2 (exponential)
- Jitter: ±20%

### Error Classification

| Error Type | Action | Logged | Alerted |
|------------|--------|--------|---------|
| Network timeout | Retry with backoff | Yes | After 3 failures |
| Invalid credentials | Stop system | Yes | Immediately |
| Insufficient margin | Skip order, log | Yes | If frequent |
| Rate limit (429) | Backoff, retry | Yes | No |
| Invalid order params | Skip order, log | Yes | If frequent |
| WebSocket disconnect | Reconnect with backoff | Yes | After 5 failures |
| Database lock | Retry with timeout | Yes | If persistent |

---

## Security & Compliance

### Credential Management

- Store credentials in environment variables only
- Never log full access tokens
- Support token rotation without restart
- Separate leader and follower credentials

### Audit Trail

- Log all order placements with timestamps
- Store request/response payloads (redacted)
- Track all configuration changes
- Maintain immutable audit log

### Data Privacy

- Redact PII from logs
- Encrypt database at rest (OS-level recommended)
- Limit access to database files
- No external data transmission beyond DhanHQ API

---

## Performance Considerations

### Latency Budget

- WebSocket event receipt: ~100-500ms
- Order validation: <50ms
- Position sizing calculation: <50ms
- DhanHQ place_order API: ~200-1000ms
- Database write: <20ms
- **Total end-to-end**: <2 seconds target

### Optimization Strategies

1. **Pre-fetch Data**:
   - Cache instrument metadata (lot sizes, tick sizes)
   - Refresh funds/positions every 30 seconds
   - Keep running capital ratio

2. **Async Operations**:
   - Non-blocking WebSocket processing
   - Parallel API calls where possible
   - Background database writes

3. **Connection Pooling**:
   - Reuse HTTP connections
   - Persistent WebSocket with keepalive
   - Single SQLite connection with WAL mode

4. **Rate Limiting**:
   - Client-side request throttling
   - Respect DhanHQ rate limits
   - Queue overflow handling

---

## Monitoring & Observability

### Key Metrics

- **Replication Lag**: Time from leader order to follower order placed
- **Success Rate**: % of orders successfully replicated
- **API Latency**: p50, p95, p99 for DhanHQ API calls
- **WebSocket Uptime**: Connection stability %
- **Database Performance**: Write latency, read latency

### Logging

**Log Levels**:
- DEBUG: WebSocket messages, API requests/responses
- INFO: Orders placed, configuration changes
- WARNING: Retries, skipped orders, rate limits
- ERROR: API failures, validation errors
- CRITICAL: Authentication failures, circuit breaker open

**Structured Logging**:
```python
logger.info("follower_order_placed", extra={
    "leader_order_id": "...",
    "follower_order_id": "...",
    "symbol": "NIFTY25000CE",
    "leader_qty": 50,
    "follower_qty": 15,
    "latency_ms": 1234
})
```

### Health Checks

- WebSocket connection status
- Last processed event timestamp
- Database connectivity
- API connectivity (both accounts)
- Available margin in follower account

---

## Deployment & Operations

### System Requirements

- Python 3.9+
- 100MB disk space (+ SQLite database growth)
- 512MB RAM minimum
- Network connectivity with <500ms latency to DhanHQ

### Startup Sequence

1. Load configuration from environment
2. Initialize database (apply migrations)
3. Authenticate both accounts
4. Fetch and cache instrument metadata
5. Initialize position sizing (fetch funds)
6. Connect WebSocket to leader orders
7. Enter ready state (event loop)

### Graceful Shutdown

1. Stop accepting new events
2. Complete in-flight order placements
3. Flush database writes
4. Close WebSocket connection
5. Close database connection
6. Log shutdown complete

### Backup & Recovery

**Database Backup**:
- Daily automated backups via `VACUUM INTO`
- Retain 7 days of backups
- Test restore procedure monthly

**State Recovery**:
- On restart, reconcile orders from last 24 hours
- Compare database state with API state
- Update any missed status changes

---

## Testing Strategy

### Unit Tests

- Configuration loading and validation
- Position sizing calculations
- Lot size rounding logic
- Order parameter validation
- Database CRUD operations

### Integration Tests

- DhanHQ API connectivity (sandbox)
- WebSocket connection and reconnection
- End-to-end order replication (small qty)
- Database migrations
- Error handling scenarios

### Load Tests

- Concurrent order processing
- Database write performance
- WebSocket message throughput
- Memory usage under sustained load

---

## Future Enhancements

### Phase 2 Features

1. **Multi-follower support**: Copy from 1 leader to N followers
2. **Partial replication**: Copy only specific instruments/strategies
3. **Advanced position sizing**: Kelly criterion, volatility-based
4. **Smart order routing**: Split large orders, iceberg orders
5. **Dashboard UI**: Web interface for monitoring and control

### Phase 3 Features

1. **ML-based filtering**: Skip low-probability trades
2. **Backtesting engine**: Test strategies on historical data
3. **Portfolio optimization**: Correlation-aware position sizing
4. **Multi-leader support**: Aggregate signals from multiple leaders

---

## Appendix

### Glossary

- **Leader Account**: Source account whose orders are replicated (Account A)
- **Follower Account**: Destination account that copies orders (Account B)
- **Position Sizing**: Calculating appropriate quantity for follower orders
- **Lot Size**: Minimum tradable quantity for options/futures (e.g., 50 for NIFTY)
- **Copy Ratio**: Multiplier for follower quantities (if fixed ratio strategy used)
- **Circuit Breaker**: Pattern to prevent cascading failures

### References

- DhanHQ API Documentation: https://dhanhq.co/docs/v2/
- DhanHQ Python SDK: https://pypi.org/project/dhanhq/
- DhanHQ API Reference: https://api.dhan.co/v2/#/

---

**Document Version**: 1.0  
**Last Updated**: 2025-10-02  
**Author**: Copy Trading System Architecture Team


