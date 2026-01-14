"""Config flow for ThermoPro TP920."""
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.components.bluetooth import async_discovered_service_info

from .const import DOMAIN

UNIT_OPTIONS = {
    "celsius": "Celsius (°C)",
    "fahrenheit": "Fahrenheit (°F)",
}

DEFAULT_UPDATE_INTERVAL = 60
MIN_UPDATE_INTERVAL = 15
MAX_UPDATE_INTERVAL = 3600


class ThermoProTP920ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for ThermoPro TP920."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        devices = {}

        for info in async_discovered_service_info(self.hass):
            if info.name and "tp920" in info.name.lower():
                devices[info.address] = f"{info.name} ({info.address})"

        if user_input is not None:
            return self.async_create_entry(
                title="ThermoPro TP920",
                data=user_input,
            )

        schema = {
            vol.Required("address"): (
                vol.In(devices) if devices else str
            ),
            vol.Optional("unit", default="celsius"): vol.In(UNIT_OPTIONS),
            vol.Optional(
                "update_interval",
                default=DEFAULT_UPDATE_INTERVAL,
            ): vol.All(
                vol.Coerce(int),
                vol.Range(min=MIN_UPDATE_INTERVAL, max=MAX_UPDATE_INTERVAL),
            ),
        }

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(schema),
        )
