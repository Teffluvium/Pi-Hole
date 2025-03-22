import sys
import time

import board
import busio
import digitalio
from adafruit_rgb_display import color565
from adafruit_rgb_display.st7789 import ST7789

# from board import CE0, D24, D25, MISO, MOSI, SCK

# Configuration for CS and DC pins:
CS_PIN = board.CE0
DC_PIN = board.D25
RESET_PIN = board.D24
BAUDRATE = 24000000


def busio_test():
    print("Running busio_test")

    spi = busio.SPI(board.SCLK, board.MOSI, board.MISO)
    print("  Locking SPI")
    while not spi.try_lock():
        pass
    spi.configure(baudrate=16000000)
    spi.unlock()

    print("  Writing bytes to SPI")
    while True:
        spi.write(bytes(range(64)))
        time.sleep(0.1)


def display_test():
    print("Running display_test")

    # Setup SPI bus using hardware SPI:
    spi = busio.SPI(clock=board.SCK, MOSI=board.MOSI, MISO=board.MISO)

    # Create the ST7789 display:
    print("  Creating the display")
    display = ST7789(
        spi,
        rotation=90,
        width=135,
        height=240,
        x_offset=53,
        y_offset=40,
        baudrate=BAUDRATE,
        cs=digitalio.DigitalInOut(CS_PIN),
        dc=digitalio.DigitalInOut(DC_PIN),
        rst=digitalio.DigitalInOut(RESET_PIN),
    )

    # Main loop: same as above
    print("  Updating the display")
    while True:
        # Clear the display
        display.fill(0)
        # Draw a red pixel in the center.
        display.pixel(120, 160, color565(255, 0, 0))
        # Pause 2 seconds.
        time.sleep(2)
        # Clear the screen blue.
        display.fill(color565(0, 0, 255))
        # Pause 2 seconds.
        time.sleep(2)


if __name__ == "__main__":
    # busio_test()
    display_test()
