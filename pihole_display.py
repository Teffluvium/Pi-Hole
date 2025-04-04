# SPDX-FileCopyrightText: 2021 ladyada for Adafruit Industries
# SPDX-License-Identifier: MIT

import itertools
import os
import shutil
import subprocess
import time
from enum import Enum, auto
from pathlib import Path

import board
import digitalio
from adafruit_rgb_display import st7789
from dotenv import load_dotenv
from pihole6api import PiHole6Client
from PIL import Image, ImageDraw, ImageFont

# Identify GPIO pins used on the display
CS_PIN = board.CE0  # These are FeatherWing defaults on M0/M4
DC_PIN = board.D25  # These are FeatherWing defaults on M0/M4
RESET_PIN = None
BACKLIGHT_PIN = board.D22  # Display backlight
BUTTON_A_PIN = board.D23  # Button A
BUTTON_B_PIN = board.D24  # Button B

# Config for display baudrate (default max is 24mhz):
BAUDRATE = 64_000_000

# # Display geometry for 135x240 display
# DISPLAY_WIDTH = 135
# DISPLAY_HEIGHT = 240
# DISPLAY_X_OFFSET = 53
# DISPLAY_Y_OFFSET = 40
# ROTATION = 270  # 90

# Display geometry for 240x240 display
DISPLAY_WIDTH = 240
DISPLAY_HEIGHT = 240
DISPLAY_X_OFFSET = 0
DISPLAY_Y_OFFSET = 80
ROTATION = 0  # 180

# Text font used in the display
#   Alternatively load a TTF font.  Make sure the .ttf font file is
#   in the same directory as the python script!
#   Some other nice fonts to try: http://www.dafont.com/bitmap.php
FONT_TYPE = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_SIZE = 16


def get_api_info_from_env() -> tuple[str, str]:
    """Retrieve the API URL and Token from a local .env file.  If the
    .env file cannot be located, a new file is created from env_template.
    """
    env_template_file = Path("env_template")
    env_file = Path(".env")
    if not env_file.exists():
        shutil.copy2(str(env_template_file), str(env_file))
        print(f"A new environment file '{env_file.absolute()}' has been created.")
        print(
            "Update PIHOLE_API_URL and PIHOLE_API_TOKEN "
            "in the file and re-run the application."
        )
        exit()

    load_dotenv(override=True)
    PIHOLE_API_URL = os.getenv("PIHOLE_API_URL")
    PIHOLE_API_TOKEN = os.getenv("PIHOLE_API_TOKEN")

    if not PIHOLE_API_URL or not PIHOLE_API_TOKEN:
        print("The API_TOKEN could not be found in the environment variables.")
        exit()

    return PIHOLE_API_URL, PIHOLE_API_TOKEN


def initialize_display() -> digitalio.DigitalInOut:
    # Setup SPI bus using hardware SPI:
    spi = board.SPI()

    # Create the ST7789 display:
    disp = st7789.ST7789(
        spi,
        cs=digitalio.DigitalInOut(CS_PIN),
        dc=digitalio.DigitalInOut(DC_PIN),
        rst=RESET_PIN,
        baudrate=BAUDRATE,
        width=DISPLAY_WIDTH,
        height=DISPLAY_HEIGHT,
        x_offset=DISPLAY_X_OFFSET,
        y_offset=DISPLAY_Y_OFFSET,
    )

    return disp


def initialize_backlight() -> digitalio.DigitalInOut:
    # Turn on the backlight
    backlight = digitalio.DigitalInOut(BACKLIGHT_PIN)
    backlight.switch_to_output()
    backlight.value = False

    return backlight


def initialize_buttons() -> tuple[digitalio.DigitalInOut, digitalio.DigitalInOut]:
    # Setup of buttons A and B
    buttonA = digitalio.DigitalInOut(BUTTON_A_PIN)
    buttonB = digitalio.DigitalInOut(BUTTON_B_PIN)
    buttonA.switch_to_input()
    buttonB.switch_to_input()

    return buttonA, buttonB


def c_to_f(temp: float) -> float:
    # Convert Celcius to Fahrenheit
    return (temp * 9 / 5) + 32


def get_system_stats() -> dict[str, str]:
    # CLI commands to get system information
    cmd = {
        "IP": "hostname -I | cut -d' ' -f1",
        "HOST": "hostname | tr -d '\\n'",
        "CPU": "top -bn1 | grep load | awk '{printf \"CPU Load: %.2f\", $(NF-2)}'",
        "MemUsage": [
            "free -m | awk 'NR==2{printf \"Mem: %s/%s MB  %.2f%%\", $3,$2,$3*100/$2 }'",
        ],
        "Disk": 'df -h | awk \'$NF=="/"{printf "Disk: %d/%d GB  %s", $3,$2,$5}\'',
        "Temp": [
            "cat /sys/class/thermal/thermal_zone0/temp | "
            "awk '{printf \"%.5f\", $(NF-0) / 1000}'",
        ],
    }

    # Gather the system information
    stats = {
        k: subprocess.check_output(v, shell=True).decode("utf-8")
        for k, v in cmd.items()
    }

    # Add labels to some fields
    stats["IP"] = f"IP: {stats.get('IP').strip()}"
    stats["HOST"] = f"HOST: {stats.get('HOST').strip()}"

    # Convert the temperature to Fahrenheit
    stats["Temp"] = f"CPU Temp: {c_to_f(float(stats.get('Temp'))):.1f} F"

    return stats


