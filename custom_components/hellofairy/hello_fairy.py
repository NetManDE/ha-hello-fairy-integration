# Standard imports
import asyncio
import enum
import logging
from typing import Any, Callable

# 3rd party imports
from bleak import BleakClient, BleakError
from bleak.backends.client import BaseBleakClient
from bleak.backends.device import BLEDevice
from bleak_retry_connector import establish_connection

from .const import (
    WRITE_CHAR_UUID,
    NOTIFY_CHAR_UUID,
    CMD_HEADER_A,
    CMD_SET_LIGHT,
    CMD_DIY_CONTROL,
    CMD_PIXEL_DATA,
    CMD_DIY_SETTINGS,
    LIGHT_MODE_SCENE,
    DIY_TYPE_STATIC,
    DIY_TYPE_SHOW_STATIC,
    DIY_TYPE_SAVE,
    CMD_DELAY_MS,
    PIXEL_CHUNK_SIZE,
    DEFAULT_PIXEL_COUNT,
    SCENE_BRIGHTNESS_MAX,
)

_LOGGER = logging.getLogger(__name__)


class Conn(enum.Enum):
    DISCONNECTED = 1
    UNPAIRED = 2
    PAIRING = 3
    PAIRED = 4


def calculate_checksum(data: bytes) -> int:
    """Calculate checksum for command packet (sum all bytes mod 256)"""
    return sum(data) % 256


