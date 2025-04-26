# SPDX-FileCopyrightText: 2021 ladyada for Adafruit Industries
# SPDX-License-Identifier: MIT

import itertools
import os
import shutil
import socket
import subprocess
import sys
import time
from enum import Enum, auto
from pathlib import Path

import board
import digitalio
import psutil
from adafruit_rgb_display import st7789
from dotenv import load_dotenv
from pihole6api import PiHole6Client
from PIL import Image, ImageDraw, ImageFont

# Identify GPIO pins used on the display
CS_PIN = board.CE0  # These are FeatherWing defaults on M0/M4
DC_PIN = board.D25  # These are FeatherWing defaults on M0/M5
RESET_PIN = None
BACKLIGHT_PIN = board.D22  # Display backlight
# Swap D23 and D24 depending on how you want A and B oriented
BUTTON_A_PIN = board.D24  # Button A
BUTTON_B_PIN = board.D23  # Button B

# Config for display baudrate (default max is 24mhz):
BAUDRATE: int = 64_000_000

# # Display geometry for 135x240 display
# DISPLAY_WIDTH: int = 135
# DISPLAY_HEIGHT: int = 240
# DISPLAY_X_OFFSET: int = 53
# DISPLAY_Y_OFFSET: int = 40
# ROTATION: int = 270  # 90

# Display geometry for 240x240 display
DISPLAY_WIDTH: int = 240
DISPLAY_HEIGHT: int = 240
DISPLAY_X_OFFSET: int = 0
DISPLAY_Y_OFFSET: int = 80
ROTATION: int = 0  # 180

# Text font used in the display
#   Alternatively load a TTF font.  Make sure the .ttf font file is
#   in the same directory as the python script!
#   Some other nice fonts to try: http://www.dafont.com/bitmap.php
FONT_TYPE = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_SIZE = 16

COLOR_LIST = [
    "#FFFFFF",  # White
    "#FFFF00",  # Yellow
    "#00FF00",  # Green
    "#00FFFF",  # Cyan
    "#FF00FF",  # Magenta
    # "#0000FF",  # Blue (a bit too dark on black background)
]


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

    if (
        not PIHOLE_API_URL
        or not PIHOLE_API_TOKEN
        or PIHOLE_API_URL.strip() == ""
        or PIHOLE_API_TOKEN.strip() == ""
    ):
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


def get_cpu_load() -> str:
    # Getting load over 1, 5, and 15 minutes
    load1, load5, load15 = psutil.getloadavg()

    # cpu_usage = (load1/os.cpu_count()) * 100
    # cpu_usage = (load5/os.cpu_count()) * 100
    cpu_usage = (load15 / os.cpu_count()) * 100

    return f"CPU Usage: {cpu_usage:.2f} %"


def get_host_name() -> str:
    """Get the hostname of the system.
    This function uses the socket library to retrieve the hostname
    of the system.

    If the hostname cannot be retrieved, it is set to "Unknown".

    Returns:
        str: Formatted string with the hostname or "Unknown".
    """
    try:
        host_name = socket.gethostname()
    except Exception as e:
        host_name = "Unknown"
        print(f"Unable to get Hostname. Error: {e}")

    return f"HOST: {host_name}"


def get_host_ip() -> str:
    """Get the IP address of the system.
    This function uses the socket library to retrieve the IP address
    of the system.

    If the IP address cannot be retrieved, it is set to "Unknown".

    Returns:
        str: Formatted string with the IP address or "Unknown".
    """
    try:
        # Using a system call to "hostname -I" instead of socket.gethostbyname(host_name)
        # because it return localhost (127.0.0.1) instead of network IP address
        host_ip = (
            subprocess.check_output(["hostname", "-I"]).decode().strip().split()[0]
        )
    except Exception as e:
        host_ip = "Unknown"
        print(f"Unable to get Host IP. Error: {e}")

    return f"IP: {host_ip}"


def to_mb(val: int) -> float:
    return val / 2**20


def to_gb(val: int) -> float:
    return val / 2**30


def get_memory_usage() -> str:
    """Get the memory usage of the system.
    This function uses the psutil library to retrieve the memory
    usage of the system.
    Returns:
        str: Formatted string with the memory usage.
    """

    total = to_mb(psutil.virtual_memory()[0])
    used = to_mb(psutil.virtual_memory()[1])
    memory = psutil.virtual_memory()[2]

    return f"Mem: {used:.0f}/{total:.0f} MB {memory:.2f} %"


def get_disk_usage() -> str:
    """Get the disk usage of the system.
    This function uses the psutil library to retrieve the disk
    usage of the system.

    Returns:
        str: Formatted string with the disk usage.
    """
    current_path = os.path.abspath(os.path.dirname(__file__))
    usage = psutil.disk_usage(current_path)

    total = to_gb(usage[0])
    used = to_gb(usage[1])
    disk = usage[3]

    return f"Disk: {used:.0f}/{total:.0f} GB {disk:.2f} %"


def get_temperature() -> str:
    """Calculate the average temperature of all sensors using psutil package.

    Returns:
        float: The average temperature of all sensors in Farenheit.
    """
    if not hasattr(psutil, "sensors_temperatures"):
        sys.exit("Platform not supported")

    # Get the temperature sensors
    temps = psutil.sensors_temperatures()

    if not temps:
        sys.exit("Unable to read temperature")

    # Calculate the average temperature
    total_temp = 0.0
    count = 0
    for sensor in temps.values():
        for entry in sensor:
            total_temp += entry.current
            count += 1

    avg_temp = 0.0 if count == 0 else total_temp / count

    # Convert to Fahrenheit
    avg_temp_f = c_to_f(avg_temp)

    return f"Temp: {avg_temp_f:.2f} F"


