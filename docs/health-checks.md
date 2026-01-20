# Health Checks

FastAPI OTEL Common provides Kubernetes-compatible health check endpoints for monitoring application status and dependencies.

## Overview

The library includes four health check endpoints:

- **/healthz** (liveness): Is the application running?
- **/livez** (liveness alias): Same as /healthz
- **/readyz** (readiness): Can the application accept traffic?
- **/startupz** (startup): Has the application finished starting up?

## Endpoints

### Liveness Probe: `/healthz` or `/livez`

Indicates whether the application is alive and running. This should only fail if the application is completely broken and needs to be restarted.

**Response (200 OK)**:
```json
{
  "status": "ok",
  "timestamp": "2026-01-20T10:30:00.000000"
}
```

**Use Case**: Kubernetes liveness probe to restart crashed pods

**Example**:
```yaml
livenessProbe:
  httpGet:
    path: /healthz
    port: 8000
  initialDelaySeconds: 30
  periodSeconds: 10
```

### Readiness Probe: `/readyz`

Indicates whether the application is ready to accept traffic. Checks all critical dependencies:

- **Database connectivity**: Can the app connect to PostgreSQL?
- **OIDC provider**: Is the authentication server reachable?

**Response (200 OK - All healthy)**:
```json
{
  "status": "ready",
  "timestamp": "2026-01-20T10:30:00.000000",
  "checks": {
    "database": {
      "status": "healthy",
      "host": "localhost",
      "port": "5432",
      "database": "mydb"
    },
    "oidc_provider": {
      "status": "healthy",
      "url": "https://auth.example.com/.well-known/openid-configuration",
      "response_time_ms": 45
    }
  }
}
```

**Response (503 Service Unavailable - Degraded)**:
```json
{
  "status": "not_ready",
  "timestamp": "2026-01-20T10:30:00.000000",
  "checks": {
    "database": {
      "status": "unhealthy",
      "error": "connection timeout",
      "host": "localhost",
      "port": "5432",
      "database": "mydb"
    },
    "oidc_provider": {
      "status": "healthy",
      "url": "https://auth.example.com/.well-known/openid-configuration",
      "response_time_ms": 42
    }
  }
}
```

**Use Case**: Kubernetes readiness probe to control traffic routing

**Example**:
```yaml
readinessProbe:
  httpGet:
    path: /readyz
    port: 8000
  initialDelaySeconds: 10
  periodSeconds: 5
  failureThreshold: 3
```

### Startup Probe: `/startupz`

Indicates whether the application has completed its startup sequence. Used by Kubernetes to know when to switch from startup to liveness probes.

**Response (503 Service Unavailable - Starting)**:
```json
{
  "status": "starting",
  "timestamp": "2026-01-20T10:30:00.000000"
}
```

**Response (200 OK - Started)**:
```json
{
  "status": "started",
  "timestamp": "2026-01-20T10:30:05.000000",
  "startup_time": "2026-01-20T10:30:05.123456"
}
```

**Use Case**: Kubernetes startup probe for slow-starting applications

**Example**:
```yaml
startupProbe:
  httpGet:
    path: /startupz
    port: 8000
  initialDelaySeconds: 0
  periodSeconds: 5
  failureThreshold: 30  # Allow 150 seconds for startup
```

## Usage

Health checks are automatically included when you create an app:

```python
from fastapi_otel_common import create_app

app = create_app()
# Health endpoints are now available at:
# - /healthz
# - /livez
# - /readyz
# - /startupz
```

## Kubernetes Configuration

Complete example for a FastAPI deployment:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: fastapi-app
spec:
  replicas: 3
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
        ports:
        - containerPort: 8000
        
        # Startup probe: Allow 150 seconds for startup
        startupProbe:
          httpGet:
            path: /startupz
            port: 8000
          initialDelaySeconds: 0
          periodSeconds: 5
          failureThreshold: 30
        
        # Liveness probe: Restart if unhealthy for 30 seconds
        livenessProbe:
          httpGet:
            path: /healthz
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
          failureThreshold: 3
        
        # Readiness probe: Remove from service if not ready
        readinessProbe:
          httpGet:
            path: /readyz
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 5
          timeoutSeconds: 3
          successThreshold: 1
          failureThreshold: 3
        
        env:
        - name: DB_HOST
          value: postgres-service
        - name: OIDC_DISCOVERY_URL
          value: https://auth.example.com/.well-known/openid-configuration
