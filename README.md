# Hello Fairy / CN Curtain Light - Home Assistant Integration

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)

Home Assistant integration for Hello Fairy and CN Curtain Light Bluetooth LED devices.

## Supported Devices

- **CN_The_Curtain_Light_BLE256** (256 addressable LEDs)
- **CN_The_Curtain_Light_BLE900** (900 addressable LEDs)
- **Hello Fairy** devices

## Features

✅ **Power Control** - Turn lights on/off
✅ **Brightness Control** - 0-255 brightness levels
✅ **RGB Color Control** - Full RGB color support
✅ **Built-in Scene Effects** - 30+ pre-programmed effects (Christmas, Fireworks, Halloween, etc.)
✅ **Pixel Addressability** - Individual pixel control (256 or 900 pixels)
✅ **Local Bluetooth** - No cloud required
✅ **Fast Response** - Direct BLE communication

## Installation

### HACS (Recommended)

1. Open HACS in Home Assistant
2. Go to "Integrations"
3. Click the three dots in the top right corner
4. Select "Custom repositories"
5. Add this repository URL: `https://github.com/NetManDE/ha-hello-fairy-integration`
6. Select "Integration" as the category
7. Click "Add"
8. Find "Hello Fairy LED Curtain Light" in the list and install it
9. Restart Home Assistant

### Manual Installation

1. Copy the `custom_components/hellofairy` directory to your Home Assistant's `custom_components` directory
2. Restart Home Assistant

## Configuration

### Prerequisites

- **Bluetooth Adapter**: Your Home Assistant instance must have a Bluetooth adapter
- **Bluetooth Integration**: The Home Assistant Bluetooth integration must be enabled
- **ESPHome Bluetooth Proxy** (optional but recommended): For extended range, set up an ESPHome device as a Bluetooth proxy

### Setup

1. Go to **Settings** → **Devices & Services**
2. Click **+ Add Integration**
3. Search for **"Hello Fairy"**
4. The integration will automatically discover nearby devices
5. Select your device from the list (or enter MAC address manually)
6. Click **Submit**

Your LED curtain light will appear as a new light entity!

## Usage

### Basic Control

```yaml
# Turn on with white color
service: light.turn_on
target:
  entity_id: light.curtain_light
data:
  brightness: 255

# Set to red color
service: light.turn_on
target:
  entity_id: light.curtain_light
data:
  rgb_color: [255, 0, 0]
  brightness: 200

# Turn off
service: light.turn_off
target:
  entity_id: light.curtain_light
```

### Scene Effects

The integration supports 30+ built-in scene effects from the original app:

```yaml
# Christmas Tree effect
service: light.turn_on
target:
  entity_id: light.curtain_light
data:
  effect: christmas_tree
  brightness: 255

# Fireworks effect
service: light.turn_on
target:
  entity_id: light.curtain_light
data:
  effect: fireworks
  brightness: 200

# Halloween effect
service: light.turn_on
target:
  entity_id: light.curtain_light
data:
  effect: halloween
  brightness: 255

# Turn off effect (return to color mode)
service: light.turn_on
target:
  entity_id: light.curtain_light
data:
  effect: none
  rgb_color: [255, 255, 255]
```

**Available Effects:**
- `christmas_tree`, `christmas` - Christmas themed patterns
- `halloween` - Halloween themed patterns
- `fireworks` - Fireworks animations
- `easter` - Easter themed patterns
- `valentines` - Valentine's Day patterns
- `carnival` - Carnival/party patterns
- `thanksgiving` - Thanksgiving patterns
- `landscape_tree`, `fence`, `house` - Nature/building patterns
- `car`, `tv`, `donut` - Object patterns
- `animal` - Animal themed patterns
- `science` - Science themed patterns
- And many more! (See `SCENES` in `const.py` for full list)

### Automation Example

```yaml
automation:
  - alias: "Sunset Lights"
    trigger:
      - platform: sun
        event: sunset
    action:
      - service: light.turn_on
        target:
          entity_id: light.curtain_light
        data:
          rgb_color: [255, 100, 50]
          brightness: 180
```

