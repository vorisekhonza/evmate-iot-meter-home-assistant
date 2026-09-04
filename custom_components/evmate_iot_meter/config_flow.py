from __future__ import annotations
from typing import Any
import aiohttp
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import CONF_PORT, DEFAULT_PORT, DOMAIN, UPDATE_PATH

async def _validate(hass, host: str, port: int) -> dict[str, Any]:
    url = f"http://{host}:{port}{UPDATE_PATH}"
    session = async_get_clientsession(hass)
    async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as response:
        response.raise_for_status()
        data = await response.json(content_type=None)
    if not isinstance(data, dict) or "ID" not in data:
        raise ValueError("Unexpected EVmate response")
    return data

class EVmateConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            host = user_input[CONF_HOST].strip()
            port = user_input[CONF_PORT]
            try:
                data = await _validate(self.hass, host, port)
            except (aiohttp.ClientError, TimeoutError, ValueError):
                errors["base"] = "cannot_connect"
            else:
                meter_id = str(data.get("ID", host))
                await self.async_set_unique_id(f"evmate-{meter_id}")
                self._abort_if_unique_id_configured(
                    updates={CONF_HOST: host, CONF_PORT: port}
                )
                return self.async_create_entry(
                    title=f"EVmate IoT Meter {meter_id}",
                    data={CONF_HOST: host, CONF_PORT: port},
                )

        schema = vol.Schema({
            vol.Required(CONF_HOST, default=(user_input or {}).get(CONF_HOST, "")): str,
            vol.Required(CONF_PORT, default=(user_input or {}).get(CONF_PORT, DEFAULT_PORT)):
                vol.All(vol.Coerce(int), vol.Range(min=1, max=65535)),
        })
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)
