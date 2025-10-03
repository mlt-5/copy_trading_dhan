# Setup Guide - DhanHQ Copy Trading System

## Prerequisites

- **Python**: 3.8 or higher
- **Operating System**: Linux, macOS, or Windows
- **DhanHQ Account**: Active trading account with API access
- **Internet**: Stable connection for WebSocket streaming

---

## Step-by-Step Setup

### 1. Verify Python Installation

```bash
python --version
# Should show Python 3.8 or higher
```

If Python is not installed, download from [python.org](https://www.python.org/downloads/).

---

### 2. Navigate to Project Directory

```bash
cd /Users/mjolnir/Desktop/copy_trading_dhan/tasks/Task-009-DhanHQ-API-Architecture
```

---

### 3. Create Virtual Environment (Recommended)

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate

# On Windows:
venv\Scripts\activate
```

---

### 4. Install Dependencies

```bash
pip install -r requirements.txt
```

**Expected output:**
```
Successfully installed dhanhq-2.0.0 python-dotenv-1.0.0 websocket-client-1.6.0 ...
```

---

### 5. Configure Environment Variables

```bash
# Copy the example environment file
cp env.example .env

# Edit the .env file with your credentials
nano .env  # or use your preferred editor
```

**Required fields:**
```bash
# Leader account (account to copy FROM)
LEADER_CLIENT_ID=your_leader_client_id
LEADER_ACCESS_TOKEN=your_leader_access_token

# Follower account (account to copy TO)
FOLLOWER_CLIENT_ID=your_follower_client_id
FOLLOWER_ACCESS_TOKEN=your_follower_access_token

# Position sizing
SIZING_STRATEGY=CAPITAL_PROPORTIONAL
CAPITAL_RATIO=0.5  # Use 50% of follower capital
```

**How to get DhanHQ credentials:**
1. Login to your DhanHQ account
2. Go to API Management section
3. Generate API credentials (Client ID and Access Token)
4. Copy and paste into `.env` file

---

### 6. Verify Configuration

```bash
# Test configuration loading
cd src
python -c "from core import get_config; print('✅ Config loaded successfully')"
```

**Expected output:**
```
✅ Config loaded successfully
```

---

### 7. Initialize Database

```bash
# Database will be auto-created on first run
# But you can verify database setup:
python -c "from core import init_database; db = init_database(); print('✅ Database initialized')"
```

**Expected output:**
```
✅ Database initialized
```

---

### 8. Test Authentication

```bash
# Test leader account authentication
python -c "
from dhan_api import DhanAuthManager
from core import get_config
leader_config, follower_config, _ = get_config()
auth = DhanAuthManager()
auth.authenticate_leader(leader_config.client_id, leader_config.access_token)
print('✅ Leader authenticated')
"
```

**Expected output:**
```
✅ Leader authenticated
```

---

### 9. Run the System

#### Option A: Using Quick Start Script (Recommended)

```bash
cd examples
python quick_start.py
```

#### Option B: Using Main Module Directly

```bash
cd src
python main.py
```

**Expected output:**
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

✅ System started successfully!
📊 Monitoring leader account for orders...
Press Ctrl+C to stop
```

---

### 10. Verify Operation

1. **Check logs:**
   ```bash
   tail -f ../../copy_trading.log
   ```

2. **Check database:**
   ```bash
   sqlite3 ../../copy_trading.db "SELECT COUNT(*) FROM orders;"
   ```

3. **Place a test order** in your leader account and watch the system replicate it

---

## Troubleshooting

### Authentication Errors

**Error:** `Authentication failed`

**Solution:**
1. Verify your Client ID and Access Token are correct
2. Check if tokens have expired
3. Ensure API access is enabled in your DhanHQ account
4. Verify you're using v2 API credentials

### WebSocket Connection Errors

**Error:** `WebSocket connection failed`

**Solution:**
1. Check internet connectivity
2. Verify firewall allows WebSocket connections
3. Ensure DhanHQ WebSocket endpoint is accessible: `wss://api-feed.dhan.co`
4. Check if your network blocks WebSocket connections

### Module Import Errors

**Error:** `ModuleNotFoundError: No module named 'dhanhq'`

**Solution:**
```bash
# Ensure you're in the virtual environment
source venv/bin/activate  # On macOS/Linux

# Reinstall dependencies
pip install -r requirements.txt
```

### Insufficient Margin Errors

**Error:** `Insufficient margin for order`

**Solution:**
1. Reduce `CAPITAL_RATIO` in `.env` (e.g., from 0.5 to 0.3)
2. Check follower account has sufficient funds
3. Review `MAX_POSITION_SIZE` limit
4. Ensure follower account has required margin for the product type

### Database Lock Errors

**Error:** `database is locked`

**Solution:**
1. Ensure only one instance of the system is running
2. Check `DB_WAL_MODE=true` in `.env`
3. Close any other database connections

---

## Configuration Options

### Position Sizing Strategies

1. **CAPITAL_PROPORTIONAL** (Recommended)
   ```bash
   SIZING_STRATEGY=CAPITAL_PROPORTIONAL
   CAPITAL_RATIO=0.5  # Follower uses 50% of leader's capital proportion
   ```

2. **FIXED_RATIO**
   ```bash
   SIZING_STRATEGY=FIXED_RATIO
   FIXED_RATIO=2.0  # Follower trades 2x leader quantity
   ```

3. **RISK_BASED**
   ```bash
   SIZING_STRATEGY=RISK_BASED
   RISK_PER_TRADE_PCT=2.0  # Risk 2% of capital per trade
   ```

### Risk Limits

```bash
MAX_DAILY_LOSS=10000.0      # Stop trading after 10,000 INR loss
MAX_POSITION_SIZE=500000.0  # Max position value of 5 lakhs
MAX_OPEN_POSITIONS=10       # Max 10 concurrent positions
```

### Logging

```bash
LOG_LEVEL=INFO              # DEBUG for detailed logs
LOG_FILE=copy_trading.log   # Log file path
LOG_MAX_SIZE_MB=10          # Rotate after 10 MB
```

---

## Advanced Setup

### Running as a Service (Linux)

Create a systemd service file:

```bash
sudo nano /etc/systemd/system/copy-trading.service
```

Content:
```ini
[Unit]
Description=DhanHQ Copy Trading System
After=network.target

[Service]
Type=simple
User=your_username
WorkingDirectory=/path/to/Task-009-DhanHQ-API-Architecture/src
ExecStart=/path/to/venv/bin/python main.py
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable copy-trading
sudo systemctl start copy-trading
sudo systemctl status copy-trading
```

---

## Security Best Practices

1. **Never commit `.env` file** to git
   ```bash
   echo ".env" >> .gitignore
   ```

2. **Restrict file permissions**
   ```bash
   chmod 600 .env
   ```

3. **Use environment-specific credentials**
   - Production: `.env.production`
   - Staging: `.env.staging`
   - Development: `.env.development`

4. **Rotate access tokens regularly**
   - Set token expiry reminders
   - Update `.env` when tokens are rotated

5. **Monitor for unauthorized access**
   - Review API logs regularly
   - Set up alerts for unusual activity

---

## Next Steps

1. ✅ System is running
2. 📊 Monitor logs for order replication
3. 🧪 Test with small quantities first
4. 📈 Gradually increase position sizes
5. 🔍 Review copy mappings in database
6. 📝 Customize risk limits as needed

---

## Support

- **Documentation**: See `README.md` and `QUICKSTART.md`
- **Examples**: Check `examples/` directory
- **DhanHQ API**: https://api.dhan.co
- **Issues**: Check `errors.md` for known issues

---

**Setup complete! Your copy trading system is ready to use.** 🚀

