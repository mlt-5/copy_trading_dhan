# Copy Trading System - Visual Overview

## System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          DhanHQ Cloud Services                              │
│  ┌──────────────────────────┐           ┌─────────────────────────────┐    │
│  │  REST API                │           │  WebSocket Stream           │    │
│  │  • Place Orders          │           │  • Order Updates (Leader)   │    │
│  │  • Get Funds/Positions   │           │  • Real-time Events         │    │
│  └────────┬─────────────────┘           └──────────────┬──────────────┘    │
└───────────┼──────────────────────────────────────────┼──────────────────────┘
            │                                           │
            │ HTTPS                                     │ WSS
            │                                           │
┌───────────▼───────────────────────────────────────────▼──────────────────────┐
│                     Copy Trading Application (Python)                        │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────┐    │
│  │                        Main Orchestrator                            │    │
│  │                    (State Machine + Event Loop)                     │    │
│  └──┬────────────────────────────────────────────────────────────┬───┘    │
│     │                                                             │         │
│     │  ┌──────────────────────────────────────────────────────┐ │         │
│     │  │          Configuration Manager                       │ │         │
│     │  │  • Environment Variables                             │ │         │
│     │  │  • Leader/Follower Credentials                       │ │         │
│     │  │  • Sizing Strategy, Risk Limits                      │ │         │
│     │  └──────────────────────────────────────────────────────┘ │         │
│     │                                                             │         │
│     │  ┌──────────────────────────────────────────────────────┐ │         │
│     │  │       Authentication Manager                         │ │         │
│     │  │  • Leader DhanHQ Client                              │ │         │
│     │  │  • Follower DhanHQ Client                            │ │         │
│     │  │  • Token Validation                                  │ │         │
│     │  └──────────────────────────────────────────────────────┘ │         │
│     │                                                             │         │
│     │  ┌───────────────────────────┐  ┌──────────────────────┐ │         │
│     ├─▶│   WebSocket Manager       │  │   Order Manager      │◀┤         │
│     │  │  • Connect to Leader      │  │  • Validate Orders   │ │         │
│     │  │  • Receive Order Events   │  │  • Place to Follower │ │         │
│     │  │  • Auto-reconnect         │  │  • Track Status      │ │         │
│     │  │  • Event Callbacks        │  │  • Audit Logging     │ │         │
│     │  └───────────┬───────────────┘  └──────────▲───────────┘ │         │
│     │              │                              │             │         │
│     │              │ Order Event                  │ API Call    │         │
│     │              │                              │             │         │
│     │              ▼                              │             │         │
│     │  ┌─────────────────────────────────────────┴───────────┐ │         │
│     │  │          Position Sizing Engine                     │ │         │
│     │  │  • Fetch Leader/Follower Funds                      │ │         │
│     │  │  • Calculate Capital Ratio                          │ │         │
│     │  │  • Apply Sizing Strategy:                           │ │         │
│     │  │    - Capital Proportional                           │ │         │
│     │  │    - Fixed Ratio                                    │ │         │
│     │  │    - Risk-Based                                     │ │         │
│     │  │  • Round to Lot Size                                │ │         │
│     │  │  • Apply Risk Limits                                │ │         │
│     │  │  • Validate Margin                                  │ │         │
│     │  └─────────────────────────────────────────────────────┘ │         │
│     │                              │                            │         │
│     │                              ▼                            │         │
│     │  ┌───────────────────────────────────────────────────────┴───────┐ │
│     └─▶│              SQLite Database Manager                          │ │
│        │  ┌──────────────────────────────────────────────────────────┐ │ │
│        │  │  Tables (12):                                            │ │ │
│        │  │  • orders: Leader & follower orders                      │ │ │
│        │  │  • order_events: Lifecycle events                        │ │ │
│        │  │  • trades: Execution records                             │ │ │
│        │  │  • copy_mappings: Leader→Follower links                  │ │ │
│        │  │  • positions: Position snapshots                         │ │ │
│        │  │  • funds: Fund limit snapshots                           │ │ │
│        │  │  • instruments: Cached metadata (lot sizes, etc.)        │ │ │
│        │  │  • audit_log: API interaction history                    │ │ │
│        │  │  • config: System configuration state                    │ │ │
│        │  │                                                           │ │ │
│        │  │  Views (3): Active orders, Latest positions/funds        │ │ │
│        │  │                                                           │ │ │
│        │  │  Features: WAL mode, Prepared statements, Transactions   │ │ │
│        │  └──────────────────────────────────────────────────────────┘ │ │
│        └──────────────────────────────────────────────────────────────┘ │
│                                                                            │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │                         Utilities                                   │  │
│  │  • Structured Logging (stdout + file)                               │  │
│  │  • Signal Handlers (SIGINT/SIGTERM)                                 │  │
│  │  • Graceful Shutdown Logic                                          │  │
│  └────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Data Flow: Order Replication

