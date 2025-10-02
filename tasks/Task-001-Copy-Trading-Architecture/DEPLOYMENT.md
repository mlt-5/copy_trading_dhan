# Deployment Guide

This guide covers deploying the copy trading system for production use.

## Pre-Deployment Checklist

- [ ] Tested in sandbox environment (if available)
- [ ] Verified credentials for both accounts
- [ ] Options trading enabled on both accounts
- [ ] Sufficient funds in follower account
- [ ] Risk limits configured appropriately
- [ ] Backup strategy in place
- [ ] Monitoring solution ready

## Deployment Options

### Option 1: Local Machine (Simplest)

**Pros**: Easy setup, full control  
**Cons**: Requires machine to be always on, single point of failure

```bash
# 1. Clone/download code
cd ~/trading
git clone <repo> copy_trading

# 2. Setup
cd copy_trading/tasks/Task-001-Copy-Trading-Architecture
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. Configure
cp env.example .env
nano .env  # Add credentials

# 4. Test
python -m src.main

# 5. Run in background (using nohup)
nohup python -m src.main > logs/app.log 2>&1 &

# 6. Check it's running
tail -f logs/app.log
```

### Option 2: Linux Server (Recommended)

**Pros**: Always on, more reliable, remote access  
**Cons**: Requires server management

#### A. Setup on Ubuntu/Debian

```bash
# Install Python 3.9+
sudo apt update
sudo apt install python3.9 python3.9-venv python3-pip

# Create app directory
sudo mkdir -p /opt/copy_trading
sudo chown $USER:$USER /opt/copy_trading
cd /opt/copy_trading

# Clone code
git clone <repo> .

# Setup virtual environment
python3.9 -m venv venv
source venv/bin/activate
pip install -r tasks/Task-001-Copy-Trading-Architecture/requirements.txt

# Configure
cd tasks/Task-001-Copy-Trading-Architecture
cp env.example .env
nano .env  # Add credentials
chmod 600 .env  # Secure permissions
```

#### B. Create Systemd Service

Create `/etc/systemd/system/copy-trading.service`:

```ini
[Unit]
Description=Options Copy Trading System
After=network.target

[Service]
Type=simple
User=trader
WorkingDirectory=/opt/copy_trading/tasks/Task-001-Copy-Trading-Architecture
Environment="PATH=/opt/copy_trading/venv/bin"
ExecStart=/opt/copy_trading/venv/bin/python -m src.main
Restart=on-failure
RestartSec=10
StandardOutput=append:/var/log/copy_trading/app.log
StandardError=append:/var/log/copy_trading/error.log

[Install]
WantedBy=multi-user.target
```

Create log directory:
```bash
sudo mkdir -p /var/log/copy_trading
sudo chown trader:trader /var/log/copy_trading
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable copy-trading
sudo systemctl start copy-trading

# Check status
sudo systemctl status copy-trading

# View logs
sudo journalctl -u copy-trading -f
```

### Option 3: Docker (Advanced)

Create `Dockerfile`:

```dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/

CMD ["python", "-m", "src.main"]
```

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  copy-trading:
    build: .
    container_name: copy-trading
    restart: unless-stopped
    env_file: .env
    volumes:
      - ./copy_trading.db:/app/copy_trading.db
      - ./logs:/app/logs
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

Deploy:
```bash
docker-compose up -d
docker-compose logs -f
```

## Environment Configuration

### Production Environment Variables

```env
# Accounts
LEADER_CLIENT_ID=<production_leader_id>
LEADER_ACCESS_TOKEN=<production_leader_token>
FOLLOWER_CLIENT_ID=<production_follower_id>
FOLLOWER_ACCESS_TOKEN=<production_follower_token>

# Environment
DHAN_ENV=prod

# Strategy (conservative for production)
SIZING_STRATEGY=capital_proportional
MAX_POSITION_SIZE_PCT=10.0

# Monitoring
LOG_LEVEL=INFO
SQLITE_PATH=/var/lib/copy_trading/copy_trading.db

# Safety
ENABLE_COPY_TRADING=true
```

### Security Hardening

1. **File Permissions**:
```bash
chmod 600 .env
chmod 600 copy_trading.db
```

2. **Firewall** (if applicable):
```bash
# Allow outbound HTTPS (for DhanHQ API)
sudo ufw allow out 443/tcp
sudo ufw allow out 80/tcp
```

3. **User Isolation**:
```bash
# Create dedicated user
sudo useradd -r -s /bin/false trader
sudo chown -R trader:trader /opt/copy_trading
```

## Monitoring & Alerts

### 1. Log Monitoring

Use `logrotate` to manage logs:

Create `/etc/logrotate.d/copy-trading`:
```
/var/log/copy_trading/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0640 trader trader
}
```

### 2. Health Check Script

Create `healthcheck.sh`:

