"""Test script to verify proper shutdown behavior."""
import asyncio
import os
import time
import pytest

# Set environment variables for testing
os.environ["ENABLE_OTEL_METRICS"] = "True"
os.environ["ENABLE_OTEL_INSTRUMENTATION"] = "True"
os.environ["OTEL_METRIC_EXPORT_TIMEOUT"] = "2000"  # Short timeout for testing
os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = "http://localhost:4317"
os.environ["SERVICE_NAME"] = "test-shutdown"
os.environ["SERVICE_VERSION"] = "1.0.0"

from fastapi_otel_common import create_app

@pytest.mark.asyncio
async def test_shutdown():
    """Test application startup and shutdown."""
    print("Creating FastAPI application...")
    app = create_app(title="Shutdown Test")
    
    print("Application created successfully")
    
    # Simulate some application usage
    print("Simulating application runtime...")
    await asyncio.sleep(1)
    
    # Trigger shutdown by exiting the lifespan context
    print("Initiating shutdown...")
    start_time = time.time()
    
    # The lifespan context manager will handle shutdown
    async with app.router.lifespan_context(app):
        await asyncio.sleep(0.1)
    
    shutdown_duration = time.time() - start_time
    
    print(f"Shutdown completed in {shutdown_duration:.2f} seconds")
    
    if shutdown_duration > 10:
        pytest.fail(f"Shutdown took too long: {shutdown_duration:.2f} seconds")
    else:
        print("✅ Shutdown completed successfully within timeout!")
        # Test passes if we reach here

if __name__ == "__main__":
    try:
        asyncio.run(test_shutdown())
    except KeyboardInterrupt:
        print("\n⚠️  Interrupted by user")
    except Exception as e:
        print(f"❌ Error during test: {e}")
        import traceback
        traceback.print_exc()