```
┌──────────────┐
│ Leader Places│
│ Options Order│
└──────┬───────┘
       │
       ▼
┌───────────────────┐
│ DhanHQ Processes  │
│ Order             │
└──────┬────────────┘
       │
       ▼
┌───────────────────────┐
│ WebSocket Event       │
│ (orderId, qty, etc.)  │
└──────┬────────────────┘
       │
       ▼
┌────────────────────────────────┐
│ WebSocket Manager              │
│ • Receives event               │
│ • Validates message            │
│ • Filters relevant orders      │
└──────┬─────────────────────────┘
       │
       ▼
┌────────────────────────────────┐
│ Order Manager                  │
│ • Parse order details          │
│ • Check if options order       │
│ • Save leader order to DB      │
│ • Check if already replicated  │
└──────┬─────────────────────────┘
       │
       ▼
┌────────────────────────────────┐
│ Position Sizing Engine         │
│ • Fetch leader funds           │
│ • Fetch follower funds         │
│ • Calculate capital ratio      │
│ • Apply sizing strategy        │
│ • Round to lot size            │
│ • Apply risk limits            │
│ • Validate margin              │
└──────┬─────────────────────────┘
       │
       ▼
┌────────────────────────────────┐
│ Order Manager                  │
│ • Build follower order params  │
│ • Call DhanHQ place_order API  │
│ • Get follower order ID        │
│ • Save follower order to DB    │
└──────┬─────────────────────────┘
       │
       ▼
┌────────────────────────────────┐
│ Database Manager               │
│ • Save copy_mapping record     │
│ • Link leader ↔ follower       │
│ • Store quantities             │
│ • Log to audit_log             │
└──────┬─────────────────────────┘
       │
       ▼
┌────────────────────────────────┐
│ Follower Order Placed          │
│ ✓ Audit trail complete         │
│ ✓ Monitoring logs generated    │
└────────────────────────────────┘
```

## Module Dependencies

```
main.py
  ├─ config/
  │   └─ config.py (no dependencies)
  │
  ├─ auth/
  │   ├─ config/
  │   └─ dhanhq (external)
  │
  ├─ database/
  │   ├─ config/
  │   ├─ models.py
  │   └─ sqlite3 (stdlib)
  │
  ├─ position_sizing/
  │   ├─ config/
  │   ├─ database/
  │   └─ dhanhq (external)
  │
  ├─ orders/
  │   ├─ config/
  │   ├─ database/
  │   ├─ position_sizing/
  │   └─ dhanhq (external)
  │
  ├─ websocket/
  │   ├─ config/
  │   └─ dhanhq (external)
  │
  └─ utils/
      └─ logger.py (stdlib only)
```

## State Machine

```
┌─────────────────┐
│  INITIALIZING   │ ── Load config, create instances
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ AUTHENTICATING  │ ── Validate credentials, init clients
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   CONNECTING    │ ── Establish WebSocket connection
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│      READY      │◄─┐ Monitor for orders, process events
└────────┬────────┘  │
         │           │
         │  Event    │
         ├───────────┘
         │
         │ (Ctrl+C / SIGTERM)
         ▼
┌─────────────────┐
│ SHUTTING_DOWN   │ ── Disconnect WS, close DB, cleanup
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│     STOPPED     │ ── Exit
└─────────────────┘
```

## Position Sizing Strategies

### 1. Capital Proportional (Default)

```
Leader Capital:   ₹1,000,000
Follower Capital: ₹500,000
Capital Ratio:    0.5

Leader Order:     100 qty
Follower Order:   50 qty (100 × 0.5 = 50)

✓ Automatic scaling
✓ Maintains proportional exposure
✓ Adjusts as balances change
```

### 2. Fixed Ratio

```
Copy Ratio:       0.5 (configured)

Leader Order:     100 qty
Follower Order:   50 qty (100 × 0.5 = 50)

✓ Simple and predictable
✓ Independent of capital changes
✓ Requires manual adjustment
```

### 3. Risk-Based

```
Follower Capital:     ₹500,000
Max Position Size:    10% = ₹50,000
Premium:              ₹100
Lot Size:             50

Value per lot:        ₹100 × 50 = ₹5,000
Max lots:             ₹50,000 / ₹5,000 = 10 lots
Follower Order:       500 qty (10 lots × 50)

✓ Capital-aware risk management
✓ Limits max position value
✓ Premium-based calculations
```

## Configuration Hierarchy

```
Environment Variables (.env)
         ↓
ConfigLoader (config.py)
         ↓
┌────────┴────────┐
│                 │
▼                 ▼
AccountConfig     SystemConfig
- client_id       - environment
- access_token    - sizing_strategy
- account_type    - copy_ratio
                  - max_position_size_pct
                  - sqlite_path
                  - log_level
                  - enable_copy_trading
```

## Database Schema Relationships

```
orders ──┬── order_events (1:N)
         │
         └── trades (1:N)
         
copy_mappings
  ├── leader_order_id  → orders.id (leader)
  └── follower_order_id → orders.id (follower)

positions (snapshots by timestamp)
funds (snapshots by timestamp)
instruments (reference data)
audit_log (independent log)
config (key-value store)
```

## File Organization

