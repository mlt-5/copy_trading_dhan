# Testing Guide - DhanHQ Copy Trading System

Comprehensive guide for testing the copy trading system.

## Overview

The test suite includes:
- **Unit Tests**: Fast, isolated tests for individual components
- **Integration Tests**: Tests for component interactions
- **Resilience Tests**: Tests for retry, rate limiting, circuit breaking

---

## Quick Start

### Install Test Dependencies

```bash
pip install -r requirements-dev.txt
```

### Run All Tests

```bash
pytest
```

### Run with Coverage

```bash
pytest --cov=src --cov-report=html
open htmlcov/index.html
```

---

## Test Categories

### 1. Unit Tests

**Location**: `tests/test_*.py` with `@pytest.mark.unit`

**Purpose**: Test individual functions and methods in isolation

**Examples**:
```bash
# All unit tests
pytest -m unit

# Specific module
pytest tests/test_config.py -m unit
```

**Coverage**: `test_config.py`, `test_models.py`, `test_database.py`, `test_position_sizer.py`, `test_resilience.py`

### 2. Integration Tests

**Location**: `tests/test_integration.py` with `@pytest.mark.integration`

**Purpose**: Test multiple components working together

**Examples**:
```bash
# All integration tests
pytest -m integration

# Specific test
pytest tests/test_integration.py::TestOrderReplicationFlow
```

**Coverage**: Order replication flow, database persistence, system performance

### 3. Slow Tests

**Location**: Tests marked with `@pytest.mark.slow`

**Purpose**: Performance and load tests

**Examples**:
```bash
# Run slow tests
pytest -m slow

# Skip slow tests
pytest -m "not slow"
```

---

## Test Structure

```
tests/
├── __init__.py                 # Test package
├── conftest.py                 # Fixtures and configuration
├── README.md                   # Test documentation
├── test_config.py              # Configuration tests
├── test_models.py              # Data model tests
├── test_database.py            # Database tests
├── test_position_sizer.py      # Position sizing tests
├── test_resilience.py          # Resilience utilities tests
└── test_integration.py         # Integration tests
```

---

## Running Tests

### By File

```bash
pytest tests/test_config.py
pytest tests/test_database.py
pytest tests/test_integration.py
```

### By Marker

```bash
# Unit tests only
pytest -m unit

# Integration tests only
pytest -m integration

# Everything except slow tests
pytest -m "not slow"
```

### By Test Name

```bash
# Specific test
pytest tests/test_config.py::TestGetConfig::test_get_config_with_env_vars

# Pattern matching
pytest -k "test_capital_proportional"
```

### With Output Options

```bash
# Verbose output
pytest -v

# Show print statements
pytest -s

# Stop on first failure
pytest -x

# Show local variables on failure
pytest -l
```

---

## Test Coverage

### Generate Coverage Report

```bash
# HTML report
pytest --cov=src --cov-report=html

# Terminal report
pytest --cov=src --cov-report=term-missing

# Both
pytest --cov=src --cov-report=html --cov-report=term-missing
```

### View Coverage

```bash
# Open HTML report
open htmlcov/index.html

# Or navigate to:
# htmlcov/index.html in your browser
```

### Coverage Goals

| Component | Target | Current |
|-----------|--------|---------|
| Core Modules | 85%+ | TBD |
| API Modules | 80%+ | TBD |
| Utils | 90%+ | TBD |
| Overall | 80%+ | TBD |

---

## Writing Tests

### Test File Template

```python
"""
Unit tests for module_name.
"""

import pytest
from module_name import ClassName


@pytest.mark.unit
class TestClassName:
    """Test ClassName functionality."""
    
    def test_method_name(self):
        """Test that method does something."""
        # Arrange
        instance = ClassName()
        
        # Act
        result = instance.method()
        
        # Assert
        assert result is not None
```

### Using Fixtures

```python
def test_with_fixtures(temp_db, mock_env, sample_order_data):
    """Test using multiple fixtures."""
    # temp_db: Temporary database path
    # mock_env: Mock environment variables
    # sample_order_data: Sample order data dictionary
    
    from core.database import DatabaseManager
    db = DatabaseManager(temp_db)
    # Use sample_order_data...
```

