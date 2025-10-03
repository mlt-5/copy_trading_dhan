# Understanding models.py and database.py

**Purpose**: Explanation of the roles and relationship between `models.py` and `database.py`

---

## Overview: The Data Layer Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Application Layer                     │
│          (main.py, order_replicator.py, etc.)           │
└────────────────────┬────────────────────────────────────┘
                     │
                     ↓
         ┌───────────────────────┐
         │     dhan_api/         │  ← API calls to DhanHQ
         │     orders.py         │
         └───────────┬───────────┘
                     │
                     ↓
         ┌───────────────────────┐
         │   core/models.py      │  ← Data Structures (What)
         └───────────┬───────────┘
                     │
                     ↓
         ┌───────────────────────┐
         │   core/database.py    │  ← Data Operations (How)
         └───────────┬───────────┘
                     │
                     ↓
         ┌───────────────────────┐
         │  SQLite Database      │  ← Persistent Storage
         │  (copy_trading.db)    │
         └───────────────────────┘
```

---

## models.py - Data Structures (What)

**Location**: `src/core/models.py`

**Purpose**: Define the **shape** and **structure** of data objects

### What It Does

1. **Defines Data Structures**
   - Creates Python classes (dataclasses) representing business entities
   - Defines what fields each entity has
   - Defines data types for each field
   - Provides default values

2. **Type Safety**
   - Ensures type consistency across the application
   - Enables IDE autocompletion
   - Catches type errors at development time

3. **Serialization**
   - Provides `to_dict()` methods to convert objects to dictionaries
   - Makes it easy to convert between Python objects and JSON/database

4. **Documentation**
   - Self-documenting code (field names and types)
   - Clear contracts for what data looks like

### Key Models Defined

| Model | Purpose | Fields |
|-------|---------|--------|
| `Order` | Represents a trading order | 45 fields (id, status, side, quantity, price, etc.) |
| `Trade` | Represents a trade execution | 18 fields (order_id, quantity, price, timestamps, etc.) |
| `Position` | Represents a portfolio position | Holdings, P&L, average price, etc. |
| `Funds` | Represents account funds | Available margin, used margin, balance |
| `OrderEvent` | Represents order state changes | Order updates, status changes, timestamps |
| `Instrument` | Represents a tradable instrument | Security info, exchange, symbols |
| `CopyMapping` | Maps leader to follower accounts | Multipliers, filters, rules |

### Example: Order Model

```python
@dataclass
class Order:
    """Represents an order in the database."""
    # Required fields
    id: str                              # DhanHQ orderId
    account_type: Literal['leader', 'follower']
    status: str                          # Order status
    side: str                            # BUY/SELL
    product: str                         # CNC/INTRADAY/MARGIN
    order_type: str                      # LIMIT/MARKET
    security_id: str                     # Instrument ID
    quantity: int                        # Order quantity
    
    # Optional fields
    price: Optional[float] = None
    trigger_price: Optional[float] = None
    correlation_id: Optional[str] = None
    # ... 40+ more fields
    
    def to_dict(self) -> dict:
        """Convert order to dictionary."""
        return {
            'id': self.id,
            'status': self.status,
            'side': self.side,
            # ... all fields
        }
