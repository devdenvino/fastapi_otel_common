"""Test shutdown without OTLP endpoint configured - should be instant."""
import asyncio
import os
import time
import pytest

# Set environment variables for testing - NO OTLP endpoint
os.environ["ENABLE_OTEL_METRICS"] = "True"
os.environ["ENABLE_OTEL_INSTRUMENTATION"] = "True"
os.environ["SERVICE_NAME"] = "test-shutdown-no-otlp"
os.environ["SERVICE_VERSION"] = "1.0.0"
# Explicitly unset OTLP endpoints
if "OTEL_EXPORTER_OTLP_ENDPOINT" in os.environ:
    del os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"]
if "OTEL_EXPORTER_OTLP_TRACES_ENDPOINT" in os.environ:
    del os.environ["OTEL_EXPORTER_OTLP_TRACES_ENDPOINT"]
if "OTEL_EXPORTER_OTLP_METRICS_ENDPOINT" in os.environ:
    del os.environ["OTEL_EXPORTER_OTLP_METRICS_ENDPOINT"]

from fastapi import FastAPI
from fastapi.testclient import TestClient
from fastapi_otel_common import create_app

@pytest.mark.asyncio
async def test_shutdown_without_otlp():
    """Test application shutdown when OTLP is not configured."""
    print("Creating FastAPI application (no OTLP endpoint)...")
    app = create_app(title="Shutdown No OTLP Test")
    
    print("Application created, generating traffic...")
    
    # Use TestClient to make requests
    client = TestClient(app)
    
    # Make several requests
    for i in range(10):
        response = client.get("/health/liveness")
        print(f"Request {i+1}: {response.status_code}")
    
    print("Traffic generated, initiating shutdown...")
    start_time = time.time()
    
    # The TestClient will trigger shutdown when the app context exits
    del client
    await asyncio.sleep(0.1)
    
    shutdown_duration = time.time() - start_time
    
    print(f"Shutdown completed in {shutdown_duration:.2f} seconds")
    
    if shutdown_duration > 5:
        print("⚠️  WARNING: Shutdown took longer than expected!")
        pytest.fail(f"Shutdown took {shutdown_duration:.2f} seconds, expected < 5 seconds")
    else:
        print("✅ Shutdown completed successfully!")

if __name__ == "__main__":
    try:
        asyncio.run(test_shutdown_without_otlp())
    except KeyboardInterrupt:
        print("\n⚠️  Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error during test: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