```bash
#!/bin/bash

LOG_FILE=/var/log/copy_trading/app.log
MAX_AGE=300  # 5 minutes

if [ -f "$LOG_FILE" ]; then
    LAST_LOG=$(stat -c %Y "$LOG_FILE")
    NOW=$(date +%s)
    AGE=$((NOW - LAST_LOG))
    
    if [ $AGE -gt $MAX_AGE ]; then
        echo "ALERT: No activity in $AGE seconds"
        # Send alert (email, SMS, etc.)
        exit 1
    fi
fi

# Check if process is running
if ! pgrep -f "python.*src.main" > /dev/null; then
    echo "ALERT: Process not running"
    exit 1
fi

echo "OK: System healthy"
exit 0
```

Schedule with cron:
```bash
*/5 * * * * /opt/copy_trading/healthcheck.sh
```

### 3. Database Backup

Create `backup.sh`:

```bash
#!/bin/bash

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR=/var/backups/copy_trading
DB_PATH=/var/lib/copy_trading/copy_trading.db

mkdir -p $BACKUP_DIR

sqlite3 $DB_PATH ".backup $BACKUP_DIR/backup_$DATE.db"

# Keep only last 7 days
find $BACKUP_DIR -name "backup_*.db" -mtime +7 -delete

echo "Backup created: $BACKUP_DIR/backup_$DATE.db"
```

Schedule daily:
```bash
0 2 * * * /opt/copy_trading/backup.sh
```

### 4. Email Alerts (Optional)

Install `mailutils`:
```bash
sudo apt install mailutils
```

Modify healthcheck to send email:
```bash
echo "Alert message" | mail -s "Copy Trading Alert" your@email.com
```

## Maintenance

### Daily Tasks
- Check logs for errors: `tail -100 /var/log/copy_trading/app.log`
- Verify recent trades in database
- Monitor follower account margin

### Weekly Tasks
- Review performance metrics
- Check for software updates
- Verify backup integrity
- Review and adjust position size limits

### Monthly Tasks
- Rotate access tokens (if required by broker)
- Full database backup and archival
- Performance analysis and optimization
- Security review

## Troubleshooting in Production

### Service Won't Start

```bash
# Check service status
sudo systemctl status copy-trading

# Check logs
sudo journalctl -u copy-trading -n 50

# Verify configuration
cd /opt/copy_trading/tasks/Task-001-Copy-Trading-Architecture
source ../../venv/bin/activate
python -c "from src.config import get_config; get_config()"
```

### High Memory Usage

```bash
# Check memory
ps aux | grep python

# If needed, restart
sudo systemctl restart copy-trading
```

### Database Locked

```bash
# Check for stale locks
lsof /var/lib/copy_trading/copy_trading.db

# If needed, kill stale processes
kill -9 <PID>
```

## Rollback Procedure

If issues arise:

1. **Stop the system**:
```bash
sudo systemctl stop copy-trading
```

2. **Restore database** (if needed):
```bash
cp /var/backups/copy_trading/backup_<date>.db /var/lib/copy_trading/copy_trading.db
```

3. **Revert code** (if updated):
```bash
cd /opt/copy_trading
git checkout <previous-tag>
```

4. **Restart**:
```bash
sudo systemctl start copy-trading
```

## Performance Tuning

### Database Optimization

```bash
# Vacuum database (during low activity)
sqlite3 copy_trading.db "VACUUM;"

# Analyze tables
sqlite3 copy_trading.db "ANALYZE;"

# Check integrity
sqlite3 copy_trading.db "PRAGMA integrity_check;"
```

### Log Rotation

Adjust log levels based on needs:
- Development: `DEBUG`
- Production: `INFO`
- High-volume: `WARNING`

## Scaling Considerations

For higher volume:
- Consider PostgreSQL instead of SQLite
- Add Redis for caching
- Implement message queue (RabbitMQ, Kafka)
- Horizontal scaling with multiple followers
- Load balancing for API calls

## Security Checklist

- [ ] `.env` file permissions: 600
- [ ] Database file permissions: 600
- [ ] Dedicated user account
- [ ] No hardcoded secrets in code
- [ ] Regular token rotation
- [ ] Encrypted backups
- [ ] Secure log storage
- [ ] Firewall rules configured
- [ ] SSH key-only access (no password)
- [ ] Regular security updates

## Compliance

- Maintain audit logs for regulatory compliance
- Keep backups for required retention period
- Document all trades and decisions
- Regular reconciliation with broker statements

## Disaster Recovery

### Backup Strategy
- **Database**: Daily automated backups, 30-day retention
- **Configuration**: Version control + encrypted backup
- **Logs**: 7-day rotation, archived monthly

### Recovery Scenarios

1. **Server Failure**: 
   - Deploy to new server
   - Restore latest database backup
   - Resume from last processed order

2. **Data Corruption**:
   - Stop system immediately
   - Restore from last known good backup
   - Reconcile with broker API

3. **Credential Compromise**:
   - Revoke compromised tokens immediately
   - Generate new credentials
   - Update `.env` and restart

## Support & Escalation

**Critical Issues** (system down, wrong trades):
1. Stop system immediately
2. Assess impact
3. Notify stakeholders
4. Implement fix or rollback

**Non-Critical Issues** (warnings, performance):
1. Document in logs
2. Schedule maintenance window
3. Apply fix during low-activity period

---

**Deployment Checklist Complete?** Test thoroughly before going live!


