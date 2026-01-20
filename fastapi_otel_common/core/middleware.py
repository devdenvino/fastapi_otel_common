"""
Production-ready middleware for security, logging, metrics, and rate limiting.

This module provides middleware components for:
- Request ID tracking for distributed tracing
- Security headers (OWASP best practices)
- Request/response logging with timing
- OpenTelemetry metrics collection
- Global error handling
- Rate limiting protection
"""
import time
import uuid
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Callable, Dict, Tuple

from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from ..logging.logger import get_logger

logger = get_logger(__name__)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Add unique request ID to each request for distributed tracing.
    
    The request ID is added to both request.state and response headers.
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        
        # Security headers applied to all responses
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        
        # Content Security Policy - Only apply to Swagger UI endpoints
        # This allows OIDC provider connections for OAuth2 flows in documentation
        swagger_paths = ["/docs", "/redoc", "/openapi.json"]
        if request.url.path in swagger_paths:
            # Import here to avoid circular dependencies
            from ..core.config import OIDC_ISSUER
            from urllib.parse import urlparse
            
            oidc_origin = ""
            if OIDC_ISSUER:
                parsed = urlparse(OIDC_ISSUER)
                oidc_origin = f"{parsed.scheme}://{parsed.netloc}"
            
            csp_policy = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
                "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
                "img-src 'self' data: https://fastapi.tiangolo.com; "
                "font-src 'self' data:; "
                f"connect-src 'self' https://cdn.jsdelivr.net {oidc_origin}"
            )
            response.headers["Content-Security-Policy"] = csp_policy
        
        return response


