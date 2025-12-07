# Bluetooth Protocol Documentation for Home Assistant Integration
**Application:** com.hsr.sslight (LED Light Control App)
**Device Names:** CN_The_Curtain_Light_BLE256, CN_The_Curtain_Light_BLE900

## BLE Service & Characteristic UUIDs

### Primary Service
```
Service UUID: 49535343-fe7d-4ae5-8fa9-9fafd205e455
```

### Characteristics
```
Write Characteristic:  49535343-8841-43f4-a8d4-ecbe34729bb3
Notify Characteristic: 49535343-1e4d-4bd9-ba61-23c647249616
CCCD UUID (for notifications): 00002902-0000-1000-8000-00805f9b34fb
```

## Protocol Structure

### Command Frame Format (Type A - Header 0xAA)
```
[0xAA] [CMD_TYPE] [PAYLOAD...] [CHECKSUM]
```

### Command Frame Format (Type B - Header 0xBB)
```
[0xBB] [CMD_TYPE] [LENGTH] [PAYLOAD...] [CHECKSUM]
```

### Checksum Calculation
```python
def calculate_checksum(data):
    """
    Calculate checksum for command packet
    Sum all bytes and modulo 256
    """
    checksum = sum(data) % 256
    return checksum & 0xFF
```

## Common Command Types

### 1. DIY Picture/Animation Control (0xD0 / -48)
**Command Class:** `w2`
**Purpose:** Set DIY picture parameters (direction, speed, type)

**Structure:**
```
[0xAA] [0xD0] [direction] [speed_default] [speed] [type] [checksum]
```

**Parameters:**
- `direction`: Animation direction (0-255)
- `speed_default`: Default speed value
- `speed`: Current speed (0-255)
- `type`: DIY mode type
  - 0: Static
  - 1: Show static DIY picture
  - 2: Dynamic run
  - 3: Static type
  - 4: Save DIY picture
  - 6: Prepare mode
  - 7: Dynamic picture mode

**Alternative Structure (for specific modes):**
```
[0xAA] [0xD0] [param1] [param2] [param3] [checksum]
```

**Example (Set static DIY mode):**
```python
cmd = [0xAA, 0xD0, 0x00, 0x64, 0x00, 0x01]  # direction=0, speed=100, type=1 (static)
cmd.append(calculate_checksum(cmd))
# Result: [0xAA, 0xD0, 0x00, 0x64, 0x00, 0x01, 0x1F]
```

### 2. Set DIY Pixel Data (0xDA / -38)
**Command Class:** `y2`
**Purpose:** Set individual pixel/LED colors

**Structure:**
```
[0xAA] [0xDA] [frame_number] [pixel_index_1] [color_1_RGB] [pixel_index_2] [color_2_RGB] ... [checksum]
```

**Parameters:**
- `frame_number`: Frame/scene number (1-based)
- `pixel_index`: LED pixel index (2 bytes, little-endian)
- `color_RGB`: 24-bit RGB color (3 bytes: R, G, B)

**Example (Set pixel 0 to red, pixel 1 to blue):**
```python
# Frame 1, Pixel 0 = Red (0xFF0000), Pixel 1 = Blue (0x0000FF)
cmd = [0xAA, 0xDA, 0x01]  # Frame 1
# Pixel 0 index (little-endian)
cmd.extend([0x00, 0x00])  # index = 0
# Pixel 0 color (RGB)
cmd.extend([0xFF, 0x00, 0x00])  # Red
# Pixel 1 index
cmd.extend([0x01, 0x00])  # index = 1
# Pixel 1 color
cmd.extend([0x00, 0x00, 0xFF])  # Blue
cmd.append(calculate_checksum(cmd))
# Result: [0xAA, 0xDA, 0x01, 0x00, 0x00, 0xFF, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0xFF, checksum]
```

### 3. Set Dynamic Picture Frame (0xD7 / -41)
**Command Class:** `c3`
**Purpose:** Control multi-frame animations