```

## Customizing Health Checks

### Adding Custom Checks

You can add custom health checks by extending the health router:

```python
from fastapi_otel_common import create_app
from fastapi_otel_common.routes import health

@health.router.get("/custom-check")
async def custom_health_check():
    """Custom health check for your dependencies."""
    # Check your custom service
    try:
        # Your check logic here
        return {"status": "healthy", "service": "my-service"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}

app = create_app()
```

### Disabling Dependency Checks

If you want a simpler readiness check without dependency validation:

```python
from fastapi import APIRouter
from fastapi_otel_common import create_app

# Create app
app = create_app()

# Override the readyz endpoint
@app.get("/readyz")
async def simple_readiness():
    return {"status": "ready"}
```

## Monitoring and Alerting

### Prometheus Example

Monitor health check success rates:

```yaml
- alert: HighHealthCheckFailureRate
  expr: |
    (
      sum(rate(http_server_request_count_total{http_route="/readyz", http_status_code!="200"}[5m]))
      /
      sum(rate(http_server_request_count_total{http_route="/readyz"}[5m]))
    ) > 0.1
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "High health check failure rate"
    description: "Readiness probe failing more than 10% of the time"
```

### Load Balancer Configuration

#### AWS ALB Target Group

```json
{
  "HealthCheckPath": "/healthz",
  "HealthCheckIntervalSeconds": 30,
  "HealthCheckTimeoutSeconds": 5,
  "HealthyThresholdCount": 2,
  "UnhealthyThresholdCount": 3
}
```

#### NGINX

```nginx
upstream backend {
    server app1:8000;
    server app2:8000;
    server app3:8000;
}

server {
    location / {
        proxy_pass http://backend;
        
        # Use readyz for health checks
        health_check uri=/readyz interval=10s fails=3 passes=2;
    }
}
```

## Health Check Flow

```
┌─────────────────┐
│ Pod Starting    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Startup Probe   │◄─── Checks /startupz every 5s
│ (0-150s)        │      Returns 503 until ready
└────────┬────────┘
         │ 200 OK
         ▼
┌─────────────────────────────┐
│ Liveness & Readiness Probes │
│ Running Simultaneously      │
└─────────────────────────────┘
         │
         ├─► Liveness (/healthz) ────► Always returns 200
         │   Every 10s                   Unless app crashed
         │
         └─► Readiness (/readyz) ───► Returns 200 if deps healthy
             Every 5s                   Returns 503 if deps down
```

## Best Practices

1. **Separate Concerns**:
   - Liveness: Only checks if the app is alive
   - Readiness: Checks if the app can serve traffic
   - Startup: Gives slow apps time to initialize

2. **Fast Checks**: Keep health checks under 1 second
   - Use timeouts on external checks
   - Run checks in parallel (we do this automatically)

3. **Fail Fast**: Don't retry failed checks within the endpoint

4. **No Side Effects**: Health checks should be read-only

5. **Appropriate Thresholds**:
   - Liveness: High threshold (3-5 failures)
   - Readiness: Low threshold (2-3 failures)
   - Startup: Very high threshold (30+ for slow apps)

6. **Monitor Health Checks**: Track failure rates and response times

## Troubleshooting

### Readiness probe always fails

Check that your database and OIDC provider are accessible:

```bash
# Test database
psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c "SELECT 1"

# Test OIDC
curl -v $OIDC_DISCOVERY_URL
```

### Startup probe timeout

Increase `failureThreshold` in your Kubernetes config:

```yaml
startupProbe:
  failureThreshold: 60  # Allow 300 seconds (60 * 5s)
```

### Health checks causing high load

Reduce check frequency:

```yaml
readinessProbe:
  periodSeconds: 10  # Increase from 5 to 10
```

## See Also

- [Configuration Guide](configuration.md)
- [Middleware Documentation](middleware.md)
- [Metrics Documentation](metrics.md)
