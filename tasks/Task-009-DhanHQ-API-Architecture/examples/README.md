# DhanHQ Copy Trading Examples

This directory contains example scripts demonstrating various features of the copy trading system.

## Prerequisites

1. **Environment Variables**: Copy `.env.example` to `.env` and configure:
   ```bash
   # Leader account
   LEADER_CLIENT_ID=your_leader_client_id
   LEADER_ACCESS_TOKEN=your_leader_access_token
   
   # Follower account
   FOLLOWER_CLIENT_ID=your_follower_client_id
   FOLLOWER_ACCESS_TOKEN=your_follower_access_token
   
   # System settings
   SIZING_STRATEGY=CAPITAL_PROPORTIONAL  # or FIXED_RATIO, RISK_BASED
   CAPITAL_RATIO=0.5  # Use 50% of follower capital
   ```

2. **Install Dependencies**:
   ```bash
   cd ..
   pip install -r requirements.txt
   ```

## Quick Start

Run the basic copy trading system:

```bash
python quick_start.py
```

This will:
1. Authenticate both leader and follower accounts
2. Initialize database and components
3. Connect to leader's order WebSocket feed
4. Replicate leader orders to follower account
5. Monitor and log all activities

Press `Ctrl+C` to stop gracefully.

## Example Scripts

### 1. `quick_start.py`
Basic usage showing how to start the copy trading system.

**Features**:
- Full system initialization
- Real-time order replication
- Graceful shutdown

**Usage**:
```bash
python quick_start.py
```

---

### 2. `check_balance.py` (Coming soon)
Check fund limits and available balance for both accounts.

**Features**:
- Fund limit retrieval
- Margin calculation
- Available balance display

---

### 3. `position_sizing_demo.py` (Coming soon)
Demonstrate position sizing strategies.

**Features**:
- Compare different sizing strategies
- Calculate quantities for sample orders
- Show margin requirements

---

### 4. `replay_orders.py` (Coming soon)
Replay historical orders from database.

**Features**:
- Load historical orders
- Analyze copy mappings
- Performance metrics

---

## Logging

All examples use structured logging. Check logs in:
- Console output (INFO level)
- `copy_trading.log` (DEBUG level)

## Troubleshooting

### Authentication Errors
- Verify your client IDs and access tokens
- Ensure tokens are not expired
- Check DhanHQ API status

### Connection Issues
- Check internet connectivity
- Verify WebSocket endpoint is accessible
- Review firewall settings

### Order Replication Failures
- Check follower account has sufficient margin
- Verify security ID is valid
- Review position size limits

## Advanced Configuration

Edit `src/core/config.py` for advanced settings:

```python
# Position sizing
SIZING_STRATEGY = "CAPITAL_PROPORTIONAL"
CAPITAL_RATIO = 0.5
FIXED_RATIO = 2.0
RISK_PER_TRADE_PCT = 2.0

# Order filtering
ALLOWED_EXCHANGES = ["NSE", "BSE"]
ALLOWED_SEGMENTS = ["EQ", "FNO"]
BLOCKED_SYMBOLS = []

# Risk limits
MAX_DAILY_LOSS = 10000.0
MAX_POSITION_SIZE = 500000.0
```

## Support

For issues or questions:
1. Check the main README: `../README.md`
2. Review documentation: `../docs/`
3. Check DhanHQ API docs: https://api.dhan.co

---

**Note**: These are examples for demonstration. Always test in a sandbox environment before live trading.

