---
layout: default
title: Logging
nav_order: 3.5
---

# Rich Logging with Loguru
{: .no_toc }

## Table of contents
{: .no_toc .text-delta }

1. TOC
{:toc}

---

## Overview

FastAPI OTEL Common integrates [Loguru](https://github.com/Delgan/loguru) for structured logging with automatic OTLP export.

## Key Features

- ✅ **Colorized Console**: Readable and informative logs in your terminal.
- ✅ **Automatic OTLP Export**: Logs are forwarded to your OpenTelemetry collector via gRPC.
- ✅ **Correlation**: Automatically logs **Trace ID** and **Span ID** for every log entry, both in console and OTLP.
- ✅ **Library Interception**: Captures logs from `uvicorn`, `fastapi`, and `logging` and routes them through Loguru.
- ✅ **Rich Exceptions**: detailed stack traces with variable values.

## Configuration

Configure the logging behavior using environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `LOG_LEVEL` | INFO | Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL) |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | http://localhost:4317 | Endpoint for sending logs to OTEL |
| `SERVICE_NAME` | my-service | Name of the service for log identification |
| `SERVICE_VERSION` | 1.0.0 | Version of the service |

## Usage

### Basic Usage

Use the standard `get_logger` helper to get a logger instance:

```python
from fastapi_otel_common.logging import get_logger

logger = get_logger(__name__)

logger.info("Application started")
logger.debug("Debug information", extra={"user_id": 123})
```

### Async Logging Decorator

Automatically log async function calls, arguments, and results:

```python
from fastapi_otel_common.logging import async_log, get_logger

logger = get_logger(__name__)

@async_log(logger, "info", "Processing order {order_id}, result: {result}")
async def process_order(order_id: str):
    # business logic
    return "success"
```

### Exception Logging

Loguru makes exception logging trivial:

```python
try:
    1 / 0
except Exception:
    logger.exception("An error occurred during calculation")
```

## Advanced Features

### Intercepting Standard Logging

The library automatically intercepts logs from standard Python `logging` (including `uvicorn`). If you have other libraries using the standard library, their logs will automatically flow into Loguru.

### Backward Compatibility

The logger returned by `get_logger` is a wrapper that supports the `extra` keyword argument for compatibility with existing codebases transitioning to Loguru:

```python
# This works and correctly binds fields in Loguru
logger.info("Message with extra", extra={"request_id": "abc-123"})
```

## OpenTelemetry Integration

When `setup_logger()` is called (automatically within `create_app()`), it:
1. Configures a `LoggerProvider` with your `SERVICE_NAME`.
2. Attaches a `BatchLogRecordProcessor` for efficient background export.
3. **Injects Trace Context**: Uses a Loguru patcher to automatically extract `trace_id` and `span_id` from the current OpenTelemetry context and include them in every log message.
   - In the console, they appear as `trace_id=... span_id=...`.
   - In OTLP/structured logs, they are included as standard fields for correlation.
4. Adds an OTLP Sink to Loguru to ensure all logs reach your observability backend (e.g., SigNoz, Jaeger, Grafana Loki).

## Next Steps

- [OpenTelemetry Metrics](metrics)
- [Middleware Documentation](middleware)
- [Configuration Guide](configuration)
