# DhanHQ Copy Trading System

**Production-Ready Copy Trading System with DhanHQ v2 API Integration**

---

## 🎯 **Overview**

Comprehensive copy trading system that automatically replicates orders from a leader account to a follower account using DhanHQ v2 API.

### **Key Features**

- ✅ Real-time order replication via WebSocket
- ✅ Multiple order types (MARKET, LIMIT, SL, SL-M, CO, BO)
- ✅ 3 position sizing strategies
- ✅ Automatic margin validation
- ✅ Production-ready resilience (retry, rate limiting, circuit breaker)
- ✅ Comprehensive testing (1,399 lines)
- ✅ Complete documentation

---

## 📊 **Project Status**

**Status**: ✅ **100% Complete - Production Ready**

| Component | Lines | Status |
|-----------|-------|--------|
| API Modules (11) | 2,503 | ✅ Complete |
| Core Modules (6) | 2,208 | ✅ Complete |
| Utils (2) | 559 | ✅ Complete |
| Main Orchestrator | 275 | ✅ Complete |
| Test Suite (9 files) | 1,399 | ✅ Complete |
| **Total Source Code** | **5,557** | **✅** |
| **Total with Tests** | **6,956** | **✅** |

---

## 🚀 **Quick Start**

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure credentials
cp env.example .env
nano .env  # Add your DhanHQ credentials

# 3. Run the system
cd examples && python quick_start.py
```

**See**: [QUICKSTART.md](./QUICKSTART.md) for 5-minute setup guide

---

## 📚 **Documentation**

### **Getting Started**
- **[QUICKSTART.md](./QUICKSTART.md)** - 5-minute setup
- **[SETUP.md](./SETUP.md)** - Comprehensive setup
- **[env.example](./env.example)** - Configuration template

### **Deployment**
- **[DEPLOYMENT.md](./DEPLOYMENT.md)** - 5 deployment options
- **[MIGRATION_GUIDE.md](./MIGRATION_GUIDE.md)** - Migrate from Task-001

### **Development**
- **[TESTING.md](./TESTING.md)** - Testing guide
- **[tests/README.md](./tests/README.md)** - Test suite
- **[examples/README.md](./examples/README.md)** - Examples

### **Reference**
- **[EXECUTIVE_SUMMARY.md](./EXECUTIVE_SUMMARY.md)** - Complete overview
- **[PROJECT_STRUCTURE.md](./PROJECT_STRUCTURE.md)** - Architecture
- **[changelogs.md](./changelogs.md)** - Change history
- **[TODO.md](./TODO.md)** - Tasks (all complete!)

---

## ⚙️ **Configuration**

```bash
# Leader account (copy FROM)
LEADER_CLIENT_ID=your_leader_id
LEADER_ACCESS_TOKEN=your_leader_token

# Follower account (copy TO)
FOLLOWER_CLIENT_ID=your_follower_id
FOLLOWER_ACCESS_TOKEN=your_follower_token

# Position sizing
SIZING_STRATEGY=CAPITAL_PROPORTIONAL
CAPITAL_RATIO=0.5
```

**See**: [env.example](./env.example) for all options

---

## 🧪 **Testing**

```bash
# Install dev dependencies
pip install -r requirements-dev.txt

# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html
```

**See**: [TESTING.md](./TESTING.md)

---

## 📁 **Project Structure**

```
src/
├── dhan_api/          # 11 API modules (2,503 lines)
├── core/              # 6 core modules (2,208 lines)
├── utils/             # 2 utilities (559 lines)
└── main.py            # Orchestrator (275 lines)

tests/                 # 9 test files (1,399 lines)
examples/              # Example scripts
```

**See**: [PROJECT_STRUCTURE.md](./PROJECT_STRUCTURE.md)

---

## 🎓 **Key Modules**

### **DhanHQ API Modules** (11)
1. **authentication** - Auth & tokens
2. **orders** - Basic orders
3. **super_order** - CO/BO orders
4. **forever_order** - GTT orders
5. **portfolio** - Holdings & positions
6. **edis** - EDIS operations
7. **traders_control** - Risk controls
8. **funds** - Funds & margin
9. **statement** - Trade statements
10. **postback** - Webhooks
11. **live_order_update** - WebSocket

### **Core Modules** (6)
1. **config** - Configuration
2. **models** - Data models
3. **database** - SQLite operations
4. **position_sizer** - Position sizing
5. **order_replicator** - Order replication
6. **main** - Orchestrator

### **Utils** (2)
1. **logger** - Structured logging
2. **resilience** - Retry, rate limit, circuit breaker

---

## 🛡️ **Resilience**

```python
# Retry with backoff
@RetryStrategy(max_attempts=3)
def api_call():
    return client.get_data()

# Rate limiting
limiter = RateLimiter(rate=10, burst=20)

# Circuit breaker
breaker = CircuitBreaker(failure_threshold=5)
```

---

## 🚢 **Deployment Options**

1. **Local** - Direct execution
2. **Background** - nohup/screen
3. **systemd** - Linux service
4. **Docker** - Container
5. **Cloud** - AWS/GCP VM

**See**: [DEPLOYMENT.md](./DEPLOYMENT.md)

---

## 📞 **Support**

- **Setup**: [SETUP.md](./SETUP.md)
- **Deployment**: [DEPLOYMENT.md](./DEPLOYMENT.md)
- **Testing**: [TESTING.md](./TESTING.md)
- **DhanHQ API**: https://api.dhan.co
- **Changes**: [changelogs.md](./changelogs.md)

---

## 🎉 **Ready to Trade!**

System is **100% complete** and **production-ready**.

**Start**: Follow [QUICKSTART.md](./QUICKSTART.md)

---

**Version**: 1.0.0  
**Status**: Production Ready  
**Last Updated**: October 4, 2025
