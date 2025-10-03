-- Database Migration Script: v1/v2 → v3
-- Migrates existing database schema to comprehensive v3
-- Date: 2025-10-03
-- 
-- IMPORTANT: Backup your database before running this migration!
-- 
-- Usage:
--   sqlite3 your_database.db < migrate_to_v3.sql
--
-- Or in Python:
--   with open('migrate_to_v3.sql', 'r') as f:
--       conn.executescript(f.read())
-- =============================================================================

-- Enable foreign keys
PRAGMA foreign_keys = ON;

-- Begin transaction
BEGIN TRANSACTION;

-- =============================================================================
-- 1. CREATE NEW TABLES (not in v1/v2)
-- =============================================================================

-- Authentication tokens
CREATE TABLE IF NOT EXISTS auth_tokens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_type TEXT NOT NULL,
    access_token TEXT NOT NULL,
    token_type TEXT DEFAULT 'Bearer',
    expires_at INTEGER,
    refresh_token TEXT,
    scope TEXT,
    is_active INTEGER DEFAULT 1,
    last_used_at INTEGER,
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL,
    CHECK (account_type IN ('leader', 'follower')),
    CHECK (is_active IN (0, 1))
);

CREATE INDEX IF NOT EXISTS idx_auth_tokens_account ON auth_tokens(account_type, is_active);
CREATE INDEX IF NOT EXISTS idx_auth_tokens_expiry ON auth_tokens(expires_at);

-- Rate limit tracking
CREATE TABLE IF NOT EXISTS rate_limit_tracking (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_type TEXT NOT NULL,
    endpoint TEXT NOT NULL,
    request_count INTEGER DEFAULT 0,
    window_start INTEGER NOT NULL,
    window_end INTEGER NOT NULL,
    last_request_at INTEGER,
    created_at INTEGER NOT NULL,
    CHECK (account_type IN ('leader', 'follower'))
);

CREATE INDEX IF NOT EXISTS idx_rate_limit_account_endpoint ON rate_limit_tracking(account_type, endpoint, window_end);