### Mocking External APIs

```python
from unittest.mock import Mock, patch

def test_api_call():
    """Test API call with mock."""
    mock_api = Mock()
    mock_api.place_order.return_value = {'orderId': '12345'}
    
    result = mock_api.place_order(quantity=100)
    
    assert result['orderId'] == '12345'
    mock_api.place_order.assert_called_once_with(quantity=100)
```

---

## Available Fixtures

See `tests/conftest.py` for all fixtures.

### Database Fixtures

- `temp_db`: Temporary database file path
- `reset_singletons`: Reset singleton instances between tests

### Environment Fixtures

- `mock_env`: Mock environment variables with sensible defaults

### Sample Data Fixtures

- `sample_order_data`: Basic order data
- `sample_co_order_data`: Cover Order data
- `sample_bo_order_data`: Bracket Order data
- `sample_funds_data`: Funds/margin data

### Mock API Fixtures

- `mock_dhan_client`: Mock DhanHQ client instance

---

## Testing Resilience Features

### Retry Logic

```python
from utils.resilience import RetryStrategy

@RetryStrategy(max_attempts=3, backoff_factor=2.0)
def unstable_api_call():
    # Will retry up to 3 times with exponential backoff
    return api.get_data()
```

### Rate Limiting

```python
from utils.resilience import RateLimiter

limiter = RateLimiter(rate=10, burst=20)

@limiter
def rate_limited_call():
    # Limited to 10 calls/second, burst of 20
    return api.get_data()
```

### Circuit Breaker

```python
from utils.resilience import CircuitBreaker

breaker = CircuitBreaker(
    failure_threshold=5,
    recovery_timeout=60.0
)

@breaker
def protected_call():
    # Circuit opens after 5 failures
    # Recovers after 60 seconds
    return api.get_data()
```

---

## Continuous Integration

### GitHub Actions Example

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    strategy:
      matrix:
        python-version: [3.8, 3.9, '3.10', '3.11']
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements-dev.txt
    
    - name: Run tests
      run: |
        pytest --cov=src --cov-report=xml --cov-report=term
    
    - name: Upload coverage
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
```

---

## Troubleshooting

### ImportError: No module named 'src'

**Problem**: Python can't find src directory

**Solution**:
```bash
# Option 1: Add to PYTHONPATH
PYTHONPATH=src pytest

# Option 2: Install in editable mode
pip install -e .

# Option 3: Check pytest.ini has pythonpath = src
```

### Database Lock Errors

**Problem**: Database locked from previous test

**Solution**: Use `reset_singletons` fixture:
```python
def test_database(temp_db, reset_singletons):
    # reset_singletons ensures clean state
    db = DatabaseManager(temp_db)
```

### Slow Test Suite

**Problem**: Tests taking too long

**Solution**:
```bash
# Skip slow tests during development
pytest -m "not slow"

# Run in parallel (requires pytest-xdist)
pip install pytest-xdist
pytest -n auto
```

### Mock Not Working

**Problem**: Mock doesn't affect real code

**Solution**: Patch at point of use, not definition:
```python
# Wrong
@patch('module_defining_function')

# Right
@patch('module_using_function.function_name')
```

---

## Best Practices

1. **Fast Tests**: Keep unit tests under 0.1s each
2. **Isolated Tests**: Each test should be independent
3. **Clear Names**: Test names should describe what they test
4. **One Assert**: Focus on testing one thing per test
5. **Arrange-Act-Assert**: Structure tests clearly
6. **Mock External**: Don't make real API calls
7. **Use Fixtures**: Share common setup code
8. **Mark Tests**: Use markers to categorize tests

---

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [Pytest Fixtures](https://docs.pytest.org/en/stable/fixture.html)
- [Python Mock](https://docs.python.org/3/library/unittest.mock.html)
- [Coverage.py](https://coverage.readthedocs.io/)
- [Testing Best Practices](https://docs.python-guide.org/writing/tests/)

---

**Happy Testing!** 🧪

