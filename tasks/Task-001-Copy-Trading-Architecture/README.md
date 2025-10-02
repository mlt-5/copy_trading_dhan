# Options Copy Trading System

A real-time options copy trading application that replicates orders from a leader account (Account A) to a follower account (Account B) using DhanHQ API v2, Python, and SQLite3.

## Features

- ✅ **Real-time Order Replication**: Instantly copy orders via WebSocket
- ✅ **Intelligent Position Sizing**: Adjust quantities based on available capital
- ✅ **Options-Specific**: Designed for options trading with lot size handling
- ✅ **Multiple Sizing Strategies**: Capital proportional, fixed ratio, or risk-based
- ✅ **Risk Management**: Position size limits and margin validation
- ✅ **Resilient Architecture**: SQLite persistence, automatic reconnection, audit trail
- ✅ **Production-Ready**: Structured logging, error handling, graceful shutdown

## Architecture

See [architecture/ARCHITECTURE.md](architecture/ARCHITECTURE.md) for comprehensive system design documentation.

### High-Level Overview

```
Leader Account → DhanHQ API → WebSocket Stream → Copy Trading App
                                                      ↓
                                           Position Sizing Engine
                                                      ↓
                                              Order Validation
                                                      ↓
                                           Follower Account Orders
```

### Components

1. **Configuration Manager**: Environment-based configuration
2. **Authentication Module**: Multi-account credential management
3. **Database Layer**: SQLite with WAL mode for persistence
4. **Position Sizing Engine**: Capital-aware quantity calculation
5. **Order Manager**: Order placement and tracking
6. **WebSocket Manager**: Real-time leader order stream
7. **Main Orchestrator**: Event loop and state machine

## Prerequisites

- Python 3.9 or higher
- DhanHQ trading accounts (leader and follower)
- DhanHQ API access tokens
- Options trading enabled on both accounts

## Installation

### 1. Clone/Download

```bash
# If using git
git clone <repository-url>
cd copy_trading_dhan/tasks/Task-001-Copy-Trading-Architecture

# Or extract the archive
unzip copy_trading_architecture.zip
cd Task-001-Copy-Trading-Architecture
```

### 2. Create Virtual Environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate (macOS/Linux)
source venv/bin/activate

# Activate (Windows)
venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your credentials
nano .env  # or use your preferred editor
```

**Required Configuration**:
```env
LEADER_CLIENT_ID=your_leader_client_id
LEADER_ACCESS_TOKEN=your_leader_access_token
FOLLOWER_CLIENT_ID=your_follower_client_id
FOLLOWER_ACCESS_TOKEN=your_follower_access_token
```

See `.env.example` for all configuration options.

## Usage

### Start the System

```bash
python -m src.main
```

### Expected Output

```
2025-10-02 10:00:00 | INFO     | Starting Copy Trading System v1.0.0
2025-10-02 10:00:01 | INFO     | Loading configuration...
2025-10-02 10:00:01 | INFO     | Initializing database...
2025-10-02 10:00:02 | INFO     | Authenticating accounts...
2025-10-02 10:00:03 | INFO     | Both accounts authenticated successfully
2025-10-02 10:00:04 | INFO     | WebSocket connected successfully
============================================================
COPY TRADING SYSTEM STARTED
Environment: prod
Sizing Strategy: capital_proportional
Max Position Size: 10.0%
Monitoring leader account for new orders...
============================================================
```

### Stop the System

Press `Ctrl+C` for graceful shutdown.

## Configuration

### Position Sizing Strategies

#### 1. Capital Proportional (Default)
Scales quantity based on capital ratio between accounts.

```env
SIZING_STRATEGY=capital_proportional
```

**Example**:
- Leader capital: ₹1,000,000
- Follower capital: ₹500,000
- Leader order: 100 qty
- Follower order: 50 qty (scaled down)

#### 2. Fixed Ratio
Uses a fixed multiplier for all orders.

```env
SIZING_STRATEGY=fixed_ratio
COPY_RATIO=0.5
```

**Example**:
- Leader order: 100 qty
- Follower order: 50 qty (always 50% of leader)

#### 3. Risk-Based
Limits position size as percentage of capital.

```env
SIZING_STRATEGY=risk_based
MAX_POSITION_SIZE_PCT=10.0
```

**Example**:
- Follower capital: ₹500,000
- Max position: ₹50,000 (10%)
- Premium: ₹100
- Lot size: 50
- Max lots: 10 (₹50,000 / ₹5,000 per lot)

### Risk Management

Set maximum position size to limit exposure:

```env
MAX_POSITION_SIZE_PCT=10.0  # Max 10% of capital per position
```

### Logging

Adjust log verbosity:

```env
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR, CRITICAL
```

## Database

The system uses SQLite for persistence:

- **Default path**: `./copy_trading.db`
- **Mode**: WAL (Write-Ahead Logging) for concurrent reads
- **Retention**: All orders, trades, and audit logs

### Schema

Key tables:
- `orders`: All orders (leader & follower)
- `copy_mappings`: Links between leader and follower orders
- `positions`: Position snapshots
- `funds`: Fund limit snapshots
- `instruments`: Cached instrument metadata
- `audit_log`: API interaction history

### Backup

```bash
# Manual backup
sqlite3 copy_trading.db ".backup copy_trading_backup.db"

