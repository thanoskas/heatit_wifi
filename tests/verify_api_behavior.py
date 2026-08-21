
import asyncio
import sys
from unittest.mock import MagicMock, AsyncMock, patch

# Mock homeassistant before importing anything else
class MockModule(MagicMock):
    def __getattr__(self, name):
        if name in ("__spec__", "__path__"):
            return None
        return MagicMock()

sys.modules["homeassistant"] = MockModule()
sys.modules["homeassistant.core"] = MockModule()
sys.modules["homeassistant.helpers"] = MockModule()
sys.modules["homeassistant.helpers.aiohttp_client"] = MockModule()
sys.modules["homeassistant.helpers.typing"] = MockModule()
sys.modules["homeassistant.helpers.update_coordinator"] = MockModule()
sys.modules["homeassistant.config_entries"] = MockModule()
sys.modules["homeassistant.const"] = MockModule()
sys.modules["homeassistant.exceptions"] = MockModule()

# Mock aiohttp correctly
mock_aiohttp = MagicMock()
class ClientError(Exception): pass
mock_aiohttp.ClientError = ClientError
sys.modules["aiohttp"] = mock_aiohttp
import aiohttp

# Mock the constants to avoid import errors from .const
sys.modules["custom_components.heatit_wifi6.const"] = MagicMock()

from custom_components.heatit_wifi6.api import HeatitWiFi6API

class MockResponse:
    def __init__(self, text_data="{}", fail_attempts=0):
        self.text_data = text_data
        self.fail_attempts = fail_attempts
        self.current_attempt = 0

    async def __aenter__(self):
        self.current_attempt += 1
        if self.current_attempt <= self.fail_attempts:
            raise asyncio.TimeoutError()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

    async def text(self):
        return self.text_data

class MockSession:
    def __init__(self, response):
        self.response = response

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

    def post(self, *args, **kwargs): return self.response
    def get(self, *args, **kwargs): return self.response
    def delete(self, *args, **kwargs): return self.response

async def test_api_behavior():
    print("Running functional tests...")

    # Setup
    mock_aiohttp.ClientTimeout = MagicMock()
    mock_aiohttp.resolver.ThreadedResolver = MagicMock()
    mock_aiohttp.TCPConnector.return_value = MagicMock()

    api = HeatitWiFi6API("http://localhost")

    # Test Case 1: Success on first attempt
    print("Test 1: Success on first attempt")
    resp = MockResponse(text_data='{"status": "Success"}')
    mock_aiohttp.ClientSession.return_value = MockSession(resp)
    result = await api._get("/test")
    assert result == {"status": "Success"}
    print("  Success!")

    # Test Case 2: Success after 1 retry
    print("Test 2: Success after 1 retry")
    resp = MockResponse(text_data='{"status": "Success"}', fail_attempts=1)
    mock_aiohttp.ClientSession.return_value = MockSession(resp)
    with patch("custom_components.heatit_wifi6.api.asyncio.sleep", AsyncMock()):
        result = await api._get("/test", retries=1)
        assert result == {"status": "Success"}
    print("  Success!")

    # Test Case 3: Failure after all retries
    print("Test 3: Failure after all retries")
    resp = MockResponse(text_data='{"status": "Success"}', fail_attempts=3)
    mock_aiohttp.ClientSession.return_value = MockSession(resp)
    with patch("custom_components.heatit_wifi6.api.asyncio.sleep", AsyncMock()):
        result = await api._post("/test", {"data": "test"}, retries=2)
        assert result == {}
    print("  Success!")

    # Test Case 4: Delete with retries
    print("Test 4: Delete with retries")
    resp = MockResponse(text_data='{"status": "Deleted"}', fail_attempts=1)
    mock_aiohttp.ClientSession.return_value = MockSession(resp)
    with patch("custom_components.heatit_wifi6.api.asyncio.sleep", AsyncMock()):
        result = await api._delete("/test", retries=1)
        assert result == {"status": "Deleted"}
    print("  Success!")

    # Test Case 5: External session usage
    print("Test 5: External session usage")
    ext_resp = MockResponse(text_data='{"status": "Ext"}')
    ext_session = MockSession(ext_resp)
    api_ext = HeatitWiFi6API("http://localhost", session=ext_session)
    mock_aiohttp.ClientSession.reset_mock()
    result = await api_ext._get("/test")
    assert result == {"status": "Ext"}
    mock_aiohttp.ClientSession.assert_not_called()
    print("  Success!")

if __name__ == "__main__":
    asyncio.run(test_api_behavior())
