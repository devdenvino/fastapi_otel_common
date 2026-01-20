# Rate Limiting

FastAPI OTEL Common provides flexible rate limiting with support for both in-memory (single instance) and Redis-backed (distributed) rate limiting.

## Overview

Rate limiting protects your API from abuse and ensures fair resource usage. Two backends are supported:

- **Memory**: Fast, simple, suitable for single-instance deployments
- **Redis**: Distributed, suitable for multi-instance/Kubernetes deployments

## Configuration

### Environment Variables

```bash
# Enable/disable rate limiting (default: false)
ENABLE_RATE_LIMIT_MIDDLEWARE=true

# Requests per minute per IP (default: 60)
RATE_LIMIT_PER_MINUTE=100

# Requests per hour per IP (default: 1000)
RATE_LIMIT_PER_HOUR=5000

# Backend: 'memory' or 'redis' (default: memory)
RATE_LIMITER_BACKEND=redis

# Redis connection URL (required for redis backend)
REDIS_URL=redis://localhost:6379
```

## Memory Backend (Default)

Best for single-instance deployments or development.

### Usage

```python
from fastapi_otel_common import create_app
import os

# Configure rate limiting
os.environ["ENABLE_RATE_LIMIT_MIDDLEWARE"] = "true"
os.environ["RATE_LIMIT_PER_MINUTE"] = "60"
os.environ["RATE_LIMIT_PER_HOUR"] = "1000"
os.environ["RATE_LIMITER_BACKEND"] = "memory"

app = create_app()
```

### Pros and Cons

✅ **Pros**:
- Zero dependencies
- Very fast (in-memory)
- Simple setup

❌ **Cons**:
- Per-instance limits (not global)
- Lost on restart
- Not suitable for distributed systems

## Redis Backend

Best for production multi-instance deployments.

### Installation

```bash
# Install with Redis support
pip install fastapi_otel_common[redis]

# Or manually
pip install redis>=5.0.0
```

### Usage

```python
from fastapi_otel_common import create_app
import os

# Configure Redis rate limiting
os.environ["ENABLE_RATE_LIMIT_MIDDLEWARE"] = "true"
os.environ["RATE_LIMITER_BACKEND"] = "redis"
os.environ["REDIS_URL"] = "redis://localhost:6379"
os.environ["RATE_LIMIT_PER_MINUTE"] = "100"
os.environ["RATE_LIMIT_PER_HOUR"] = "5000"

app = create_app()
```

### Redis Connection Options

The Redis URL supports various formats:

```bash
# Simple local
REDIS_URL=redis://localhost:6379

# With password
REDIS_URL=redis://:password@localhost:6379

# Specific database
REDIS_URL=redis://localhost:6379/0

# SSL/TLS
REDIS_URL=rediss://user:password@redis.example.com:6380/0

# Unix socket
REDIS_URL=redis+unix:///var/run/redis.sock
```

### Pros and Cons

✅ **Pros**:
- Truly distributed (works across all instances)
- Persistent across restarts
- Scales horizontally
- Supports Redis Cluster

❌ **Cons**:
- Requires Redis infrastructure
- Slightly slower (network latency)
- Additional dependency

## Response Headers

When rate limiting is active, responses include informational headers:

```http
HTTP/1.1 200 OK
X-RateLimit-Limit-Minute: 60
X-RateLimit-Limit-Hour: 1000
X-RateLimit-Remaining-Minute: 45
X-RateLimit-Remaining-Hour: 892
```

When rate limit is exceeded:

```http
HTTP/1.1 429 Too Many Requests
X-RateLimit-Limit-Minute: 60
X-RateLimit-Limit-Hour: 1000
X-RateLimit-Remaining-Minute: 0
X-RateLimit-Remaining-Hour: 0
Retry-After: 42

{
  "detail": "Rate limit exceeded. Please try again later.",
  "request_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

## Excluded Paths

The following paths are automatically excluded from rate limiting:

- `/healthz`
- `/livez`
- `/readyz`
- `/startupz`
- `/health`
- `/docs`
- `/openapi.json`

## Advanced Usage

### Per-Endpoint Rate Limits

You can use the slowapi library directly for per-endpoint limits:

```python
from fastapi_otel_common import create_app
from slowapi import Limiter
from slowapi.util import get_remote_address

app = create_app()
limiter = Limiter(key_func=get_remote_address)

@app.get("/expensive-operation")
@limiter.limit("5/minute")  # Stricter limit for this endpoint
async def expensive_operation():
    return {"status": "success"}
```

### Custom Key Functions

Rate limit by something other than IP:

```python
from fastapi import Request
from slowapi import Limiter

def get_user_id(request: Request) -> str:
    """Rate limit by authenticated user ID."""
    # Extract from JWT or session
    return request.state.user_id

limiter = Limiter(key_func=get_user_id)

@app.get("/user-specific")
@limiter.limit("100/hour")
async def user_specific_endpoint():
    return {"data": "..."}