class Lamp:
    """The class that represents a Hello Fairy / CN Curtain Light lamp"""

    def __init__(self, ble_device: BLEDevice, pixel_count: int = DEFAULT_PIXEL_COUNT):
        self._client: BleakClient | None = None
        self._ble_device = ble_device
        self._mac = self._ble_device.address
        self._pixel_count = pixel_count

        _LOGGER.debug(
            f"Initializing LED Curtain Light {self._ble_device.name} ({self._mac}) "
            f"with {pixel_count} pixels"
        )
        _LOGGER.debug(f"BLE_device details: {self._ble_device.details}")

        self._is_on = False
        self._rgb = (255, 255, 255)  # Default white
        self._brightness = 255  # 0-255
        self.versions: str | None = None

        # Store func to call on state received:
        self._state_callbacks: list[Callable[[], None]] = []
        self._conn = Conn.DISCONNECTED
        self._pair_resp_event = asyncio.Event()
        self._read_service = False

    def __str__(self) -> str:
        """The string representation"""
        str_rgb = f"rgb_{self._rgb} "
        str_bri = f"bri_{self._brightness} "
        str_rep = (
            f"<Lamp {self._mac} "
            f"{'ON' if self._is_on else 'OFF'} "
            f"{str_bri}{str_rgb}"
            f">"
        )
        return str_rep

    def add_callback_on_state_changed(self, func: Callable[[], None]) -> None:
        """Register callbacks to be called when lamp state is received or bt disconnected"""
        self._state_callbacks.append(func)

    def run_state_changed_cb(self) -> None:
        """Execute all registered callbacks for a state change"""
        for func in self._state_callbacks:
            func()

    def diconnected_cb(self, client: BaseBleakClient) -> None:
        _LOGGER.debug(f"Disconnected CB from client {client}")
        self._conn = Conn.DISCONNECTED
        self.run_state_changed_cb()

    async def connect(self, num_tries: int = 3) -> None:
        if self._client and not self._client.is_connected:
            await self.disconnect()
        if self._conn == Conn.PAIRING or self._conn == Conn.PAIRED:
            return

        _LOGGER.debug("Initiating new connection")
        try:
            if self._client:
                await self.disconnect()

            _LOGGER.debug(f"Connecting now to {self._ble_device}...")
            self._client = await establish_connection(
                BleakClient,
                device=self._ble_device,
                name=self._mac,
                disconnected_callback=self.diconnected_cb,
                max_attempts=4,
            )
            _LOGGER.debug(f"Connected: {self._client.is_connected}")
            self._conn = Conn.UNPAIRED

            # Read services if in debug mode:
            if not self._read_service and _LOGGER.isEnabledFor(logging.DEBUG):
                await self.read_services()
                self._read_service = True
                await asyncio.sleep(0.2)

            # Enable notifications
            _LOGGER.debug("Enabling notifications")
            await self._client.start_notify(NOTIFY_CHAR_UUID, self._notification_handler)
            await asyncio.sleep(0.1)

            self._conn = Conn.PAIRED
            _LOGGER.debug(f"Connection status: {self._conn}")

            # Advertise to HA lamp is now available:
            self.run_state_changed_cb()

        except asyncio.TimeoutError:
            _LOGGER.error("Connection Timeout error")
        except BleakError as err:
            _LOGGER.error(f"Connection: BleakError: {err}")

    def _notification_handler(self, sender: int, data: bytearray) -> None:
        """Handle notifications from the device"""
        _LOGGER.debug(f"Notification from {sender}: {data.hex()}")
        # Parse notification data if needed for state updates
        # The app receives state updates here, but for simplicity we'll track state locally

    async def disconnect(self) -> None:
        if self._client is None:
            return
        try:
            if self._client.is_connected:
                await self._client.stop_notify(NOTIFY_CHAR_UUID)
            await self._client.disconnect()
        except asyncio.TimeoutError:
            _LOGGER.error("Disconnection: Timeout error")
        except BleakError as err:
            _LOGGER.error(f"Disconnection: BleakError: {err}")
        self._conn = Conn.DISCONNECTED

    @property
    def mac(self) -> str:
        return self._mac

    @property
    def available(self) -> bool:
        return self._conn == Conn.PAIRED

    @property
    def is_on(self) -> bool:
        return self._is_on

    @property
    def brightness(self) -> int:
        return self._brightness

    @property
    def color(self) -> tuple[int, int, int]:
        return self._rgb

    @property
    def pixel_count(self) -> int:
        return self._pixel_count

    def get_prop_min_max(self) -> dict[str, Any]:
        return {
            "brightness": {"min": 0, "max": 255},
            "color": {"min": 0, "max": 255},
        }

    async def send_cmd(self, cmd_bytes: bytes, wait_notif: float = 0.05) -> bool:
        """Send command to the device"""
        await self.connect()
        if self._conn == Conn.PAIRED and self._client is not None:
            # Check if client is actually connected
            if not self._client.is_connected:
                _LOGGER.warning("Client not connected, attempting reconnection")
                await self.disconnect()
                await self.connect()
                if not self._client or not self._client.is_connected:
                    _LOGGER.error("Failed to reconnect to device")
                    return False

            try:
                _LOGGER.debug(f"Sending command: {cmd_bytes.hex()}")
                await self._client.write_gatt_char(WRITE_CHAR_UUID, bytearray(cmd_bytes))
                await asyncio.sleep(wait_notif)
                return True
            except AssertionError as err:
                _LOGGER.error(f"Send Cmd: AssertionError (connection lost): {err}")
                # Mark as disconnected and try to recover on next command
                self._conn = Conn.DISCONNECTED
            except asyncio.TimeoutError:
                _LOGGER.error("Send Cmd: Timeout error")
            except BleakError as err:
                _LOGGER.error(f"Send Cmd: BleakError: {err}")
                # Connection might be lost, mark as disconnected
                if "Operation failed with ATT error" in str(err):
                    self._conn = Conn.DISCONNECTED
        return False

    def _build_diy_control_cmd(self, direction: int = 0, speed: int = 100, diy_type: int = DIY_TYPE_STATIC) -> bytes:
        """Build DIY control command (0xD0)"""
        cmd = bytearray([CMD_HEADER_A, CMD_DIY_CONTROL, direction, speed, 0, diy_type])
        cmd.append(calculate_checksum(cmd))
        return bytes(cmd)

    def _build_pixel_data_cmd(self, frame: int, pixels: list[tuple[int, int, int, int]]) -> bytes:
        """
        Build pixel data command (0xDA)
        pixels: list of (pixel_index, r, g, b) tuples
        """
        cmd = bytearray([CMD_HEADER_A, CMD_PIXEL_DATA, frame])

        for pixel_index, r, g, b in pixels:
            # Add pixel index (little-endian, 2 bytes)
            cmd.append(pixel_index & 0xFF)
            cmd.append((pixel_index >> 8) & 0xFF)
            # Add RGB color
            cmd.extend([r, g, b])

        cmd.append(calculate_checksum(cmd))
        return bytes(cmd)

    def _build_set_scene_cmd(self, scene_number: int, brightness: int = 2000) -> bytes:
        """
        Build scene mode command (0x03)
        scene_number: Scene ID (1-50+)
        brightness: Scene brightness (0-2550, default 2000)
        """
        # Clamp brightness to valid range
        brightness = min(SCENE_BRIGHTNESS_MAX, max(0, int(brightness)))

        cmd = bytearray([
            CMD_HEADER_A,
            CMD_SET_LIGHT,
            LIGHT_MODE_SCENE,
            scene_number & 0xFF,
            (brightness >> 8) & 0xFF,  # brightness high byte
            brightness & 0xFF,          # brightness low byte
        ])
        cmd.append(calculate_checksum(cmd))
        return bytes(cmd)

    async def turn_on(self) -> None:
        """Turn the lamp on"""
        _LOGGER.debug("Send Cmd: Turn On")
        # Set to static DIY mode
        cmd = self._build_diy_control_cmd(diy_type=DIY_TYPE_SHOW_STATIC)
        if await self.send_cmd(cmd):
            self._is_on = True
            # Set current color
            await self.set_color(*self._rgb, self._brightness)

    async def turn_off(self) -> None:
        """Turn the lamp off"""
        _LOGGER.debug("Send Cmd: Turn Off")
        # Set all pixels to black
        await self.set_all_pixels_color(0, 0, 0)
        self._is_on = False

    async def set_brightness(self, brightness: int) -> None:
        """Set the brightness [0-255]"""
        brightness = min(255, max(0, int(brightness)))
        _LOGGER.debug(f"Set_brightness {brightness}")

        self._brightness = brightness
        # Re-apply current color with new brightness
        if self._is_on:
            await self.set_color(*self._rgb, brightness)

    async def set_color(self, red: int, green: int, blue: int, brightness: int | None = None) -> None:
        """Set the color of the lamp [0-255]"""
        if brightness is None:
            brightness = self._brightness

        _LOGGER.debug(f"Set_color RGB({red}, {green}, {blue}), brightness={brightness}")

        # Apply brightness scaling to RGB values
        scale = brightness / 255.0
        r = int(red * scale)
        g = int(green * scale)
        b = int(blue * scale)

        self._rgb = (red, green, blue)
        self._brightness = brightness

        # Set all pixels to this color
        await self.set_all_pixels_color(r, g, b)

    async def set_all_pixels_color(self, r: int, g: int, b: int) -> None:
        """Set all pixels to the same color"""
        _LOGGER.debug(f"Setting all {self._pixel_count} pixels to RGB({r}, {g}, {b})")

        # First set to static mode
        cmd = self._build_diy_control_cmd(diy_type=DIY_TYPE_SHOW_STATIC)
        await self.send_cmd(cmd)
        await asyncio.sleep(0.05)

        frame = 1
        # Send pixels in chunks to avoid MTU issues
        for start_idx in range(0, self._pixel_count, PIXEL_CHUNK_SIZE):
            end_idx = min(start_idx + PIXEL_CHUNK_SIZE, self._pixel_count)

            # Build list of (pixel_index, r, g, b) tuples
            pixels = [(idx, r, g, b) for idx in range(start_idx, end_idx)]

            cmd = self._build_pixel_data_cmd(frame, pixels)
            await self.send_cmd(cmd, wait_notif=CMD_DELAY_MS / 1000.0)

    async def set_pixel_color(self, pixel_index: int, r: int, g: int, b: int) -> None:
        """Set a single pixel color"""
        if pixel_index >= self._pixel_count:
            _LOGGER.warning(f"Pixel index {pixel_index} out of range (max {self._pixel_count})")
            return

        frame = 1
        pixels = [(pixel_index, r, g, b)]
        cmd = self._build_pixel_data_cmd(frame, pixels)
        await self.send_cmd(cmd)

    async def save_current_state(self) -> None:
        """Save the current DIY state to device memory"""
        _LOGGER.debug("Saving current state")
        cmd = self._build_diy_control_cmd(diy_type=DIY_TYPE_SAVE)
        await self.send_cmd(cmd)

    async def set_scene(self, scene_number: int, brightness: int | None = None) -> None:
        """
        Set a built-in scene/effect
        scene_number: Scene ID (1-50+, see SCENES dict in const.py)
        brightness: Optional brightness override (0-255), maps to 0-2550 internally
        """
        if brightness is None:
            # Use current brightness, scaled to scene range
            scene_brightness = int((self._brightness / 255.0) * SCENE_BRIGHTNESS_MAX)
        else:
            # Map 0-255 to 0-2550
            brightness = min(255, max(0, int(brightness)))
            scene_brightness = int((brightness / 255.0) * SCENE_BRIGHTNESS_MAX)

        _LOGGER.debug(f"Setting scene {scene_number} with brightness {scene_brightness}")
        cmd = self._build_set_scene_cmd(scene_number, scene_brightness)
        if await self.send_cmd(cmd):
            self._is_on = True
            if brightness is not None:
                self._brightness = brightness

    async def read_services(self) -> None:
        """Read and log all BLE services (debug)"""
        if self._client is None:
            return
        for service in self._client.services:
            _LOGGER.info(f"[Service] {service}")
            for char in service.characteristics:
                if "read" in char.properties:
                    try:
                        value = bytes(await self._client.read_gatt_char(char.uuid))
                        _LOGGER.info(
                            f"  [Characteristic] {char} ({','.join(char.properties)}), "
                            f"Value: {value.hex()}"
                        )
                    except Exception as e:
                        _LOGGER.error(
                            f"  [Characteristic] {char} ({','.join(char.properties)}), "
                            f"Value: {e}"
                        )
                else:
                    _LOGGER.info(
                        f"  [Characteristic] {char} ({','.join(char.properties)})"
                    )

                for descriptor in char.descriptors:
                    try:
                        value = bytes(
                            await self._client.read_gatt_descriptor(descriptor.handle)
                        )
                        _LOGGER.info(f"    [Descriptor] {descriptor} | Value: {value.hex()}")
                    except Exception as e:
                        _LOGGER.error(f"    [Descriptor] {descriptor} | Value: {e}")


