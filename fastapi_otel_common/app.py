from .telemetry.tracing import setup_tracer, trace_exceptions_middleware
from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

from .core.config import APP_TITLE, APP_VERSION, ALLOWED_ORIGINS, SWAGGER_CLIENT_ID
from .routes import health


def create_app():
    setup_tracer()

    app = FastAPI(
        title=APP_TITLE,
        version=APP_VERSION,
        swagger_ui_oauth2_redirect_url="/docs/oauth2-redirect",
        swagger_ui_init_oauth={
            "usePkceWithAuthorizationCodeGrant": True,
            "clientId": SWAGGER_CLIENT_ID or "",
            "scopes": "openid profile email api:read api:write",
        },
    )

    # Instrument the app FIRST to capture the full request time, including other middleware.

    app.add_middleware(
        CORSMiddleware,
        allow_origins=ALLOWED_ORIGINS if ALLOWED_ORIGINS != ["*"] else ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.middleware("http")(trace_exceptions_middleware)

    app.include_router(health.router)

    return app


def instrument_app(app: FastAPI):
    FastAPIInstrumentor.instrument_app(app)
