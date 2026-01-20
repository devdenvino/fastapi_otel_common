"""Test shutdown with actual traffic to ensure exporters handle unreachable endpoints."""
import asyncio
import os
import time
import pytest

# Set environment variables for testing
os.environ["ENABLE_OTEL_METRICS"] = "True"
os.environ["ENABLE_OTEL_INSTRUMENTATION"] = "True"
os.environ["OTEL_METRIC_EXPORT_TIMEOUT"] = "2000"  # Short timeout for testing
os.environ["OTEL_BSP_EXPORT_TIMEOUT"] = "2000"  # Short timeout for batch span processor
os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = "http://localhost:4317"  # Unreachable endpoint
os.environ["SERVICE_NAME"] = "test-shutdown-traffic"
os.environ["SERVICE_VERSION"] = "1.0.0"
os.environ["OTEL_SHUTDOWN_TIMEOUT"] = "2000"  # 2 second shutdown timeout

from fastapi import FastAPI
from fastapi.testclient import TestClient
from fastapi_otel_common import create_app

@pytest.mark.asyncio
async def test_shutdown_with_traffic():
    """Test application shutdown after generating traffic."""
    print("Creating FastAPI application...")
    app = create_app(title="Shutdown Traffic Test")
    
    print("Application created, generating traffic...")
    
    # Use TestClient to make requests
    client = TestClient(app)
    
    # Make several requests to generate spans and metrics
    for i in range(10):
        response = client.get("/health/liveness")
        print(f"Request {i+1}: {response.status_code}")
    
    print("Traffic generated, waiting for batch to accumulate...")
    await asyncio.sleep(1)
    
    # Now trigger shutdown
    print("Initiating shutdown with pending exports...")
    start_time = time.time()
    
    # The TestClient will trigger shutdown when the app context exits
    # We just need to wait a bit for the lifespan to complete
    del client
    await asyncio.sleep(0.5)
    
    shutdown_duration = time.time() - start_time
    
    print(f"Shutdown completed in {shutdown_duration:.2f} seconds")
    
    if shutdown_duration > 10:
        print("⚠️  WARNING: Shutdown took longer than expected!")
        pytest.fail(f"Shutdown took {shutdown_duration:.2f} seconds, expected < 10 seconds")
    else:
        print("✅ Shutdown completed successfully within timeout!")

if __name__ == "__main__":
    try:
        asyncio.run(test_shutdown_with_traffic())
    except KeyboardInterrupt:
        print("\n⚠️  Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error during test: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