async def find_device_by_address(
    address: str, timeout: float = 20.0
) -> BLEDevice | None:
    from bleak import BleakScanner

    return await BleakScanner.find_device_by_address(address.upper(), timeout=timeout)


async def discover_hello_fairy_lamps(
    scanner: type[BleakClient] | None = None, timeout: float = 10.0
) -> list[dict]:
    """
    Discover Hello Fairy / CN Curtain Light devices
    Returns list of dicts with 'ble_device' key
    """
    from bleak import BleakScanner

    _LOGGER.debug("Scanning for Hello Fairy / CN Curtain Light devices...")

    # Device name prefixes to look for
    device_prefixes = ["CN_The_Curtain_Light", "Hello Fairy", "BMSL"]

    discovered_lamps = []

    try:
        # Use the provided scanner class or default to BleakScanner
        scanner_class = scanner if scanner is not None else BleakScanner
        _LOGGER.debug(f"Using scanner: {scanner_class}")

        # Perform the scan
        devices = await scanner_class.discover(timeout=timeout)
        _LOGGER.debug(f"Found {len(devices)} total Bluetooth devices")

        # Filter for Hello Fairy devices
        for device in devices:
            _LOGGER.debug(f"Checking device: {device.name} ({device.address})")
            if device.name:
                for prefix in device_prefixes:
                    if device.name.startswith(prefix):
                        _LOGGER.info(f"Found Hello Fairy device: {device.name} ({device.address})")
                        discovered_lamps.append({"ble_device": device})
                        break

    except Exception as e:
        _LOGGER.error(f"Error during device discovery: {e}", exc_info=True)
        raise BleakError(f"Device discovery failed: {e}")

    _LOGGER.info(f"Discovery complete, found {len(discovered_lamps)} Hello Fairy devices")
    return discovered_lamps