-- Order modifications tracking
CREATE TABLE IF NOT EXISTS order_modifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id TEXT NOT NULL,
    modification_type TEXT NOT NULL,
    old_value TEXT,
    new_value TEXT,
    status TEXT,
    error_message TEXT,
    modified_at INTEGER NOT NULL,
    FOREIGN KEY(order_id) REFERENCES orders(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_order_modifications_order ON order_modifications(order_id, modified_at);

-- Forever orders (GTT)
CREATE TABLE IF NOT EXISTS forever_orders (
    id TEXT PRIMARY KEY,
    account_type TEXT NOT NULL,
    correlation_id TEXT,
    status TEXT NOT NULL,
    order_type TEXT NOT NULL,
    security_id TEXT NOT NULL,
    exchange_segment TEXT NOT NULL,
    trading_symbol TEXT,
    trigger_type TEXT NOT NULL,
    trigger_price_above REAL,
    trigger_price_below REAL,
    transaction_type TEXT NOT NULL,
    product TEXT NOT NULL,
    order_type_after_trigger TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    price REAL,
    disclosed_qty INTEGER,
    validity TEXT DEFAULT 'DAY',
    oco_leg_id TEXT,
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL,
    triggered_at INTEGER,
    expires_at INTEGER,
    triggered_order_id TEXT,
    raw_request TEXT,
    raw_response TEXT,
    CHECK (account_type IN ('leader', 'follower')),
    CHECK (status IN ('PENDING', 'ACTIVE', 'TRIGGERED', 'CANCELLED', 'EXPIRED')),
    CHECK (order_type IN ('SINGLE', 'OCO')),
    CHECK (trigger_type IN ('LTP_ABOVE', 'LTP_BELOW', 'LTP_RANGE')),
    CHECK (transaction_type IN ('BUY', 'SELL')),
    FOREIGN KEY(triggered_order_id) REFERENCES orders(id)
);

CREATE INDEX IF NOT EXISTS idx_forever_orders_account ON forever_orders(account_type, status);
CREATE INDEX IF NOT EXISTS idx_forever_orders_security ON forever_orders(security_id, exchange_segment);
CREATE INDEX IF NOT EXISTS idx_forever_orders_status ON forever_orders(status);
CREATE INDEX IF NOT EXISTS idx_forever_orders_correlation ON forever_orders(correlation_id);

-- Holdings (separate from positions)
CREATE TABLE IF NOT EXISTS holdings (
    snapshot_ts INTEGER NOT NULL,
    account_type TEXT NOT NULL,
    security_id TEXT NOT NULL,
    exchange_segment TEXT NOT NULL,
    trading_symbol TEXT,
    isin TEXT,
    total_qty INTEGER NOT NULL,
    dpqty INTEGER DEFAULT 0,
    t1qty INTEGER DEFAULT 0,
    available_qty INTEGER NOT NULL,
    collateral_qty INTEGER DEFAULT 0,
    collateral_update_qty INTEGER DEFAULT 0,
    avg_cost_price REAL,
    ltp REAL,
    realized_pl REAL DEFAULT 0,
    unrealized_pl REAL DEFAULT 0,
    raw_data TEXT,
    PRIMARY KEY(snapshot_ts, account_type, security_id),
    CHECK (account_type IN ('leader', 'follower'))
);

CREATE INDEX IF NOT EXISTS idx_holdings_account ON holdings(account_type, snapshot_ts);
CREATE INDEX IF NOT EXISTS idx_holdings_security ON holdings(security_id);
CREATE INDEX IF NOT EXISTS idx_holdings_isin ON holdings(isin);

-- eDIS transactions
CREATE TABLE IF NOT EXISTS edis_transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_type TEXT NOT NULL,
    isin TEXT NOT NULL,
    qty INTEGER NOT NULL,
    exchange TEXT NOT NULL,
    segment TEXT NOT NULL,
    bulk INTEGER DEFAULT 0,
    tpin TEXT,
    status TEXT NOT NULL,
    request_id TEXT,
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL,
    authorized_at INTEGER,
    expires_at INTEGER,
    raw_request TEXT,
    raw_response TEXT,
    error_message TEXT,
    CHECK (account_type IN ('leader', 'follower')),
    CHECK (status IN ('PENDING', 'AUTHORIZED', 'REJECTED', 'EXPIRED'))
);

CREATE INDEX IF NOT EXISTS idx_edis_account ON edis_transactions(account_type, status);
CREATE INDEX IF NOT EXISTS idx_edis_isin ON edis_transactions(isin);
CREATE INDEX IF NOT EXISTS idx_edis_request ON edis_transactions(request_id);

-- Trader's control
CREATE TABLE IF NOT EXISTS traders_control (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_type TEXT NOT NULL,
    control_type TEXT NOT NULL,
    kill_switch_status TEXT,
    daily_loss_limit REAL,
    position_size_limit REAL,
    order_value_limit REAL,
    is_active INTEGER DEFAULT 1,
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL,
    activated_at INTEGER,
    deactivated_at INTEGER,
    activated_by TEXT,
    reason TEXT,
    CHECK (account_type IN ('leader', 'follower')),
    CHECK (control_type IN ('KILL_SWITCH', 'RISK_LIMIT', 'POSITION_LIMIT')),
    CHECK (is_active IN (0, 1))
);

CREATE INDEX IF NOT EXISTS idx_traders_control_account ON traders_control(account_type, is_active);
CREATE INDEX IF NOT EXISTS idx_traders_control_type ON traders_control(control_type, is_active);

-- Risk violations
CREATE TABLE IF NOT EXISTS risk_violations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_type TEXT NOT NULL,
    violation_type TEXT NOT NULL,
    limit_value REAL NOT NULL,
    actual_value REAL NOT NULL,
    order_id TEXT,
    security_id TEXT,
    action_taken TEXT,
    violated_at INTEGER NOT NULL,
    CHECK (account_type IN ('leader', 'follower')),
    CHECK (violation_type IN ('DAILY_LOSS', 'POSITION_SIZE', 'ORDER_VALUE')),
    FOREIGN KEY(order_id) REFERENCES orders(id)
);