def get_pihole_stats(client: PiHole6Client) -> dict[str, str]:
    # Gather summary stats for the PiHole
    stats_summary = client.metrics.get_stats_summary()
    total_queries = stats_summary.get("queries").get("total")
    blocked_queries = stats_summary.get("queries").get("blocked")
    percent_queries = stats_summary.get("queries").get("percent_blocked")

    # Get current list of clients served by PiHole
    client_dict = client.client_management.get_clients()
    client_list = client_dict.get("clients")

    stats = {
        "Client Count": f"Number of Clients: {len(client_list):}",
        "Total Queries": f"Total Queries: {total_queries:,}",
        "Blocked Queries": f"Blocked Queries: {blocked_queries:,}",
        "Percent Blocked": f"Percent Blocked: {percent_queries:.1f}%",
    }

    return stats


def update_frame_text(
    draw: ImageDraw,
    font: ImageFont.FreeTypeFont,
    stats: dict[str, str],
) -> None:
    # First define some constants to allow easy resizing of shapes.
    padding = -2
    top = padding
    # Move left to right keeping track of the current x position for drawing shapes.
    x = 5

    # Determine the vertical text separation for this font
    text = "Temp Text"
    bbox = draw.textbbox((0, 0), text, font=font)
    # text_width = bbox[2] - bbox[0]
    y_offset = bbox[3] - bbox[1]
    y_offset += 7

    color_list = [
        "#FFFFFF",  # White
        "#FFFF00",  # Yellow
        "#00FF00",  # Green
        "#00FFFF",  # Cyan
        "#FF00FF",  # Magenta
        # "#0000FF",  # Blue (a bit too dark on black background)
    ]
    color_cycle = itertools.cycle(color_list)

    # Write four lines of text.
    y = top
    for val in stats.values():
        draw.text((x, y), val, font=font, fill=next(color_cycle))
        y += y_offset


def initialize_image(disp: st7789.ST7789) -> Image.Image:
    # Create blank image for drawing.
    # Make sure to create image with mode 'RGB' for full color.
    height = disp.width  # we swap height/width to rotate it to landscape!
    width = disp.height
    image = Image.new("RGB", (width, height))

    return image


class ButtonState(Enum):
    ONLY_A = auto()
    ONLY_B = auto()
    BOTH = auto()
    NONE = auto()


def get_button_states(
    buttonA: digitalio.DigitalInOut, buttonB: digitalio.DigitalInOut
) -> ButtonState:
    # Return the state of the button presses:
    if buttonA.value and not buttonB.value:  # just button A pressed
        return ButtonState.ONLY_A
    if buttonB.value and not buttonA.value:  # just button B pressed
        return ButtonState.ONLY_B
    if buttonA.value or buttonB.value:  # no buttons pressed
        return ButtonState.NONE
    if not buttonA.value and not buttonB.value:
        return ButtonState.BOTH


def main():
    # Establish a connection to the PiHole API
    api_url, api_token = get_api_info_from_env()
    client = PiHole6Client(api_url, api_token)

    # Initialize the hardware
    disp = initialize_display()
    (buttonA, buttonB) = initialize_buttons()
    image = initialize_image(disp)
    backlight = initialize_backlight()

    # Get drawing object to draw on image.
    draw = ImageDraw.Draw(image)

    # Initialize the font
    font = ImageFont.truetype(FONT_TYPE, FONT_SIZE)

    try:
        while True:
            # Turn off backlight and draw a black filled box to clear the image.
            backlight.value = False  # turn off backlight
            draw.rectangle((0, 0, disp.width, disp.height), outline=0, fill=0)

            stats_dict = {}
            match get_button_states(buttonA, buttonB):
                case ButtonState.ONLY_A:
                    print("Button A pressed")
                    backlight.value = True  # turn on backlight
                    stats_dict = get_system_stats()

                case ButtonState.ONLY_B:
                    print("Button B pressed")
                    backlight.value = True  # turn on backlight
                    stats_dict = get_pihole_stats(client)

                case ButtonState.BOTH:
                    print("Buttons A and B pressed")

                case ButtonState.NONE:
                    # print("No buttons pressed")
                    pass

            update_frame_text(draw, font, stats_dict)

            # Display image.
            disp.image(image, ROTATION)
            time.sleep(0.05)

    except KeyboardInterrupt:
        print()
        print(f"Exiting {__file__}")
        print()
        # Turn off the backlight when Ctrl-C is pressed
        backlight.value = False

    except Exception as e:
        # Turn off the backlight before exiting
        backlight.value = False
        print(e)


if __name__ == "__main__":
    main()
