# Database Schema v3 - Comprehensive DhanHQ API Coverage

**Version**: 3.0  
**Date**: October 3, 2025  
**Status**: ✅ Complete

---

## Overview

This document describes the comprehensive database schema (v3) that covers all DhanHQ v2 API modules for the copy trading system. The schema is designed for SQLite with WAL mode for concurrent reads and includes complete audit trails.

---

## Architecture Principles

1. **Comprehensive Coverage**: All 11 DhanHQ API modules are covered
2. **Audit Trail**: Complete tracking of all API interactions and order lifecycle
3. **Resilience**: Support for WebSocket reconnection, postback webhooks, and error recovery
4. **Performance**: Optimized indexes for common query patterns
5. **Data Integrity**: Foreign keys, constraints, and validation
6. **Security**: Sensitive data flagging and encryption support

---

## Schema Modules

### 1. Authentication & Configuration

#### Tables
- **`auth_tokens`**: Store and manage authentication tokens for leader/follower accounts
  - Token storage with expiration tracking
  - Last usage timestamp for monitoring
  - Active/inactive flag for token rotation

- **`rate_limit_tracking`**: Track API rate limits per endpoint
  - Request count per time window
  - Per-account, per-endpoint tracking
  - Supports rate limiting logic

- **`config`**: System configuration with metadata
  - Enhanced with data types and categories
  - Sensitive data flagging
  - Category-based organization (auth, orders, risk, system)

#### Key Features
- Token rotation support without downtime
- Rate limit enforcement
- Configuration versioning

---

### 2. Orders (Enhanced)

#### Tables
- **`orders`**: Comprehensive order tracking
  - All order types: MARKET, LIMIT, STOP_LOSS, STOP_LOSS_MARKET
  - Cover Order (CO) and Bracket Order (BO) support
  - AMO (After Market Order) tracking
  - Exchange order ID mapping
  - Partial fill tracking (traded_qty, remaining_qty)
  - Average execution price

- **`order_events`**: Order lifecycle event tracking
  - Event source tracking (REST_API, WEBSOCKET, POSTBACK)
  - Sequence numbers for ordering
  - JSON event data storage

- **`order_modifications`**: Track order modification history
  - Modification type (QUANTITY, PRICE, TRIGGER_PRICE, VALIDITY)
  - Old/new value tracking
  - Success/failure status

#### Key Features
- Complete order lifecycle tracking
- Support for all DhanHQ order types
- Multi-source event capture
- Modification audit trail

---

### 3. Super Orders (Cover & Bracket)

#### Tables
- **`bracket_order_legs`**: Track BO legs (ENTRY, TARGET, SL)
  - Parent-child relationship tracking
  - Per-leg status tracking
  - Account-wise separation

#### Integration
- Cover Order parameters in `orders` table:
  - `co_stop_loss_value`
  - `co_trigger_price`
  
- Bracket Order parameters in `orders` table:
  - `bo_profit_value`
  - `bo_stop_loss_value`
  - `bo_order_type`
  - `parent_order_id`
  - `leg_type`

---

### 4. Forever Orders (GTT)

#### Tables
- **`forever_orders`**: Good Till Triggered orders
  - Single and OCO (One Cancels Other) support
  - Trigger conditions: LTP_ABOVE, LTP_BELOW, LTP_RANGE
  - Order to place after trigger
  - Expiration tracking
  - Link to triggered order

#### Key Features
- SINGLE and OCO order types
- Multiple trigger conditions
- Correlation with copy trading
- Trigger history tracking

---

### 5. Portfolio (Positions & Holdings)

#### Tables
- **`positions`**: Intraday and overnight positions
  - Day and Net position types
  - Buy/Sell quantity tracking
  - Average buy/sell prices
  - Realized/unrealized P&L
  - Margin requirements
  - LTP and close price

- **`holdings`**: Long-term delivery holdings
  - Total, DP, T+1 quantities
  - Available quantity for trading
  - Collateral tracking
  - Average cost and current LTP
  - P&L calculation

#### Key Features
- Separate position and holding tracking
- Collateral management
- P&L computation support
- Snapshot-based history

---

### 6. eDIS (Electronic Delivery Instruction)

#### Tables
- **`edis_transactions`**: TPIN and authorization tracking
  - ISIN-based tracking
  - TPIN storage (encrypted)
  - Authorization status
  - CDSL request ID mapping
  - Expiration tracking

#### Key Features
- Secure TPIN handling
- Request-response tracking
- Status lifecycle management
- Expiration monitoring

---

### 7. Trader's Control (Risk Management)

#### Tables
- **`traders_control`**: Kill switch and risk limits
  - Control types: KILL_SWITCH, RISK_LIMIT, POSITION_LIMIT
  - Daily loss limits
  - Position size limits
  - Order value limits
  - Activation/deactivation audit

