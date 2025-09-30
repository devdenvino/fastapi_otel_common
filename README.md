# fastapi_otel_common

## Overview

`fastapi_otel_common` is a Python library designed to provide common utilities and components for FastAPI applications. It includes features such as configuration management, database integration, logging, routing, security, and telemetry.

## Features

- **Core Configuration**: Centralized configuration management for FastAPI applications.
- **Database Integration**: Utilities for database connections and migrations.
- **Logging**: Structured logging setup for better observability.
- **Routing**: Predefined routes for health checks and other common endpoints.
- **Security**: Authentication and authorization utilities.
- **Telemetry**: OpenTelemetry integration for distributed tracing.

## Installation

To install the package, use pip:

```bash
pip install fastapi_otel_common
```

## Usage

### Example

Here is an example of how to use `fastapi_otel_common` in your FastAPI application:

```python
from fastapi import FastAPI
from fastapi_otel_common.core.config import Config
from fastapi_otel_common.logging.logger import setup_logging
from fastapi_otel_common.telemetry.tracing import setup_tracing

app = FastAPI()

# Setup configuration
config = Config()

# Setup logging
setup_logging(config)

# Setup telemetry
setup_tracing(app, config)

@app.get("/health")
def health_check():
    return {"status": "healthy"}
```

## Project Structure

- `core/`: Contains configuration and models.
- `database/`: Database utilities and migration scripts.
- `logging/`: Logging setup and utilities.
- `routes/`: Predefined routes for the application.
- `security/`: Authentication and authorization utilities.
- `telemetry/`: OpenTelemetry integration for tracing.

## Contributing

Contributions are welcome! Please fork the repository and submit a pull request.

## License

This project is licensed under the MIT License. See the LICENSE file for details.

## Contact

For questions or support, please contact the maintainers.