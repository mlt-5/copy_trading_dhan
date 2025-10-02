# Quick Start Guide

Get the copy trading system up and running in 5 minutes.

## Prerequisites Check

- [ ] Python 3.9+ installed (`python3 --version`)
- [ ] DhanHQ leader account credentials
- [ ] DhanHQ follower account credentials
- [ ] Options trading enabled on both accounts

## Installation Steps

### 1. Install Dependencies

```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install packages
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
# Copy environment template
cp env.example .env

# Edit with your credentials
nano .env
```

**Minimum required configuration**:
```env
LEADER_CLIENT_ID=your_leader_client_id
LEADER_ACCESS_TOKEN=your_leader_access_token
FOLLOWER_CLIENT_ID=your_follower_client_id
FOLLOWER_ACCESS_TOKEN=your_follower_access_token
```

### 3. Test Connection (Optional but Recommended)

Create a test script `test_connection.py`:

```python
from src.config import get_config
from src.auth import authenticate_accounts

# Load config
leader_config, follower_config, system_config = get_config()

print(f"Leader Client ID: {leader_config.client_id}")
print(f"Follower Client ID: {follower_config.client_id}")

# Test authentication
auth_manager = authenticate_accounts()
print("✓ Authentication successful!")
```

Run it:
```bash
python test_connection.py
```

### 4. Start the System

```bash
python -m src.main
```

## Expected Behavior

When running correctly, you should see:

```
============================================================
COPY TRADING SYSTEM STARTED
Environment: prod
Sizing Strategy: capital_proportional
Max Position Size: 10.0%
Monitoring leader account for new orders...
============================================================
```

## First Trade Test

1. Place a **small** options order in your leader account
2. Watch the console logs for replication activity
3. Check your follower account for the copied order
4. Verify the quantity was adjusted appropriately

## Stop the System

Press `Ctrl+C` to stop gracefully.

## Troubleshooting Quick Fixes

### "Missing required environment variables"
→ Check your `.env` file has all required variables

### "Authentication failed"
→ Verify your access tokens are correct and not expired

### "WebSocket connection failed"
→ Check internet connection and DhanHQ service status

### "Calculated quantity is 0"
→ Follower capital too low, increase funds or adjust strategy

## Configuration Examples

### Conservative (10% position size, 50% of leader size)
```env
SIZING_STRATEGY=fixed_ratio
COPY_RATIO=0.5
MAX_POSITION_SIZE_PCT=10.0
```

### Aggressive (20% position size, capital proportional)
```env
SIZING_STRATEGY=capital_proportional
MAX_POSITION_SIZE_PCT=20.0
```

### Risk-Based (strict 5% position limit)
```env
SIZING_STRATEGY=risk_based
MAX_POSITION_SIZE_PCT=5.0
```

## Next Steps

- Read [README.md](README.md) for full documentation
- Review [architecture/ARCHITECTURE.md](architecture/ARCHITECTURE.md) for system design
- Monitor logs for any warnings or errors
- Set up database backups
- Consider adding monitoring/alerting

## Safety Reminders

- ⚠️ Start with small positions
- ⚠️ Monitor actively, don't run unattended
- ⚠️ Test in sandbox first if available
- ⚠️ Set appropriate position size limits
- ⚠️ Keep logs for audit purposes

---

**Need Help?** See [README.md](README.md) Troubleshooting section.


