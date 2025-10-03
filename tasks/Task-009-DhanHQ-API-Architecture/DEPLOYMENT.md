# Deployment Guide - DhanHQ Copy Trading System

Comprehensive guide for deploying the copy trading system to production.

---

## Pre-Deployment Checklist

### 1. Environment Setup
- [ ] Python 3.8+ installed
- [ ] Virtual environment created
- [ ] All dependencies installed (`requirements.txt`)
- [ ] Development tools installed (`requirements-dev.txt` for testing)

### 2. Configuration
- [ ] `.env` file created from `env.example`
- [ ] Leader account credentials configured
- [ ] Follower account credentials configured
- [ ] Position sizing strategy selected
- [ ] Risk limits configured
- [ ] Database path configured

### 3. Testing
- [ ] All unit tests passing (`pytest -m unit`)
- [ ] All integration tests passing (`pytest -m integration`)
- [ ] Test coverage reviewed
- [ ] Manual testing completed

### 4. Security
- [ ] `.env` file NOT committed to git
- [ ] File permissions set correctly (`chmod 600 .env`)
- [ ] API tokens are valid and not expired
- [ ] Firewall rules configured (if applicable)
- [ ] SSL/TLS configured for WebSocket (production uses WSS)

---

## Deployment Options

### Option 1: Local Development/Testing

**Use Case**: Testing, development, personal use

**Steps**:
```bash
# 1. Clone/navigate to project
cd /Users/mjolnir/Desktop/copy_trading_dhan/tasks/Task-009-DhanHQ-API-Architecture

# 2. Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp env.example .env
nano .env  # Edit with your credentials

# 5. Run system
cd examples
python quick_start.py
```

**Pros**: Easy to set up, full control  
**Cons**: Requires terminal open, no auto-restart

---

### Option 2: Background Process (macOS/Linux)

**Use Case**: Running on personal machine in background

#### Using `nohup`:

```bash
# Start in background
cd /Users/mjolnir/Desktop/copy_trading_dhan/tasks/Task-009-DhanHQ-API-Architecture/src
nohup python main.py > ../copy_trading.log 2>&1 &

# Get process ID
echo $!

# Check if running
ps aux | grep main.py

# Stop
kill <PID>
```

#### Using `screen`:

```bash
# Start screen session
screen -S copy_trading

# Run system
cd /Users/mjolnir/Desktop/copy_trading_dhan/tasks/Task-009-DhanHQ-API-Architecture/src
python main.py

# Detach: Ctrl+A, then D
# Reattach: screen -r copy_trading
# Stop: Reattach and Ctrl+C
```

**Pros**: Runs in background, survives terminal close  
**Cons**: No auto-restart on failure, manual management

---

### Option 3: systemd Service (Linux)

**Use Case**: Production deployment on Linux server

#### Create Service File:

```bash
sudo nano /etc/systemd/system/copy-trading.service
```

**Content**:
```ini
[Unit]
Description=DhanHQ Copy Trading System
After=network.target

[Service]
Type=simple
User=your_username
Group=your_group
WorkingDirectory=/path/to/Task-009-DhanHQ-API-Architecture/src
Environment="PATH=/path/to/venv/bin"
EnvironmentFile=/path/to/Task-009-DhanHQ-API-Architecture/.env
ExecStart=/path/to/venv/bin/python main.py
Restart=on-failure
RestartSec=10
StandardOutput=append:/path/to/logs/copy_trading.log
StandardError=append:/path/to/logs/copy_trading_error.log

[Install]
WantedBy=multi-user.target
```

#### Enable and Start:

```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable service (start on boot)
sudo systemctl enable copy-trading

# Start service
sudo systemctl start copy-trading

# Check status
sudo systemctl status copy-trading

# View logs
sudo journalctl -u copy-trading -f

# Stop service
sudo systemctl stop copy-trading

# Restart service
sudo systemctl restart copy-trading
```

**Pros**: Auto-restart, runs on boot, systemd management  
**Cons**: Linux only, requires sudo access

---

### Option 4: Docker Container

**Use Case**: Portable deployment, isolation

#### Create Dockerfile:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ ./src/
COPY .env .env

# Run application
CMD ["python", "src/main.py"]
```

#### Build and Run:

```bash
# Build image
docker build -t copy-trading .

# Run container
docker run -d \
  --name copy-trading \
  --restart unless-stopped \
  -v $(pwd)/copy_trading.db:/app/copy_trading.db \
  -v $(pwd)/logs:/app/logs \
  copy-trading

# View logs
docker logs -f copy-trading

# Stop
docker stop copy-trading

