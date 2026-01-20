# Tests

This directory contains the test suite for `fastapi_otel_common`.

## Available Tests

- **[test_middleware.py](test_middleware.py)** - Middleware functionality tests
  - Request ID middleware
  - Security headers middleware
  - Logging middleware
  - Rate limiting middleware

- **[test_rbac.py](test_rbac.py)** - Role-based access control tests
  - RequireRoles dependency
  - RequireAllRoles dependency
  - RequireRolesComplex with AND/OR logic
  - Role condition classes
  - Client-specific role checking
  - Error scenarios

- **[test_shutdown.py](test_shutdown.py)** - Graceful shutdown tests
  - Clean shutdown behavior
  - Resource cleanup

- **[test_shutdown_no_otlp.py](test_shutdown_no_otlp.py)** - Shutdown without OTLP
  - Shutdown when OTLP is disabled

- **[test_shutdown_with_traffic.py](test_shutdown_with_traffic.py)** - Shutdown under load
  - Shutdown with active requests
  - Request handling during shutdown

## Running Tests

### Run All Tests

```bash
pytest tests/
```

### Run Specific Test File

```bash
pytest tests/test_rbac.py
```

### Run with Coverage

```bash
pytest tests/ --cov=fastapi_otel_common --cov-report=html
```

### Run with Verbose Output

```bash
pytest tests/ -v
```

### Run Specific Test

```bash
pytest tests/test_rbac.py::test_admin_access -v
```

## Test Requirements

Install test dependencies:
```bash
pip install -e ".[test]"
```

Or manually:
```bash
pip install pytest pytest-cov pytest-asyncio httpx
```

## Test Structure

Tests follow pytest conventions:
- Test files start with `test_`
- Test functions start with `test_`
- Use fixtures for common setup
- Mock external dependencies (OIDC, databases, etc.)

## Continuous Integration

These tests run automatically on:
- Pull requests
- Commits to main branch
- Pre-release checks

See `.github/workflows/` for CI configuration.

## Writing Tests

When adding new tests:

1. **Follow naming conventions**:
   ```python
   def test_feature_behavior():
       """Test that feature does X when Y."""
       pass
   ```

2. **Use fixtures** for common setup:
   ```python
   @pytest.fixture
   def client():
       return TestClient(app)
   ```

3. **Test edge cases**:
   - Success scenarios
   - Error scenarios
   - Boundary conditions
   - Invalid inputs

4. **Mock external dependencies**:
   ```python
   @pytest.fixture
   def mock_oidc_token():
       return "mock-jwt-token"
   ```

5. **Keep tests isolated** - each test should be independent

6. **Add docstrings** explaining what is being tested

## Test Coverage

Maintain high test coverage for:
- ✅ Core functionality
- ✅ Security features (RBAC)
- ✅ Middleware
- ✅ Error handling
- ✅ Edge cases

Run coverage report:
```bash
pytest tests/ --cov=fastapi_otel_common --cov-report=term-missing
```

## Debugging Tests

Run with debugging output:
```bash
pytest tests/ -vv -s
```

Run specific test with debugger:
```bash
pytest tests/test_rbac.py::test_function_name --pdb
```

## Contributing

When contributing tests:
1. Ensure all tests pass before submitting PR
2. Add tests for new features
3. Maintain or improve code coverage
4. Follow existing test patterns
5. Update this README if adding new test categories
