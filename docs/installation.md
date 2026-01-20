---
layout: default
title: Installation
nav_order: 2
---

# Installation Guide
{: .no_toc }

## Table of contents
{: .no_toc .text-delta }

1. TOC
{:toc}

---

## Requirements

- Python 3.12 or higher
- pip or uv package manager

## Basic Installation

### Using pip

```bash
pip install fastapi_otel_common
```

### Using uv (recommended)

```bash
uv pip install fastapi_otel_common
```

## Development Installation

For development with testing and linting tools:

```bash
# Clone the repository
git clone https://github.com/devdenvino/fastapi_otel_common.git
cd fastapi_otel_common

# Install with development dependencies
pip install -e ".[dev]"
```

### Development Dependencies Include

- pytest - Testing framework
- pytest-asyncio - Async test support
- pytest-cov - Coverage reporting
- mypy - Static type checking
- ruff - Fast Python linter
- black - Code formatter

## Verifying Installation

```python
import fastapi_otel_common

print(fastapi_otel_common.__version__)
# Output: 0.0.2
```

## Docker Installation

If using Docker, add to your `Dockerfile`:

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Or install directly
RUN pip install fastapi_otel_common

COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## Next Steps

- [Configuration Guide](configuration) - Configure your application
- [Quick Start](index#quick-start) - Build your first app
- [Examples](examples) - See working examples