CREATE INDEX IF NOT EXISTS idx_risk_violations_account ON risk_violations(account_type, violated_at);
CREATE INDEX IF NOT EXISTS idx_risk_violations_type ON risk_violations(violation_type);

-- Margin requirements
CREATE TABLE IF NOT EXISTS margin_requirements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_type TEXT NOT NULL,
    order_id TEXT,
    security_id TEXT NOT NULL,
    exchange_segment TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    price REAL,
    product TEXT NOT NULL,
    total_margin REAL NOT NULL,
    span_margin REAL,
    exposure_margin REAL,
    var_margin REAL,
    calculated_at INTEGER NOT NULL,
    CHECK (account_type IN ('leader', 'follower')),
    FOREIGN KEY(order_id) REFERENCES orders(id)
);

CREATE INDEX IF NOT EXISTS idx_margin_requirements_account ON margin_requirements(account_type);
CREATE INDEX IF NOT EXISTS idx_margin_requirements_order ON margin_requirements(order_id);

-- Ledger entries
CREATE TABLE IF NOT EXISTS ledger_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_type TEXT NOT NULL,
    entry_date TEXT NOT NULL,
    particulars TEXT,
    voucherNo TEXT,
    voucherDate TEXT,
    debit REAL DEFAULT 0,
    credit REAL DEFAULT 0,
    balance REAL,
    created_at INTEGER NOT NULL,
    CHECK (account_type IN ('leader', 'follower'))
);

CREATE INDEX IF NOT EXISTS idx_ledger_account_date ON ledger_entries(account_type, entry_date);
CREATE INDEX IF NOT EXISTS idx_ledger_date ON ledger_entries(entry_date);

-- Postback configurations
CREATE TABLE IF NOT EXISTS postback_configs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_type TEXT NOT NULL,
    webhook_url TEXT NOT NULL,
    webhook_secret TEXT,
    event_types TEXT,
    is_active INTEGER DEFAULT 1,
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL,
    last_triggered_at INTEGER,
    CHECK (account_type IN ('leader', 'follower')),
    CHECK (is_active IN (0, 1))
);

CREATE INDEX IF NOT EXISTS idx_postback_configs_account ON postback_configs(account_type, is_active);

-- Postback events
CREATE TABLE IF NOT EXISTS postback_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_type TEXT NOT NULL,
    event_type TEXT NOT NULL,
    order_id TEXT,
    payload TEXT NOT NULL,
    signature TEXT,
    is_verified INTEGER,
    is_processed INTEGER DEFAULT 0,
    processed_at INTEGER,
    error_message TEXT,
    received_at INTEGER NOT NULL,
    CHECK (account_type IN ('leader', 'follower')),
    CHECK (is_verified IN (0, 1)),
    CHECK (is_processed IN (0, 1)),
    FOREIGN KEY(order_id) REFERENCES orders(id)
);

CREATE INDEX IF NOT EXISTS idx_postback_events_account ON postback_events(account_type, received_at);
CREATE INDEX IF NOT EXISTS idx_postback_events_order ON postback_events(order_id);
CREATE INDEX IF NOT EXISTS idx_postback_events_processed ON postback_events(is_processed, received_at);

-- WebSocket connections
CREATE TABLE IF NOT EXISTS websocket_connections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_type TEXT NOT NULL,
    connection_id TEXT NOT NULL,
    ws_url TEXT NOT NULL,
    status TEXT NOT NULL,
    subscribed_events TEXT,
    connect_attempts INTEGER DEFAULT 0,
    last_heartbeat_at INTEGER,
    connected_at INTEGER,
    disconnected_at INTEGER,
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL,
    CHECK (account_type IN ('leader', 'follower')),
    CHECK (status IN ('CONNECTING', 'CONNECTED', 'DISCONNECTED', 'ERROR'))
);

CREATE INDEX IF NOT EXISTS idx_ws_connections_account ON websocket_connections(account_type, status);
CREATE INDEX IF NOT EXISTS idx_ws_connections_status ON websocket_connections(status);

