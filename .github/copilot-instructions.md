# GitHub Copilot Instructions for FastAPI OTEL Common

When working with this repository or using the `fastapi-otel-common` library, follow these guidelines:

## Framework & Patterns
- Use **FastAPI** for all API development.
- Use **Pydantic v2** for data validation.
- All database operations must be **Asynchronous** using SQLAlchemy.

## Observability
- **NEVER** use standard `logging`. Always import and use `loguru`'s `logger`.
- Prefer `create_app` from `fastapi_otel_common` instead of manually initializing `FastAPI()`.
- Ensure all spans are properly closed using context managers.

## Security
- Use the `get_current_user` dependency for authentication.
- For authorization, use `RequireRoles` or `RequireAllRoles` from `fastapi_otel_common.security`.
- Always prefer environment variables for secrets, following the pattern in `env.example`.

## Code Style
- Follow **PEP 8** standards.
- Use type hints for all function arguments and return types.
- Format code using **Black** (line length 100).

## Testing
- Use **pytest** and **pytest-asyncio**.
- Ensure health check endpoints are tested.
- Mock external OIDC/DB dependencies in unit tests.
