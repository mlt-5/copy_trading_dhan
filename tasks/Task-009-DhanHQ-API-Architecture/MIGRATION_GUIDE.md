# Migration Guide - From Old to New Architecture

Guide for migrating from the old Task-001 architecture to the new Task-009 DhanHQ API-aligned architecture.

---

## Overview

**Old Architecture** (`Task-001-Copy-Trading-Architecture`):
- Monolithic structure
- Mixed API and business logic
- Limited modularity
- Basic error handling

**New Architecture** (`Task-009-DhanHQ-API-Architecture`):
- Modular, API-aligned structure
- Clear separation of concerns
- Comprehensive testing
- Production-ready resilience

---

## Key Differences

### File Structure

**Old**:
```
Task-001/src/
├── auth/auth.py
├── config/config.py
├── database/database.py
├── orders/order_manager.py
├── position_sizing/position_sizer.py
└── websocket/ws_manager.py
```

**New**:
```
Task-009/src/
├── dhan_api/           # 11 API modules
│   ├── authentication.py
│   ├── orders.py
│   ├── super_order.py
│   └── ...
├── core/               # Business logic
│   ├── config.py
│   ├── database.py
│   ├── position_sizer.py
│   └── order_replicator.py
├── utils/              # Utilities
│   ├── logger.py
│   └── resilience.py
└── main.py             # Orchestrator
```

### Module Mapping

| Old Module | New Module | Notes |
|------------|------------|-------|
| `auth/auth.py` | `dhan_api/authentication.py` | Enhanced with token rotation |
| `config/config.py` | `core/config.py` | Added validation, enums |
| `database/database.py` | `core/database.py` | Added WAL mode, more methods |
| `database/models.py` | `core/models.py` | Added more models |
| `orders/order_manager.py` | Split into: | Better separation |
| | `dhan_api/orders.py` | Basic orders |
| | `dhan_api/super_order.py` | CO/BO orders |
| | `core/order_replicator.py` | Replication logic |
| `position_sizing/position_sizer.py` | `core/position_sizer.py` | Enhanced with FundsAPI |
| `websocket/ws_manager.py` | `dhan_api/live_order_update.py` | Improved reconnection |
| `main.py` | `main.py` | Restructured orchestrator |
| N/A | `dhan_api/forever_order.py` | NEW: GTT orders |
| N/A | `dhan_api/portfolio.py` | NEW: Portfolio management |
| N/A | `dhan_api/edis.py` | NEW: EDIS operations |
| N/A | `dhan_api/traders_control.py` | NEW: Risk controls |
| N/A | `dhan_api/funds.py` | NEW: Funds management |
| N/A | `dhan_api/statement.py` | NEW: Statements |
| N/A | `dhan_api/postback.py` | NEW: Webhooks |
| N/A | `utils/resilience.py` | NEW: Retry, rate limit, circuit breaker |
| N/A | `tests/*` | NEW: Comprehensive test suite |

---

## Migration Steps

### Step 1: Backup Old System

```bash
# Backup entire old system
cd /Users/mjolnir/Desktop/copy_trading_dhan
cp -r tasks/Task-001-Copy-Trading-Architecture tasks/Task-001-BACKUP-$(date +%Y%m%d)

# Backup database
cp copy_trading.db copy_trading_OLD_$(date +%Y%m%d).db
```

### Step 2: Install New System

```bash
# Navigate to new system
cd tasks/Task-009-DhanHQ-API-Architecture

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Step 3: Migrate Configuration

**Old `.env`**:
```bash
LEADER_CLIENT_ID=...
LEADER_ACCESS_TOKEN=...
FOLLOWER_CLIENT_ID=...
FOLLOWER_ACCESS_TOKEN=...
```

**New `.env`** (same format, more options):
```bash
# Copy from env.example
cp env.example .env

# Add your credentials (same as old system)
# Plus new options:
SIZING_STRATEGY=CAPITAL_PROPORTIONAL
CAPITAL_RATIO=0.5
MAX_DAILY_LOSS=10000.0
MAX_POSITION_SIZE=500000.0
# ... see env.example for all options
```

### Step 4: Migrate Database

**Option A: Fresh Start**
```bash
# New system will create new database
# Old data stays in old database
```

**Option B: Migrate Data** (optional)
```bash
# Export data from old database
sqlite3 ../../../copy_trading.db "SELECT * FROM orders;" > old_orders.csv

# Import into new database (manual, if needed)
# Note: Schema may have changed, manual mapping required
```

### Step 5: Update Code References

If you have custom code that imports from old modules:

**Old**:
```python
from auth.auth import DhanAuthManager
from orders.order_manager import OrderManager
from position_sizing.position_sizer import PositionSizer
```

**New**:
```python
from dhan_api import DhanAuthManager
from core import OrderReplicator, PositionSizer
```

### Step 6: Test New System

```bash
# Run tests
pytest