# Start
docker start copy-trading
```

**Pros**: Isolated, portable, easy to manage  
**Cons**: Requires Docker knowledge, additional layer

---

### Option 5: Cloud VM (AWS EC2, Google Cloud, etc.)

**Use Case**: Production deployment with high availability

#### Setup Steps:

1. **Provision VM**:
   - Ubuntu 22.04 LTS recommended
   - Minimum: 1 CPU, 2GB RAM
   - Storage: 20GB+

2. **SSH into VM**:
   ```bash
   ssh user@your-vm-ip
   ```

3. **Install Dependencies**:
   ```bash
   sudo apt update
   sudo apt install python3 python3-pip python3-venv git -y
   ```

4. **Clone/Upload Code**:
   ```bash
   git clone <your-repo>
   # or
   scp -r ./Task-009-DhanHQ-API-Architecture user@your-vm-ip:/home/user/
   ```

5. **Setup Virtual Environment**:
   ```bash
   cd Task-009-DhanHQ-API-Architecture
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

6. **Configure**:
   ```bash
   cp env.example .env
   nano .env  # Add credentials
   ```

7. **Run as systemd Service** (see Option 3)

8. **Configure Firewall** (if needed):
   ```bash
   sudo ufw allow ssh
   sudo ufw allow 443  # If exposing web interface
   sudo ufw enable
   ```

**Pros**: Production-grade, scalable, remote access  
**Cons**: Costs money, requires cloud knowledge

---

## Post-Deployment Configuration

### 1. Monitoring

#### Setup Log Monitoring:

```bash
# Tail logs in real-time
tail -f copy_trading.log

# Check for errors
grep ERROR copy_trading.log

# Check for warnings
grep WARNING copy_trading.log
```

#### Monitor Process:

```bash
# Check if running
ps aux | grep python | grep main.py

# Check resource usage
top -p <PID>

# Or with htop
htop -p <PID>
```

### 2. Database Management

#### Regular Backups:

```bash
# Backup database
cp copy_trading.db copy_trading_$(date +%Y%m%d_%H%M%S).db

# Or create cron job
crontab -e

# Add line (daily backup at 2 AM):
0 2 * * * cp /path/to/copy_trading.db /path/to/backups/copy_trading_$(date +\%Y\%m\%d).db
```

#### Database Maintenance:

```bash
# Check database size
ls -lh copy_trading.db

# Vacuum database (optimize)
sqlite3 copy_trading.db "VACUUM;"

# Check integrity
sqlite3 copy_trading.db "PRAGMA integrity_check;"
```

### 3. Log Rotation

#### Setup logrotate (Linux):

```bash
sudo nano /etc/logrotate.d/copy-trading
```

**Content**:
```
/path/to/copy_trading.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0644 user group
}
```

---

## Security Best Practices

### 1. Credentials Management

- ✅ Store credentials in `.env` file only
- ✅ Never commit `.env` to version control
- ✅ Set restrictive file permissions: `chmod 600 .env`
- ✅ Use strong, unique access tokens
- ✅ Rotate tokens regularly (every 90 days)

### 2. Network Security

- ✅ Use firewall to restrict access
- ✅ Only allow necessary inbound/outbound traffic
- ✅ Use SSH keys instead of passwords (for remote access)
- ✅ Keep system and dependencies updated

### 3. Application Security

- ✅ Run as non-root user
- ✅ Use virtual environment (isolation)
- ✅ Keep dependencies updated: `pip install --upgrade -r requirements.txt`
- ✅ Monitor logs for suspicious activity
- ✅ Set appropriate risk limits

### 4. Data Security

- ✅ Regular database backups
- ✅ Encrypt sensitive data at rest (if applicable)
- ✅ Secure backup storage
- ✅ Test restore procedures

---

## Monitoring & Alerts

### 1. System Health

**Check Points**:
- Process is running
- Database is accessible
- WebSocket connection is active
- No critical errors in logs

**Monitoring Script** (`monitor.sh`):
```bash
#!/bin/bash

# Check if process is running
if ! pgrep -f "main.py" > /dev/null; then
    echo "ERROR: Copy trading system is not running!"
    # Send alert (email, Slack, etc.)
    exit 1
fi

# Check for recent errors
ERROR_COUNT=$(grep -c ERROR copy_trading.log | tail -100)
if [ $ERROR_COUNT -gt 10 ]; then
    echo "WARNING: High error count: $ERROR_COUNT"
    # Send alert
fi

echo "System health check: OK"
```

### 2. Trading Metrics

**Monitor**:
- Orders replicated successfully
- Failed replication attempts
- Margin validation failures
- WebSocket disconnections

