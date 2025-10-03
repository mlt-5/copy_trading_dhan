-- Copy Trading System Database Schema
-- Version: 1
-- SQLite v3 with WAL mode for concurrent reads

-- Enable foreign keys
PRAGMA foreign_keys = ON;

-- Enable WAL mode for better concurrency
PRAGMA journal_mode = WAL;

-- Set synchronous mode
PRAGMA synchronous = NORMAL;

-- =============================================================================
-- Core Tables
-- =============================================================================

-- Orders table: Track all orders from both accounts
CREATE TABLE IF NOT EXISTS orders (
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
    raw_request TEXT,                       -- JSON
    raw_response TEXT,                      -- JSON
    CHECK (account_type IN ('leader', 'follower'))
);

CREATE INDEX IF NOT EXISTS idx_orders_correlation ON orders(correlation_id);
CREATE INDEX IF NOT EXISTS idx_orders_account ON orders(account_type, created_at);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
CREATE INDEX IF NOT EXISTS idx_orders_security ON orders(security_id, exchange_segment);

-- Order events: Track order lifecycle events
CREATE TABLE IF NOT EXISTS order_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id TEXT NOT NULL,
    event_type TEXT NOT NULL,              -- PLACED/EXECUTED/CANCELLED/REJECTED/MODIFIED/PARTIAL
    event_data TEXT,                       -- JSON
    event_ts INTEGER NOT NULL,
    sequence INTEGER,
    UNIQUE(order_id, sequence),
    FOREIGN KEY(order_id) REFERENCES orders(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_order_events_order_ts ON order_events(order_id, event_ts);
CREATE INDEX IF NOT EXISTS idx_order_events_type ON order_events(event_type, event_ts);

-- Trades: Track executed trades
CREATE TABLE IF NOT EXISTS trades (
    id TEXT PRIMARY KEY,                   -- Trade ID
    order_id TEXT NOT NULL,
    account_type TEXT NOT NULL,
    trade_ts INTEGER NOT NULL,
    quantity INTEGER NOT NULL,
    price REAL NOT NULL,
    exchange_segment TEXT,
    security_id TEXT,
    raw_data TEXT,                         -- JSON
    FOREIGN KEY(order_id) REFERENCES orders(id) ON DELETE CASCADE,
    CHECK (account_type IN ('leader', 'follower'))
);

CREATE INDEX IF NOT EXISTS idx_trades_order ON trades(order_id);
CREATE INDEX IF NOT EXISTS idx_trades_account_ts ON trades(account_type, trade_ts);
CREATE INDEX IF NOT EXISTS idx_trades_security ON trades(security_id, exchange_segment);

-- Positions: Periodic snapshots of positions
CREATE TABLE IF NOT EXISTS positions (
    snapshot_ts INTEGER NOT NULL,
    account_type TEXT NOT NULL,
    security_id TEXT NOT NULL,
    exchange_segment TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    avg_price REAL NOT NULL,
    realized_pl REAL,
    unrealized_pl REAL,
    product TEXT,
    raw_data TEXT,                         -- JSON
    PRIMARY KEY(snapshot_ts, account_type, security_id, exchange_segment),
    CHECK (account_type IN ('leader', 'follower'))
);

CREATE INDEX IF NOT EXISTS idx_positions_ts ON positions(snapshot_ts);
CREATE INDEX IF NOT EXISTS idx_positions_account ON positions(account_type, snapshot_ts);
CREATE INDEX IF NOT EXISTS idx_positions_security ON positions(security_id);

-- Funds: Periodic snapshots of fund limits
CREATE TABLE IF NOT EXISTS funds (
    snapshot_ts INTEGER NOT NULL,
    account_type TEXT NOT NULL,
    available_balance REAL NOT NULL,
    collateral REAL,
    margin_used REAL,
    raw_data TEXT,                         -- JSON
    PRIMARY KEY(snapshot_ts, account_type),
    CHECK (account_type IN ('leader', 'follower'))
);

CREATE INDEX IF NOT EXISTS idx_funds_account_ts ON funds(account_type, snapshot_ts);

-- Instruments: Cached instrument metadata
CREATE TABLE IF NOT EXISTS instruments (
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
    meta TEXT,                             -- JSON
    updated_at INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_instruments_symbol ON instruments(symbol, exchange_segment);
CREATE INDEX IF NOT EXISTS idx_instruments_underlying ON instruments(underlying_security_id, expiry_date);
CREATE INDEX IF NOT EXISTS idx_instruments_type ON instruments(instrument_type, exchange_segment);

-- Copy mappings: Link leader orders to follower orders
CREATE TABLE IF NOT EXISTS copy_mappings (
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
    FOREIGN KEY(follower_order_id) REFERENCES orders(id),
    CHECK (status IN ('pending', 'placed', 'failed', 'cancelled'))
);

CREATE INDEX IF NOT EXISTS idx_copy_mappings_leader ON copy_mappings(leader_order_id);
CREATE INDEX IF NOT EXISTS idx_copy_mappings_follower ON copy_mappings(follower_order_id);
CREATE INDEX IF NOT EXISTS idx_copy_mappings_status ON copy_mappings(status, created_at);

-- Audit log: Track all API interactions
CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    action TEXT NOT NULL,                  -- API action (place_order, cancel_order, etc.)
    account_type TEXT NOT NULL,
    request_data TEXT,                     -- JSON (redacted)
    response_data TEXT,                    -- JSON (redacted)
    status_code INTEGER,
    error_message TEXT,
    duration_ms INTEGER,
    ts INTEGER NOT NULL,
    CHECK (account_type IN ('leader', 'follower'))
);

CREATE INDEX IF NOT EXISTS idx_audit_action_ts ON audit_log(action, ts);
CREATE INDEX IF NOT EXISTS idx_audit_account ON audit_log(account_type, ts);

-- Configuration: System configuration and state
CREATE TABLE IF NOT EXISTS config (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    description TEXT,
    updated_at INTEGER NOT NULL
);

-- =============================================================================
-- Initial Configuration
-- =============================================================================

INSERT OR REPLACE INTO config (key, value, description, updated_at) VALUES
    ('schema_version', '1', 'Database schema version', strftime('%s', 'now')),
    ('last_leader_event_ts', '0', 'Last processed leader event timestamp', strftime('%s', 'now')),
    ('copy_enabled', 'true', 'Global copy trading enabled flag', strftime('%s', 'now')),
    ('last_position_snapshot_ts', '0', 'Last position snapshot timestamp', strftime('%s', 'now')),
    ('last_funds_snapshot_ts', '0', 'Last funds snapshot timestamp', strftime('%s', 'now'));

-- =============================================================================
-- Views for Convenience
-- =============================================================================

-- Active orders view
CREATE VIEW IF NOT EXISTS v_active_orders AS
SELECT 
    o.*,
    cm.follower_order_id,
    cm.sizing_strategy
FROM orders o
LEFT JOIN copy_mappings cm ON o.id = cm.leader_order_id
WHERE o.status IN ('PENDING', 'OPEN')
ORDER BY o.created_at DESC;

-- Latest positions view
CREATE VIEW IF NOT EXISTS v_latest_positions AS
SELECT p.*
FROM positions p
INNER JOIN (
    SELECT account_type, security_id, exchange_segment, MAX(snapshot_ts) as max_ts
    FROM positions
    GROUP BY account_type, security_id, exchange_segment
) latest ON p.account_type = latest.account_type
    AND p.security_id = latest.security_id
    AND p.exchange_segment = latest.exchange_segment
    AND p.snapshot_ts = latest.max_ts;

-- Latest funds view
CREATE VIEW IF NOT EXISTS v_latest_funds AS
SELECT f.*
FROM funds f
INNER JOIN (
    SELECT account_type, MAX(snapshot_ts) as max_ts
    FROM funds
    GROUP BY account_type
) latest ON f.account_type = latest.account_type
    AND f.snapshot_ts = latest.max_ts;