- **`risk_violations`**: Track limit violations
  - Violation types with actual vs limit values
  - Related order/security tracking
  - Action taken (ORDER_REJECTED, KILL_SWITCH_ACTIVATED)

#### Key Features
- Real-time risk monitoring
- Automated limit enforcement
- Violation audit trail
- Kill switch support

---

### 8. Funds & Margin

#### Tables
- **`funds`**: Account fund limits and balances
  - Available balance
  - SOD (Start of Day) limit
  - Collateral value
  - Margin used/available
  - Withdrawable balance
  - Blocked margin

- **`margin_requirements`**: Order-level margin calculation
  - Total margin required
  - SPAN, Exposure, VAR margins
  - Pre-order margin check

#### Key Features
- Real-time fund tracking
- Margin requirement validation
- Multiple margin types
- Historical snapshots

---

### 9. Statements (Ledger & Trade Book)

#### Tables
- **`ledger_entries`**: Account ledger with debit/credit
  - Date-based entries
  - Voucher tracking
  - Running balance
  - Particulars/description

- **`trades`**: Executed trades with charges
  - Exchange trade ID mapping
  - Complete charge breakdown:
    - Brokerage
    - Exchange charges
    - Clearing charges
    - STT (Securities Transaction Tax)
    - Stamp duty
    - GST
  - Net amount calculation

#### Key Features
- Complete ledger history
- Detailed trade book
- Charge itemization
- Net P&L calculation

---

### 10. Postback (Webhooks)

#### Tables
- **`postback_configs`**: Webhook configuration
  - Webhook URL
  - Secret for signature verification (encrypted)
  - Event type subscriptions
  - Active/inactive flag
  - Last triggered timestamp

- **`postback_events`**: Received webhook events
  - Event type and payload
  - Signature verification
  - Processing status
  - Error tracking

#### Key Features
- Webhook registration
- Signature verification support
- Event deduplication
- Processing status tracking

---

### 11. Live Order Updates (WebSocket)

#### Tables
- **`websocket_connections`**: Connection tracking
  - Connection status (CONNECTING, CONNECTED, DISCONNECTED, ERROR)
  - Subscribed events
  - Heartbeat monitoring
  - Reconnection attempts

- **`websocket_messages`**: Received messages
  - Message type and payload
  - Sequence number for ordering
  - Processing status
  - Related order mapping

#### Key Features
- Connection state management
- Heartbeat tracking
- Message sequencing
- Processing deduplication

---

### 12. Instruments & Market Data

#### Tables
- **`instruments`**: Cached instrument metadata
  - Security ID, symbol, trading symbol
  - Instrument type (OPTIDX, OPTSTK, FUTIDX, FUTSTK, EQUITY)
  - Expiry, strike, option type
  - Lot size, tick size
  - Underlying security
  - ISIN code

#### Key Features
- Comprehensive instrument data
- Options and futures support
- Efficient lookup indexes
- ISIN mapping

---

### 13. Copy Trading

#### Tables
- **`copy_mappings`**: Leader-follower order mapping
  - Quantity mapping
  - Sizing strategy tracking
  - Status (pending, placed, failed, cancelled)
  - Error tracking

#### Key Features
- Leader-follower correlation
- Position sizing support
- Copy status tracking
- Error diagnostics

---

### 14. Audit & Logging

#### Tables
- **`audit_log`**: Complete API interaction log
  - Action and module tracking
  - Request/response (redacted)
  - Duration and status code
  - Error messages

- **`error_log`**: System error tracking
  - Error type and code
  - Stack trace
  - Context (JSON)
  - Severity levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)
  - Related entities (order, account)

#### Key Features
- Complete audit trail
- Performance monitoring
- Error analysis
- Severity classification

---

## Database Views

### Active Data Views
- **`v_active_orders`**: Currently active orders with copy mappings
- **`v_active_forever_orders`**: Active GTT orders
- **`v_active_bracket_orders`**: Active bracket orders with leg details
- **`v_cover_orders`**: All cover orders
- **`v_active_websocket_connections`**: Live WebSocket connections

### Latest Snapshots
- **`v_latest_positions`**: Most recent positions per account
- **`v_latest_holdings`**: Most recent holdings per account
- **`v_latest_funds`**: Most recent fund limits per account

### Analytics
- **`v_recent_trades`**: Recent trades with P&L
- **`v_recent_errors`**: Error summary (last 24 hours)

---

## Indexes

The schema includes comprehensive indexes for optimal query performance:

1. **Primary Keys**: All tables have appropriate primary keys
2. **Foreign Keys**: Referential integrity with cascade deletes where appropriate
3. **Lookup Indexes**: Fast lookups by account, security, status
4. **Composite Indexes**: Multi-column indexes for common queries
5. **Timestamp Indexes**: Efficient time-range queries

---

## Data Types & Constraints

### Account Types
- `'leader'`: Source account for copy trading
- `'follower'`: Destination account for copy trading