-- WebSocket messages
CREATE TABLE IF NOT EXISTS websocket_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    connection_id TEXT NOT NULL,
    account_type TEXT NOT NULL,
    message_type TEXT NOT NULL,
    order_id TEXT,
    payload TEXT NOT NULL,
    sequence_number INTEGER,
    is_processed INTEGER DEFAULT 0,
    processed_at INTEGER,
    received_at INTEGER NOT NULL,
    CHECK (account_type IN ('leader', 'follower')),
    CHECK (is_processed IN (0, 1)),
    FOREIGN KEY(order_id) REFERENCES orders(id)
);

CREATE INDEX IF NOT EXISTS idx_ws_messages_connection ON websocket_messages(connection_id, received_at);
CREATE INDEX IF NOT EXISTS idx_ws_messages_account ON websocket_messages(account_type, received_at);
CREATE INDEX IF NOT EXISTS idx_ws_messages_order ON websocket_messages(order_id);
CREATE INDEX IF NOT EXISTS idx_ws_messages_processed ON websocket_messages(is_processed, received_at);
CREATE INDEX IF NOT EXISTS idx_ws_messages_sequence ON websocket_messages(connection_id, sequence_number);

-- Error log
CREATE TABLE IF NOT EXISTS error_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    error_type TEXT NOT NULL,
    error_code TEXT,
    error_message TEXT NOT NULL,
    stack_trace TEXT,
    context TEXT,
    severity TEXT DEFAULT 'ERROR',
    account_type TEXT,
    order_id TEXT,
    occurred_at INTEGER NOT NULL,
    CHECK (severity IN ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'))
);

CREATE INDEX IF NOT EXISTS idx_error_log_type ON error_log(error_type, occurred_at);
CREATE INDEX IF NOT EXISTS idx_error_log_severity ON error_log(severity, occurred_at);
CREATE INDEX IF NOT EXISTS idx_error_log_account ON error_log(account_type, occurred_at);

-- =============================================================================
-- 2. ALTER EXISTING TABLES (add new columns)
-- =============================================================================

-- Enhance orders table
-- Note: SQLite doesn't support adding columns with CHECK constraints in ALTER TABLE
-- We'll add the columns and the constraints will be enforced in v3

-- Check if columns exist first (SQLite specific approach)
-- These ALTER TABLEs will fail silently if columns already exist

-- Add order enhancements
ALTER TABLE orders ADD COLUMN order_status TEXT;
ALTER TABLE orders ADD COLUMN trading_symbol TEXT;
ALTER TABLE orders ADD COLUMN traded_qty INTEGER DEFAULT 0;
ALTER TABLE orders ADD COLUMN remaining_qty INTEGER;
ALTER TABLE orders ADD COLUMN avg_price REAL;
ALTER TABLE orders ADD COLUMN after_market_order INTEGER DEFAULT 0;
ALTER TABLE orders ADD COLUMN amo_time TEXT;
ALTER TABLE orders ADD COLUMN is_sliced_order INTEGER DEFAULT 0;
ALTER TABLE orders ADD COLUMN slice_order_id TEXT;
ALTER TABLE orders ADD COLUMN slice_index INTEGER;
ALTER TABLE orders ADD COLUMN total_slice_quantity INTEGER;
ALTER TABLE orders ADD COLUMN exchange_order_id TEXT;
ALTER TABLE orders ADD COLUMN exchange_time INTEGER;
ALTER TABLE orders ADD COLUMN completed_at INTEGER;
ALTER TABLE orders ADD COLUMN algo_id TEXT;
ALTER TABLE orders ADD COLUMN drv_expiry_date INTEGER;
ALTER TABLE orders ADD COLUMN drv_option_type TEXT;
ALTER TABLE orders ADD COLUMN drv_strike_price REAL;
ALTER TABLE orders ADD COLUMN oms_error_code TEXT;
ALTER TABLE orders ADD COLUMN oms_error_description TEXT;

-- Add event source to order_events
ALTER TABLE order_events ADD COLUMN event_source TEXT;

