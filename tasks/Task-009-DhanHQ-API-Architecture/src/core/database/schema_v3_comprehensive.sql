-- Copy Trading System Database Schema v3
-- Comprehensive Schema for All DhanHQ v2 API Modules
-- Version: 3.0
-- Date: 2025-10-03
--
-- Modules Covered:
-- 1. Authentication & Configuration
-- 2. Orders (all types: MARKET, LIMIT, SL, SL-M)
-- 3. Super Orders (Cover Orders, Bracket Orders)
-- 4. Forever Orders (GTT - Good Till Triggered)
-- 5. Portfolio (Positions, Holdings)
-- 6. eDIS (Electronic Delivery Instruction Slip)
-- 7. Trader's Control (Kill Switch, Risk Limits)
-- 8. Funds & Margin
-- 9. Statements (Ledger, Trade Book)
-- 10. Postback (Webhook Configurations)
-- 11. Live Order Updates (WebSocket Subscriptions)
-- =============================================================================

-- Enable foreign keys
PRAGMA foreign_keys = ON;

-- Enable WAL mode for better concurrency
PRAGMA journal_mode = WAL;

-- Set synchronous mode
PRAGMA synchronous = NORMAL;

-- =============================================================================
-- 1. AUTHENTICATION & CONFIGURATION
-- =============================================================================

-- Authentication tokens and sessions
CREATE TABLE IF NOT EXISTS auth_tokens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_type TEXT NOT NULL,             -- 'leader' or 'follower'
    access_token TEXT NOT NULL,             -- DhanHQ access token (encrypted)
    token_type TEXT DEFAULT 'Bearer',       -- Token type
    expires_at INTEGER,                     -- Token expiration timestamp (if applicable)
    refresh_token TEXT,                     -- Refresh token (if applicable)
    scope TEXT,                             -- Token scope/permissions
    is_active INTEGER DEFAULT 1,            -- Active flag
    last_used_at INTEGER,                   -- Last usage timestamp
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL,
    CHECK (account_type IN ('leader', 'follower')),
    CHECK (is_active IN (0, 1))
);

CREATE INDEX IF NOT EXISTS idx_auth_tokens_account ON auth_tokens(account_type, is_active);
CREATE INDEX IF NOT EXISTS idx_auth_tokens_expiry ON auth_tokens(expires_at);

-- API rate limiting tracking
CREATE TABLE IF NOT EXISTS rate_limit_tracking (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_type TEXT NOT NULL,             -- 'leader' or 'follower'
    endpoint TEXT NOT NULL,                 -- API endpoint
    request_count INTEGER DEFAULT 0,        -- Request count
    window_start INTEGER NOT NULL,          -- Rate limit window start
    window_end INTEGER NOT NULL,            -- Rate limit window end
    last_request_at INTEGER,                -- Last request timestamp
    created_at INTEGER NOT NULL,
    CHECK (account_type IN ('leader', 'follower'))
);

CREATE INDEX IF NOT EXISTS idx_rate_limit_account_endpoint ON rate_limit_tracking(account_type, endpoint, window_end);

-- System configuration (enhanced)
CREATE TABLE IF NOT EXISTS config (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    data_type TEXT DEFAULT 'string',        -- 'string', 'integer', 'boolean', 'json'
    category TEXT,                          -- 'auth', 'orders', 'risk', 'system', etc.
    description TEXT,
    is_sensitive INTEGER DEFAULT 0,         -- Flag for sensitive data
    updated_at INTEGER NOT NULL,
    CHECK (data_type IN ('string', 'integer', 'boolean', 'json')),
    CHECK (is_sensitive IN (0, 1))
);

CREATE INDEX IF NOT EXISTS idx_config_category ON config(category);

-- =============================================================================
-- 2. ORDERS (Enhanced for all order types)
-- =============================================================================

