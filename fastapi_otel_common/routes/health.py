"""Health check endpoints for application monitoring.

Provides Kubernetes-compatible health probes:
- /healthz: Liveness probe - indicates if the application is running
- /readyz: Readiness probe - indicates if the application can accept traffic
- /livez: Alias for liveness probe
- /startupz: Startup probe - indicates if the application has started successfully
"""
import asyncio
from datetime import datetime
from typing import Any, Dict, List

import httpx
from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import DB_HOST, DB_NAME, DB_PORT, OIDC_DISCOVERY_URL
from ..database.db import get_db_session_with_async_context
from ..logging.logger import get_logger

router = APIRouter(tags=["health"])
logger = get_logger(__name__)

# Track startup completion
_startup_complete = False
_startup_time = datetime.utcnow()


def mark_startup_complete() -> None:
    """Mark the application as having completed startup."""
    global _startup_complete, _startup_time
    _startup_complete = True
    _startup_time = datetime.utcnow()


async def check_database() -> Dict[str, Any]:
    """Check database connectivity.
    
    Returns:
        dict: Database health status
    """
    try:
        async with get_db_session_with_async_context() as session:
            result = await session.execute(text("SELECT 1"))
            result.scalar()
            return {
                "status": "healthy",
                "host": DB_HOST,
                "port": DB_PORT,
                "database": DB_NAME,
            }
    except Exception as e:
        logger.error(f"Database health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "host": DB_HOST,
            "port": DB_PORT,
            "database": DB_NAME,
        }


async def check_oidc_provider() -> Dict[str, Any]:
    """Check OIDC provider connectivity.
    
    Returns:
        dict: OIDC provider health status
    """
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(OIDC_DISCOVERY_URL)
            response.raise_for_status()
            return {
                "status": "healthy",
                "url": OIDC_DISCOVERY_URL,
                "response_time_ms": int(response.elapsed.total_seconds() * 1000),
            }
    except Exception as e:
        logger.error(f"OIDC provider health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "url": OIDC_DISCOVERY_URL,
        }


@router.get("/healthz")
@router.get("/livez")
async def liveness() -> dict:
    """Liveness probe endpoint.
    
    Indicates whether the application is running. This should only fail if the
    application is completely broken and needs to be restarted.
    
    Returns:
        dict: Simple status indicator
    """
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}


@router.get("/readyz")
async def readiness(response: Response) -> dict:
    """Readiness probe endpoint.
    
    Indicates whether the application is ready to accept traffic. Checks all
    critical dependencies including database and authentication provider.
    
    Args:
        response: FastAPI response object to set status code
        
    Returns:
        dict: Detailed readiness status
    """
    checks = {}
    all_healthy = True
    
    # Run all health checks in parallel
    db_check, oidc_check = await asyncio.gather(
        check_database(),
        check_oidc_provider(),
        return_exceptions=True
    )
    
    # Process database check
    if isinstance(db_check, Exception):
        checks["database"] = {"status": "unhealthy", "error": str(db_check)}
        all_healthy = False
    else:
        checks["database"] = db_check
        if db_check["status"] != "healthy":
            all_healthy = False
    
    # Process OIDC check
    if isinstance(oidc_check, Exception):
        checks["oidc_provider"] = {"status": "unhealthy", "error": str(oidc_check)}
        all_healthy = False
    else:
        checks["oidc_provider"] = oidc_check
        if oidc_check["status"] != "healthy":
            all_healthy = False
    
    # Set appropriate status code
    if not all_healthy:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    
    return {
        "status": "ready" if all_healthy else "not_ready",
        "timestamp": datetime.utcnow().isoformat(),
        "checks": checks,
    }


@router.get("/startupz")
async def startup(response: Response) -> dict:
    """Startup probe endpoint.
    
    Indicates whether the application has completed its startup sequence.
    Used by Kubernetes to know when to switch from startup to liveness probes.
    
    Args:
        response: FastAPI response object to set status code
        
    Returns:
        dict: Startup status
    """
    if not _startup_complete:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {
            "status": "starting",
            "timestamp": datetime.utcnow().isoformat(),
        }
    
    return {
        "status": "started",
        "timestamp": datetime.utcnow().isoformat(),
        "startup_time": _startup_time.isoformat(),
    }


# Backward compatibility - keep the old endpoint
@router.get("/health")
async def health() -> dict:
    """Legacy health check endpoint.
    
    Deprecated: Use /healthz, /readyz, or /livez instead.
    
    Returns:
        dict: Simple status indicator
    """
    return {"status": "ok"}