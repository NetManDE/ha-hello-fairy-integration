""" light platform """
from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_HS_COLOR,
    ATTR_EFFECT,
    ENTITY_ID_FORMAT,
    PLATFORM_SCHEMA,
    LightEntity,
    LightEntityFeature,
    ColorMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_MAC, CONF_NAME, EVENT_HOMEASSISTANT_STOP
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import generate_entity_id
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util.color import color_hs_to_RGB, color_RGB_to_hs
from homeassistant.util.color import (
    color_temperature_kelvin_to_mired as kelvin_to_mired,
)
from homeassistant.util.color import (
    color_temperature_mired_to_kelvin as mired_to_kelvin,
)

from .const import DOMAIN, SCENES
from .hello_fairy import BleakError, Lamp

if TYPE_CHECKING:
    from bleak.backends.device import BLEDevice

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_MAC): cv.string,
        vol.Optional(CONF_NAME, default=DOMAIN): cv.string,
    }
)

# Build effect list from available scenes
LIGHT_EFFECT_LIST = ["none"] + sorted(SCENES.keys())

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the platform from config_entry."""
    _LOGGER.debug(
        f"light async_setup_entry: setting up the config entry {config_entry.title} "
        f"with data:{config_entry.data}"
    )
    name = config_entry.data.get(CONF_NAME) or DOMAIN
    ble_device = hass.data[DOMAIN][config_entry.entry_id]

    entity = HelloFairyBT(name, ble_device)
    async_add_entities([entity])


class HelloFairyBT(LightEntity):
    """Representation of a light."""

    def __init__(self, name: str, ble_device: BLEDevice) -> None:
        """Initialize the light."""
        self._name = name
        self._mac = ble_device.address
        self.entity_id = generate_entity_id(ENTITY_ID_FORMAT, self._name, [])
        self._is_on = False
        self._rgb = (255, 255, 255)  # Default to white
        self._brightness = 255  # Default to full brightness
        self._effect_list = LIGHT_EFFECT_LIST
        self._effect = "none"
        self._available = True

        _LOGGER.info(f"[LIGHT_INIT] Initializing Hello Fairy Entity: {self.name}, {self._mac}")
        _LOGGER.debug(f"[LIGHT_INIT] BLE Device: {ble_device.name} ({ble_device.address})")
        self._dev = Lamp(ble_device)
        self._prop_min_max = self._dev.get_prop_min_max()
        _LOGGER.debug(f"[LIGHT_INIT] Properties: {self._prop_min_max}")

        # Register callback to update availability when connection state changes
        self._dev.add_callback_on_state_changed(self._on_device_state_changed)
        _LOGGER.debug("[LIGHT_INIT] Registered state change callback")

    def _on_device_state_changed(self) -> None:
        """Called when device connection state changes."""
        new_available = self._dev.available
        _LOGGER.info(f"[LIGHT_CALLBACK] Device state changed - available: {new_available}, conn: {self._dev._conn}")

        if self._available != new_available:
            _LOGGER.info(f"[LIGHT_CALLBACK] ⚡ Availability changing from {self._available} to {new_available}")
            self._available = new_available
            # Notify Home Assistant of the state change
            self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added to hass."""
        _LOGGER.info(f"[LIGHT_ADDED] Entity {self.name} ({self._mac}) added to Home Assistant")
        self.async_on_remove(
            self.hass.bus.async_listen_once(
                EVENT_HOMEASSISTANT_STOP, self.async_will_remove_from_hass
            )
        )
        # Don't force refresh on startup - stay optimistically available
        _LOGGER.debug("[LIGHT_ADDED] Entity initialization complete, staying optimistically available")

    async def async_will_remove_from_hass(self, event=None) -> None:
        """Run when entity will be removed from hass."""
        _LOGGER.info(f"[LIGHT_REMOVE] Removing entity {self.name} from Home Assistant")
        try:
            _LOGGER.debug("[LIGHT_REMOVE] Disconnecting from device...")
            await self._dev.disconnect()
            _LOGGER.debug("[LIGHT_REMOVE] ✅ Successfully disconnected")
        except BleakError as ex:
            _LOGGER.warning(
                f"[LIGHT_REMOVE] ⚠️ BleakError while disconnecting from {self._dev._mac}: {ex}"
            )
        except Exception as ex:
            _LOGGER.error(
                f"[LIGHT_REMOVE] ❌ Unexpected error disconnecting from {self._dev._mac}: {ex}",
                exc_info=True
            )

    @property
    def device_info(self) -> dict[str, Any]:
        # TODO: replace with _attr
        prop = {
            "identifiers": {
                # Serial numbers are unique identifiers within a specific domain
                (DOMAIN, self.unique_id)
            },
            "name": self._name,
            "manufacturer": "HelloFairy",
            "model": "HelloFairy Model",
        }
        return prop

    @property
    def unique_id(self) -> str:
        # TODO: replace with _attr
        """Return the unique id of the light."""
        return self._mac

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        _LOGGER.debug(f"[LIGHT_AVAILABLE] Checking availability for {self.name}: {self._available}")
        return self._available

    @property
    def should_poll(self) -> bool:
        """Polling needed for a updating status."""
        return False

    @property
    def name(self) -> str:
        """Return the name of the light if any."""
        return self._name

    @property
    def brightness(self) -> int:
        """Return the brightness of this light between 0..255."""
        return self._brightness

    @property
    def hs_color(self) -> tuple[Any]:
        """
        Return the Hue and saturation color value.
        Lamp has rgb => we calculate hs
        """
        return color_RGB_to_hs(*self._rgb)

    @property
    def effect_list(self):
        """Return the list of supported effects."""
        return self._effect_list

    @property
    def effect(self):
        """Return the current effect."""
        return self._effect

    @property
    def is_on(self) -> bool:
        """Return true if light is on."""
        return self._is_on

    @property
    def supported_color_modes(self) -> set[ColorMode]:
        """Flag supported color modes."""
        return {ColorMode.HS}

    @property
    def color_mode(self) -> ColorMode:
        """Return the active color mode."""
        return ColorMode.HS

    @property
    def supported_features(self) -> LightEntityFeature:
        """Flag supported features."""
        return LightEntityFeature.EFFECT

    async def async_update(self) -> None:
        # The lamp state is tracked locally in this entity
        # Availability is updated via callbacks from the device
        _LOGGER.debug(f"[LIGHT_UPDATE] Updating lamp state for {self.name}")
        _LOGGER.debug(f"[LIGHT_UPDATE] Device connection state: {self._dev._conn}")
        _LOGGER.debug(f"[LIGHT_UPDATE] Current availability: {self._available}")
        _LOGGER.debug(f"[LIGHT_UPDATE] Current state - is_on: {self._is_on}, brightness: {self._brightness}, rgb: {self._rgb}")
        # Note: availability is now managed via device state callbacks, not here

    async def async_turn_on(self, **kwargs: int) -> None:
        """Turn the light on."""
        _LOGGER.info(f"[LIGHT_ON] 💡 Turning on {self.name} with attributes: {kwargs}")

        # First if brightness of dev to 0: turn off
        if ATTR_BRIGHTNESS in kwargs:
            brightness = kwargs[ATTR_BRIGHTNESS]
            if brightness == 0:
                _LOGGER.debug("[LIGHT_ON] Brightness set to 0, turning off instead")
                await self.async_turn_off()
                return
        else:
            brightness = self._brightness
            _LOGGER.debug(f"[LIGHT_ON] Using current brightness: {brightness}")

        # ATTR cannot be set while light is off, so turn it on first
        if not self._is_on:
            _LOGGER.info("[LIGHT_ON] Light is off, turning on first")
            await self._dev.turn_on()
            self._is_on = True
            self.async_write_ha_state()  # Update Home Assistant
            _LOGGER.debug("[LIGHT_ON] ✅ Light turned on")

        if ATTR_HS_COLOR in kwargs:
            rgb: tuple[int, int, int] = color_hs_to_RGB(*kwargs.get(ATTR_HS_COLOR))
            self._rgb = rgb
            _LOGGER.info(f"[LIGHT_ON] 🎨 Setting color RGB: {rgb} with brightness: {brightness}")
            await self._dev.set_color(*rgb, brightness=brightness)
            # Update state
            self._brightness = brightness
            self.async_write_ha_state()  # Update Home Assistant
            _LOGGER.debug("[LIGHT_ON] ✅ Color set successfully")
            return

        if ATTR_BRIGHTNESS in kwargs:
            _LOGGER.info(f"[LIGHT_ON] 🔆 Setting brightness: {brightness}")
            await self._dev.set_brightness(brightness)
            # Update state
            self._brightness = brightness
            self.async_write_ha_state()  # Update Home Assistant
            _LOGGER.debug("[LIGHT_ON] ✅ Brightness set successfully")
            return

        if ATTR_EFFECT in kwargs:
            effect_name = kwargs[ATTR_EFFECT]
            self._effect = effect_name
            _LOGGER.info(f"[LIGHT_ON] ✨ Setting effect: {effect_name}")

            # Handle scene effects
            if effect_name != "none" and effect_name in SCENES:
                scene_id = SCENES[effect_name]
                _LOGGER.info(f"[LIGHT_ON] Setting scene {effect_name} (ID: {scene_id}) with brightness: {brightness}")
                await self._dev.set_scene(scene_id, brightness=brightness)
                # Update state
                self._brightness = brightness
                self.async_write_ha_state()  # Update Home Assistant
                _LOGGER.debug("[LIGHT_ON] ✅ Effect set successfully")
                return

    async def async_turn_off(self, **kwargs: int) -> None:
        """Turn the light off."""
        _LOGGER.info(f"[LIGHT_OFF] 🌙 Turning off {self.name}")

        await self._dev.turn_off()
        self._is_on = False
        self.async_write_ha_state()  # Update Home Assistant
        _LOGGER.debug("[LIGHT_OFF] ✅ Light turned off")