```

### Why Separate from Database?

✅ **Clean Separation**: Business logic separate from storage logic
✅ **Reusability**: Same models can be used with different databases
✅ **Testing**: Easy to create mock objects for testing
✅ **Type Safety**: Python type hints work everywhere
✅ **Flexibility**: Can change database implementation without changing models

---

## database.py - Data Operations (How)

**Location**: `src/core/database.py`

**Purpose**: Handle **all database operations** (CRUD operations)

### What It Does

1. **Connection Management**
   - Establishes SQLite connections
   - Manages connection pooling
   - Handles connection errors and retries

2. **CRUD Operations** (Create, Read, Update, Delete)
   - **Create**: Insert new records
   - **Read**: Query and retrieve records
   - **Update**: Modify existing records
   - **Delete**: Remove records (soft or hard)

3. **Transaction Management**
   - Begin/commit/rollback transactions
   - Ensures data consistency
   - Handles concurrent access

4. **Schema Management**
   - Initialize database schema
   - Run migrations
   - Version control for database structure

5. **Query Optimization**
   - Uses indexes for fast lookups
   - Prepared statements for security
   - Efficient batch operations

### Key Operations Provided

#### Order Operations (8 methods)
```python
save_order(order: Order)              # Insert or update order
get_order(order_id: str) -> Order     # Get order by ID
get_order_by_correlation_id()         # Get order by custom ID
update_order_status()                 # Update order status
save_order_modification()             # Log order modifications
get_order_modifications()             # Get modification history
save_order_event()                    # Log order events
get_order_events()                    # Get order event timeline
```

#### Trade Operations (5 methods)
```python
save_trade(trade: Trade)              # Insert or update trade
get_trade_by_id()                     # Get trade by ID
get_trades_by_order_id()              # Get all trades for an order
get_trades()                          # Advanced filtering
get_trades_summary()                  # Aggregated statistics
```

#### Position & Funds Operations
```python
save_position()                       # Update position
get_positions()                       # Get all positions
save_funds()                          # Update fund info
get_funds()                           # Get account funds
```

#### Copy Mapping Operations
```python
save_copy_mapping()                   # Configure leader-follower
get_copy_mapping()                    # Get mapping rules
update_copy_mapping()                 # Modify mapping
```

### Example: Save Order Operation

```python
def save_order(self, order: Order) -> None:
    """
    Save order to database.
    
    Args:
        order: Order object with all fields
    """
    # Convert model to database format
    self.conn.execute("""
        INSERT OR REPLACE INTO orders (
            id, account_type, status, side, product,
            order_type, security_id, quantity, price,
            created_at, updated_at, ...
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ...)
    """, (
        order.id,
        order.account_type,
        order.status,
        order.side,
        order.product,
        order.order_type,
        order.security_id,
        order.quantity,
        order.price,
        order.created_at,
        order.updated_at,
        # ... all 45 fields
    ))
    self.conn.commit()
    
    logger.debug(f"Saved order: {order.id}")
```

### Why Separate from Models?

✅ **Single Responsibility**: Each file has one job
✅ **Database Independence**: Can swap SQLite for PostgreSQL
✅ **Centralized Logic**: All SQL queries in one place
✅ **Error Handling**: Centralized database error management
✅ **Performance**: Optimize queries without changing models
✅ **Security**: Prevent SQL injection with prepared statements

---

## How They Work Together

### Example: Placing an Order

```python
# Step 1: API wrapper gets response from DhanHQ
# File: dhan_api/orders.py
response = dhan_client.place_order(...)  # API call

# Step 2: Create Order model from response
# File: core/models.py (implicitly used)
order = Order(
    id=response['orderId'],
    status=response['orderStatus'],
    side='BUY',
    quantity=100,
    price=3500.0,
    # ... other fields from response
)

# Step 3: Save order to database
# File: core/database.py
db_manager = DatabaseManager('copy_trading.db')
db_manager.save_order(order)  # Persists to SQLite

# Later: Retrieve order
retrieved_order = db_manager.get_order(order.id)
print(retrieved_order.status)  # Access using model attributes
```

### Data Flow

```
┌──────────────────────────────────────────────────────┐
│ 1. DhanHQ API Response (JSON)                        │
│    {"orderId": "123", "orderStatus": "PENDING", ...} │
└─────────────────┬────────────────────────────────────┘
                  │
                  ↓
┌──────────────────────────────────────────────────────┐
│ 2. Parse into Order model (models.py)                │
│    order = Order(id="123", status="PENDING", ...)    │
└─────────────────┬────────────────────────────────────┘
                  │
                  ↓
┌──────────────────────────────────────────────────────┐
│ 3. Save to database (database.py)                    │
│    db.save_order(order)                              │
└─────────────────┬────────────────────────────────────┘
                  │
                  ↓
