---
layout: default
title: Contributing
nav_order: 8
---

# Contributing to fastapi_otel_common
{: .no_toc }

## Table of contents
{: .no_toc .text-delta }

1. TOC
{:toc}

---

## Overview

Thank you for your interest in contributing! This document provides guidelines for contributing to this project.

## Development Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/devdenvino/fastapi_otel_common.git
   cd fastapi_otel_common
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install development dependencies**
   ```bash
   pip install -e ".[dev]"
   ```

## Code Style

This project follows Python best practices and uses automated tools for code quality:

- **Black** for code formatting (line length: 100)
- **Ruff** for linting and import sorting
- **MyPy** for type checking

Run formatting and linting:
```bash
# Format code
black .

# Lint code
ruff check .

# Type check
mypy fastapi_otel_common
```

## Testing

All code changes should include tests. We use pytest for testing.

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=fastapi_otel_common --cov-report=term-missing

# Run specific test file
pytest test_middleware.py -v
```

## Coding Guidelines

1. **Type Hints**: All functions must have proper type hints
   ```python
   def my_function(param: str) -> dict:
       return {"result": param}
   ```

2. **Docstrings**: Use Google-style docstrings
   ```python
   def my_function(param: str) -> dict:
       """Short description.
       
       Args:
           param: Description of parameter
           
       Returns:
           dict: Description of return value
       """
       return {"result": param}
   ```

3. **Imports**: Keep imports organized (standard lib, third-party, local)
   ```python
   import os
   from typing import Optional
   
   from fastapi import FastAPI
   from pydantic import BaseModel
   
   from .config import APP_TITLE
   ```

4. **Error Handling**: Use proper exception handling with logging
   ```python
   try:
       result = risky_operation()
   except SpecificError as e:
       logger.error(f"Operation failed: {e}")
       raise
   ```

## Commit Messages

Follow conventional commits format:

- `feat: add new middleware`
- `fix: resolve rate limiting issue`
- `docs: update README`
- `test: add tests for middleware`
- `refactor: improve error handling`
- `chore: update dependencies`

## Pull Request Process

1. Create a feature branch: `git checkout -b feature/my-feature`
2. Make your changes with tests
3. Ensure all tests pass and code is formatted
4. Update documentation if needed
5. Push and create a pull request
6. Wait for review and address feedback

## Project Structure

```
fastapi_otel_common/
├── core/           # Core configuration and middleware
├── database/       # Database session management
├── logging/        # Logging configuration
├── routes/         # Common routes (health checks)
├── security/       # Authentication and authorization
└── telemetry/      # OpenTelemetry tracing
```

## Questions?

Feel free to open an issue for questions or discussions.
