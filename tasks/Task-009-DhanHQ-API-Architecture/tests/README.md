# Test Suite - DhanHQ Copy Trading System

Comprehensive test suite for ensuring code quality and correctness.

## Test Structure

```
tests/
├── __init__.py              # Test package initialization
├── conftest.py              # Pytest fixtures and configuration
├── test_config.py           # Configuration tests
├── test_models.py           # Data model tests
├── test_database.py         # Database tests
├── test_position_sizer.py   # Position sizing tests
├── test_integration.py      # Integration tests
└── README.md                # This file
```

---

## Running Tests

### Prerequisites

Install development dependencies:
```bash
pip install -r requirements-dev.txt
```

### Run All Tests

```bash
pytest
```

### Run Specific Test Files

```bash
# Test configuration
pytest tests/test_config.py

# Test database
pytest tests/test_database.py

# Test integration
pytest tests/test_integration.py
```

### Run by Marker

```bash
# Run only unit tests
pytest -m unit

# Run only integration tests
pytest -m integration

# Run tests except slow ones
pytest -m "not slow"
```

### Run with Coverage

```bash
# Generate HTML coverage report
pytest --cov=src --cov-report=html

# View coverage in browser
open htmlcov/index.html
```

### Run with Verbose Output

```bash
pytest -v
```

---

## Test Categories

### Unit Tests (`@pytest.mark.unit`)
- Fast, isolated tests
- No external dependencies
- Test individual functions/methods
- **Examples**: Configuration parsing, model creation, utility functions

### Integration Tests (`@pytest.mark.integration`)
- Test multiple components together
- May require database or mock APIs
- Test complete workflows
- **Examples**: Order replication flow, database persistence

### Slow Tests (`@pytest.mark.slow`)
- Tests that take > 1 second
- Performance tests
- Load tests
- **Examples**: Rapid order processing, stress tests

---

## Writing Tests

### Test File Naming

- Prefix with `test_`: `test_module_name.py`
- Mirror source structure: `src/core/config.py` → `tests/test_config.py`

### Test Class Naming

```python
class TestClassName:
    """Test ClassName functionality."""
    
    def test_method_behavior(self):
        """Test that method behaves correctly."""
        # Test code
```

### Using Fixtures

Fixtures are defined in `conftest.py`:

```python
def test_with_fixtures(temp_db, mock_env, sample_order_data):
    """Test using multiple fixtures."""
    # Use fixtures in test
    db = DatabaseManager(temp_db)
    # ...
```

### Mocking External APIs

```python
from unittest.mock import Mock

def test_api_call():
    """Test API call with mock."""
    mock_api = Mock()
    mock_api.get_data.return_value = {'status': 'success'}
    
    result = mock_api.get_data()
    assert result['status'] == 'success'
```

---

## Available Fixtures

### Database Fixtures

- **`temp_db`**: Temporary database file path
- **`reset_singletons`**: Reset singleton instances between tests

### Environment Fixtures

- **`mock_env`**: Mock environment variables for testing

### Sample Data Fixtures

- **`sample_order_data`**: Sample basic order data
- **`sample_co_order_data`**: Sample Cover Order data
- **`sample_bo_order_data`**: Sample Bracket Order data
- **`sample_funds_data`**: Sample funds data

### Mock API Fixtures

- **`mock_dhan_client`**: Mock DhanHQ client

---

## Test Coverage Goals

| Component | Target Coverage |
|-----------|----------------|
| Core Modules | 85%+ |
| API Modules | 80%+ |
| Utils | 90%+ |
| Overall | 80%+ |

---

## Continuous Integration

### GitHub Actions (Example)

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v2
    
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: '3.8'
    
    - name: Install dependencies
      run: |
        pip install -r requirements-dev.txt
    
    - name: Run tests
      run: |
        pytest --cov=src --cov-report=xml
    
    - name: Upload coverage
      uses: codecov/codecov-action@v2
```

---

## Troubleshooting

### ImportError: No module named 'src'

**Solution**: Ensure pytest is run from project root or `pythonpath` is configured:
```bash
PYTHONPATH=src pytest
```

### Database Lock Errors

**Solution**: Use `reset_singletons` fixture to clean up between tests:
```python
def test_database(temp_db, reset_singletons):
    # Test code
```

### Slow Tests

**Solution**: Mark as slow and skip during development:
```python
@pytest.mark.slow
def test_performance():
    # Test code

# Skip slow tests
pytest -m "not slow"
```

---

## Best Practices

1. **Test Naming**: Use descriptive names that explain what is being tested
   ```python
   def test_capital_proportional_strategy_calculates_correct_quantity()
   ```

2. **Arrange-Act-Assert**: Structure tests clearly
   ```python
   def test_example():
       # Arrange
       data = create_test_data()
       
       # Act
       result = process_data(data)
       
       # Assert
       assert result == expected
   ```

3. **One Assertion Per Test**: Focus on testing one thing
   ```python
   def test_order_id_is_set():
       order = Order(...)
       assert order.order_id == "12345"
   
   def test_order_quantity_is_set():
       order = Order(...)
       assert order.quantity == 100
   ```

4. **Use Fixtures**: Don't repeat setup code
   ```python
   @pytest.fixture
   def sample_order():
       return Order(...)
   
   def test_order(sample_order):
       assert sample_order.order_id is not None
   ```

5. **Mock External Dependencies**: Don't make real API calls in tests
   ```python
   @patch('dhan_api.orders.OrdersAPI.place_order')
   def test_order_placement(mock_place_order):
       mock_place_order.return_value = {'orderId': '12345'}
       # Test code
   ```

---

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [Pytest Fixtures](https://docs.pytest.org/en/stable/fixture.html)
- [Python Mock](https://docs.python.org/3/library/unittest.mock.html)
- [Test Coverage](https://coverage.readthedocs.io/)

---

**Happy Testing!** 🧪