```
Task-001-Copy-Trading-Architecture/
│
├── 📁 architecture/
│   └── ARCHITECTURE.md         (Comprehensive design doc)
│
├── 📁 src/                     (Application source code)
│   ├── 📁 config/              (2 files)
│   ├── 📁 auth/                (2 files)
│   ├── 📁 database/            (4 files: schema, models, manager)
│   ├── 📁 position_sizing/     (2 files)
│   ├── 📁 orders/              (2 files)
│   ├── 📁 websocket/           (2 files)
│   ├── 📁 utils/               (2 files)
│   └── main.py                 (Orchestrator)
│
├── 📁 tests/                   (Empty, ready for implementation)
│
├── 📄 README.md                (Complete user guide)
├── 📄 QUICKSTART.md            (5-minute setup)
├── 📄 DEPLOYMENT.md            (Production deployment)
├── 📄 PROJECT_SUMMARY.md       (Project overview)
├── 📄 SYSTEM_OVERVIEW.md       (This file)
│
├── 📄 TODO.md                  (Project tracking)
├── 📄 changelogs.md            (Development history)
├── 📄 errors.md                (Error tracking)
│
├── 📄 requirements.txt         (Python dependencies)
├── 📄 env.example              (Config template)
└── 📄 .gitignore               (Version control)

Total: 26 files, ~6,300 lines
```

## Technology Stack

```
┌─────────────────────────────────────┐
│         Application Layer           │
│  Python 3.9+ (Main Language)        │
└─────────────┬───────────────────────┘
              │
┌─────────────▼───────────────────────┐
│         Integration Layer           │
│  • DhanHQ Python SDK (v2.0.2)       │
│  • WebSocket Client                 │
│  • REST API Client                  │
└─────────────┬───────────────────────┘
              │
┌─────────────▼───────────────────────┐
│       Persistence Layer             │
│  • SQLite 3 (Embedded)              │
│  • WAL Mode (Concurrent Reads)      │
│  • Prepared Statements              │
└─────────────┬───────────────────────┘
              │
┌─────────────▼───────────────────────┐
│       Standard Library              │
│  • json, logging, time              │
│  • dataclasses, typing              │
│  • sqlite3, signal, threading       │
└─────────────────────────────────────┘
```

## Execution Flow

```
$ python -m src.main
         │
         ▼
    Setup Logging
         │
         ▼
    Load Configuration
    (from .env)
         │
         ▼
    Initialize Database
    (create schema if needed)
         │
         ▼
    Authenticate Accounts
    (leader & follower)
         │
         ▼
    Initialize Position Sizer
    (fetch funds, cache)
         │
         ▼
    Initialize Order Manager
    (ready to replicate)
         │
         ▼
    Connect WebSocket
    (to leader orders)
         │
         ▼
    ╔══════════════════╗
    ║   Event Loop     ║ ◄─── Process order events
    ║   (READY State)  ║      as they arrive
    ╚══════════════════╝
         │
         │ (SIGINT/SIGTERM)
         ▼
    Graceful Shutdown
    (disconnect, close DB)
         │
         ▼
    Exit (0)
```

## Security Model

```
┌─────────────────────────────────────┐
│   Credentials (Environment Vars)    │
│   • Never hardcoded                 │
│   • Not committed to git            │
│   • File permissions: 600           │
└─────────────┬───────────────────────┘
              │
┌─────────────▼───────────────────────┐
│   Configuration Loader              │
│   • Loads from .env                 │
│   • Validates presence              │
│   • Singleton pattern               │
└─────────────┬───────────────────────┘
              │
┌─────────────▼───────────────────────┐
│   Authentication Manager            │
│   • Initializes DhanHQ clients      │
│   • Validates credentials           │
│   • Redacts tokens in logs          │
└─────────────┬───────────────────────┘
              │
┌─────────────▼───────────────────────┐
│   Secure Operations                 │
│   • Token used in API calls         │
│   • Never logged in plaintext       │
│   • Supports token rotation         │
└─────────────────────────────────────┘
```

## Error Handling Strategy

```
Try/Except Blocks at Every Layer
         │
         ▼
    Log Error with Context
    (structured logging)
         │
         ├─ Transient Error? ──► Retry with Backoff
         │                       (idempotent operations)
         │
         ├─ Critical Error? ───► Stop System
         │                       (auth failure, etc.)
         │
         └─ Order Error? ──────► Skip Order, Log
                                 (insufficient margin, etc.)
```

---

## Quick Reference

### Start System
```bash
python -m src.main
```

### Stop System
```
Ctrl+C (graceful shutdown)
```

### Check Logs
```bash
tail -f logs/app.log  # or stdout
```

### Query Database
```bash
sqlite3 copy_trading.db "SELECT * FROM copy_mappings ORDER BY created_at DESC LIMIT 10;"
```

### Configuration Files
- **Credentials**: `.env`
- **Dependencies**: `requirements.txt`
- **Schema**: `src/database/schema.sql`

### Documentation Map
- **Setup**: `QUICKSTART.md` → `README.md`
- **Architecture**: `ARCHITECTURE.md`
- **Production**: `DEPLOYMENT.md`
- **Overview**: `PROJECT_SUMMARY.md` (or this file)

---

**Version**: 1.0.0  
**Status**: ✅ Production Ready  
**Last Updated**: 2025-10-02