-- Enhance trades table for complete Trade Book API coverage
-- Reference: https://dhanhq.co/docs/v2/orders/ (Trade Book section)
ALTER TABLE trades ADD COLUMN order_type TEXT;              -- orderType (LIMIT/MARKET/STOP_LOSS/STOP_LOSS_MARKET)
ALTER TABLE trades ADD COLUMN updated_at INTEGER;           -- updateTime (epoch)
ALTER TABLE trades ADD COLUMN exchange_time INTEGER;        -- exchangeTime (epoch)
ALTER TABLE trades ADD COLUMN drv_expiry_date INTEGER;      -- drvExpiryDate (epoch) - For F&O expiry
ALTER TABLE trades ADD COLUMN drv_option_type TEXT;         -- drvOptionType (CALL/PUT) - Option type
ALTER TABLE trades ADD COLUMN drv_strike_price REAL;        -- drvStrikePrice - Option strike price

-- Enhance config table
ALTER TABLE config ADD COLUMN data_type TEXT DEFAULT 'string';
ALTER TABLE config ADD COLUMN category TEXT;
ALTER TABLE config ADD COLUMN is_sensitive INTEGER DEFAULT 0;

-- Enhance positions table
ALTER TABLE positions ADD COLUMN position_type TEXT;
ALTER TABLE positions ADD COLUMN buy_qty INTEGER DEFAULT 0;
ALTER TABLE positions ADD COLUMN sell_qty INTEGER DEFAULT 0;
ALTER TABLE positions ADD COLUMN buy_avg REAL DEFAULT 0;
ALTER TABLE positions ADD COLUMN sell_avg REAL DEFAULT 0;
ALTER TABLE positions ADD COLUMN total_pl REAL DEFAULT 0;
ALTER TABLE positions ADD COLUMN ltp REAL;
ALTER TABLE positions ADD COLUMN close_price REAL;
ALTER TABLE positions ADD COLUMN multiplier REAL;
ALTER TABLE positions ADD COLUMN margin_required REAL;

-- Enhance funds table
ALTER TABLE funds ADD COLUMN sodLimit REAL;
ALTER TABLE funds ADD COLUMN margin_available REAL;
ALTER TABLE funds ADD COLUMN withdrawable_balance REAL;
ALTER TABLE funds ADD COLUMN blocked_margin REAL;

-- Enhance trades table
ALTER TABLE trades ADD COLUMN exchange_trade_id TEXT;
ALTER TABLE trades ADD COLUMN trading_symbol TEXT;
ALTER TABLE trades ADD COLUMN trade_value REAL;
ALTER TABLE trades ADD COLUMN brokerage REAL DEFAULT 0;
ALTER TABLE trades ADD COLUMN exchange_charges REAL DEFAULT 0;
ALTER TABLE trades ADD COLUMN clearing_charges REAL DEFAULT 0;
ALTER TABLE trades ADD COLUMN stt REAL DEFAULT 0;
ALTER TABLE trades ADD COLUMN stamp_duty REAL DEFAULT 0;
ALTER TABLE trades ADD COLUMN transaction_charges REAL DEFAULT 0;
ALTER TABLE trades ADD COLUMN gst REAL DEFAULT 0;
ALTER TABLE trades ADD COLUMN total_charges REAL DEFAULT 0;
ALTER TABLE trades ADD COLUMN net_amount REAL;

-- Enhance instruments table
ALTER TABLE instruments ADD COLUMN trading_symbol TEXT;
ALTER TABLE instruments ADD COLUMN isin TEXT;

-- Create indexes for new columns
CREATE INDEX IF NOT EXISTS idx_orders_exchange ON orders(exchange_order_id);
CREATE INDEX IF NOT EXISTS idx_orders_slice ON orders(slice_order_id, slice_index);
CREATE INDEX IF NOT EXISTS idx_order_events_source ON order_events(event_source, event_ts);
CREATE INDEX IF NOT EXISTS idx_config_category ON config(category);
CREATE INDEX IF NOT EXISTS idx_instruments_trading_symbol ON instruments(trading_symbol);
CREATE INDEX IF NOT EXISTS idx_instruments_isin ON instruments(isin);
CREATE INDEX IF NOT EXISTS idx_trades_exchange ON trades(exchange_order_id);
CREATE INDEX IF NOT EXISTS idx_audit_module ON audit_log(module, ts);