### Order Status
- `PENDING`: Order created, not yet submitted
- `TRANSIT`: Order in transit to exchange
- `OPEN`: Order active at exchange
- `PARTIAL`: Partially filled
- `EXECUTED`: Completely filled
- `CANCELLED`: Cancelled by user
- `REJECTED`: Rejected by exchange/system

### Exchange Segments
- `NSE_EQ`: NSE Equity
- `NSE_FNO`: NSE Futures & Options
- `BSE_EQ`: BSE Equity
- `BSE_FNO`: BSE Futures & Options
- `MCX_COMM`: MCX Commodity
- `CDS_FUT`: Currency Derivatives

### Products
- `CNC`: Cash & Carry (delivery)
- `INTRADAY`: Intraday (MIS)
- `MARGIN`: Margin product (NRML)
- `MTF`: Margin Trading Facility
- `CO`: Cover Order
- `BO`: Bracket Order

---

## Migration from v2 to v3

### New Tables Added
1. `auth_tokens`
2. `rate_limit_tracking`
3. `order_modifications`
4. `forever_orders`
5. `holdings`
6. `edis_transactions`
7. `traders_control`
8. `risk_violations`
9. `margin_requirements`
10. `ledger_entries`
11. `postback_configs`
12. `postback_events`
13. `websocket_connections`
14. `websocket_messages`
15. `error_log`

### Enhanced Tables
1. **`orders`**: Added fields for exchange details, AMO, partial fills
2. **`config`**: Added data_type, category, is_sensitive
3. **`trades`**: Added complete charge breakdown
4. **`order_events`**: Added event_source field

### Backward Compatibility
- All v2 tables and columns are preserved
- Existing queries will continue to work
- New fields have sensible defaults

---

## Usage Examples

### Check Active Orders
```sql
SELECT * FROM v_active_orders 
WHERE account_type = 'leader'
ORDER BY created_at DESC;
```

### Get Latest Positions with P&L
```sql
SELECT 
    security_id,
    net_qty,
    realized_pl,
    unrealized_pl,
    total_pl
FROM v_latest_positions
WHERE account_type = 'follower'
AND net_qty != 0;
```

### Check Risk Violations (Last 24 Hours)
```sql
SELECT 
    violation_type,
    actual_value,
    limit_value,
    action_taken,
    datetime(violated_at, 'unixepoch') as violated_time
FROM risk_violations
WHERE violated_at > (strftime('%s', 'now') - 86400)
ORDER BY violated_at DESC;
```

### Monitor WebSocket Health
```sql
SELECT 
    account_type,
    status,
    seconds_since_heartbeat,
    connect_attempts
FROM v_active_websocket_connections;
```

### Recent Errors Summary
```sql
SELECT * FROM v_recent_errors
ORDER BY error_count DESC, last_occurred DESC;
```

---

## Performance Considerations

1. **WAL Mode**: Write-Ahead Logging for concurrent reads
2. **Indexes**: Comprehensive indexing for fast queries
3. **Partitioning**: Consider time-based partitioning for large datasets
4. **Archiving**: Regular archival of old data (trades, audit logs)
5. **Vacuum**: Regular VACUUM operations to reclaim space

---

## Security Considerations

1. **Token Encryption**: `auth_tokens.access_token` should be encrypted at rest
2. **TPIN Security**: `edis_transactions.tpin` should be encrypted
3. **Webhook Secrets**: `postback_configs.webhook_secret` should be encrypted
4. **Sensitive Config**: Use `config.is_sensitive` flag for sensitive configuration
5. **Log Redaction**: All logs should redact tokens and sensitive data

---

## Maintenance

### Daily Tasks
- Monitor WebSocket connections
- Check error_log for critical issues
- Review risk_violations

### Weekly Tasks
- Analyze audit_log for patterns
- Review rate_limit_tracking
- Check database size and performance

### Monthly Tasks
- Archive old audit_log entries (>90 days)
- Archive old trade data (>1 year)
- VACUUM database
- Review and optimize indexes

---

## Configuration

### Initial Configuration (Auto-Created)
The schema automatically creates essential configuration entries:

```
schema_version = 3
copy_enabled = true
co_enabled = true
bo_enabled = true
forever_enabled = true
kill_switch_enabled = false
daily_loss_limit_enabled = true
position_size_limit_enabled = true
ws_reconnect_enabled = true
ws_max_reconnect_attempts = 10
postback_enabled = false
```

---

## Future Enhancements

Potential future additions:
1. Market data streaming tables
2. Option chain caching
3. Strategy backtesting tables
4. Performance analytics tables
5. Multi-strategy support
6. Advanced risk metrics

---

## Support

For schema questions or issues:
1. Refer to DhanHQ v2 API documentation: https://dhanhq.co/docs/v2/
2. Check the docs_links.txt file for specific module documentation
3. Review the audit_log and error_log tables for debugging

---

**Document Version**: 1.0  
**Last Updated**: October 3, 2025  
**Schema Version**: 3.0

