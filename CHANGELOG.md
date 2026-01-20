# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed
- **Shutdown hang**: Fixed application hanging on shutdown when metrics export fails
  - Added proper OpenTelemetry provider shutdown in lifespan handler
  - Added `OTEL_METRIC_EXPORT_TIMEOUT` configuration (default: 5000ms)
  - Added timeout to metrics and trace exporters to prevent indefinite hangs
  - Added graceful error handling during shutdown to log warnings instead of blocking

### Changed
- **Telemetry shutdown**: Both tracer and meter providers are now properly shut down during application shutdown
- **Documentation**: Updated metrics documentation with shutdown troubleshooting section

## [0.1.0] - 2026-01-20

### Added

#### OpenTelemetry Metrics
- **Metrics support**: Added comprehensive OpenTelemetry Metrics with OTLP export
- **MetricsMiddleware**: Automatically collects HTTP request metrics
- **Standard metrics**: Request count, duration, size, and active requests histograms
- **Configuration**: `ENABLE_OTEL_METRICS` and `OTEL_METRIC_EXPORT_INTERVAL` environment variables
- **Documentation**: Complete metrics documentation with Prometheus/Grafana examples

#### Advanced Health Checks
- **Kubernetes probes**: Added `/healthz`, `/livez`, `/readyz`, and `/startupz` endpoints
- **Dependency checks**: Readiness probe validates database and OIDC provider connectivity
- **Startup tracking**: Startup probe indicates when application initialization is complete
- **Parallel checks**: Health checks run concurrently for fast response times
- **Documentation**: Comprehensive health check documentation with Kubernetes examples

#### Distributed Rate Limiting
- **Redis backend**: Added Redis-based rate limiting for multi-instance deployments
- **RedisRateLimiter**: Full async Redis rate limiter with automatic key expiration
- **RedisRateLimitMiddleware**: Drop-in replacement for memory-based rate limiting
- **Configuration**: `RATE_LIMITER_BACKEND` and `REDIS_URL` environment variables
- **Optional dependency**: Redis support via `pip install fastapi_otel_common[redis]`
- **Documentation**: Complete rate limiting guide with Redis setup and Kubernetes examples

#### Lifecycle Management
- **Lifespan context**: Added proper application startup/shutdown lifecycle
- **Resource cleanup**: Automatic cleanup of Redis connections and other resources
- **Startup initialization**: Marks startup complete for health checks
- **Graceful shutdown**: Clean resource disposal on application shutdown

#### Documentation
- **New docs**: Added `metrics.md`, `health-checks.md`, and `rate-limiting.md`
- **Updated README**: Refreshed feature list and quick start guide
- **Configuration examples**: Added comprehensive environment variable examples
- **Kubernetes examples**: Added deployment manifests for all features

### Changed
- **Middleware order**: Reordered middleware stack to optimize metrics collection
- **app.py**: Refactored to support lifespan context and conditional Redis initialization
- **config.py**: Added new configuration options for metrics and Redis
- **env.example**: Updated with all new configuration options

### Fixed
- **Import order**: Improved module organization in app.py
- **Type hints**: Enhanced type safety with Optional types for Redis

### Improved
- **Error handling**: Redis rate limiter fails open if Redis is unavailable
- **Performance**: Metrics middleware uses efficient metric recording
- **Health checks**: Run dependency checks in parallel for faster responses

## [0.0.2] - Previous Release

### Features
- OpenTelemetry tracing integration
- OIDC authentication support
- Security headers middleware
- Request ID tracking
- Logging middleware
- Database management with SQLAlchemy
- In-memory rate limiting

---

## Migration Guide: 0.0.2 → 0.1.0

### Breaking Changes
None! This is a backward-compatible release.

### New Optional Features

#### Enable Metrics (Recommended)
```bash
export ENABLE_OTEL_METRICS=true
export OTEL_METRIC_EXPORT_INTERVAL=60000
```

#### Use Redis Rate Limiting (Multi-Instance Deployments)
```bash
# Install Redis support
pip install fastapi_otel_common[redis]

# Configure
export ENABLE_RATE_LIMIT_MIDDLEWARE=true
export RATE_LIMITER_BACKEND=redis
export REDIS_URL=redis://localhost:6379
```

#### Health Checks
New endpoints are automatically available:
- `/healthz` - Liveness probe
- `/readyz` - Readiness probe (checks dependencies)
- `/startupz` - Startup probe

Update your Kubernetes manifests to use these probes.

### Deprecations
- `/health` endpoint is deprecated, use `/healthz` instead (both work for now)

### Recommendations
1. Enable metrics to gain visibility into request performance
2. Switch to Redis rate limiter if running multiple instances
3. Update health check endpoints to Kubernetes-standard paths
4. Review new documentation for best practices
