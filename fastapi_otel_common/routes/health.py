"""Health check endpoints for application monitoring."""
from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/healthz")
async def health() -> dict:
    """Health check endpoint.
    
    Returns:
        dict: Simple status indicator
    """
    return {"status": "ok"}