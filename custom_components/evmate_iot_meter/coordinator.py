from __future__ import annotations
from datetime import timedelta
import logging
from typing import Any
import aiohttp

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import CONF_PORT, DEFAULT_PORT, DEFAULT_SCAN_INTERVAL, DOMAIN, UPDATE_PATH

_LOGGER = logging.getLogger(__name__)

class EVmateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.host = entry.data["host"]
        self.port = entry.data.get(CONF_PORT, DEFAULT_PORT)
        self.url = f"http://{self.host}:{self.port}{UPDATE_PATH}"
        self.session = async_get_clientsession(hass)
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            async with self.session.get(
                self.url, timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                response.raise_for_status()
                data = await response.json(content_type=None)
        except (aiohttp.ClientError, TimeoutError, ValueError) as err:
            raise UpdateFailed(f"Unable to read {self.url}: {err}") from err

        if not isinstance(data, dict):
            raise UpdateFailed("EVmate returned invalid data")
        return data
