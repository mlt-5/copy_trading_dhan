# Quick Start Guide

Get your DhanHQ Copy Trading System running in 5 minutes.

## Prerequisites

- Python 3.8+
- DhanHQ account with API access
- Two accounts: Leader (to copy from) and Follower (to copy to)

## Step 1: Setup Environment

1. **Clone or navigate to the project**:
   ```bash
   cd tasks/Task-009-DhanHQ-API-Architecture
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables**:
   
   Copy the example file and edit:
   ```bash
   cp env.example .env
   nano .env  # or use your preferred editor
   ```
   
   **Required fields in `.env`:**
   ```bash
   # Leader account (account to copy FROM)
   LEADER_CLIENT_ID=your_leader_client_id
   LEADER_ACCESS_TOKEN=your_leader_access_token
   
   # Follower account (account to copy TO)
   FOLLOWER_CLIENT_ID=your_follower_client_id
   FOLLOWER_ACCESS_TOKEN=your_follower_access_token
   
   # System configuration
   SIZING_STRATEGY=CAPITAL_PROPORTIONAL
   CAPITAL_RATIO=0.5
   ```

## Step 2: Verify Configuration

Run a quick test to verify your credentials:

```bash
cd src
python -c "from core import get_config; print('✅ Config loaded successfully')"
```

## Step 3: Initialize Database

The database will be created automatically on first run, but you can verify:

```bash
python -c "from core import init_database; db = init_database(); print('✅ Database initialized')"
```

## Step 4: Run the System

**Using the quick start example**:

```bash
cd examples
python quick_start.py
```

You should see:
```
============================================================
DhanHQ Copy Trading System - Quick Start
============================================================

Starting copy trading system...
[INFO] Authenticating leader account...
[INFO] Authenticating follower account...
[INFO] ✅ Both accounts authenticated
[INFO] Initializing DhanHQ API modules...
[INFO] ✅ API modules initialized
[INFO] Initializing position sizer...
[INFO] ✅ Position sizer initialized
[INFO] Initializing order replicator...
[INFO] ✅ Order replicator initialized
[INFO] Initializing WebSocket manager...
[INFO] ✅ WebSocket connected
[INFO] Starting monitoring loop...

✅ System started successfully!
📊 Monitoring leader account for orders...
Press Ctrl+C to stop
```

**Or using the main module directly**:

```bash
cd src
python main.py
```

## Step 5: Monitor Operation

The system will now:

1. **Monitor** leader account for new orders via WebSocket
2. **Calculate** appropriate follower quantities based on sizing strategy
3. **Validate** sufficient margin and risk limits
4. **Replicate** orders to follower account
5. **Log** all activities to console and `copy_trading.log`

### What to Expect

When leader places an order:
```
[INFO] 📥 Order update: 12345678 (PENDING)
[INFO] Replicating order: 12345678
[INFO] ✅ Order replicated: leader=12345678, follower=87654321
```

## Stop the System

Press `Ctrl+C` to gracefully shutdown:

```
^C
⚠️ Shutting down...
[INFO] Stopping WebSocket manager...
[INFO] Stopping copy trading system...
✅ System stopped gracefully
```

## Verify Operation

Check the database for replicated orders:

```bash
sqlite3 ../../copy_trading.db "SELECT * FROM copy_mappings;"
```

Or check logs:

```bash
tail -f ../../copy_trading.log
```

## Troubleshooting

### "Authentication failed"
- Verify `LEADER_CLIENT_ID` and `LEADER_ACCESS_TOKEN` are correct
- Ensure tokens haven't expired
- Check DhanHQ API status

### "WebSocket connection failed"
- Check internet connectivity
- Verify firewall allows WebSocket connections
- Ensure DhanHQ WebSocket endpoint is accessible

### "Insufficient margin"
- Reduce `CAPITAL_RATIO` (e.g., from 0.5 to 0.3)
- Check follower account has sufficient funds
- Review `MAX_POSITION_SIZE` limit

### "Order replication failed"
- Check logs for specific error: `tail -f ../../copy_trading.log`
- Verify security ID is valid
- Ensure exchange segment is supported

## Next Steps

1. **Customize Position Sizing**: Edit `SIZING_STRATEGY` in `.env`
   - `CAPITAL_PROPORTIONAL`: Scale by capital ratio
   - `FIXED_RATIO`: Fixed multiplier (e.g., 2x)
   - `RISK_BASED`: Risk-adjusted sizing

2. **Configure Order Filtering**: Edit `src/core/config.py`
   - Allowed exchanges/segments
   - Blocked symbols
   - Product type filters

3. **Set Risk Limits**: Update `src/core/config.py`
   - `MAX_DAILY_LOSS`: Maximum loss per day
   - `MAX_POSITION_SIZE`: Maximum position value

4. **Review Examples**: Check `examples/` directory for more usage patterns

5. **Read Documentation**: See `README.md` for comprehensive guide

## Production Deployment

For production use:

1. Use environment-specific `.env` files
2. Enable database backups
3. Set up monitoring and alerts
4. Configure log rotation
5. Use process manager (systemd, supervisor)
6. Set up secure token storage

See `DEPLOYMENT.md` for detailed instructions.

---

**Need Help?** 
- Documentation: `README.md`
- Examples: `examples/`
- DhanHQ API: https://api.dhan.co

