import subprocess
import time
import os
from signal import pause

from gpiozero import Button, LED

scan_button = Button(17)
send_button = Button(27)
led = LED(16)


def blink_10(led_light):
    count = 0
    while count < 11:
        led_light.on()
        time.sleep(0.1)
        led_light.off()
        time.sleep(0.1)
        count += 1


def send_code():
    try:
        if os.stat('captured_key.txt').st_size == 0:
            raise OSError
        print('Sending code...')
        os.system('ir-ctl -d /dev/lirc0 --send=captured_key.txt')
    except OSError:
        print('No code found. Please scan first')


def scan_code():
    try:
        print('Deleting old remote configuration..')
        os.remove('captured_key.txt')
        print('Deleting successful.')
        print('------------------------------------')
    except OSError:
        pass
    print('Scanner activated.\nAim the controller at the the IR receiver and press the power button.')
    print('5 seconds remaining.')
    led.on()
    cmd = subprocess.Popen("ir-ctl " + '--mode2 -d /dev/lirc1 -r > captured_key.txt', stdout=subprocess.PIPE, shell=True)
    time.sleep(5)
    subprocess.Popen.kill(cmd)
    led.off()
    if os.stat('captured_key.txt').st_size > 0:
        print('Scan successful! Remote captured')
        blink_10(led)
    else:
        print('Scan failed')


scan_button.when_pressed = scan_code
send_button.when_pressed = send_code

pause()