# Run system in test mode
cd examples
python quick_start.py
```

### Step 7: Run Both Systems in Parallel (Optional)

For safety, run both systems side-by-side initially:

1. **Old system**: Continue running with real trades
2. **New system**: Run in parallel to verify behavior
3. **Compare**: Check that both systems make same decisions
4. **Switch**: When confident, switch to new system only

---

## Configuration Migration

### Sizing Strategy

**Old** (hardcoded in code):
```python
SIZING_STRATEGY = "CAPITAL_PROPORTIONAL"
```

**New** (environment variable):
```bash
# In .env
SIZING_STRATEGY=CAPITAL_PROPORTIONAL
CAPITAL_RATIO=0.5
```

### Risk Limits

**Old** (may not have existed):
```python
# Hardcoded or not implemented
```

**New** (configurable):
```bash
# In .env
MAX_DAILY_LOSS=10000.0
MAX_POSITION_SIZE=500000.0
MAX_OPEN_POSITIONS=10
```

### Logging

**Old**:
```python
# Basic logging
logging.basicConfig(level=logging.INFO)
```

**New** (structured):
```python
# Configured in utils/logger.py
# Supports JSON logging, rotation, multiple handlers
```

---

## Feature Comparison

| Feature | Old System | New System |
|---------|-----------|-----------|
| **Basic Orders** | ✅ Yes | ✅ Yes (enhanced) |
| **Cover Orders (CO)** | ✅ Yes | ✅ Yes (improved) |
| **Bracket Orders (BO)** | ✅ Yes | ✅ Yes (improved) |
| **GTT Orders** | ❌ No | ✅ Yes (new) |
| **Position Sizing** | ✅ Basic | ✅ Advanced (3 strategies) |
| **Margin Validation** | ⚠️ Limited | ✅ Complete |
| **WebSocket** | ✅ Yes | ✅ Yes (improved reconnection) |
| **Database** | ✅ SQLite | ✅ SQLite (WAL mode) |
| **Error Handling** | ⚠️ Basic | ✅ Comprehensive |
| **Retry Logic** | ❌ No | ✅ Yes (exponential backoff) |
| **Rate Limiting** | ❌ No | ✅ Yes (token bucket) |
| **Circuit Breaker** | ❌ No | ✅ Yes |
| **Testing** | ❌ None | ✅ Comprehensive (1,399 lines) |
| **Documentation** | ⚠️ Limited | ✅ Extensive (21 files) |
| **Type Hints** | ⚠️ Partial | ✅ Complete |

---

## Benefits of Migration

### 1. Better Code Organization
- Clear separation: API vs. business logic
- Each API has its own module
- Easy to find and maintain code

### 2. More Features
- 7 NEW API modules
- Resilience utilities
- Comprehensive testing
- Better error handling

### 3. Production Ready
- Retry logic for transient failures
- Rate limiting to respect API limits
- Circuit breaker for failing services
- Comprehensive logging

### 4. Better Developer Experience
- Easy to test
- Easy to extend
- Well documented
- Type safe

### 5. Future Proof
- Aligned with DhanHQ API structure
- Easy to add new features
- API changes isolated to specific modules

---

## Rollback Plan

If you need to rollback to old system:

### Quick Rollback

```bash
# Stop new system
pkill -f "main.py"

# Start old system
cd tasks/Task-001-Copy-Trading-Architecture/src
python main.py
```

### Full Rollback

1. **Stop new system**
2. **Restore old database** (if you migrated data):
   ```bash
   cp copy_trading_OLD_YYYYMMDD.db copy_trading.db
   ```
3. **Start old system**
4. **Verify** trades are working

---

## Common Migration Issues

### Issue: Import Errors

**Problem**: Old code tries to import from old structure

**Solution**: Update imports:
```python
# Old
from orders.order_manager import OrderManager

# New
from core.order_replicator import OrderReplicator
```

### Issue: Configuration Not Found

**Problem**: `.env` file not configured

**Solution**:
```bash
cp env.example .env
nano .env  # Add credentials
```

### Issue: Database Schema Mismatch

**Problem**: Old database structure incompatible

**Solution**: Start with fresh database or manually migrate

### Issue: Different Behavior

**Problem**: New system behaves differently

**Solution**: 
- Check configuration (sizing strategy, risk limits)
- Review logs for differences
- Compare copy_mappings between systems

---

## Testing Migration

### 1. Test Configuration

```bash
python -c "from core import get_config; print('Config OK')"
```

### 2. Test Database

```bash
python -c "from core import init_database; db = init_database(); print('Database OK')"
```

### 3. Test Authentication

```bash
cd src
python -c "
from dhan_api import DhanAuthManager
from core import get_config
leader_config, _, _ = get_config()
auth = DhanAuthManager()
auth.authenticate_leader(leader_config.client_id, leader_config.access_token)
print('Auth OK')
"
```

### 4. Run Full Test Suite

```bash
pip install -r requirements-dev.txt
pytest
```

---

## Support

If you encounter issues during migration:

1. **Check logs**: `tail -f copy_trading.log`
2. **Review configuration**: Ensure `.env` is correctly set
3. **Test components**: Use test suite to verify
4. **Compare with old**: Run both systems side-by-side
5. **Check documentation**: QUICKSTART.md, SETUP.md, README.md

---

## Timeline

**Recommended Migration Timeline**:

- **Week 1**: Setup and testing
  - Install new system
  - Configure environment
  - Run test suite
  - Run in parallel with old system

- **Week 2**: Monitoring
  - Compare behaviors
  - Verify replication accuracy
  - Check logs for errors
  - Fine-tune configuration

- **Week 3**: Switch
  - Stop old system
  - Run new system exclusively
  - Monitor closely
  - Keep old system as backup

- **Week 4+**: Optimization
  - Optimize configuration
  - Review performance
  - Remove old system (optional)

---

**Migration complete!** Welcome to the new architecture! 🎉