**Query Database**:
```bash
# Recent copy mappings
sqlite3 copy_trading.db "SELECT * FROM copy_mappings ORDER BY created_at DESC LIMIT 10;"

# Failed replications today
sqlite3 copy_trading.db "SELECT COUNT(*) FROM copy_mappings WHERE status='failed' AND date(created_at, 'unixepoch') = date('now');"

# Success rate
sqlite3 copy_trading.db "SELECT 
    COUNT(CASE WHEN status='placed' THEN 1 END) * 100.0 / COUNT(*) as success_rate 
FROM copy_mappings;"
```

---

## Troubleshooting

### System Won't Start

**Check**:
1. Python version: `python --version` (must be 3.8+)
2. Dependencies installed: `pip list | grep dhanhq`
3. `.env` file exists and is readable
4. Credentials are valid
5. Check logs for errors

**Common Issues**:
- Missing environment variables
- Expired access tokens
- Database file locked
- Port conflicts

### WebSocket Disconnects

**Check**:
1. Internet connection stable
2. Firewall not blocking WSS
3. DhanHQ API status
4. Check reconnection logs

**Solution**: System auto-reconnects with backoff

### Orders Not Replicating

**Check**:
1. Leader account has orders
2. Order status is replicable (PENDING/TRANSIT/OPEN)
3. Follower has sufficient margin
4. Position size limits not exceeded
5. Check copy_mappings table for errors

**Debug**:
```bash
# Check recent orders
sqlite3 copy_trading.db "SELECT * FROM orders ORDER BY created_at DESC LIMIT 5;"

# Check failed mappings
sqlite3 copy_trading.db "SELECT * FROM copy_mappings WHERE status='failed' ORDER BY created_at DESC LIMIT 5;"
```

### High Memory Usage

**Check**:
- Database size: `ls -lh copy_trading.db`
- Log file size: `ls -lh copy_trading.log`
- Python process: `top -p <PID>`

**Solution**:
- Vacuum database: `sqlite3 copy_trading.db "VACUUM;"`
- Rotate logs
- Restart system if needed

---

## Maintenance

### Daily
- [ ] Check system is running
- [ ] Review logs for errors
- [ ] Verify orders are replicating

### Weekly
- [ ] Review replication success rate
- [ ] Check database size
- [ ] Verify backups are working

### Monthly
- [ ] Update dependencies (if security fixes)
- [ ] Review and adjust risk limits
- [ ] Clean up old logs/data
- [ ] Test disaster recovery

### Quarterly
- [ ] Rotate API tokens
- [ ] Full system audit
- [ ] Performance review
- [ ] Update documentation

---

## Scaling Considerations

### Multiple Followers

To copy from one leader to multiple followers:

1. Create multiple instances with different follower credentials
2. Use separate databases for each follower
3. Share leader connection (careful with rate limits)

**Alternative**: Modify `main.py` to support multiple followers

### Multiple Leaders

To copy from multiple leaders to one follower:

1. Run separate instances for each leader
2. Implement leader priority/filtering
3. Be careful with position limits

---

## Disaster Recovery

### Backup Strategy

**What to Backup**:
- `.env` file (store securely!)
- `copy_trading.db` (daily backups)
- Configuration files
- Logs (optional, for audit)

**Backup Script**:
```bash
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR=/path/to/backups

# Create backup directory
mkdir -p $BACKUP_DIR/$DATE

# Backup database
cp copy_trading.db $BACKUP_DIR/$DATE/

# Backup .env (encrypted)
tar czf - .env | openssl enc -aes-256-cbc -e -out $BACKUP_DIR/$DATE/env.tar.gz.enc

# Keep only last 30 days
find $BACKUP_DIR -type d -mtime +30 -exec rm -rf {} +
```

### Recovery Procedure

1. **Install system** on new machine (see deployment options)
2. **Restore `.env`** file
3. **Restore database**: `cp backup/copy_trading.db ./`
4. **Start system**
5. **Verify** orders are replicating

---

## Production Checklist

### Before Going Live

- [ ] All tests passing
- [ ] Manual testing completed
- [ ] Configuration verified
- [ ] Risk limits set appropriately
- [ ] Backup strategy implemented
- [ ] Monitoring setup
- [ ] Logs configured and rotating
- [ ] Security hardening complete
- [ ] Documentation reviewed
- [ ] Disaster recovery plan tested

### First Day

- [ ] Start with small position sizes
- [ ] Monitor closely for first hour
- [ ] Check replication is working correctly
- [ ] Verify margin calculations
- [ ] Review logs frequently

### First Week

- [ ] Gradually increase position sizes
- [ ] Monitor success rate
- [ ] Adjust risk limits if needed
- [ ] Review and optimize configuration

---

## Support & Resources

- **Documentation**: See README.md, QUICKSTART.md, TESTING.md
- **DhanHQ API**: https://api.dhan.co
- **Python**: https://www.python.org/
- **SQLite**: https://www.sqlite.org/

---

**Deployment complete!** Your copy trading system is ready for production. 🚀

