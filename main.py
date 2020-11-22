import subprocess
from time import sleep
import os
import datetime

from gpiozero import Button, LED, MotionSensor

scan_button = Button(17)  # button used to scan the IR signal to be sent to the AC unit
test_button = Button(27)  # button used to send the IR signal (for testing only)
led = LED(16)
vibration_sensor = MotionSensor(25)
motion_sensor = MotionSensor(26)


def blink_10(led_light):  # simple function to fast blink the LEDs
    count = 0
    while count < 11:
        led_light.on()
        sleep(0.1)
        led_light.off()
        sleep(0.1)
        count += 1


def shutdown_ac():  # function that sends the IR code (testing only?)
    try:
        if os.stat('captured_key.txt').st_size < 10:  # checks if code has been scanned. if not raises an error.
            raise OSError
        print('Sending code...')
        os.system('ir-ctl -d /dev/lirc0 --send=captured_key.txt > /dev/null 2>&1 &')
        print('Code sent.')
    except OSError:
        print('No code found. Please scan first')


def scan_code():  # activates the scanner for 5 seconds. Press remote button once to scan and save it.
    if os.path.exists('captured_key.txt'):
        print('Replacing old remote configuration..')
        os.remove('captured_key.txt')

    print('Scanner activated.\n')
    led.on()
    cmd = subprocess.Popen("ir-ctl " + '--mode2 -d /dev/lirc1 -r > captured_key.txt', stdout=subprocess.PIPE, shell=True)
    sleep(5)
    subprocess.Popen.kill(cmd)
    led.off()
    if os.stat('captured_key.txt').st_size > 10:
        print('Scan successful! Remote captured')
        blink_10(led)
    else:
        print('Scan failed')


def set_time_limit(time_object, time_type, time_to_add):  # ads a certain time to an input datetime object (shifts the time by x minutes/seconds).
    if time_type == 'minutes':
        return (time_object + datetime.timedelta(minutes=time_to_add)).time()
    if time_type == 'seconds':
        return (time_object + datetime.timedelta(seconds=time_to_add)).time()


def airco_running():  # Vibration has been detected. It has been determined the airco is running. This function checks if the airco can be on with or without limitations. If so it will enforce said limitations
    now = datetime.datetime.now().time()
    start = datetime.time(8)  # beginning of the time period where the airco can NOT be on unrestricted. (Format (hours, minutes) i.e.: datetime.time(8, 30) is 08:30 AM.)
    end = datetime.time(22)  # ending of the time period where the airco can NOT be on unrestricted.     (Format (hours, minutes) i.e.: datetime.time(22, 15) is 10:15 PM.)

    if now < start or now > end:  # Checks if the airco is in the "unrestricted time period". If so, we will not continue further.
        return None  # skip function

    last_motion = datetime.datetime.now()  # The last motion variable is a date-time (time) variable which contains the last point in time MOTION has been detected. It is set to the current time now for initialisation.
    airco_run_limit = 3  # time in minutes the airco is allowed to run without detecting motion

    last_vibration = datetime.datetime.now()  # The last vibration variable is a date-time (time) variable which contains the last point in time VIBRATION (airco status) has been detected. It is set to the current time now for initialisation.
    vibration_limit = 10  # amount of seconds vibrations is allowed to be not registered to allow to send A/C off signal. This is to prevent actually starting the A/C if it has already been switched on, and in the meantime allowing for vibration
    # sensor inaccuracies where it might or might not registered vibration continuously.

    vibration_time_limit = set_time_limit(last_vibration, 'seconds', vibration_limit)  # latest moment the shut-off signal can be sent if vibration has not been detected meanwhile to prevent accidentally starting the AC.
    time_limit = set_time_limit(last_motion, 'minutes', airco_run_limit)  # latest date-time moment the airco is allowed to be on

    print('Entering loop')  # for debugging only
    while True:
        if now < start or now > end:  # This once again checks if since the time the airco started, we have now entered the "unrestricted" time span. In this case the script is no longer needed.
            break

        if motion_sensor.is_active:  # Motion is detected. time_limit variable will be set to current time + 'airco_run_limit' variable. This will be the new time where the AC will be shutoff if no motion detected.
            print('Motion detected')  # for debugging only
            # print('led on')
            led.on()  # for debugging only
            # print('sleep 1s')
            sleep(1)  # for debugging only
            # print('led off')
            led.off()  # for debugging only
            last_motion = datetime.datetime.now()
            time_limit = set_time_limit(last_motion, 'minutes', airco_run_limit)
            print(f'Time limit reset to {time_limit}')  # debugging only
            continue  # skip rest of the loop because unnecessary because movement has been detected.

        if vibration_sensor.is_active:
            vibration_time_limit = set_time_limit(datetime.datetime.now(), 'seconds', vibration_limit)
            print('Vibration detected')  # debugging only

        now = datetime.datetime.now().time()
        if now > time_limit:  # Airco has been on without detected movement for longer than the allowed limit.
            if datetime.datetime.now().time() < vibration_time_limit:  # If the airco has been registered on the last 10 seconds. We will not shutdown the AC (to prevent accidentally starting the AC instead of stopping it)
                shutdown_ac()  # send A/C off signal.
                print('Legit shutdown')  # for debugging only
            print('Airco off!')  # for debugging only
            break

        sleep(0.1)

    print('leaving loop')  # for debugging only


def main():
    while True:
        if scan_button.is_pressed:
            scan_code()
        if vibration_sensor.is_active:
            airco_running()
        if test_button.is_pressed:
            shutdown_ac()
        sleep(0.1)


if __name__ == "__main__":
    main()
