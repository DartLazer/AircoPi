import subprocess
from time import sleep
import os
import pathlib
import datetime
import shutil

from gpiozero import Button, LED, MotionSensor

scan_button = Button(17)  # button used to scan the IR signal to be sent to the AC unit
test_button = Button(27)  # button used to send the IR signal (for testing only)
red_led = LED(16)
blue_led = LED(12)
vibration_sensor = MotionSensor(25)
motion_sensor = MotionSensor(26)

pwd = str(pathlib.Path(__file__).parent.absolute())  # determines the present working directory (PATH) to dertmine where to load and store the captured key files
captured_key_file_location = pwd + '/captured_key.txt'  # name given to the captured key file
backup_file = pwd + '/key_backup.txt'  # name given to the backup key file


def blink_10_fast(led_light):  # simple function to fast blink the LEDs
    for x in range(0, 10):
        led_light.on()
        sleep(0.05)
        led_light.off()
        sleep(0.05)


def blink_2_slow(led_light):
    for x in range(0, 2):
        led_light.on()
        sleep(0.4)
        led_light.off()
        sleep(0.4)


def dual_blink_2_slow(led_light1, led_light2):
    for x in range(0, 2):
        led_light1.on()
        led_light2.on()
        sleep(0.4)
        led_light1.off()
        led_light2.off()
        sleep(0.4)


def shutdown_ac():  # function that sends the IR code (testing only?)
    try:
        if os.stat(captured_key_file_location).st_size < 10:  # checks if code has been scanned. if not raises an error.
            raise OSError
        print('Sending code...')
        command = ['ir-ctl', '-d', '/dev/lirc0', '--send=' + captured_key_file_location]
        result = str(subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE).stderr).casefold()
        if 'failed' in result:
            print('IR SEND FAILED')
            blink_2_slow(red_led)
            blink_2_slow(blue_led)
    except OSError:
        print('No code found. Please scan first')
        dual_blink_2_slow(red_led, blue_led)


def check_airco_off():  # function that checks if the airco is shutdown correctly. If not, it will attempt to shutdown the airco again.
    vibration_time_limit = datetime.datetime.now().time()
    i = 0
    x = 0
    while i < 20:
        sleep(1)
        now = datetime.datetime.now()
        if vibration_sensor.is_active:
            vibration_time_limit = set_time_limit(now, 'seconds', 10)
        if i == 19:
            if now.time() < vibration_time_limit:
                print('Airco still on. reattempting shutdown')
                shutdown_ac()
                i = 0
                x += 1
                sleep(15)
                continue
        if x == 5:
            print('Airco shutdown failed 5 times. Restarting raspberry pi.')
            os.system("sudo reboot now")
        i += 1


def scan_code():  # activates the scanner for 5 seconds. Press remote button once to scan and save it.
    if os.path.exists(captured_key_file_location):  # checks if a code already exists, if so backs it up and removes the present one
        print('Backing up old remote configuration..')
        shutil.copyfile(captured_key_file_location, backup_file)  # backup old key
        os.remove(captured_key_file_location)  # remove old key (the NON backup)

    print('Scanner activated.\n')
    red_led.on()  # red LED on to indicate you should scan the code now
    command_string = "sudo ir-ctl --mode2 -d /dev/lirc1 -r > " + captured_key_file_location  # string to be used to activate the IR receiver and the associate capture  file name
    cmd = subprocess.Popen(command_string, stdout=subprocess.PIPE, shell=True)  # executes command
    sleep(5)  # 5 seconds window to send IR code
    subprocess.Popen.kill(cmd)  # kills receiving mode
    red_led.off()
    if os.stat(captured_key_file_location).st_size > 10:
        print('Scan successful! Remote captured')
        try:
            os.remove(backup_file)
            print('Cleaning up backup file.')
        except OSError:
            pass
        blink_10_fast(red_led)
        os.system("sudo reboot now")
    else:
        print('Scan failed')  # following logic restores backup key if no key has been scanned
        os.remove(captured_key_file_location)
        if os.path.exists(backup_file):
            shutil.copyfile(backup_file, captured_key_file_location)
            os.remove(backup_file)
            print('Restoring backup.')