CREATE TABLE IF NOT EXISTS orders (
    id TEXT PRIMARY KEY,                    -- DhanHQ order ID
    account_type TEXT NOT NULL,             -- 'leader' or 'follower'
    correlation_id TEXT,                    -- Link leader to follower orders
    
    -- Order details
    status TEXT NOT NULL,                   -- PENDING/TRANSIT/OPEN/PARTIAL/EXECUTED/CANCELLED/REJECTED
    order_status TEXT,                      -- Additional status from API
    side TEXT NOT NULL,                     -- BUY/SELL
    product TEXT NOT NULL,                  -- CNC/INTRADAY/MARGIN/MTF/CO/BO
    order_type TEXT NOT NULL,               -- MARKET/LIMIT/STOP_LOSS/STOP_LOSS_MARKET
    validity TEXT NOT NULL,                 -- DAY/IOC
    
    -- Instrument details
    security_id TEXT NOT NULL,
    exchange_segment TEXT NOT NULL,         -- NSE_EQ/NSE_FNO/BSE_EQ/BSE_FNO/MCX_COMM/CDS_FUT
    trading_symbol TEXT,                    -- Trading symbol
    
    -- Quantity and pricing
    quantity INTEGER NOT NULL,
    disclosed_qty INTEGER,
    price REAL,
    trigger_price REAL,
    traded_qty INTEGER DEFAULT 0,           -- Quantity traded/filled
    remaining_qty INTEGER,                  -- Remaining quantity
    avg_price REAL,                         -- Average execution price
    
    -- Cover Order (CO) parameters
    co_stop_loss_value REAL,               -- CO stop-loss level
    co_trigger_price REAL,                 -- CO trigger price
    
    -- Bracket Order (BO) parameters
    bo_profit_value REAL,                  -- BO target profit level
    bo_stop_loss_value REAL,              -- BO stop-loss level
    bo_order_type TEXT,                    -- BO order type (MARKET/LIMIT)
    
    -- Multi-leg order tracking
    parent_order_id TEXT,                  -- For BO legs: parent BO order ID
    leg_type TEXT,                         -- For BO legs: 'ENTRY', 'TARGET', 'SL'
    
    -- Order Slicing tracking
    is_sliced_order INTEGER DEFAULT 0,     -- Flag: order created via slicing API (0=false, 1=true)
    slice_order_id TEXT,                   -- Common ID for all orders from same slice request
    slice_index INTEGER,                   -- Order number within slice (1, 2, 3, etc.)
    total_slice_quantity INTEGER,          -- Original total quantity before slicing
    
    -- AMO (After Market Order) flags
    after_market_order INTEGER DEFAULT 0,  -- AMO flag (0=false, 1=true)
    amo_time TEXT,                         -- AMO order time (PRE_OPEN/OPEN/OPEN_30/OPEN_60)
    
    -- Exchange details
    exchange_order_id TEXT,                -- Exchange order ID
    exchange_time INTEGER,                 -- Exchange timestamp
    algo_id TEXT,                          -- Exchange Algo ID for Dhan
    
    -- Derivatives info (F&O)
    drv_expiry_date INTEGER,               -- For F&O, expiry date of contract (epoch)
    drv_option_type TEXT,                  -- Type of Option: CALL or PUT
    drv_strike_price REAL,                 -- For Options, Strike Price
    
    -- Error tracking
    oms_error_code TEXT,                   -- Error code if order is rejected/failed
    oms_error_description TEXT,            -- Error description if order is rejected/failed
    
    -- Timestamps
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL,
    completed_at INTEGER,                  -- Order completion timestamp
    
    -- Raw data
    raw_request TEXT,                      -- JSON
    raw_response TEXT,                     -- JSON
    
    CHECK (account_type IN ('leader', 'follower')),
    CHECK (status IN ('PENDING', 'TRANSIT', 'OPEN', 'PARTIAL', 'PART_TRADED', 'EXECUTED', 'CANCELLED', 'REJECTED')),
    CHECK (drv_option_type IS NULL OR drv_option_type IN ('CALL', 'PUT')),
    CHECK (side IN ('BUY', 'SELL')),
    CHECK (order_type IN ('MARKET', 'LIMIT', 'STOP_LOSS', 'STOP_LOSS_MARKET')),
    CHECK (validity IN ('DAY', 'IOC')),
    CHECK (leg_type IS NULL OR leg_type IN ('ENTRY', 'TARGET', 'SL')),
    CHECK (is_sliced_order IN (0, 1)),
    CHECK (after_market_order IN (0, 1))
);

CREATE INDEX IF NOT EXISTS idx_orders_correlation ON orders(correlation_id);
CREATE INDEX IF NOT EXISTS idx_orders_account ON orders(account_type, created_at);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
CREATE INDEX IF NOT EXISTS idx_orders_security ON orders(security_id, exchange_segment);
CREATE INDEX IF NOT EXISTS idx_orders_parent ON orders(parent_order_id);
CREATE INDEX IF NOT EXISTS idx_orders_leg_type ON orders(leg_type);
CREATE INDEX IF NOT EXISTS idx_orders_slice ON orders(slice_order_id, slice_index);
CREATE INDEX IF NOT EXISTS idx_orders_exchange ON orders(exchange_order_id);

