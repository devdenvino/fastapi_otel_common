"""Core configuration and middleware exports.

To avoid circular imports, import middleware directly from .middleware module:
    from fastapi_otel_common.core.middleware import RequestIDMiddleware
"""

__all__: list[str] = []
