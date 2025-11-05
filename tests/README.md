# CNPERP Testing Framework

This document outlines the testing strategy for the CNPERP application.

## Test Structure

The testing framework is organized into three main categories:

1. **Unit Tests** (`tests/unit/`): Test individual components in isolation
2. **API Tests** (`tests/api/`): Test API endpoints and responses
3. **Integration Tests** (`tests/integration/`): Test workflows across multiple components

## Running Tests

### Backend Tests

Run all backend tests:
```
pytest
```

Run specific test categories:
```
pytest tests/unit/
pytest tests/api/
pytest tests/integration/
```

Run with coverage:
```
pytest --cov=app
```

### Frontend Tests

Run frontend tests:
```
cd static
npm test
```

## Adding New Tests

- Follow the naming convention: `test_*.py` for backend tests and `*.test.js` for frontend tests
- Use appropriate markers (`@pytest.mark.unit`, `@pytest.mark.api`, `@pytest.mark.integration`)
- Utilize fixtures from `conftest.py` for database and authentication setup

## CI/CD Integration

Tests automatically run on GitHub Actions for:
- Pull requests to main/master/develop branches
- Direct pushes to main/master/develop branches

See `.github/workflows/test.yml` for configuration details.