-- Order events: Track order lifecycle events
CREATE TABLE IF NOT EXISTS order_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id TEXT NOT NULL,
    event_type TEXT NOT NULL,              -- PLACED/MODIFIED/EXECUTED/CANCELLED/REJECTED/PARTIAL/TRANSIT
    event_source TEXT,                     -- 'REST_API', 'WEBSOCKET', 'POSTBACK'
    event_data TEXT,                       -- JSON
    event_ts INTEGER NOT NULL,
    sequence INTEGER,
    UNIQUE(order_id, sequence),
    FOREIGN KEY(order_id) REFERENCES orders(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_order_events_order_ts ON order_events(order_id, event_ts);
CREATE INDEX IF NOT EXISTS idx_order_events_type ON order_events(event_type, event_ts);
CREATE INDEX IF NOT EXISTS idx_order_events_source ON order_events(event_source, event_ts);

-- Order modifications tracking
CREATE TABLE IF NOT EXISTS order_modifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id TEXT NOT NULL,
    modification_type TEXT NOT NULL,       -- 'QUANTITY', 'PRICE', 'TRIGGER_PRICE', 'VALIDITY'
    old_value TEXT,                        -- Previous value (JSON)
    new_value TEXT,                        -- New value (JSON)
    status TEXT,                           -- 'PENDING', 'SUCCESS', 'FAILED'
    error_message TEXT,
    modified_at INTEGER NOT NULL,
    FOREIGN KEY(order_id) REFERENCES orders(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_order_modifications_order ON order_modifications(order_id, modified_at);

-- =============================================================================
-- 3. SUPER ORDERS (Cover & Bracket Orders)
-- =============================================================================

-- Bracket Order legs tracking
CREATE TABLE IF NOT EXISTS bracket_order_legs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    parent_order_id TEXT NOT NULL,         -- BO parent order ID
    leg_order_id TEXT NOT NULL,            -- Individual leg order ID
    leg_type TEXT NOT NULL,                -- 'ENTRY', 'TARGET', 'SL'
    account_type TEXT NOT NULL,            -- 'leader', 'follower'
    status TEXT DEFAULT 'PENDING',         -- Track leg status
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL,
    
    UNIQUE(parent_order_id, leg_order_id, account_type),
    CHECK (account_type IN ('leader', 'follower')),
    CHECK (leg_type IN ('ENTRY', 'TARGET', 'SL'))
);

CREATE INDEX IF NOT EXISTS idx_bo_legs_parent ON bracket_order_legs(parent_order_id);
CREATE INDEX IF NOT EXISTS idx_bo_legs_leg ON bracket_order_legs(leg_order_id);
CREATE INDEX IF NOT EXISTS idx_bo_legs_account ON bracket_order_legs(account_type);
CREATE INDEX IF NOT EXISTS idx_bo_legs_type ON bracket_order_legs(leg_type, status);

-- =============================================================================
-- 4. FOREVER ORDERS (GTT - Good Till Triggered)
-- =============================================================================

CREATE TABLE IF NOT EXISTS forever_orders (
    id TEXT PRIMARY KEY,                   -- Forever order ID
    account_type TEXT NOT NULL,            -- 'leader' or 'follower'
    correlation_id TEXT,                   -- Link leader to follower forever orders
    
    -- Order details
    status TEXT NOT NULL,                  -- PENDING/ACTIVE/TRIGGERED/CANCELLED/EXPIRED
    order_type TEXT NOT NULL,              -- 'SINGLE', 'OCO' (One Cancels Other)
    
    -- Instrument details
    security_id TEXT NOT NULL,
    exchange_segment TEXT NOT NULL,
    trading_symbol TEXT,
    
    -- Trigger conditions
    trigger_type TEXT NOT NULL,            -- 'LTP_ABOVE', 'LTP_BELOW', 'LTP_RANGE'
    trigger_price_above REAL,              -- Trigger when LTP goes above
    trigger_price_below REAL,              -- Trigger when LTP goes below
    
    -- Order to be placed when triggered
    transaction_type TEXT NOT NULL,        -- 'BUY', 'SELL'
    product TEXT NOT NULL,                 -- CNC/INTRADAY/MARGIN
    order_type_after_trigger TEXT NOT NULL, -- MARKET/LIMIT/STOP_LOSS/STOP_LOSS_MARKET
    quantity INTEGER NOT NULL,
    price REAL,                            -- Price for LIMIT orders
    disclosed_qty INTEGER,
    validity TEXT DEFAULT 'DAY',           -- DAY/IOC
    
    -- OCO leg (if order_type = 'OCO')
    oco_leg_id TEXT,                       -- Reference to another forever order
    
    -- Timestamps
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL,
    triggered_at INTEGER,                  -- When the order was triggered
    expires_at INTEGER,                    -- Expiration timestamp
    
    -- Related order after trigger
    triggered_order_id TEXT,               -- Order ID after trigger
    
    -- Raw data
    raw_request TEXT,                      -- JSON
    raw_response TEXT,                     -- JSON
    
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

-- =============================================================================
-- 5. PORTFOLIO (Positions & Holdings)
-- =============================================================================

-- Positions: Intraday and overnight positions
CREATE TABLE IF NOT EXISTS positions (
    snapshot_ts INTEGER NOT NULL,
    account_type TEXT NOT NULL,
    security_id TEXT NOT NULL,
    exchange_segment TEXT NOT NULL,
    
    -- Position details
    product TEXT,                          -- CNC/INTRADAY/MARGIN/MTF
    position_type TEXT,                    -- 'DAY', 'NET'
    
    -- Quantity and pricing
    buy_qty INTEGER DEFAULT 0,
    sell_qty INTEGER DEFAULT 0,
    net_qty INTEGER NOT NULL,              -- Net quantity (buy - sell)
    buy_avg REAL DEFAULT 0,                -- Average buy price
    sell_avg REAL DEFAULT 0,               -- Average sell price
    
    -- P&L
    realized_pl REAL DEFAULT 0,
    unrealized_pl REAL DEFAULT 0,
    total_pl REAL DEFAULT 0,
    
    -- Market data
    ltp REAL,                              -- Last traded price
    close_price REAL,                      -- Previous close price
    
    -- Margin details
    multiplier REAL,
    margin_required REAL,
    
    -- Raw data
    raw_data TEXT,                         -- JSON
    
    PRIMARY KEY(snapshot_ts, account_type, security_id, exchange_segment, product),
    CHECK (account_type IN ('leader', 'follower'))
);

CREATE INDEX IF NOT EXISTS idx_positions_ts ON positions(snapshot_ts);
CREATE INDEX IF NOT EXISTS idx_positions_account ON positions(account_type, snapshot_ts);
CREATE INDEX IF NOT EXISTS idx_positions_security ON positions(security_id);

-- Holdings: Long-term holdings (delivery)
CREATE TABLE IF NOT EXISTS holdings (
    snapshot_ts INTEGER NOT NULL,
    account_type TEXT NOT NULL,
    security_id TEXT NOT NULL,
    exchange_segment TEXT NOT NULL,
    
    -- Holding details
    trading_symbol TEXT,
    isin TEXT,                             -- ISIN code
    
    -- Quantity and pricing
    total_qty INTEGER NOT NULL,            -- Total quantity held
    dpqty INTEGER DEFAULT 0,               -- Demat quantity
    t1qty INTEGER DEFAULT 0,               -- T+1 quantity
    available_qty INTEGER NOT NULL,        -- Available for trading
    
    -- Collateral
    collateral_qty INTEGER DEFAULT 0,      -- Pledged as collateral
    collateral_update_qty INTEGER DEFAULT 0,
    
    -- Pricing
    avg_cost_price REAL,                   -- Average cost price
    ltp REAL,                              -- Last traded price
    
    -- P&L
    realized_pl REAL DEFAULT 0,
    unrealized_pl REAL DEFAULT 0,
    
    -- Raw data
    raw_data TEXT,                         -- JSON
    
    PRIMARY KEY(snapshot_ts, account_type, security_id),
    CHECK (account_type IN ('leader', 'follower'))
);

CREATE INDEX IF NOT EXISTS idx_holdings_account ON holdings(account_type, snapshot_ts);
CREATE INDEX IF NOT EXISTS idx_holdings_security ON holdings(security_id);
CREATE INDEX IF NOT EXISTS idx_holdings_isin ON holdings(isin);

-- =============================================================================
-- 6. EDIS (Electronic Delivery Instruction Slip)
-- =============================================================================

CREATE TABLE IF NOT EXISTS edis_transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_type TEXT NOT NULL,            -- 'leader' or 'follower'
    
    -- Transaction details
    isin TEXT NOT NULL,                    -- ISIN code
    qty INTEGER NOT NULL,                  -- Quantity
    exchange TEXT NOT NULL,                -- Exchange
    segment TEXT NOT NULL,                 -- Segment
    bulk INTEGER DEFAULT 0,                -- Bulk flag
    
    -- TPIN and authorization
    tpin TEXT,                             -- TPIN (Transaction PIN) - encrypted
    
    -- Status
    status TEXT NOT NULL,                  -- PENDING/AUTHORIZED/REJECTED/EXPIRED
    request_id TEXT,                       -- CDSL request ID
    
    -- Timestamps
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL,
    authorized_at INTEGER,                 -- Authorization timestamp
    expires_at INTEGER,                    -- Expiration timestamp
    
    -- Response data
    raw_request TEXT,                      -- JSON
    raw_response TEXT,                     -- JSON
    error_message TEXT,
    
    CHECK (account_type IN ('leader', 'follower')),
    CHECK (status IN ('PENDING', 'AUTHORIZED', 'REJECTED', 'EXPIRED'))
);

CREATE INDEX IF NOT EXISTS idx_edis_account ON edis_transactions(account_type, status);
CREATE INDEX IF NOT EXISTS idx_edis_isin ON edis_transactions(isin);
CREATE INDEX IF NOT EXISTS idx_edis_request ON edis_transactions(request_id);

-- =============================================================================
-- 7. TRADER'S CONTROL (Kill Switch & Risk Controls)
-- =============================================================================

CREATE TABLE IF NOT EXISTS traders_control (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_type TEXT NOT NULL,            -- 'leader' or 'follower'
    
    -- Control type
    control_type TEXT NOT NULL,            -- 'KILL_SWITCH', 'RISK_LIMIT', 'POSITION_LIMIT'
    
    -- Kill switch
    kill_switch_status TEXT,               -- 'ACTIVE', 'INACTIVE'
    
    -- Risk limits
    daily_loss_limit REAL,                 -- Daily loss limit
    position_size_limit REAL,              -- Position size limit
    order_value_limit REAL,                -- Single order value limit
    
    -- Status
    is_active INTEGER DEFAULT 1,           -- Active flag
    
    -- Timestamps
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL,
    activated_at INTEGER,                  -- When control was activated
    deactivated_at INTEGER,                -- When control was deactivated
    
    -- Audit
    activated_by TEXT,                     -- Who activated
    reason TEXT,                           -- Reason for activation
    
    CHECK (account_type IN ('leader', 'follower')),
    CHECK (control_type IN ('KILL_SWITCH', 'RISK_LIMIT', 'POSITION_LIMIT')),
    CHECK (is_active IN (0, 1))
);

CREATE INDEX IF NOT EXISTS idx_traders_control_account ON traders_control(account_type, is_active);
CREATE INDEX IF NOT EXISTS idx_traders_control_type ON traders_control(control_type, is_active);

-- Risk limit violations
CREATE TABLE IF NOT EXISTS risk_violations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_type TEXT NOT NULL,            -- 'leader' or 'follower'
    
    -- Violation details
    violation_type TEXT NOT NULL,          -- 'DAILY_LOSS', 'POSITION_SIZE', 'ORDER_VALUE'
    limit_value REAL NOT NULL,             -- Configured limit
    actual_value REAL NOT NULL,            -- Actual value that violated
    
    -- Related entities
    order_id TEXT,                         -- Related order (if applicable)
    security_id TEXT,                      -- Related security (if applicable)
    
    -- Action taken
    action_taken TEXT,                     -- 'ORDER_REJECTED', 'KILL_SWITCH_ACTIVATED'
    
    -- Timestamps
    violated_at INTEGER NOT NULL,
    
    CHECK (account_type IN ('leader', 'follower')),
    CHECK (violation_type IN ('DAILY_LOSS', 'POSITION_SIZE', 'ORDER_VALUE')),
    FOREIGN KEY(order_id) REFERENCES orders(id)
);