**Structure:**
```
[0xAA] [0xD7] [frame_number] [state] [checksum]
```

**Parameters:**
- `frame_number`: Frame index (1-based)
- `state`: Frame state
  - 0: Start frame
  - 2: End frame

**Example (Start frame 1):**
```python
cmd = [0xAA, 0xD7, 0x01, 0x00]  # Frame 1, state=start
cmd.append(calculate_checksum(cmd))
```

### 4. Set DIY Settings (0x0E / 14)
**Command Class:** `h2`
**Purpose:** Configure DIY mode settings (brightness, speed, etc.)

**Structure:**
```
[0xAA] [0x0E] [number] [0x01] [speed] [brightness] [changing_mode] [enabled_status] [checksum]
```

**Parameters:**
- `number`: DIY scene number
- `speed`: Animation speed (0-255)
- `brightness`: Brightness level (0-255)
- `changing_mode`: Color changing mode
- `enabled_status`: Enable/disable status

**Example (Set DIY brightness to 128):**
```python
cmd = [0xAA, 0x0E, 0x01, 0x01, 0x64, 0x80, 0x00, 0x01]  # brightness=128
cmd.append(calculate_checksum(cmd))
```

### 5. Music Mode (with brightness and HSV)
**Command Class:** `s1`
**Purpose:** Control music-reactive mode

**Structure:**
```
[0xAA] [CMD_TYPE] [mode] [auto] [sensitivity] [brightness] [hue] [saturation] [checksum]
```

**Parameters:**
- `mode`: Music mode type (0-255)
- `auto`: Auto mode (0=off, 1=on)
- `sensitivity`: Sound sensitivity (0-255)
- `brightness`: Brightness level (0-255)
- `hue`: Hue value (0-360)
- `saturation`: Saturation value (0-100)

## MTU Size and Data Chunking

**Maximum Transmission Unit (MTU):** The app uses adaptive MTU sizing
- Default MTU appears to be variable based on negotiation
- Commands are chunked based on: `sendMaxCount = (MTU_SIZE - 1) / 3`
- For pixel data, chunks are sent sequentially with delays

## Sending Commands via BLE

### Python Example using `bleak`

```python
import asyncio
from bleak import BleakClient, BleakScanner

SERVICE_UUID = "49535343-fe7d-4ae5-8fa9-9fafd205e455"
WRITE_CHAR_UUID = "49535343-8841-43f4-a8d4-ecbe34729bb3"
NOTIFY_CHAR_UUID = "49535343-1e4d-4bd9-ba61-23c647249616"

def calculate_checksum(data):
    return sum(data) % 256

async def send_command(client, command_bytes):
    """Send command to BLE device"""
    await client.write_gatt_char(WRITE_CHAR_UUID, bytearray(command_bytes))

async def set_static_mode(client):
    """Set device to static DIY mode"""
    cmd = [0xAA, 0xD0, 0x00, 0x64, 0x00, 0x01]
    cmd.append(calculate_checksum(cmd))
    await send_command(client, cmd)

async def set_pixel_color(client, frame, pixel_index, r, g, b):
    """Set a single pixel color"""
    cmd = [0xAA, 0xDA, frame]
    # Pixel index (little-endian, 2 bytes)
    cmd.extend([pixel_index & 0xFF, (pixel_index >> 8) & 0xFF])
    # RGB color
    cmd.extend([r, g, b])
    cmd.append(calculate_checksum(cmd))
    await send_command(client, cmd)

async def set_all_pixels_color(client, r, g, b, pixel_count=256):
    """Set all pixels to same color"""
    # First set to static mode
    await set_static_mode(client)
    await asyncio.sleep(0.1)

    # Send pixels in chunks
    frame = 1
    chunk_size = 85  # Adjust based on MTU

    for start_idx in range(0, pixel_count, chunk_size):
        end_idx = min(start_idx + chunk_size, pixel_count)

        cmd = [0xAA, 0xDA, frame]
        for pixel_idx in range(start_idx, end_idx):
            cmd.extend([pixel_idx & 0xFF, (pixel_idx >> 8) & 0xFF])
            cmd.extend([r, g, b])

        cmd.append(calculate_checksum(cmd))
        await send_command(client, cmd)
        await asyncio.sleep(0.05)  # Small delay between chunks

async def main():
    # Find device
    devices = await BleakScanner.discover()
    led_device = None
    for device in devices:
        if "CN_The_Curtain_Light" in device.name:
            led_device = device
            break

    if not led_device:
        print("Device not found")
        return

    # Connect and send commands
    async with BleakClient(led_device.address) as client:
        # Enable notifications
        await client.start_notify(NOTIFY_CHAR_UUID, lambda s, d: print(f"Notify: {d.hex()}"))

        # Set all LEDs to red
        await set_all_pixels_color(client, 255, 0, 0, pixel_count=256)

        await asyncio.sleep(2)

if __name__ == "__main__":
    asyncio.run(main())
```

