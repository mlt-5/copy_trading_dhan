-- Copy Trading System Database Schema v2
-- Migration: Add Cover Order & Bracket Order Support
-- Version: 2.0
-- Date: 2025-10-02

-- =============================================================================
-- Schema Migrations for CO/BO Support
-- =============================================================================

-- Add CO/BO columns to orders table
ALTER TABLE orders ADD COLUMN co_stop_loss_value REAL;           -- CO stop-loss level
ALTER TABLE orders ADD COLUMN co_trigger_price REAL;             -- CO trigger price (if supported)
ALTER TABLE orders ADD COLUMN bo_profit_value REAL;              -- BO target profit level
ALTER TABLE orders ADD COLUMN bo_stop_loss_value REAL;           -- BO stop-loss level
ALTER TABLE orders ADD COLUMN bo_order_type TEXT;                -- BO order type (MARKET/LIMIT)
ALTER TABLE orders ADD COLUMN parent_order_id TEXT;              -- For BO legs: parent BO order ID
ALTER TABLE orders ADD COLUMN leg_type TEXT;                     -- For BO legs: 'ENTRY', 'TARGET', 'SL'

-- Add indexes for new columns
CREATE INDEX IF NOT EXISTS idx_orders_parent ON orders(parent_order_id);
CREATE INDEX IF NOT EXISTS idx_orders_leg_type ON orders(leg_type);

-- Create bracket_order_legs table for tracking BO relationships
CREATE TABLE IF NOT EXISTS bracket_order_legs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    parent_order_id TEXT NOT NULL,     -- BO parent order ID
    leg_order_id TEXT NOT NULL,        -- Individual leg order ID
    leg_type TEXT NOT NULL,            -- 'ENTRY', 'TARGET', 'SL'
    account_type TEXT NOT NULL,        -- 'leader', 'follower'
    status TEXT DEFAULT 'PENDING',     -- Track leg status
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

-- Update schema version
UPDATE config SET value = '2', updated_at = strftime('%s', 'now') WHERE key = 'schema_version';

-- Add CO/BO specific config
INSERT OR IGNORE INTO config (key, value, description, updated_at) VALUES
    ('co_enabled', 'true', 'Cover Order replication enabled', strftime('%s', 'now')),
    ('bo_enabled', 'true', 'Bracket Order replication enabled', strftime('%s', 'now'));

-- =============================================================================
-- New Views for CO/BO Orders
-- =============================================================================

-- View: Active Bracket Orders with legs
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
WHERE o.bo_profit_value IS NOT NULL OR o.bo_stop_loss_value IS NOT NULL
ORDER BY o.created_at DESC;

-- View: Cover Orders
CREATE VIEW IF NOT EXISTS v_cover_orders AS
SELECT *
FROM orders
WHERE co_stop_loss_value IS NOT NULL
ORDER BY created_at DESC;