if __name__ == "__main__":
    import sys

    # Bleak backends are very loud, this reduces the log spam when using --debug
    logging.getLogger("bleak.backends").setLevel(logging.WARNING)
    # Start the logger to stdout
    logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
    _LOGGER.info("LED Curtain Light BT scanning starts")

    async def test_light() -> None:
        # Replace with your device MAC address
        device = await find_device_by_address("AA:BB:CC:DD:EE:FF")
        if device is None:
            print("No device found")
            return

        lamp = Lamp(device, pixel_count=256)
        await lamp.connect()
        await asyncio.sleep(1.0)

        # Turn on with white
        await lamp.turn_on()
        await asyncio.sleep(2.0)

        # Change to red
        await lamp.set_color(red=255, green=0, blue=0)
        await asyncio.sleep(2.0)

        # Change to green
        await lamp.set_color(red=0, green=255, blue=0)
        await asyncio.sleep(2.0)

        # Change to blue
        await lamp.set_color(red=0, green=0, blue=255)
        await asyncio.sleep(2.0)

        # Dim to 50%
        await lamp.set_brightness(128)
        await asyncio.sleep(2.0)

        # Turn off
        await lamp.turn_off()
        await asyncio.sleep(1.0)

        await lamp.disconnect()

    asyncio.run(test_light())
    print("Test completed")
