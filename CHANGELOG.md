# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.3] - 2026-02-04

### Added
- **AI Agent Skills Support**: Added built-in skills for major AI agents.
  - **Google Antigravity**: Added `.agent/skills/fastapi-otel-common/SKILL.md` for agentic workflows.
  - **GitHub Copilot**: Added `.github/copilot-instructions.md` for tailored code completion.
  - **Skills CLI Integration**: Support for `npx skills add devdenvino/fastapi_otel_common`.
- **Logging with Loguru**: Integrated [Loguru](https://github.com/Delgan/loguru) for structured logging.
  - Colorized console output with automatic Trace/Span ID correlation.
  - Automatic OTLP export via OpenTelemetry.
  - Stack trace interception for `uvicorn`, `fastapi`, and standard `logging`.
  - Rich exception formatting and `async_log` decorator.
- **RBAC**: Integrated role-based access control.
  - `RequireRoles` (OR logic), `RequireAllRoles` (AND logic), and `RequireRolesComplex` for complex boolean logic.
  - Intelligent role extraction from Keycloak-format JWTs.
- **Dual-Token Swagger Support**: Swagger UI now supports both standard OAuth2 Auth Flow and manual ID Token (Bearer) entry.

### Changed
- **User Model**: Updated `UserBase` with `roles` dictionary and helper methods (`has_role`, `has_any_role`, `has_all_roles`).
- **Refactoring & Optimization**: Major code structure refactoring for improved readability and optimized middleware stack performance.

### Documentation
- New [AI Agent Skills Guide](docs/skills.md).
- New [Logging Guide](docs/logging.md) for Loguru features.
- New [RBAC Guide](docs/role-based-access-control.md) with advanced patterns.

## [0.1.1] - 2026-01-25

### Added
- **Shutdown Optimization**: Drastically improved application shutdown speed.
  - Added `OTEL_SHUTDOWN_TIMEOUT` (default: 3000ms).
  - Graceful handling of unreachable OTLP endpoints.
- **Improved Logging**: Enhanced startup and shutdown logs for better troubleshooting.

### Fixed
- Fixed indefinite hang on shutdown when OTLP collector was unreachable.
- **Multi-database support**: Added adapter pattern for scalable database support
  - SQLite support for development (zero configuration, no PostgreSQL needed)
  - MySQL/MariaDB support out of the box
  - Easy to add custom database types (Oracle, MSSQL, etc.)
  - `DatabaseAdapter` abstract base class for creating new adapters
  - `DatabaseAdapterFactory` for registering and creating adapters
  - New configuration: `DB_TYPE` (postgresql/sqlite/mysql)
  - New configuration: `SQLITE_DB_PATH` for SQLite database location
  - Included adapters: `PostgreSQLAdapter`, `SQLiteAdapter`, `MySQLAdapter`
  - Example for adding custom databases ([examples/example_custom_database.py](examples/example_custom_database.py))

### Changed
- **Database architecture**: Refactored database module to use adapter pattern instead of conditional logic
  - Cleaner code following SOLID principles (Open/Closed, Single Responsibility)
  - Database-specific logic is now isolated in adapter classes
  - Easier to maintain and extend with new database types
  - Zero performance impact (adapter created once at startup)
- **Dependencies**: Added `aiosqlite>=0.20.0` for SQLite async support
- **Optional dependencies**: Added `mysql` extra for MySQL support (`pip install fastapi_otel_common[mysql]`)

### Documentation
- Added [MULTI_DATABASE_ARCHITECTURE.md](docs/MULTI_DATABASE_ARCHITECTURE.md) explaining the adapter pattern
- Added [QUICKSTART_SQLITE.md](docs/QUICKSTART_SQLITE.md) for quick development setup
- Updated [database.md](docs/database.md) with multi-database configuration and examples
- Updated README.md with SQLite quick start example

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
