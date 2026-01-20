# Examples

This directory contains example applications demonstrating how to use `fastapi_otel_common`.

## Available Examples

### Basic Examples

- **[example_usage.py](example_usage.py)** - Basic usage showing core features
  - OpenTelemetry tracing
  - Health checks
  - Middleware setup
  - Database integration

- **[example_advanced.py](example_advanced.py)** - Advanced features and patterns
  - Custom configurations
  - Multiple middleware
  - Complex scenarios

### RBAC Examples

- **[example_rbac.py](example_rbac.py)** - Basic role-based access control
  - Simple role checking
  - Client-specific roles
  - Realm roles

- **[example_rbac_improved.py](example_rbac_improved.py)** - Enhanced RBAC patterns
  - Default client ID usage
  - Helper methods on UserBase
  - AND/OR logic basics
  - Custom authorization logic

- **[example_rbac_complex.py](example_rbac_complex.py)** - Industry-standard complex authorization
  - Complex AND/OR conditions
  - Nested role requirements
  - Real-world enterprise scenarios
  - Regulatory compliance patterns
  - 10+ production-ready patterns

## Running Examples

### Prerequisites

1. Install the package:
   ```bash
   pip install -e .
   ```

2. Copy and configure environment variables:
   ```bash
   cp env.example .env
   # Edit .env with your configuration
   ```

3. Set up OIDC configuration (for RBAC examples):
   ```bash
   OIDC_CLIENT_ID=my-client-id
   OIDC_ISSUER=https://your-auth-server/realms/your-realm
   OIDC_JWKS_URI=https://your-auth-server/realms/your-realm/protocol/openid-connect/certs
   ```

### Run an Example

```bash
# Basic usage
python examples/example_usage.py

# RBAC examples
python examples/example_rbac.py
python examples/example_rbac_improved.py
python examples/example_rbac_complex.py

# Advanced features
python examples/example_advanced.py
```

The server will start at http://localhost:8000

## Testing Examples

You can test the examples using curl or the Swagger UI at http://localhost:8000/docs

### Example: Test RBAC Endpoints

With a valid JWT token:
```bash
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" http://localhost:8000/admin/reports
```

## Learning Path

1. Start with **example_usage.py** to understand basics
2. Move to **example_rbac.py** for simple authorization
3. Explore **example_rbac_improved.py** for cleaner patterns
4. Study **example_rbac_complex.py** for enterprise scenarios
5. Review **example_advanced.py** for production features

## Documentation

See [docs/](../docs/) for comprehensive documentation:
- [Installation](../docs/installation.md)
- [Configuration](../docs/configuration.md)
- [RBAC Documentation](../docs/role-based-access-control.md)
- [Examples Guide](../docs/examples.md)

## Contributing

When adding new examples:
1. Follow the existing naming convention: `example_*.py`
2. Include clear docstrings and comments
3. Add an entry to this README
4. Test that the example runs successfully
5. Keep examples focused on specific features