CREATE INDEX IF NOT EXISTS idx_risk_violations_account ON risk_violations(account_type, violated_at);
CREATE INDEX IF NOT EXISTS idx_risk_violations_type ON risk_violations(violation_type);

-- =============================================================================
-- 8. FUNDS & MARGIN
-- =============================================================================

CREATE TABLE IF NOT EXISTS funds (
    snapshot_ts INTEGER NOT NULL,
    account_type TEXT NOT NULL,
    
    -- Fund limits
    available_balance REAL NOT NULL,       -- Available balance
    sodLimit REAL,                         -- Start of day limit
    collateral REAL,                       -- Collateral value
    margin_used REAL,                      -- Margin utilized
    margin_available REAL,                 -- Available margin
    
    -- Specific limits
    withdrawable_balance REAL,             -- Withdrawable amount
    blocked_margin REAL,                   -- Blocked margin
    
    -- Raw data
    raw_data TEXT,                         -- JSON
    
    PRIMARY KEY(snapshot_ts, account_type),
    CHECK (account_type IN ('leader', 'follower'))
);

CREATE INDEX IF NOT EXISTS idx_funds_account_ts ON funds(account_type, snapshot_ts);

-- Margin requirements for orders
CREATE TABLE IF NOT EXISTS margin_requirements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_type TEXT NOT NULL,            -- 'leader' or 'follower'
    order_id TEXT,                         -- Related order (if applicable)
    
    -- Margin details
    security_id TEXT NOT NULL,
    exchange_segment TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    price REAL,
    product TEXT NOT NULL,                 -- CNC/INTRADAY/MARGIN
    
    -- Margin calculation
    total_margin REAL NOT NULL,            -- Total margin required
    span_margin REAL,                      -- SPAN margin
    exposure_margin REAL,                  -- Exposure margin
    var_margin REAL,                       -- VAR margin
    
    -- Timestamps
    calculated_at INTEGER NOT NULL,
    
    CHECK (account_type IN ('leader', 'follower')),
    FOREIGN KEY(order_id) REFERENCES orders(id)
);

