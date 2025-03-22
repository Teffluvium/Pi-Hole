# SPDX-FileCopyrightText: 2021 ladyada for Adafruit Industries
# SPDX-License-Identifier: MIT

import json
import subprocess
import time

import board
import digitalio
import requests
from adafruit_rgb_display import st7789
from pihole6api import PiHole6Client
from PIL import Image, ImageDraw, ImageFont

API_URL = "http://localhost"
API_TOKEN = "2A+EambjgEiPTnfo1nodZ5nagEBm++MHXFVQZKMl8vE="

# Configuration for CS and DC pins (these are FeatherWing defaults on M0/M4):
CS_PIN = digitalio.DigitalInOut(board.CE0)
DC_PIN = digitalio.DigitalInOut(board.D25)
RESET_PIN = None

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
ROTATION = 180  # 0


# Image frame
FONT_TYPE = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_SIZE = 16


def initialize_display():
    # Setup SPI bus using hardware SPI:
    spi = board.SPI()

    # Create the ST7789 display:
    disp = st7789.ST7789(
        spi,
        cs=CS_PIN,
        dc=DC_PIN,
        rst=RESET_PIN,
        baudrate=BAUDRATE,
        width=DISPLAY_WIDTH,
        height=DISPLAY_HEIGHT,
        x_offset=DISPLAY_X_OFFSET,
        y_offset=DISPLAY_Y_OFFSET,
    )

    return disp


def c_to_f(temp: float):
    # Convert Celcius to Fahrenheit
    return (temp * 9 / 5) + 32


def get_stats():
    # CLI commands to get system information
    cmd = {
        "IP": "hostname -I | cut -d' ' -f1",
        "HOST": "hostname | tr -d '\\n'",
        "CPU": "top -bn1 | " "grep load | awk '{printf \"CPU Load: %.2f\", $(NF-2)}'",
        "MemUsage": [
            "free -m | "
            "awk 'NR==2{printf \"Mem: %s/%s MB  %.2f%%\", $3,$2,$3*100/$2 }'",
        ],
        "Disk": "df -h | " 'awk \'$NF=="/"{printf "Disk: %d/%d GB  %s", $3,$2,$5}\'',
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

    # Update fields with extra info
    stats["IP"] = f'IP: {stats.get("IP").strip()}'
    stats["HOST"] = f'HOST: {stats.get("HOST").strip()}'
    # stats["Temp"] = f'CPU Temp: {float(stats.get("Temp")):.1f} C' # Display Celcius
    stats["Temp"] = (
        f'CPU Temp: {c_to_f(float(stats.get("Temp"))):.1f} F'  # Display Fahrenheit
    )

    # _ = [print(s) for s in stats.values()]
    # print()

    return stats

def get_pihole_stats(client):
    # # Pi Hole API data!
    # r = requests.get(API_URL)
    # data = json.loads(r.text)
    # _ = [print(f"{k}: {v}") for k,v in data.items()]
    # print()
    # #DNSQUERIES = data['dns_queries_today']
    # #ADSBLOCKED = data['ads_blocked_today']
    # #CLIENTS = data['unique_clients']

    current_time = int(time.time())
    twenty_four_hours_ago = current_time - (24 * 3600)

    print(f"Current Unix timestamp:      {current_time}")
    print(f"Unix timestamp 24 hours ago: {twenty_four_hours_ago}")

    pass


def update_frame_text(draw, font, stats, x, top):
    # Determine the vertical text separation for this font
    text = "Temp Text"
    bbox = draw.textbbox((0, 0), text, font=font)
    # text_width = bbox[2] - bbox[0]
    y_offset = bbox[3] - bbox[1]
    y_offset += 7

    # Write four lines of text.
    y = top
    # draw.text((x, y), IP, font=font, fill="#FFFFFF")
    draw.text((x, y), stats.get("IP"), font=font, fill="#FFFFFF")
    y += y_offset
    draw.text((x, y), stats.get("CPU"), font=font, fill="#FFFF00")
    y += y_offset
    draw.text((x, y), stats.get("MemUsage"), font=font, fill="#00FF00")
    y += y_offset
    draw.text((x, y), stats.get("Disk"), font=font, fill="#0000FF")
    y += y_offset
    draw.text((x, y), stats.get("Temp"), font=font, fill="#FF00FF")


def initialize_image(disp):
    # Create blank image for drawing.
    # Make sure to create image with mode 'RGB' for full color.
    height = disp.width  # we swap height/width to rotate it to landscape!
    width = disp.height
    image = Image.new("RGB", (width, height))

    return image


def main():
    # client = PiHole6Client(API_URL, API_TOKEN)

    disp = initialize_display()

    buttonA = digitalio.DigitalInOut(board.D23)
    buttonB = digitalio.DigitalInOut(board.D24)
    buttonA.switch_to_input()
    buttonB.switch_to_input()

    image = initialize_image(disp)

    # Get drawing object to draw on image.
    draw = ImageDraw.Draw(image)

    # Draw a black filled box to clear the image.
    draw.rectangle((0, 0, disp.width, disp.height), outline=0, fill=(0, 0, 0))
    disp.image(image, ROTATION)

    # Draw some shapes.
    # First define some constants to allow easy resizing of shapes.
    padding = -2
    top = padding
    bottom = disp.height - padding
    # Move left to right keeping track of the current x position for drawing shapes.
    x = 0

    # Alternatively load a TTF font.  Make sure the .ttf font file is in the
    # same directory as the python script!
    # Some other nice fonts to try: http://www.dafont.com/bitmap.php
    font = ImageFont.truetype(FONT_TYPE, FONT_SIZE)

    # Turn on the backlight
    backlight = digitalio.DigitalInOut(board.D22)
    backlight.switch_to_output()
    backlight.value = False

    try:
        while True:
            if buttonA.value and not buttonB.value:  # just button A pressed
                print("Button A pressed")

            if buttonB.value and not buttonA.value:  # just button B pressed
                print("Button B pressed")

            if buttonA.value or buttonB.value:
                backlight.value = False  # turn off backlight
            else:
                print("Buttons A & B pressed")
                backlight.value = True  # turn on backlight

            # Draw a black filled box to clear the image.
            draw.rectangle((0, 0, disp.width, disp.height), outline=0, fill=0)

            stats = get_stats()

            update_frame_text(draw, font, stats, x, top)

            # Display image.
            disp.image(image, ROTATION)
            time.sleep(0.05)

    except KeyboardInterrupt:
        print()
        print(f"Exiting {__file__}")
        print()
        # Turn off the backlight when Ctrl-C is pressed
        backlight.value = False


if __name__ == "__main__":
    main()
