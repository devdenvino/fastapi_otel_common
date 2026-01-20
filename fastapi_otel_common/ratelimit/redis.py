"""Redis-backed distributed rate limiter.

Provides rate limiting that works across multiple application instances.
"""
import time
from typing import Optional

from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from ..logging.logger import get_logger

logger = get_logger(__name__)


class RedisRateLimiter:
    """Redis-based rate limiter for distributed deployments.
    
    Uses Redis to track request counts per IP address, allowing rate limiting
    to work correctly across multiple application instances.
    
    Attributes:
        redis_url: Redis connection URL
        per_minute: Maximum requests per minute
        per_hour: Maximum requests per hour
        client: Redis client instance
    """
    
    def __init__(
        self,
        redis_url: str,
        per_minute: int = 60,
        per_hour: int = 1000,
    ):
        """Initialize Redis rate limiter.
        
        Args:
            redis_url: Redis connection URL (e.g., redis://localhost:6379)
            per_minute: Maximum requests per minute per IP
            per_hour: Maximum requests per hour per IP
        """
        self.redis_url = redis_url
        self.per_minute = per_minute
        self.per_hour = per_hour
        self.client: Optional[any] = None
        
    async def connect(self) -> None:
        """Establish Redis connection."""
        try:
            import redis.asyncio as redis
            self.client = await redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            # Test connection
            await self.client.ping()
            logger.info(f"Connected to Redis at {self.redis_url}")
        except ImportError:
            logger.error(
                "redis package not installed. Install with: pip install redis"
            )
            raise
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {str(e)}")
            raise
    
    async def disconnect(self) -> None:
        """Close Redis connection."""
        if self.client:
            await self.client.close()
            logger.info("Disconnected from Redis")
    
    async def is_rate_limited(self, client_id: str) -> tuple[bool, dict]:
        """Check if a client has exceeded rate limits.
        
        Args:
            client_id: Client identifier (usually IP address)
            
        Returns:
            Tuple of (is_limited, headers) where headers contain rate limit info
        """
        if not self.client:
            logger.warning("Redis client not connected, skipping rate limit check")
            return False, {}
        
        current_time = int(time.time())
        minute_key = f"ratelimit:{client_id}:minute:{current_time // 60}"
        hour_key = f"ratelimit:{client_id}:hour:{current_time // 3600}"
        
        try:
            # Use pipeline for atomic operations
            pipe = self.client.pipeline()
            
            # Increment counters
            pipe.incr(minute_key)
            pipe.expire(minute_key, 60)  # Expire after 1 minute
            pipe.incr(hour_key)
            pipe.expire(hour_key, 3600)  # Expire after 1 hour
            
            results = await pipe.execute()
            minute_count = results[0]
            hour_count = results[2]
            
            # Check limits
            is_limited = (
                minute_count > self.per_minute or 
                hour_count > self.per_hour
            )
            
            # Prepare headers
            headers = {
                "X-RateLimit-Limit-Minute": str(self.per_minute),
                "X-RateLimit-Limit-Hour": str(self.per_hour),
                "X-RateLimit-Remaining-Minute": str(max(0, self.per_minute - minute_count)),
                "X-RateLimit-Remaining-Hour": str(max(0, self.per_hour - hour_count)),
            }
            
            if is_limited:
                if minute_count > self.per_minute:
                    retry_after = 60 - (current_time % 60)
                    headers["Retry-After"] = str(retry_after)
                else:
                    retry_after = 3600 - (current_time % 3600)
                    headers["Retry-After"] = str(retry_after)
            
            return is_limited, headers
            
        except Exception as e:
            logger.error(f"Redis rate limit check failed: {str(e)}")
            # Fail open - don't rate limit if Redis is down
            return False, {}


class RedisRateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware for Redis-based distributed rate limiting.
    
    Attributes:
        limiter: RedisRateLimiter instance
        exclude_paths: List of paths to exclude from rate limiting
    """
    
    def __init__(
        self,
        app,
        limiter: RedisRateLimiter,
        exclude_paths: Optional[list[str]] = None,
    ):
        """Initialize middleware.
        
        Args:
            app: ASGI application
            limiter: RedisRateLimiter instance
            exclude_paths: Paths to exclude from rate limiting
        """
        super().__init__(app)
        self.limiter = limiter
        self.exclude_paths = exclude_paths or [
            "/healthz",
            "/livez", 
            "/readyz",
            "/startupz",
            "/health",
            "/docs",
            "/openapi.json",
        ]
    
    async def dispatch(self, request: Request, call_next):
        """Apply rate limiting to requests.
        
        Args:
            request: Incoming request
            call_next: Next middleware/handler
            
        Returns:
            Response with rate limit headers
        """
        # Skip rate limiting for excluded paths
        if request.url.path in self.exclude_paths:
            return await call_next(request)
        
        # Get client identifier (IP address)
        client_id = request.client.host if request.client else "unknown"
        
        # Check rate limit
        is_limited, headers = await self.limiter.is_rate_limited(client_id)
        
        if is_limited:
            logger.warning(
                f"Rate limit exceeded for {client_id} on {request.url.path}",
                extra={"client_id": client_id, "path": request.url.path}
            )
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "detail": "Rate limit exceeded. Please try again later.",
                    "request_id": getattr(request.state, "request_id", None),
                },
                headers=headers,
            )
        
        # Process request and add rate limit headers
        response = await call_next(request)
        
        # Add rate limit headers to response
        for key, value in headers.items():
            response.headers[key] = value
        
        return response
