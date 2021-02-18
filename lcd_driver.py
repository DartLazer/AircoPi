import board
import digitalio
from PIL import Image, ImageDraw, ImageFont
import adafruit_ssd1306

# ------------- User variables ------------ #

lcd_address = 0x3c  # address for the LCD display.
small_font_size = 10  # font size for using the small case
big_font_size = 28

# ---------- End of user variables -------- #

# Setting some variables for our reset pin etc.
RESET_PIN = digitalio.DigitalInOut(board.D4)

# Very important... This lets py-gaugette 'know' what pins to use in order to reset the display
i2c = board.I2C()
display = adafruit_ssd1306.SSD1306_I2C(128, 64, i2c, addr=lcd_address, reset=RESET_PIN)

display_status = 0  # variable used to prevent unnecessary refreshing of the LCD. If display status = 1 in some cases the main tool will set a text, set the status to 0 so future refreshes will be ignored.


def clear_display():
    display.fill(0)
    display.show()


def draw_text(text, size="small"):  # functions that draws text to the LCD in either small or big font.
    display.fill(0)
    display.show()
    if size is "small":
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", small_font_size)

    elif size is "big":
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", big_font_size)

    image = Image.new("1", (display.width, display.height))
    draw = ImageDraw.Draw(image)
    draw.text((0, 0), text, font=font, fill=255)

    display.image(image)
    display.show()
    global display_status
    display_status = 1
