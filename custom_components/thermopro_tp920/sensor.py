"""Platform for sensor integration."""
import asyncio
import logging
from datetime import timedelta

from bleak import BleakClient, BleakError

from homeassistant.components.sensor import (
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import UnitOfTemperature
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# BLE constants
WRITE_CHAR_UUID = "1086fff1-3343-4817-8bb2-b32206336ce8"
NOTIFY_CHAR_UUID = "1086fff2-3343-4817-8bb2-b32206336ce8"

MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds
DEFAULT_UPDATE_INTERVAL = 60  # seconds

HANDSHAKE_COMMANDS = [
    bytes.fromhex("01098a7a13b73ed68b67c2a0"),
    bytes.fromhex("410041"),
    bytes.fromhex("28040a2d8c6e5d"),
    bytes.fromhex("23060200ffffffff27"),
    bytes.fromhex("23060400ffffffff29"),
]


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the sensor platform."""
    address = config_entry.data["address"]

    update_interval = config_entry.data.get(
        "update_interval",
        DEFAULT_UPDATE_INTERVAL,
    )

    coordinator = ThermoProDataCoordinator(
        hass=hass,
        address=address,
        update_interval=update_interval,
    )

    await coordinator.async_config_entry_first_refresh()

    probes = [
        ThermoProTP920ProbeSensor(coordinator, config_entry, 1),
        ThermoProTP920ProbeSensor(coordinator, config_entry, 2),
    ]
    async_add_entities(probes)


class ThermoProDataCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the ThermoPro device."""

    def __init__(self, hass, address, update_interval):
        """Initialize the data update coordinator."""
        self.address = address
        self.ble_lock = asyncio.Lock()

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=update_interval),
        )

    async def _async_update_data(self):
        """Fetch data from the sensor with retry logic."""
        last_exception = None

        for attempt in range(MAX_RETRIES):
            try:
                async with self.ble_lock:
                    notification_received = asyncio.Future()

                    def notification_handler(sender, data):
                        if not notification_received.done():
                            notification_received.set_result(data)

                    async with BleakClient(self.address, timeout=20.0) as client:
                        if not client.is_connected:
                            raise BleakError("Failed to connect")

                        _LOGGER.debug(
                            "Connected to %s (Attempt %d/%d)",
                            self.address,
                            attempt + 1,
                            MAX_RETRIES,
                        )

                        for cmd in HANDSHAKE_COMMANDS:
                            await client.write_gatt_char(WRITE_CHAR_UUID, cmd)
                            await asyncio.sleep(0.4)

                        await client.start_notify(
                            NOTIFY_CHAR_UUID,
                            notification_handler,
                        )

                        try:
                            data = await asyncio.wait_for(
                                notification_received,
                                timeout=10.0,
                            )
                        except asyncio.TimeoutError:
                            raise UpdateFailed(
                                "Did not receive notification in time"
                            )
                        finally:
                            await client.stop_notify(NOTIFY_CHAR_UUID)

                        hex_data = data.hex()
                        probe1_hex = hex_data[14:18]
                        probe2_hex = hex_data[22:26]

                        def convert_to_celsius(probe_hex):
                            if probe_hex != "ffff":
                                return round(float(probe_hex) / 10.0, 1)
                            return None

                        return {
                            1: convert_to_celsius(probe1_hex),
                            2: convert_to_celsius(probe2_hex),
                        }

            except (BleakError, asyncio.TimeoutError) as e:
                last_exception = e
                _LOGGER.warning(
                    "Error communicating with %s (attempt %d/%d): %s",
                    self.address,
                    attempt + 1,
                    MAX_RETRIES,
                    e,
                )
                if attempt < MAX_RETRIES - 1:
                    await asyncio.sleep(RETRY_DELAY)

            except Exception as e:
                last_exception = e
                _LOGGER.error("Unexpected error: %s", e)
                break

        raise UpdateFailed(
            f"Failed to update after {MAX_RETRIES} attempts: {last_exception}"
        )


class ThermoProTP920ProbeSensor(CoordinatorEntity, SensorEntity):
    """Representation of a ThermoPro probe sensor."""

    _attr_has_entity_name = True
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, config_entry, probe_number):
        """Initialize the sensor."""
        super().__init__(coordinator)

        self._probe_number = probe_number
        self._unit = config_entry.data.get("unit", "celsius")

        self._attr_name = f"Probe {probe_number}"
        self._attr_unique_id = f"{coordinator.address}_{probe_number}"

        self._attr_native_unit_of_measurement = (
            UnitOfTemperature.FAHRENHEIT
            if self._unit == "fahrenheit"
            else UnitOfTemperature.CELSIUS
        )

        self._attr_device_info = {
            "identifiers": {(DOMAIN, coordinator.address)},
            "name": "ThermoPro TP920",
            "manufacturer": "ThermoPro",
        }

    @property
    def native_value(self):
        """Return the state of the sensor."""
        value_c = self.coordinator.data.get(self._probe_number)

        if value_c is None:
            return None

        if self._unit == "fahrenheit":
            return round(value_c * 9 / 5 + 32, 1)

        return value_c

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return (
            super().available
            and self.coordinator.data
            and self.coordinator.data.get(self._probe_number) is not None
        )