```

### Redis Cluster Support

For Redis Cluster deployments:

```python
from redis.asyncio.cluster import RedisCluster
from fastapi_otel_common.ratelimit.redis import RedisRateLimiter

# Custom Redis cluster client
cluster = RedisCluster(
    startup_nodes=[
        {"host": "node1", "port": 7000},
        {"host": "node2", "port": 7001},
        {"host": "node3", "port": 7002},
    ]
)

limiter = RedisRateLimiter(
    redis_url="",  # Not used for custom client
    per_minute=100,
    per_hour=5000
)
limiter.client = cluster  # Override with cluster client
```

## Kubernetes Deployment

Example deployment with Redis:

```yaml
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
data:
  ENABLE_RATE_LIMIT_MIDDLEWARE: "true"
  RATE_LIMITER_BACKEND: "redis"
  REDIS_URL: "redis://redis-service:6379"
  RATE_LIMIT_PER_MINUTE: "100"
  RATE_LIMIT_PER_HOUR: "5000"

---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: fastapi-app
spec:
  replicas: 3  # Multiple instances share rate limits via Redis
  selector:
    matchLabels:
      app: fastapi-app
  template:
    metadata:
      labels:
        app: fastapi-app
    spec:
      containers:
      - name: app
        image: my-fastapi-app:latest
        envFrom:
        - configMapRef:
            name: app-config
        ports:
        - containerPort: 8000

---
apiVersion: v1
kind: Service
metadata:
  name: redis-service
spec:
  selector:
    app: redis
  ports:
  - port: 6379
    targetPort: 6379

---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: redis
spec:
  replicas: 1
  selector:
    matchLabels:
      app: redis
  template:
    metadata:
      labels:
        app: redis
    spec:
      containers:
      - name: redis
        image: redis:7-alpine
        ports:
        - containerPort: 6379
```

## Monitoring

### Metrics

Rate limit events are tracked in OpenTelemetry metrics:

```promql
# Rate limit rejections
sum(rate(http_server_request_count_total{http_status_code="429"}[5m]))

# Rate limit rejection rate
sum(rate(http_server_request_count_total{http_status_code="429"}[5m]))
/
sum(rate(http_server_request_count_total[5m]))
```

### Logging

Rate limit violations are logged:

```json
{
  "level": "warning",
  "message": "Rate limit exceeded for 192.168.1.100 on /api/data",
  "client_id": "192.168.1.100",
  "path": "/api/data",
  "timestamp": "2026-01-20T10:30:00Z"
}
```

### Redis Monitoring

Monitor Redis performance:

```bash
# Connect to Redis CLI
redis-cli

# Check rate limit keys
KEYS ratelimit:*

# Monitor operations
MONITOR

# Get stats
INFO stats
```

## Performance

### Memory Backend

- **Latency**: <0.1ms overhead per request
- **Memory**: ~100 bytes per tracked IP
- **Throughput**: 50,000+ req/s

### Redis Backend

- **Latency**: 0.5-2ms overhead per request (depends on Redis)
- **Memory**: Minimal (Redis stores data)
- **Throughput**: Limited by Redis (10,000+ req/s typical)

### Optimization Tips

1. **Use pipelining**: Redis backend uses pipelining automatically
2. **Tune export interval**: Longer intervals = less Redis traffic
3. **Scale Redis**: Use Redis Cluster for high throughput
4. **Monitor Redis latency**: Keep Redis close to app instances
5. **Consider caching**: Cache Redis lookups for frequently-checked IPs

## Troubleshooting

### Rate limiting not working

Check configuration:

```python
import os
print("Rate limiting enabled:", os.getenv("ENABLE_RATE_LIMIT_MIDDLEWARE"))
print("Backend:", os.getenv("RATE_LIMITER_BACKEND"))
print("Redis URL:", os.getenv("REDIS_URL"))
```

### Redis connection failures

The application will log errors but **fail open** (not rate limit) if Redis is unavailable:

```
WARNING: Redis rate limit check failed: ConnectionError
```

To **fail closed** (reject requests if Redis is down), modify the error handling in `RedisRateLimiter.is_rate_limited()`.

### High Redis memory usage

Rate limit keys auto-expire:
- Minute keys: 60 seconds
- Hour keys: 3600 seconds

If memory grows, check for:
- Very high cardinality (many unique IPs)
- Expired key cleanup disabled
- Keys not expiring properly

## Best Practices

1. **Start conservative**: Begin with high limits, reduce based on usage
2. **Use Redis in production**: Always use Redis backend for multi-instance deployments
3. **Monitor rejection rates**: Alert if >5% of requests are rate limited
4. **Exclude health checks**: Already done automatically
5. **Document limits**: Make rate limits clear in API documentation
6. **Consider user tiers**: Use custom key functions for tiered limits
7. **Test failure modes**: Ensure app works when Redis is down
8. **Use Redis Sentinel**: For high availability in production

## See Also

- [Configuration Guide](configuration.md)
- [Middleware Documentation](middleware.md)
- [Health Checks](health-checks.md)
- [slowapi Documentation](https://slowapi.readthedocs.io/)
