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
CMD_SET_LIGHT = 0x03     # 3: Set light mode (HSV, Scene, Music, Warm White)
CMD_DIY_CONTROL = 0xD0  # -48: DIY picture control (direction, speed, type)
CMD_PIXEL_DATA = 0xDA   # -38: Set pixel colors
CMD_DYNAMIC_FRAME = 0xD7  # -41: Dynamic picture frame control
CMD_DIY_SETTINGS = 0x0E  # 14: DIY settings (brightness, speed, mode)

# Set Light Mode Types
LIGHT_MODE_WARM_WHITE = 0
LIGHT_MODE_HSV = 1
LIGHT_MODE_SCENE = 2
LIGHT_MODE_MUSIC = 3

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
CMD_DELAY_MS = 150  # Delay between commands in milliseconds (increased for device processing)
PIXEL_CHUNK_SIZE = 15  # Number of pixels to send per chunk (reduced to fit BLE MTU safely ~80 bytes)

# Built-in Scene IDs
SCENES = {
    # Basic Scenes
    "landscape_tree": 1,
    "christmas_tree": 2,
    "fence": 3,
    "tv": 4,
    "photo_album": 5,
    "donut": 6,
    "hang": 7,
    "car": 8,
    "house": 9,
    "car_inside": 10,
    "car_outside": 11,

    # Category Scenes (these are category IDs, actual scenes may vary)
    "christmas": 14,
    "halloween": 15,
    "easter": 16,
    "valentines": 17,
    "thanksgiving": 18,
    "four_leaf_clover": 19,
    "national_flag": 20,
    "carnival": 21,
    "ramadan": 22,
    "parent": 23,
    "animal": 24,
    "science": 25,
    "fireworks": 26,
    "shop": 27,
    "tree_pattern": 28,
    "picture": 29,
    "tree_top_star": 30,
}

# Scene brightness range (0-2550, mapped to 0-255 internally)
SCENE_BRIGHTNESS_MAX = 2550