def set_time_limit(time_object, time_type, time_to_add):  # ads a certain time to an input datetime object (shifts the time by x minutes/seconds).
    if time_type == 'minutes':
        return (time_object + datetime.timedelta(minutes=time_to_add)).time()
    if time_type == 'seconds':
        return (time_object + datetime.timedelta(seconds=time_to_add)).time()


def airco_running():  # Vibration has been detected. It has been determined the airco is running. This function checks if the airco can be on with or without limitations. If so it will enforce said limitations
    now = datetime.datetime.now().time()
    start = datetime.time(
        8)  # beginning of the time period where the airco can NOT be on unrestricted. (Format (hours, minutes) i.e.: datetime.time(8, 30) is 08:30 AM.)
    end = datetime.time(
        22)  # ending of the time period where the airco can NOT be on unrestricted.     (Format (hours, minutes) i.e.: datetime.time(22, 15) is 10:15 PM.)

    if now < start or now > end:  # Checks if the airco is in the "unrestricted time period". If so, we will not continue further.
        blink_10_fast(blue_led)
        return None  # skip function

    last_motion = datetime.datetime.now()  # The last motion variable is a date-time (time) variable which contains the last point in time MOTION has been detected. It is set to the current time now for initialisation.
    airco_run_limit = 1  # time in minutes the airco is allowed to run without detecting motion

    last_vibration = datetime.datetime.now()  # The last vibration variable is a date-time (time) variable which contains the last point in time VIBRATION (airco status) has been detected. It is set to the current time now for initialisation.
    vibration_limit = 10  # amount of seconds vibrations is allowed to be not registered to allow to send A/C off signal. This is to prevent actually starting the A/C if it has already been switched on, and in the meantime allowing for vibration
    # sensor inaccuracies where it might or might not registered vibration continuously.

    vibration_time_limit = set_time_limit(last_vibration, 'seconds',
                                          vibration_limit)  # latest moment the shut-off signal can be sent if vibration has not been detected meanwhile to prevent accidentally starting the AC.
    time_limit = set_time_limit(last_motion, 'minutes', airco_run_limit)  # latest date-time moment the airco is allowed to be on

    print('In restricted time. Starting airco control script: ')  # for debugging only
    while True:
        blue_led.on()
        if now < start or now > end:  # This once again checks if since the time the airco started, we have now entered the "unrestricted" time span. In this case the script is no longer needed.
            blink_10_fast(blue_led)
            break

        if motion_sensor.is_active:  # Motion is detected. time_limit variable will be set to current time + 'airco_run_limit' variable. This will be the new time where the AC will be shutoff if no motion detected.
            print('Motion detected')  # for debugging only
            red_led.on()  # for debugging only
            sleep(1)  # for debugging only
            red_led.off()  # for debugging only
            last_motion = datetime.datetime.now()
            time_limit = set_time_limit(last_motion, 'minutes', airco_run_limit)
            print(f'Time limit reset to {time_limit}')  # debugging only
            continue  # skip rest of the loop because unnecessary because movement has been detected.

        if vibration_sensor.is_active:
            vibration_time_limit = set_time_limit(datetime.datetime.now(), 'seconds', vibration_limit)
            #  print('Vibration detected')  # debugging only

        now = datetime.datetime.now().time()
        if now > time_limit:  # Airco has been on without detected movement for longer than the allowed limit.
            print(f'No motion for the last {airco_run_limit} minutes.')
            if now < vibration_time_limit:  # If the airco has been registered on the last 10 seconds. We will not shutdown the AC (to prevent accidentally starting the AC instead of stopping it)
                print('Attempting to shut down the AC')
                shutdown_ac()  # send A/C off signal.
                sleep(10)
                check_airco_off()  # check if airco shut down. If not, this function will restart.
                print('Airco is off')  # for debugging only
            else:
                print('Airco is already off.')
                blink_2_slow(blue_led)
            blue_led.off()
            break

        sleep(0.5)


def main():
    blink_2_slow(blue_led)
    while True:
        if scan_button.is_pressed:
            scan_code()
        if vibration_sensor.is_active:
            print('Airco vibration detected. Starting airco logic')
            airco_running()
        if test_button.is_pressed:
            shutdown_ac()
        sleep(0.5)


if __name__ == "__main__":
    main()
