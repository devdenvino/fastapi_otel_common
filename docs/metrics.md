# OpenTelemetry Metrics

FastAPI OTEL Common now includes comprehensive OpenTelemetry Metrics support for monitoring HTTP request performance and application health.

## Overview

The metrics module automatically collects and exports HTTP request metrics including:

- **Request Count**: Total number of HTTP requests by method, path, and status code
- **Request Duration**: HTTP request latency in milliseconds (histogram)
- **Request Size**: HTTP request body size in bytes (histogram)
- **Response Size**: HTTP response body size in bytes (histogram)
- **Active Requests**: Current number of in-flight HTTP requests (up-down counter)

## Configuration

Metrics are enabled by default but can be controlled via environment variables:

```bash
# Enable/disable metrics collection (default: true)
ENABLE_OTEL_METRICS=true

# Metrics export interval in milliseconds (default: 60000 = 1 minute)
OTEL_METRIC_EXPORT_INTERVAL=60000

# Metrics export timeout in milliseconds (default: 5000 = 5 seconds)
# This prevents shutdown hangs when OTLP endpoint is unavailable or slow
OTEL_METRIC_EXPORT_TIMEOUT=5000

# OTLP endpoint for metrics export (same as traces)
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317

# Service identification
SERVICE_NAME=my-api
SERVICE_VERSION=1.0.0
```

## Usage

Metrics are automatically collected when you create a FastAPI app with `create_app()`:

```python
from fastapi_otel_common import create_app

app = create_app()
```

No additional code is required - the `MetricsMiddleware` is automatically added to your application.

## Metric Details

### http.server.request.count

**Type**: Counter  
**Unit**: 1  
**Labels**:
- `http.method`: HTTP method (GET, POST, etc.)
- `http.route`: Request path/route
- `http.status_code`: HTTP status code (200, 404, 500, etc.)

**Description**: Total number of HTTP requests received by the server.

### http.server.request.duration

**Type**: Histogram  
**Unit**: ms (milliseconds)  
**Labels**:
- `http.method`: HTTP method
- `http.route`: Request path
- `http.status_code`: HTTP status code

**Description**: HTTP request processing time in milliseconds, from when the request is received until the response is sent.

### http.server.request.size

**Type**: Histogram  
**Unit**: By (bytes)  
**Labels**:
- `http.method`: HTTP method
- `http.route`: Request path
- `http.status_code`: HTTP status code

**Description**: Size of HTTP request bodies in bytes (only recorded when Content-Length header is present).

### http.server.response.size

**Type**: Histogram  
**Unit**: By (bytes)  
**Labels**:
- `http.method`: HTTP method
- `http.route`: Request path
- `http.status_code`: HTTP status code

**Description**: Size of HTTP response bodies in bytes (only recorded when Content-Length header is present).

### http.server.active_requests

**Type**: UpDownCounter  
**Unit**: 1  
**Labels**:
- `http.method`: HTTP method
- `http.route`: Request path

**Description**: Number of currently active HTTP requests being processed.

## Visualization

Metrics are exported via OTLP and can be visualized using:

### Grafana + Prometheus

1. Configure Prometheus to scrape your OTLP collector
2. Import Grafana dashboards for HTTP metrics
3. Create alerts based on request rates, latencies, or error rates

Example Prometheus queries:

```promql
# Request rate by endpoint
rate(http_server_request_count_total[5m])

# 95th percentile latency
histogram_quantile(0.95, rate(http_server_request_duration_bucket[5m]))

# Error rate
sum(rate(http_server_request_count_total{http_status_code=~"5.."}[5m]))
```

### OpenTelemetry Collector

Configure the OTLP collector to export metrics to your backend:

```yaml
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317

processors:
  batch:

exporters:
  prometheus:
    endpoint: "0.0.0.0:8889"
  otlp:
    endpoint: "your-backend:4317"

service:
  pipelines:
    metrics:
      receivers: [otlp]
      processors: [batch]
      exporters: [prometheus, otlp]
```

## Disabling Metrics

To disable metrics collection:

```bash
export ENABLE_OTEL_METRICS=false
```

Or in code:

```python
import os
os.environ["ENABLE_OTEL_METRICS"] = "false"

from fastapi_otel_common import create_app
app = create_app()
```

## Custom Metrics

You can also create custom metrics in your application:

```python
from fastapi_otel_common.telemetry.tracing import meter

# Create a counter
my_counter = meter.create_counter(
    name="my.custom.counter",
    description="My custom counter",
    unit="1"
)

# Increment it
my_counter.add(1, {"label": "value"})

# Create a histogram
my_histogram = meter.create_histogram(
    name="my.custom.duration",
    description="Duration of custom operation",
    unit="ms"
)

# Record values
my_histogram.record(123.45, {"operation": "process_data"})
```

## Troubleshooting

### Metrics not appearing

1. Check that `ENABLE_OTEL_METRICS=true`
2. Verify OTLP endpoint is accessible: `telnet localhost 4317`
3. Check application logs for metric initialization errors
4. Ensure the OTLP collector is configured to receive metrics

### Application hangs on shutdown

If your application hangs during shutdown with errors like "Failed to export metrics, error code: StatusCode.UNIMPLEMENTED":

1. **Set a timeout**: Configure `OTEL_METRIC_EXPORT_TIMEOUT=5000` (5 seconds) to prevent indefinite hangs
2. **Check OTLP support**: Ensure your OTLP endpoint supports metrics (not just traces)
3. **Verify collector config**: Some OTLP collectors need explicit metrics configuration
4. **Review logs**: Check for "Shutting down OpenTelemetry metrics provider" messages

The library now includes proper shutdown handling that:
- Flushes pending metrics before shutdown
- Times out exports that take too long
- Logs warnings instead of hanging on failures

### High cardinality warnings

If you see warnings about high cardinality metrics:

- Avoid using dynamic values (IDs, timestamps) in labels
- Use `http.route` instead of full URL paths with parameters
- Limit the number of unique label combinations

### Performance impact

Metrics collection has minimal overhead:

- ~0.1-0.5ms per request for metric recording
- Batched export reduces network overhead
- Consider increasing `OTEL_METRIC_EXPORT_INTERVAL` for high-traffic applications

## Best Practices

1. **Use appropriate metric types**: Counters for totals, histograms for distributions
2. **Keep label cardinality low**: Limit unique label combinations
3. **Export regularly**: Balance between freshness and overhead
4. **Monitor the monitors**: Track metric export failures
5. **Alert on SLOs**: Define and alert on Service Level Objectives

## See Also

- [OpenTelemetry Metrics Specification](https://opentelemetry.io/docs/specs/otel/metrics/)
- [Configuration Guide](configuration.md)
- [Health Checks](health-checks.md)