class MetricsMiddleware(BaseHTTPMiddleware):
    """Collect OpenTelemetry metrics for HTTP requests.
    
    Records:
    - Request count by method, path, and status code
    - Request duration histogram
    - Request/response size histograms
    - Active request counter
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        from ..telemetry.tracing import (
            http_request_counter,
            http_request_duration,
            http_request_size,
            http_response_size,
            http_active_requests
        )
        
        start_time = time.time()
        
        # Get request size
        request_size = int(request.headers.get("content-length", 0))
        
        # Track active requests
        labels = {
            "http.method": request.method,
            "http.route": request.url.path,
        }
        http_active_requests.add(1, labels)
        
        try:
            response = await call_next(request)
            
            # Calculate duration in milliseconds
            duration_ms = (time.time() - start_time) * 1000
            
            # Get response size
            response_size = int(response.headers.get("content-length", 0))
            
            # Complete labels with status
            metric_labels = {
                "http.method": request.method,
                "http.route": request.url.path,
                "http.status_code": str(response.status_code),
            }
            
            # Record metrics
            http_request_counter.add(1, metric_labels)
            http_request_duration.record(duration_ms, metric_labels)
            
            if request_size > 0:
                http_request_size.record(request_size, metric_labels)
            
            if response_size > 0:
                http_response_size.record(response_size, metric_labels)
            
            return response
        except Exception as exc:
            # Record error metrics
            error_labels = {
                "http.method": request.method,
                "http.route": request.url.path,
                "http.status_code": "500",
            }
            http_request_counter.add(1, error_labels)
            duration_ms = (time.time() - start_time) * 1000
            http_request_duration.record(duration_ms, error_labels)
            raise
        finally:
            # Decrement active requests
            http_active_requests.add(-1, labels)


class LoggingMiddleware(BaseHTTPMiddleware):
    """Log all requests and responses with timing"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()
        
        # Log request
        logger.info(
            f"Request started",
            extra={
                "method": request.method,
                "path": request.url.path,
                "client": request.client.host if request.client else None,
                "request_id": getattr(request.state, "request_id", None)
            }
        )
        
        try:
            response = await call_next(request)
            
            # Calculate duration
            duration = time.time() - start_time
            
            # Log response
            logger.info(
                f"Request completed",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration_ms": round(duration * 1000, 2),
                    "request_id": getattr(request.state, "request_id", None)
                }
            )
            
            return response
            
        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                f"Request failed: {str(e)}",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "duration_ms": round(duration * 1000, 2),
                    "request_id": getattr(request.state, "request_id", None),
                    "error": str(e)
                }
            )
            raise


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """Global error handler to catch unhandled exceptions"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        try:
            return await call_next(request)
        except Exception as e:
            logger.exception(
                f"Unhandled exception: {str(e)}",
                extra={
                    "path": request.url.path,
                    "method": request.method,
                    "request_id": getattr(request.state, "request_id", None)
                }
            )
            
            # Don't leak internal errors in production
            return JSONResponse(
                status_code=500,
                content={
                    "detail": "An internal error occurred. Please try again later.",
                    "request_id": getattr(request.state, "request_id", None)
                }
            )


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Simple in-memory rate limiting middleware.
    For production use, consider using Redis-based rate limiting for distributed systems.
    """
    
    def __init__(
        self, 
        app: ASGIApp,
        requests_per_minute: int = 60,
        requests_per_hour: int = 1000,
        cleanup_interval: int = 300  # Clean up old entries every 5 minutes
    ):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self.cleanup_interval = cleanup_interval
        
        # Store request timestamps: {client_ip: [timestamps]}
        self.request_history: Dict[str, list] = defaultdict(list)
        self.last_cleanup = datetime.now()
    
    def _cleanup_old_entries(self):
        """Remove old entries to prevent memory bloat"""
        now = datetime.now()
        if (now - self.last_cleanup).total_seconds() > self.cleanup_interval:
            cutoff_time = now - timedelta(hours=1)
            for client_ip in list(self.request_history.keys()):
                # Keep only requests from the last hour
                self.request_history[client_ip] = [
                    ts for ts in self.request_history[client_ip]
                    if ts > cutoff_time
                ]
                # Remove client if no recent requests
                if not self.request_history[client_ip]:
                    del self.request_history[client_ip]
            
            self.last_cleanup = now
    
    def _is_rate_limited(self, client_ip: str) -> Tuple[bool, str]:
        """Check if client has exceeded rate limits.
        
        Args:
            client_ip: IP address of the client
            
        Returns:
            Tuple of (is_limited: bool, reason: str)
        """
        now = datetime.now()
        
        # Get client's request history
        timestamps = self.request_history[client_ip]
        
        # Check per-minute limit
        one_minute_ago = now - timedelta(minutes=1)
        recent_minute_requests = [ts for ts in timestamps if ts > one_minute_ago]
        if len(recent_minute_requests) >= self.requests_per_minute:
            return True, f"Rate limit exceeded: {self.requests_per_minute} requests per minute"
        
        # Check per-hour limit
        one_hour_ago = now - timedelta(hours=1)
        recent_hour_requests = [ts for ts in timestamps if ts > one_hour_ago]
        if len(recent_hour_requests) >= self.requests_per_hour:
            return True, f"Rate limit exceeded: {self.requests_per_hour} requests per hour"
        
        return False, ""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip rate limiting for health checks and docs
        if request.url.path in ["/health", "/docs", "/redoc", "/openapi.json"]:
            return await call_next(request)
        
        # Get client IP
        client_ip = request.client.host if request.client else "unknown"
        
        # Periodic cleanup
        self._cleanup_old_entries()
        
        # Check rate limit
        is_limited, reason = self._is_rate_limited(client_ip)
        
        if is_limited:
            logger.warning(
                f"Rate limit exceeded for client",
                extra={
                    "client": client_ip,
                    "path": request.url.path,
                    "request_id": getattr(request.state, "request_id", None)
                }
            )
            
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "detail": reason,
                    "request_id": getattr(request.state, "request_id", None)
                },
                headers={
                    "Retry-After": "60"  # Suggest retry after 60 seconds
                }
            )
        
        # Record this request
        self.request_history[client_ip].append(datetime.now())
        
        # Process request
        return await call_next(request)