┌──────────────────────────────────────────────────────┐
│ 4. SQLite Database (persistent storage)              │
│    INSERT INTO orders VALUES (...)                   │
└──────────────────────────────────────────────────────┘
```

---

## Benefits of This Architecture

### 1. **Separation of Concerns**
- **models.py**: "What does the data look like?"
- **database.py**: "How do we store/retrieve it?"

### 2. **Type Safety**
```python
# With models.py, you get autocomplete and type checking
order = Order(id="123", ...)
order.status  # ✅ IDE knows this exists
order.foobar  # ❌ IDE error: attribute doesn't exist
```

### 3. **Easy Testing**
```python
# Create test data without database
test_order = Order(
    id="test123",
    status="PENDING",
    # ... minimal required fields
)

# Test business logic without database
assert test_order.status == "PENDING"
```

### 4. **Clear Contracts**
```python
# Function signature makes it clear what's expected
def process_order(order: Order) -> None:
    # ✅ Clear: expects Order model
    # ✅ Type-safe: IDE warns if you pass wrong type
    pass
```

### 5. **Easy Refactoring**
- Change database structure? Update `database.py` only
- Add new field? Update `models.py` schema and `database.py` queries
- Switch from SQLite to PostgreSQL? Replace `database.py` implementation

### 6. **Performance Optimization**
- `database.py` can optimize queries without touching models
- Add indexes, caching, connection pooling independently

---

## Real-World Example

### Scenario: Track Order Lifecycle

```python
from core.models import Order, OrderEvent
from core.database import DatabaseManager

# Initialize database
db = DatabaseManager('copy_trading.db')
db.connect()

# 1. Order placed
order = Order(
    id="112111182045",
    account_type="leader",
    status="PENDING",
    side="BUY",
    security_id="11536",
    quantity=100,
    price=3500.0,
    created_at=int(time.time()),
    updated_at=int(time.time())
)

# Save to database
db.save_order(order)

# 2. Order modified
db.save_order_modification(
    order_id=order.id,
    field_name="quantity",
    old_value=100,
    new_value=150,
    modified_at=int(time.time())
)

# 3. Order executed (partial fill)
order.status = "PARTIAL"
order.traded_qty = 50
db.save_order(order)  # Update

# Log event
db.save_order_event(
    event=OrderEvent(
        order_id=order.id,
        event_type="PARTIAL_FILL",
        event_data={"filled_qty": 50},
        event_ts=int(time.time())
    )
)

# 4. Query order history
modifications = db.get_order_modifications(order.id)
events = db.get_order_events(order.id)

# All stored, all tracked, all retrievable
```

---

## Summary

### models.py

| Aspect | Description |
|--------|-------------|
| **Purpose** | Define data structures |
| **What** | Shape of data (fields, types) |
| **Why** | Type safety, consistency, documentation |
| **Usage** | Create/manipulate objects in memory |
| **Examples** | `Order`, `Trade`, `Position`, `Funds` |

### database.py

| Aspect | Description |
|--------|-------------|
| **Purpose** | Database operations |
| **What** | CRUD operations, queries, transactions |
| **Why** | Persistence, retrieval, consistency |
| **Usage** | Save/load data from SQLite |
| **Examples** | `save_order()`, `get_order()`, `get_trades()` |

### Relationship

```
models.py (Structure) + database.py (Operations) = Complete Data Layer
```

**Analogy**:
- **models.py** = Blueprint of a house (defines what it looks like)
- **database.py** = Construction crew (builds and maintains the house)
- **SQLite** = The actual physical house (where you live)

---

## When to Use Each

### Use models.py when:
- ✅ Creating new data objects
- ✅ Passing data between functions
- ✅ Validating data structure
- ✅ Converting between formats (JSON ↔ Python)
- ✅ Type checking in IDE

### Use database.py when:
- ✅ Saving data permanently
- ✅ Retrieving historical data
- ✅ Querying/filtering records
- ✅ Updating existing records
- ✅ Managing transactions

---

**Key Takeaway**: `models.py` defines **what** the data is, `database.py` defines **how** to persist and retrieve it. Together, they form a clean, maintainable data layer.