## Home Assistant Integration Example

### Custom Component Structure

```yaml
# configuration.yaml
light:
  - platform: cn_curtain_light
    name: "LED Curtain Light"
    mac: "AA:BB:CC:DD:EE:FF"
    pixel_count: 256
```

### Key Functions to Implement

1. **Power On/Off**: Send static mode command (0xD0 with type=1) or clear all pixels
2. **Brightness Control**: Use SetDIY command (0x0E) with brightness parameter
3. **Color Control**: Use pixel data command (0xDA) to set colors
4. **Effects**: Use dynamic mode commands with different frame sequences
5. **Music Mode**: Use music mode command with sensitivity and color parameters

## Additional Command Types Discovered

Based on the decompiled source, here are additional command type bytes:

```
0x00, 0x01, 0x02, 0x03, 0x04, 0x05
0x0A (10), 0x0B (11), 0x0C (12), 0x0D (13), 0x0E (14), 0x0F (15)
0x11 (17), 0x12 (18), 0x13 (19)
0x14 (20), 0x15 (21), 0x16 (22), 0x17 (23), 0x18 (24), 0x19 (25)
0x20 (32), 0x30 (48), 0x31 (49), 0x32 (50)
0xD0 (-48), 0xD1 (-47), 0xD2 (-46), 0xD4 (-44), 0xD5 (-45)
0xD6 (-42), 0xD7 (-41), 0xD8 (-40), 0xD9 (-39)
0xDA (-38), 0xDB (-37), 0xDC (-36), 0xDD (-35)
0xE0 (-32), 0xCE (-50)
```

## Notes for Implementation

1. **Connection Sequence:**
   - Scan for device by name prefix "CN_The_Curtain_Light"
   - Connect to GATT service
   - Enable notifications on notify characteristic
   - Wait for device info response before sending commands

2. **Command Timing:**
   - Add 50-100ms delay between pixel data commands
   - Add 10ms delay after mode change commands
   - Use command queuing to avoid overwhelming the device

3. **Error Handling:**
   - Checksum errors will be rejected by device
   - Monitor notify characteristic for error responses
   - Implement retry logic for failed commands

4. **Device Variants:**
   - BLE256: 256 addressable pixels
   - BLE900: 900 addressable pixels
   - Adjust pixel_count parameter accordingly

## Testing Commands

Use a BLE testing app (like nRF Connect) to test:

1. Turn on (static white):
   - `AA D0 00 64 00 01 [checksum]`
   - `AA DA 01 00 00 FF FF FF [checksum]` (set first pixel white)

2. Turn red:
   - `AA DA 01 00 00 FF 00 00 [checksum]`

3. Save current state:
   - `AA D0 00 64 00 04 [checksum]`

---

**Generated from APK analysis of com.hsr.sslight v3.3.2**