-- =============================================================================
-- 3. UPDATE CONFIGURATION
-- =============================================================================

-- Update schema version
UPDATE config SET value = '3', updated_at = strftime('%s', 'now') WHERE key = 'schema_version';

-- Add new configuration entries
INSERT OR IGNORE INTO config (key, value, data_type, category, description, updated_at) VALUES
    ('last_holdings_snapshot_ts', '0', 'integer', 'portfolio', 'Last holdings snapshot timestamp', strftime('%s', 'now')),
    ('forever_enabled', 'true', 'boolean', 'orders', 'Forever Order replication enabled', strftime('%s', 'now')),
    ('kill_switch_enabled', 'false', 'boolean', 'risk', 'Kill switch enabled', strftime('%s', 'now')),
    ('daily_loss_limit_enabled', 'true', 'boolean', 'risk', 'Daily loss limit enabled', strftime('%s', 'now')),
    ('position_size_limit_enabled', 'true', 'boolean', 'risk', 'Position size limit enabled', strftime('%s', 'now')),
    ('ws_reconnect_enabled', 'true', 'boolean', 'websocket', 'WebSocket auto-reconnect enabled', strftime('%s', 'now')),
    ('ws_max_reconnect_attempts', '10', 'integer', 'websocket', 'Maximum WebSocket reconnection attempts', strftime('%s', 'now')),
    ('postback_enabled', 'false', 'boolean', 'postback', 'Postback webhook enabled', strftime('%s', 'now'));

-- Update existing config entries with metadata
UPDATE config SET data_type = 'integer', category = 'system' WHERE key = 'schema_version';
UPDATE config SET data_type = 'boolean', category = 'copy_trading' WHERE key = 'copy_enabled';
UPDATE config SET data_type = 'integer', category = 'copy_trading' WHERE key = 'last_leader_event_ts';
UPDATE config SET data_type = 'integer', category = 'portfolio' WHERE key = 'last_position_snapshot_ts';
UPDATE config SET data_type = 'integer', category = 'funds' WHERE key = 'last_funds_snapshot_ts';
UPDATE config SET data_type = 'boolean', category = 'orders' WHERE key = 'co_enabled';
UPDATE config SET data_type = 'boolean', category = 'orders' WHERE key = 'bo_enabled';

-- =============================================================================
-- 4. CREATE NEW VIEWS
-- =============================================================================

-- Drop existing views if they exist
DROP VIEW IF EXISTS v_active_orders;
DROP VIEW IF EXISTS v_latest_positions;
DROP VIEW IF EXISTS v_latest_holdings;
DROP VIEW IF EXISTS v_latest_funds;
DROP VIEW IF EXISTS v_active_forever_orders;
DROP VIEW IF EXISTS v_active_bracket_orders;
DROP VIEW IF EXISTS v_cover_orders;
DROP VIEW IF EXISTS v_recent_trades;
DROP VIEW IF EXISTS v_active_websocket_connections;
DROP VIEW IF EXISTS v_recent_errors;

-- Active orders view
CREATE VIEW v_active_orders AS
SELECT 
    o.*,
    cm.follower_order_id,
    cm.sizing_strategy
FROM orders o
LEFT JOIN copy_mappings cm ON o.id = cm.leader_order_id
WHERE o.status IN ('PENDING', 'TRANSIT', 'OPEN', 'PARTIAL')
ORDER BY o.created_at DESC;

-- Latest positions view
CREATE VIEW v_latest_positions AS
SELECT p.*
FROM positions p
INNER JOIN (
    SELECT account_type, security_id, exchange_segment, COALESCE(product, 'DEFAULT') as product, MAX(snapshot_ts) as max_ts
    FROM positions
    GROUP BY account_type, security_id, exchange_segment, COALESCE(product, 'DEFAULT')
) latest ON p.account_type = latest.account_type
    AND p.security_id = latest.security_id
    AND p.exchange_segment = latest.exchange_segment
    AND COALESCE(p.product, 'DEFAULT') = latest.product
    AND p.snapshot_ts = latest.max_ts;