CREATE INDEX IF NOT EXISTS idx_margin_requirements_account ON margin_requirements(account_type);
CREATE INDEX IF NOT EXISTS idx_margin_requirements_order ON margin_requirements(order_id);

-- =============================================================================
-- 9. STATEMENTS (Ledger & Trade Book)
-- =============================================================================

-- Ledger entries
CREATE TABLE IF NOT EXISTS ledger_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_type TEXT NOT NULL,            -- 'leader' or 'follower'
    
    -- Entry details
    entry_date TEXT NOT NULL,              -- Date (YYYY-MM-DD)
    particulars TEXT,                      -- Description
    voucherNo TEXT,                        -- Voucher number
    voucherDate TEXT,                      -- Voucher date
    
    -- Amount
    debit REAL DEFAULT 0,                  -- Debit amount
    credit REAL DEFAULT 0,                 -- Credit amount
    balance REAL,                          -- Running balance
    
    -- Timestamps
    created_at INTEGER NOT NULL,
    
    CHECK (account_type IN ('leader', 'follower'))
);

CREATE INDEX IF NOT EXISTS idx_ledger_account_date ON ledger_entries(account_type, entry_date);
CREATE INDEX IF NOT EXISTS idx_ledger_date ON ledger_entries(entry_date);

-- Trade book (executed trades)
-- Complete coverage of DhanHQ Trade Book API (GET /trades, GET /trades/{order-id})
-- Reference: https://dhanhq.co/docs/v2/orders/ (Trade Book section)
CREATE TABLE IF NOT EXISTS trades (
    id TEXT PRIMARY KEY,                   -- Trade ID (exchange_trade_id if available)
    order_id TEXT NOT NULL,                -- orderId - Related order ID
    account_type TEXT NOT NULL,            -- 'leader' or 'follower'
    
    -- Exchange identifiers
    exchange_order_id TEXT,                -- exchangeOrderId - Exchange order ID
    exchange_trade_id TEXT,                -- exchangeTradeId - Exchange trade ID
    
    -- Instrument details
    security_id TEXT NOT NULL,             -- securityId
    exchange_segment TEXT NOT NULL,        -- exchangeSegment
    trading_symbol TEXT,                   -- tradingSymbol
    
    -- Transaction details
    side TEXT NOT NULL,                    -- transactionType (BUY/SELL)
    product TEXT NOT NULL,                 -- productType (CNC/INTRADAY/MARGIN/MTF/CO/BO)
    order_type TEXT,                       -- orderType (LIMIT/MARKET/STOP_LOSS/STOP_LOSS_MARKET)
    
    -- Quantity and pricing
    quantity INTEGER NOT NULL,             -- tradedQuantity
    price REAL NOT NULL,                   -- tradedPrice
    trade_value REAL,                      -- Trade value (qty * price)
    
    -- Charges (not in API response, for local calculation)
    brokerage REAL DEFAULT 0,
    exchange_charges REAL DEFAULT 0,
    clearing_charges REAL DEFAULT 0,
    stt REAL DEFAULT 0,                    -- Securities Transaction Tax
    stamp_duty REAL DEFAULT 0,
    transaction_charges REAL DEFAULT 0,
    gst REAL DEFAULT 0,
    total_charges REAL DEFAULT 0,
    net_amount REAL,                       -- Net amount after charges
    
    -- Timestamps
    trade_ts INTEGER NOT NULL,             -- Trade timestamp (internal)
    created_at INTEGER NOT NULL,           -- createTime (epoch)
    updated_at INTEGER,                    -- updateTime (epoch)
    exchange_time INTEGER,                 -- exchangeTime (epoch)
    
    -- F&O derivatives info
    drv_expiry_date INTEGER,               -- drvExpiryDate (epoch) - For F&O, expiry date of contract
    drv_option_type TEXT,                  -- drvOptionType (CALL/PUT) - Type of Option
    drv_strike_price REAL,                 -- drvStrikePrice - For Options, Strike Price
    
    -- Raw data
    raw_data TEXT,                         -- JSON
    
    CHECK (account_type IN ('leader', 'follower')),
    CHECK (side IN ('BUY', 'SELL')),
    CHECK (drv_option_type IS NULL OR drv_option_type IN ('CALL', 'PUT')),
    FOREIGN KEY(order_id) REFERENCES orders(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_trades_order ON trades(order_id);
CREATE INDEX IF NOT EXISTS idx_trades_account_ts ON trades(account_type, trade_ts);
CREATE INDEX IF NOT EXISTS idx_trades_security ON trades(security_id, exchange_segment);
CREATE INDEX IF NOT EXISTS idx_trades_exchange ON trades(exchange_order_id);
CREATE INDEX IF NOT EXISTS idx_trades_exchange_trade ON trades(exchange_trade_id);

-- =============================================================================
-- 10. POSTBACK (Webhook Configurations)
-- =============================================================================

CREATE TABLE IF NOT EXISTS postback_configs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_type TEXT NOT NULL,            -- 'leader' or 'follower'
    
    -- Webhook details
    webhook_url TEXT NOT NULL,             -- Webhook URL
    webhook_secret TEXT,                   -- Secret for signature verification (encrypted)
    
    -- Configuration
    event_types TEXT,                      -- JSON array of event types to receive
    is_active INTEGER DEFAULT 1,           -- Active flag
    
    -- Timestamps
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL,
    last_triggered_at INTEGER,             -- Last time webhook was triggered
    
    CHECK (account_type IN ('leader', 'follower')),
    CHECK (is_active IN (0, 1))
);

CREATE INDEX IF NOT EXISTS idx_postback_configs_account ON postback_configs(account_type, is_active);

-- Postback events received
CREATE TABLE IF NOT EXISTS postback_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_type TEXT NOT NULL,            -- 'leader' or 'follower'
    
    -- Event details
    event_type TEXT NOT NULL,              -- Event type (order update, trade, etc.)
    order_id TEXT,                         -- Related order ID
    
    -- Payload
    payload TEXT NOT NULL,                 -- JSON payload
    signature TEXT,                        -- Signature for verification
    is_verified INTEGER,                   -- Verification status
    
    -- Processing
    is_processed INTEGER DEFAULT 0,        -- Processing flag
    processed_at INTEGER,                  -- Processing timestamp
    error_message TEXT,                    -- Error if processing failed
    
    -- Timestamps
    received_at INTEGER NOT NULL,
    
    CHECK (account_type IN ('leader', 'follower')),
    CHECK (is_verified IN (0, 1)),
    CHECK (is_processed IN (0, 1)),
    FOREIGN KEY(order_id) REFERENCES orders(id)
);

