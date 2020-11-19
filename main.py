import subprocess
import time
import os
from signal import pause
import datetime

from gpiozero import Button, LED, MotionSensor

scan_button = Button(17)  # button used to scan the IR signal to be sent to the AC unit
send_button = Button(27)  # button used to send the IR signal (for testing only)
led = LED(16)
vibration_sensor = MotionSensor(23)
motion_sensor = MotionSensor(21)


def blink_10(led_light):  # simple function to fast blink the LEDs
    count = 0
    while count < 11:
        led_light.on()
        time.sleep(0.1)
        led_light.off()
        time.sleep(0.1)
        count += 1


def send_code():  # function that sends the IR code (testing only?)
    try:
        if os.stat('captured_key.txt').st_size == 0:  # checks if code has been scanned. if not raises an error.
            raise OSError
        print('Sending code...')
        os.system('ir-ctl -d /dev/lirc0 --send=captured_key.txt')
    except OSError:
        print('No code found. Please scan first')


def scan_code():  # activates the scanner for 5 seconds. Press remote button once to scan and save it.
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


def airco_running():
    now = datetime.datetime.now().time()
    start = datetime.time(8)
    end = datetime.time(22)
    if now < start or now > end:  # Airco can be on without limitations
        return None  # skip function
        # wait for x minutes no motion scan then shutoff airco


def main():
    scan_button.when_pressed = scan_code
    send_button.when_pressed = send_code
    timestamp = datetime.time(23, 3, 00)
    vibration_sensor._when_activated = airco_running
    pause()


if __name__ == "__main__":
    main()