## Technical Details

### Bluetooth Protocol

The integration uses Bluetooth Low Energy (BLE) with the following characteristics:

- **Service UUID**: `49535343-fe7d-4ae5-8fa9-9fafd205e455`
- **Write Characteristic**: `49535343-8841-43f4-a8d4-ecbe34729bb3`
- **Notify Characteristic**: `49535343-1e4d-4bd9-ba61-23c647249616`

### Command Structure

Commands follow this format:
```
[Header] [Command Type] [Payload...] [Checksum]
```

Example commands:
- **Turn On (Static Mode)**: `AA D0 00 64 00 01 [checksum]`
- **Set Pixel Color**: `AA DA 01 [pixel_index_low] [pixel_index_high] [R] [G] [B] [checksum]`

For detailed protocol documentation, see the [BLUETOOTH_PROTOCOL_DOCUMENTATION.md](../apk/BLUETOOTH_PROTOCOL_DOCUMENTATION.md) file.

### Pixel Count Detection

The integration automatically detects whether you have:
- BLE256 variant (256 pixels) - default
- BLE900 variant (900 pixels)

The device variant is determined from the Bluetooth device name.

## Troubleshooting

### Device Not Found

**Problem**: Integration cannot find your device

**Solutions**:
1. Ensure your device is powered on and within Bluetooth range
2. Check that the Home Assistant Bluetooth integration is enabled
3. Try setting up an ESPHome Bluetooth Proxy for extended range
4. Manually enter the MAC address if auto-discovery fails

To find your device's MAC address:
1. Use the Home Assistant Bluetooth integration debug logs
2. Or use a Bluetooth scanning app on your phone (e.g., nRF Connect)

### Connection Issues

**Problem**: Device connects but doesn't respond

**Solutions**:
1. Restart Home Assistant
2. Power cycle the LED device
3. Check Bluetooth adapter compatibility
4. Review Home Assistant logs for BLE errors: **Settings** → **System** → **Logs**

### Brightness/Color Not Changing

**Problem**: Commands are sent but lights don't change

**Solutions**:
1. Ensure the device is on (turn on first, then set color/brightness)
2. Check if the device is in the correct mode (should be in DIY/static mode)
3. Reduce command frequency - the device needs time to process each command
4. Check Bluetooth signal strength

## Development

### Testing the Protocol

You can test the Bluetooth protocol directly using the standalone script:

```bash
cd custom_components/hellofairy
python3 hello_fairy.py
```

Edit the `test_light()` function to use your device's MAC address.

### Debug Logging

Enable debug logging for detailed information:

```yaml
# configuration.yaml
logger:
  default: info
  logs:
    custom_components.hellofairy: debug
```

### Protocol Analysis

This integration was reverse-engineered from the official Android app (com.hsr.sslight v3.3.2). The complete protocol documentation with all discovered commands is available in the repository.

## Credits

- **Original Integration**: Based on [ha-hello-fairy-integration](https://github.com/Alwinator/ha-hello-fairy-integration) by @Alwinator
- **Protocol Reverse Engineering**: @NetManDE
- **Device**: CN Curtain Light / Hello Fairy LED systems

## License

MIT License - See LICENSE file for details

## Support

For issues, questions, or feature requests:
- Open an issue on [GitHub](https://github.com/NetManDE/ha-hello-fairy-integration/issues)
- Check existing issues for similar problems
- Include Home Assistant logs when reporting bugs

## Changelog

### Version 1.0.1-DEV-2 (2025-12-07)
- ✨ Complete protocol rewrite based on APK reverse engineering
- ✨ Support for CN_The_Curtain_Light_BLE256 and BLE900 devices
- ✨ Proper pixel addressing (256/900 addressable pixels)
- ✨ **Built-in scene effects support** - 30+ pre-programmed effects (Christmas, Fireworks, Halloween, etc.)
- ✨ Improved color and brightness control with proper scaling
- ✨ Fixed Bluetooth command structure and checksums
- ✨ Better error handling and logging
- ✨ Comprehensive protocol documentation

### Version 1.0.0
- Initial release
- Basic Hello Fairy support