CREATE INDEX IF NOT EXISTS idx_postback_events_account ON postback_events(account_type, received_at);
CREATE INDEX IF NOT EXISTS idx_postback_events_order ON postback_events(order_id);
CREATE INDEX IF NOT EXISTS idx_postback_events_processed ON postback_events(is_processed, received_at);

-- =============================================================================
-- 11. LIVE ORDER UPDATES (WebSocket Subscriptions)
-- =============================================================================

-- WebSocket connections tracking
CREATE TABLE IF NOT EXISTS websocket_connections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_type TEXT NOT NULL,            -- 'leader' or 'follower'
    
    -- Connection details
    connection_id TEXT NOT NULL,           -- Unique connection ID
    ws_url TEXT NOT NULL,                  -- WebSocket URL
    
    -- Status
    status TEXT NOT NULL,                  -- 'CONNECTING', 'CONNECTED', 'DISCONNECTED', 'ERROR'
    
    -- Subscriptions
    subscribed_events TEXT,                -- JSON array of subscribed events
    
    -- Connection metrics
    connect_attempts INTEGER DEFAULT 0,    -- Number of connection attempts
    last_heartbeat_at INTEGER,             -- Last heartbeat timestamp
    
    -- Timestamps
    connected_at INTEGER,
    disconnected_at INTEGER,
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL,
    
    CHECK (account_type IN ('leader', 'follower')),
    CHECK (status IN ('CONNECTING', 'CONNECTED', 'DISCONNECTED', 'ERROR'))
);

