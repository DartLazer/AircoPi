# Imports the necessary libraries...
import board
import digitalio
from PIL import Image, ImageDraw, ImageFont
import adafruit_ssd1306
from time import sleep

# Setting some variables for our reset pin etc.
RESET_PIN = digitalio.DigitalInOut(board.D4)

# Very important... This lets py-gaugette 'know' what pins to use in order to reset the display
i2c = board.I2C()
display = adafruit_ssd1306.SSD1306_I2C(128, 64, i2c, addr=0x3C, reset=RESET_PIN)

def clear_display():
    display.fill(0)
    display.show()


def draw_text(text, size, screentime):
    display.fill(0)
    display.show()
    if size is "small":
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 10)
    elif size is "big":
        font2 = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 28)

    image = Image.new("1", (display.width, display.height))
    draw = ImageDraw.Draw(image)
    draw.text((0, 32), text, font=font, fill=255)

    display.image(image)
    display.show()

    sleep(screentime)
    clear_display()