# Restore
sqlite3 copy_trading.db ".restore copy_trading_backup.db"
```

## Monitoring

### Logs

All activity is logged to stdout with structured format:

```
2025-10-02 10:05:23 | INFO | OrderManager | Replicating leader order: 12345678
2025-10-02 10:05:24 | INFO | PositionSizer | Quantity calculated: leader=100, follower=50
2025-10-02 10:05:25 | INFO | OrderManager | Follower order placed successfully: 87654321
```

### Database Queries

Query recent activity:

```sql
-- Recent copy mappings
SELECT * FROM copy_mappings ORDER BY created_at DESC LIMIT 10;

-- Today's orders
SELECT * FROM orders WHERE created_at > strftime('%s', 'now', '-1 day');

-- Latest funds
SELECT * FROM v_latest_funds;

-- Latest positions
SELECT * FROM v_latest_positions;
```

## Troubleshooting

### Authentication Failed

**Error**: "Leader authentication failed" or "Follower authentication failed"

**Solution**:
1. Verify credentials in `.env`
2. Check token expiry
3. Ensure API access is enabled for both accounts

### WebSocket Connection Failed

**Error**: "WebSocket connection failed"

**Solution**:
1. Check network connectivity
2. Verify leader credentials
3. Check DhanHQ WebSocket service status

### Insufficient Margin

**Warning**: "Insufficient margin for order"

**Solution**:
1. Add funds to follower account
2. Reduce `MAX_POSITION_SIZE_PCT`
3. Use `fixed_ratio` strategy with lower `COPY_RATIO`

### Calculated Quantity is 0

**Warning**: "Calculated quantity is 0, skipping"

**Cause**: Follower capital too low relative to leader

**Solution**:
1. Increase follower capital
2. Use `fixed_ratio` strategy
3. Adjust `COPY_RATIO` to ensure minimum 1 lot

## Safety & Risk Disclosure

⚠️ **IMPORTANT DISCLAIMERS**:

1. **No Warranty**: This software is provided "as-is" without warranty
2. **Test First**: Test thoroughly in sandbox before production
3. **Monitor Actively**: Do not run unattended
4. **Position Limits**: Always set appropriate position size limits
5. **Circuit Breakers**: The system includes circuit breakers but market conditions can change rapidly
6. **Your Responsibility**: You are responsible for all orders placed

## Development

### Project Structure

```
Task-001-Copy-Trading-Architecture/
├── architecture/
│   └── ARCHITECTURE.md          # Comprehensive design doc
├── src/
│   ├── config/                  # Configuration management
│   ├── auth/                    # Authentication
│   ├── database/                # SQLite persistence
│   ├── position_sizing/         # Position sizing engine
│   ├── orders/                  # Order management
│   ├── websocket/               # WebSocket client
│   ├── utils/                   # Utilities (logging, etc.)
│   └── main.py                  # Main entry point
├── tests/                       # Unit/integration tests
├── requirements.txt             # Dependencies
├── .env.example                 # Environment template
├── .gitignore                   # Git ignore rules
└── README.md                    # This file
```

### Running Tests

```bash
# Install dev dependencies
pip install pytest pytest-cov

# Run tests
pytest tests/

# With coverage
pytest --cov=src tests/
```

### Code Quality

```bash
# Install dev tools
pip install black flake8 mypy

# Format code
black src/

# Lint
flake8 src/

# Type check
mypy src/
```

## API Reference

See [DhanHQ API Documentation](https://dhanhq.co/docs/v2/) for complete API details.

Key endpoints used:
- `POST /orders`: Place order
- `GET /fund-limits`: Get fund limits
- `GET /positions`: Get positions
- WebSocket: Order updates stream

## Roadmap

Future enhancements:
- [ ] Multi-follower support (1 leader → N followers)
- [ ] Partial replication filters (specific instruments/strategies)
- [ ] Web dashboard UI for monitoring
- [ ] Advanced strategies (Kelly criterion, volatility-based)
- [ ] Backtesting engine
- [ ] ML-based trade filtering

## Support

For issues or questions:
1. Check [architecture/ARCHITECTURE.md](architecture/ARCHITECTURE.md)
2. Review logs for error messages
3. Verify configuration in `.env`
4. Consult [DhanHQ API Docs](https://dhanhq.co/docs/v2/)

## License

This project is provided for educational and personal use.

## Acknowledgments

- DhanHQ for API access
- Python community for excellent libraries
- SQLite for reliable embedded database

---

**Version**: 1.0.0  
**Last Updated**: 2025-10-02  
**Author**: Copy Trading System Architecture Team


