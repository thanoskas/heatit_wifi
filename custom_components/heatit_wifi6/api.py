"""HTTP client for the Heatit WiFi6 thermostat REST API."""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

import aiohttp

from .const import API_PARAMETERS, API_RESET, API_STATUS

_LOGGER = logging.getLogger(__name__)


class HeatitWiFi6API:
    """Thin async wrapper around the thermostat's HTTP API."""

    def __init__(self, host: str, session: aiohttp.ClientSession) -> None:
        self._host = host.rstrip("/")
        self._session = session

    async def _request(
        self,
        method: str,
        endpoint: str,
        *,
        json_body: dict[str, Any] | None = None,
        timeout: float = 5,
        retries: int = 0,
    ) -> dict[str, Any]:
        """Send an HTTP request with optional retry/backoff and parse JSON."""
        url = f"{self._host}{endpoint}"
        client_timeout = aiohttp.ClientTimeout(total=timeout)

        for attempt in range(retries + 1):
            try:
                async with self._session.request(
                    method, url, json=json_body, timeout=client_timeout
                ) as response:
                    text = await response.text()
                    _LOGGER.debug("%s %s response: %s", method, url, text)
                    return self._parse_json(text)
            except (asyncio.TimeoutError, aiohttp.ClientError) as err:
                if attempt < retries:
                    wait_time = (attempt + 1) * 2
                    _LOGGER.debug(
                        "%s %s failed (attempt %d/%d): %s. Retrying in %ds...",
                        method, url, attempt + 1, retries + 1, err, wait_time,
                    )
                    await asyncio.sleep(wait_time)
                    continue
                _LOGGER.debug(
                    "%s %s failed after %d attempts: %s",
                    method, url, retries + 1, err,
                )
                return {}
        return {}

    @staticmethod
    def _parse_json(text: str) -> dict[str, Any]:
        """Parse JSON content from a raw text body, tolerating empty bodies."""
        if not isinstance(text, str):
            return {}
        text = text.strip()
        if not text or not text.startswith("{") or not text.endswith("}"):
            return {}
        try:
            return json.loads(text)
        except json.JSONDecodeError as err:
            _LOGGER.error("JSON parsing failed: %s", err)
            return {}

    async def get_device_id(self, retries: int = 0, timeout: float = 8) -> str:
        """Return the thermostat's device ID, or "unknown" on failure."""
        data = await self._request(
            "GET", API_STATUS, timeout=timeout, retries=retries
        )
        return data.get("id", "unknown")

    async def get_status(self, retries: int = 1, timeout: float = 5) -> dict[str, Any]:
        """Return the full status payload from the thermostat."""
        return await self._request(
            "GET", API_STATUS, timeout=timeout, retries=retries
        )

    async def set_parameter(self, parameter: str, value: Any) -> dict[str, Any]:
        """Update a single thermostat parameter."""
        _LOGGER.debug("set_parameter(%s, %s)", parameter, value)
        response = await self._request(
            "POST",
            API_PARAMETERS,
            json_body={parameter: value},
            timeout=20,
            retries=3,
        )
        if response.get("status") == "Success":
            return response
        _LOGGER.error("set_parameter(%s, %s) failed: %s", parameter, value, response)
        return {}

    async def reset_device(self, reset_type: str = "kwh") -> dict[str, Any]:
        """Send a reset command to the thermostat."""
        if reset_type not in ("factory", "settings", "kwh"):
            _LOGGER.error("Unknown reset_type: %s", reset_type)
            return {"status": "Failed", "detail": "Unknown reset_type."}

        endpoint = f"{API_RESET}/{reset_type}"
        response = await self._request("DELETE", endpoint)
        if response.get("status") == "Success":
            _LOGGER.info("reset_device(%s) succeeded", reset_type)
            return response
        _LOGGER.error("reset_device(%s) failed: %s", reset_type, response)
        return {}