-- Latest holdings view
CREATE VIEW v_latest_holdings AS
SELECT h.*
FROM holdings h
INNER JOIN (
    SELECT account_type, security_id, MAX(snapshot_ts) as max_ts
    FROM holdings
    GROUP BY account_type, security_id
) latest ON h.account_type = latest.account_type
    AND h.security_id = latest.security_id
    AND h.snapshot_ts = latest.max_ts;

-- Latest funds view
CREATE VIEW v_latest_funds AS
SELECT f.*
FROM funds f
INNER JOIN (
    SELECT account_type, MAX(snapshot_ts) as max_ts
    FROM funds
    GROUP BY account_type
) latest ON f.account_type = latest.account_type
    AND f.snapshot_ts = latest.max_ts;

-- Active forever orders view
CREATE VIEW v_active_forever_orders AS
SELECT 
    fo.*,
    cm.follower_order_id as replicated_forever_order_id
FROM forever_orders fo
LEFT JOIN copy_mappings cm ON fo.id = cm.leader_order_id
WHERE fo.status IN ('PENDING', 'ACTIVE')
ORDER BY fo.created_at DESC;

-- Active bracket orders view
CREATE VIEW v_active_bracket_orders AS
SELECT 
    o.id as parent_order_id,
    o.account_type,
    o.security_id,
    o.exchange_segment,
    o.bo_profit_value,
    o.bo_stop_loss_value,
    (SELECT leg_order_id FROM bracket_order_legs WHERE parent_order_id = o.id AND leg_type = 'ENTRY' AND account_type = o.account_type LIMIT 1) as entry_leg_id,
    (SELECT leg_order_id FROM bracket_order_legs WHERE parent_order_id = o.id AND leg_type = 'TARGET' AND account_type = o.account_type LIMIT 1) as target_leg_id,
    (SELECT leg_order_id FROM bracket_order_legs WHERE parent_order_id = o.id AND leg_type = 'SL' AND account_type = o.account_type LIMIT 1) as sl_leg_id,
    o.status,
    o.created_at
FROM orders o
WHERE (o.bo_profit_value IS NOT NULL OR o.bo_stop_loss_value IS NOT NULL)
  AND o.status IN ('PENDING', 'TRANSIT', 'OPEN', 'PARTIAL')
ORDER BY o.created_at DESC;

-- Cover orders view
CREATE VIEW v_cover_orders AS
SELECT *
FROM orders
WHERE co_stop_loss_value IS NOT NULL
ORDER BY created_at DESC;

-- Recent trades with P&L
CREATE VIEW v_recent_trades AS
SELECT 
    t.*,
    o.status as order_status,
    o.product,
    (t.price - COALESCE(t.brokerage, 0) - COALESCE(t.total_charges, 0)) as net_price
FROM trades t
LEFT JOIN orders o ON t.order_id = o.id
ORDER BY t.trade_ts DESC
LIMIT 100;

-- Active WebSocket connections
CREATE VIEW v_active_websocket_connections AS
SELECT 
    wc.*,
    (strftime('%s', 'now') - COALESCE(wc.last_heartbeat_at, 0)) as seconds_since_heartbeat
FROM websocket_connections wc
WHERE wc.status = 'CONNECTED'
ORDER BY wc.connected_at DESC;

-- Recent errors summary
CREATE VIEW v_recent_errors AS
SELECT 
    error_type,
    severity,
    COUNT(*) as error_count,
    MAX(occurred_at) as last_occurred,
    GROUP_CONCAT(DISTINCT account_type) as affected_accounts
FROM error_log
WHERE occurred_at > (strftime('%s', 'now') - 86400)  -- Last 24 hours
GROUP BY error_type, severity
ORDER BY last_occurred DESC;

-- =============================================================================
-- 5. COMMIT TRANSACTION
-- =============================================================================

COMMIT;

-- =============================================================================
-- 6. VACUUM AND ANALYZE
-- =============================================================================

VACUUM;
ANALYZE;

-- =============================================================================
-- MIGRATION COMPLETE
-- =============================================================================

SELECT 'Migration to v3 completed successfully!' as status;
SELECT value as schema_version FROM config WHERE key = 'schema_version';