CREATE INDEX IF NOT EXISTS idx_ws_connections_account ON websocket_connections(account_type, status);
CREATE INDEX IF NOT EXISTS idx_ws_connections_status ON websocket_connections(status);

-- WebSocket messages received
CREATE TABLE IF NOT EXISTS websocket_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    connection_id TEXT NOT NULL,           -- Related connection
    account_type TEXT NOT NULL,            -- 'leader' or 'follower'
    
    -- Message details
    message_type TEXT NOT NULL,            -- Message type
    order_id TEXT,                         -- Related order ID (if applicable)
    
    -- Payload
    payload TEXT NOT NULL,                 -- JSON payload
    sequence_number INTEGER,               -- Sequence number (for ordering)
    
    -- Processing
    is_processed INTEGER DEFAULT 0,        -- Processing flag
    processed_at INTEGER,                  -- Processing timestamp
    
    -- Timestamps
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

-- =============================================================================
-- INSTRUMENTS & MARKET DATA
-- =============================================================================

-- Instruments: Cached instrument metadata
CREATE TABLE IF NOT EXISTS instruments (
    security_id TEXT PRIMARY KEY,
    exchange_segment TEXT NOT NULL,
    symbol TEXT NOT NULL,
    trading_symbol TEXT,
    name TEXT,
    instrument_type TEXT,                  -- OPTIDX/OPTSTK/FUTIDX/FUTSTK/EQUITY
    expiry_date TEXT,
    strike_price REAL,
    option_type TEXT,                      -- CE/PE
    lot_size INTEGER NOT NULL,
    tick_size REAL NOT NULL,
    underlying_security_id TEXT,
    isin TEXT,                             -- ISIN code
    meta TEXT,                             -- JSON
    updated_at INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_instruments_symbol ON instruments(symbol, exchange_segment);
CREATE INDEX IF NOT EXISTS idx_instruments_trading_symbol ON instruments(trading_symbol);
CREATE INDEX IF NOT EXISTS idx_instruments_underlying ON instruments(underlying_security_id, expiry_date);
CREATE INDEX IF NOT EXISTS idx_instruments_type ON instruments(instrument_type, exchange_segment);
CREATE INDEX IF NOT EXISTS idx_instruments_isin ON instruments(isin);

-- =============================================================================
-- COPY TRADING SPECIFIC TABLES
-- =============================================================================

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

-- =============================================================================
-- AUDIT & LOGGING
-- =============================================================================

-- Audit log: Track all API interactions
CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    action TEXT NOT NULL,                  -- API action (place_order, cancel_order, etc.)
    account_type TEXT NOT NULL,
    module TEXT,                           -- Module name (orders, funds, portfolio, etc.)
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
CREATE INDEX IF NOT EXISTS idx_audit_module ON audit_log(module, ts);

-- Error log: Track errors and exceptions
CREATE TABLE IF NOT EXISTS error_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    error_type TEXT NOT NULL,              -- Error type/category
    error_code TEXT,                       -- Error code
    error_message TEXT NOT NULL,           -- Error message
    stack_trace TEXT,                      -- Stack trace
    context TEXT,                          -- JSON context
    severity TEXT DEFAULT 'ERROR',         -- 'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'
    account_type TEXT,                     -- 'leader' or 'follower' (if applicable)
    order_id TEXT,                         -- Related order (if applicable)
    occurred_at INTEGER NOT NULL,
    CHECK (severity IN ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'))
);

CREATE INDEX IF NOT EXISTS idx_error_log_type ON error_log(error_type, occurred_at);
CREATE INDEX IF NOT EXISTS idx_error_log_severity ON error_log(severity, occurred_at);
CREATE INDEX IF NOT EXISTS idx_error_log_account ON error_log(account_type, occurred_at);

-- =============================================================================
-- INITIAL CONFIGURATION
-- =============================================================================

INSERT OR REPLACE INTO config (key, value, data_type, category, description, updated_at) VALUES
    -- Schema
    ('schema_version', '3', 'integer', 'system', 'Database schema version', strftime('%s', 'now')),
    
    -- Copy Trading
    ('copy_enabled', 'true', 'boolean', 'copy_trading', 'Global copy trading enabled flag', strftime('%s', 'now')),
    ('last_leader_event_ts', '0', 'integer', 'copy_trading', 'Last processed leader event timestamp', strftime('%s', 'now')),
    
    -- Snapshots
    ('last_position_snapshot_ts', '0', 'integer', 'portfolio', 'Last position snapshot timestamp', strftime('%s', 'now')),
    ('last_funds_snapshot_ts', '0', 'integer', 'funds', 'Last funds snapshot timestamp', strftime('%s', 'now')),
    ('last_holdings_snapshot_ts', '0', 'integer', 'portfolio', 'Last holdings snapshot timestamp', strftime('%s', 'now')),
    
    -- Order Types
    ('co_enabled', 'true', 'boolean', 'orders', 'Cover Order replication enabled', strftime('%s', 'now')),
    ('bo_enabled', 'true', 'boolean', 'orders', 'Bracket Order replication enabled', strftime('%s', 'now')),
    ('forever_enabled', 'true', 'boolean', 'orders', 'Forever Order replication enabled', strftime('%s', 'now')),
    
    -- Risk Controls
    ('kill_switch_enabled', 'false', 'boolean', 'risk', 'Kill switch enabled', strftime('%s', 'now')),
    ('daily_loss_limit_enabled', 'true', 'boolean', 'risk', 'Daily loss limit enabled', strftime('%s', 'now')),
    ('position_size_limit_enabled', 'true', 'boolean', 'risk', 'Position size limit enabled', strftime('%s', 'now')),
    
    -- WebSocket
    ('ws_reconnect_enabled', 'true', 'boolean', 'websocket', 'WebSocket auto-reconnect enabled', strftime('%s', 'now')),
    ('ws_max_reconnect_attempts', '10', 'integer', 'websocket', 'Maximum WebSocket reconnection attempts', strftime('%s', 'now')),
    
    -- Postback
    ('postback_enabled', 'false', 'boolean', 'postback', 'Postback webhook enabled', strftime('%s', 'now'));

-- =============================================================================
-- VIEWS FOR CONVENIENCE
-- =============================================================================

-- Active orders view
CREATE VIEW IF NOT EXISTS v_active_orders AS
SELECT 
    o.*,
    cm.follower_order_id,
    cm.sizing_strategy
FROM orders o
LEFT JOIN copy_mappings cm ON o.id = cm.leader_order_id
WHERE o.status IN ('PENDING', 'TRANSIT', 'OPEN', 'PARTIAL')
ORDER BY o.created_at DESC;

-- Latest positions view
CREATE VIEW IF NOT EXISTS v_latest_positions AS
SELECT p.*
FROM positions p
INNER JOIN (
    SELECT account_type, security_id, exchange_segment, product, MAX(snapshot_ts) as max_ts
    FROM positions
    GROUP BY account_type, security_id, exchange_segment, product
) latest ON p.account_type = latest.account_type
    AND p.security_id = latest.security_id
    AND p.exchange_segment = latest.exchange_segment
    AND p.product = latest.product
    AND p.snapshot_ts = latest.max_ts;

-- Latest holdings view
CREATE VIEW IF NOT EXISTS v_latest_holdings AS
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
CREATE VIEW IF NOT EXISTS v_latest_funds AS
SELECT f.*
FROM funds f
INNER JOIN (
    SELECT account_type, MAX(snapshot_ts) as max_ts
    FROM funds
    GROUP BY account_type
) latest ON f.account_type = latest.account_type
    AND f.snapshot_ts = latest.max_ts;

-- Active forever orders view
CREATE VIEW IF NOT EXISTS v_active_forever_orders AS
SELECT 
    fo.*,
    cm.follower_order_id as replicated_forever_order_id
FROM forever_orders fo
LEFT JOIN copy_mappings cm ON fo.id = cm.leader_order_id
WHERE fo.status IN ('PENDING', 'ACTIVE')
ORDER BY fo.created_at DESC;

-- Active bracket orders view
CREATE VIEW IF NOT EXISTS v_active_bracket_orders AS
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
CREATE VIEW IF NOT EXISTS v_cover_orders AS
SELECT *
FROM orders
WHERE co_stop_loss_value IS NOT NULL
ORDER BY created_at DESC;

-- Recent trades with P&L
CREATE VIEW IF NOT EXISTS v_recent_trades AS
SELECT 
    t.*,
    o.status as order_status,
    o.product,
    (t.price - t.brokerage - t.total_charges) as net_price
FROM trades t
LEFT JOIN orders o ON t.order_id = o.id
ORDER BY t.trade_ts DESC
LIMIT 100;

-- Active WebSocket connections
CREATE VIEW IF NOT EXISTS v_active_websocket_connections AS
SELECT 
    wc.*,
    (strftime('%s', 'now') - wc.last_heartbeat_at) as seconds_since_heartbeat
FROM websocket_connections wc
WHERE wc.status = 'CONNECTED'
ORDER BY wc.connected_at DESC;

-- Recent errors summary
CREATE VIEW IF NOT EXISTS v_recent_errors AS
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

-- View: Sliced Orders (groups orders from same slice request)
CREATE VIEW IF NOT EXISTS v_sliced_orders AS
SELECT 
    slice_order_id,
    COUNT(*) as slice_count,
    SUM(quantity) as total_quantity,
    MAX(total_slice_quantity) as original_quantity,
    security_id,
    exchange_segment,
    side,
    product,
    order_type,
    MIN(created_at) as first_order_time,
    MAX(created_at) as last_order_time,
    GROUP_CONCAT(id || ':' || quantity, ', ') as order_details,
    SUM(CASE WHEN status = 'EXECUTED' THEN 1 ELSE 0 END) as executed_count,
    SUM(CASE WHEN status IN ('PENDING', 'TRANSIT', 'OPEN') THEN 1 ELSE 0 END) as pending_count,
    SUM(CASE WHEN status IN ('CANCELLED', 'REJECTED') THEN 1 ELSE 0 END) as failed_count
FROM orders
WHERE is_sliced_order = 1
GROUP BY slice_order_id
ORDER BY first_order_time DESC;

