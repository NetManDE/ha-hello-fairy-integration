"""Constants for the hello-fairy integration."""

DOMAIN = "hellofairy"
PLATFORM = "light"
CONF_ENTRY_METHOD = "entry_method"
CONF_ENTRY_SCAN = "Scan"
CONF_ENTRY_MANUAL = "Enter MAC manually"

# BLE UUIDs
SERVICE_UUID = "49535343-fe7d-4ae5-8fa9-9fafd205e455"
WRITE_CHAR_UUID = "49535343-8841-43f4-a8d4-ecbe34729bb3"
NOTIFY_CHAR_UUID = "49535343-1e4d-4bd9-ba61-23c647249616"
CCCD_UUID = "00002902-0000-1000-8000-00805f9b34fb"

# Protocol Constants
CMD_HEADER_A = 0xAA  # -86 in signed byte
CMD_HEADER_B = 0xBB  # -69 in signed byte

# Command Types
CMD_DIY_CONTROL = 0xD0  # -48: DIY picture control (direction, speed, type)
CMD_PIXEL_DATA = 0xDA   # -38: Set pixel colors
CMD_DYNAMIC_FRAME = 0xD7  # -41: Dynamic picture frame control
CMD_DIY_SETTINGS = 0x0E  # 14: DIY settings (brightness, speed, mode)

# DIY Control Types
DIY_TYPE_STATIC = 0
DIY_TYPE_SHOW_STATIC = 1
DIY_TYPE_DYNAMIC_RUN = 2
DIY_TYPE_STATIC_TYPE = 3
DIY_TYPE_SAVE = 4
DIY_TYPE_PREPARE = 6
DIY_TYPE_DYNAMIC = 7

# Frame States
FRAME_STATE_START = 0
FRAME_STATE_END = 2

# Device Variants
PIXEL_COUNT_BLE256 = 256
PIXEL_COUNT_BLE900 = 900
DEFAULT_PIXEL_COUNT = PIXEL_COUNT_BLE256

# Timing
CMD_DELAY_MS = 50  # Delay between commands in milliseconds
PIXEL_CHUNK_SIZE = 85  # Number of pixels to send per chunk