def get_system_stats() -> dict[str, str]:
    """Gather system statistics including CPU load, memory usage,
    disk usage, and temperature.

    Returns:
        dict: Dictionary containing system statistics.
    """
    stats = {
        "IP": get_host_ip(),
        "HOST": get_host_name(),
        "CPU": get_cpu_load(),
        "Disk": get_disk_usage(),
        "CPU Temp": get_temperature(),
    }

    return stats


def get_pihole_stats(client: PiHole6Client) -> dict[str, str]:
    """Gather PiHole statistics including client count, total queries,
    blocked queries, and percentage of blocked queries.

    Args:
        client (PiHole6Client): PiHole6Client object to interact with
            the PiHole API.

    Returns:
        dict: Dictionary containing PiHole statistics.
    """
    # Gather summary stats for the PiHole
    stats_summary = client.metrics.get_stats_summary() or {}
    queries = stats_summary.get("queries", {})
    total_queries = queries.get("total", 0)
    blocked_queries = queries.get("blocked", 0)
    percent_queries = queries.get("percent_blocked", 0.0)

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
    color_list: list[str] = COLOR_LIST,
) -> None:
    """Update the display with the given statistics.
    This function draws the statistics on the display using the
    provided ImageDraw object and font.

    Args:
        draw (ImageDraw): ImageDraw object to draw on the display.
        font (ImageFont): Font to use for drawing text.
        stats (dict): Dictionary containing statistics to display.
        color_list (list): List of colors to use for drawing text.
    """
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

    # Set the color cycle for the text
    color_cycle = itertools.cycle(color_list)

    # Write four lines of text.
    y = top
    for val in stats.values():
        draw.text((x, y), val, font=font, fill=next(color_cycle))
        y += y_offset


def initialize_image(disp: st7789.ST7789) -> Image.Image:
    """Initialize the image for the display.
    This function creates a blank image with the same dimensions as the display
    and sets the mode to 'RGB' for full color.

    Args:
        disp (st7789.ST7789): The display object to get the dimensions from.

    Returns:
        Image.Image: A blank image with the same dimensions as the display.
    """
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
    """Get the button press states for button A and button B.
    The buttons are active low, so when pressed, the value is False.
    The function returns the state of the buttons as an enum.

    Args:
        buttonA (digitalio.DigitalInOut): _description_
        buttonB (digitalio.DigitalInOut): _description_

    Returns:
        ButtonState: Can be ONLY_A, ONLY_B, BOTH, or NONE
    """
    # Button values are True when not pressed
    pressed_A = not buttonA.value
    pressed_B = not buttonB.value

    # Return the state of the button presses:
    if pressed_A and not pressed_B:  # just button A pressed
        return ButtonState.ONLY_A
    if pressed_B and not pressed_A:  # just button B pressed
        return ButtonState.ONLY_B
    if pressed_A and pressed_B:  # both buttons pressed
        return ButtonState.BOTH

    return ButtonState.NONE


def main():
    """
    Main function to initialize hardware components, establish a connection
    to the PiHole API, and handle button interactions to display system or
    PiHole statistics on the screen.
    """

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
    try:
        font = ImageFont.truetype(FONT_TYPE, FONT_SIZE)
    except Exception as e:
        print(f"Error loading font '{FONT_TYPE}': {e}")
        print("Ensure the font file exists and is not corrupted.")
        exit(1)
    font = ImageFont.truetype(FONT_TYPE, FONT_SIZE)

    try:
        while True:
            # Turn off backlight and draw a black filled box to clear the image.
            backlight.value = False  # turn off backlight
            draw.rectangle((0, 0, disp.width, disp.height), outline=0, fill=0)

            stats_dict = {}

            # Match the current button states and perform corresponding actions
            match get_button_states(buttonA, buttonB):
                case ButtonState.ONLY_A:
                    # Button A is pressed: Display system statistics
                    print("Button A pressed")
                    backlight.value = True  # turn on backlight
                    stats_dict = get_system_stats()

                case ButtonState.ONLY_B:
                    # Button B is pressed: Display PiHole statistics
                    print("Button B pressed")
                    backlight.value = True  # turn on backlight
                    stats_dict = get_pihole_stats(client)

                case ButtonState.BOTH:
                    # Both buttons A and B are pressed: No specific action defined
                    print("Buttons A and B pressed")

                case ButtonState.NONE:
                    # No buttons are pressed: Do nothing
                    # print("No buttons pressed")
                    pass

            update_frame_text(draw, font, stats_dict, COLOR_LIST)

            # Display image.
            disp.image(image, ROTATION)
            time.sleep(0.05)

    except KeyboardInterrupt:
        print(f"\nExiting {__file__}\n")

    except Exception as e:
        print(f"An error occurred: {e}")
        print("Exiting the program due to an unexpected error.")
        raise

    finally:
        # Turn off the backlight when Ctrl-C is pressed
        backlight.value = False

        # Clean up GPIO pins
        buttonA.deinit()
        buttonB.deinit()
        backlight.deinit()

        # Reset the display object
        disp.fill(0)  # Clear the display


if __name__ == "__main__":
    main()
