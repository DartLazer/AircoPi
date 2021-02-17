import subprocess
from time import sleep
import os
import pathlib
import datetime
import shutil
import signal
import lcd_driver as display

from gpiozero import Button, LED, MotionSensor

scan_button = Button(17)  # button used to scan the IR signal to be sent to the AC unit
test_button = Button(27)  # button used to send the IR signal (for testing only)
red_led = LED(16)
magnetic_switch = MotionSensor(25)  # Using MotionSensor gpiozero interface for magnetic_switch due to lack of door switch sensor interface in this package.
motion_sensor = MotionSensor(8)

pwd = str(pathlib.Path(__file__).parent.absolute())  # determines the present working directory (PATH) to determine where to load and store the captured key files
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
    except OSError:
        print('No code found. Please scan first')


def check_airco_off():  # function that checks if the airco is shutdown correctly. If not, it will attempt to shutdown the airco again.
    door_open_time_limit = datetime.datetime.now().time()
    i = 0
    x = 0
    while i < 20:
        sleep(1)
        now = datetime.datetime.now()
        if not magnetic_switch.is_active:
            door_open_time_limit = set_time_limit(now, 'seconds', 10)
        if i == 19:
            if now.time() < door_open_time_limit:
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
        display.draw_text("Old IR code found...\nBacking up old key.", "small")
        shutil.copyfile(captured_key_file_location, backup_file)  # backup old key
        sleep(2)
        os.remove(captured_key_file_location)  # remove old key (the NON backup)
        display.draw_text("Backup completed.", "small")
        sleep(2)

    print('Scanner activated.\n')
    display.draw_text("Scanner activated.\n\nPress off switch on \nremote controller now.")
    red_led.on()  # red LED on to indicate you should scan the code now
    command_string = "sudo ir-ctl --mode2 -d /dev/lirc1 -r > " + captured_key_file_location  # string to be used to activate the IR receiver and the associate capture  file name
    cmd = subprocess.Popen(command_string, stdout=subprocess.PIPE, shell=True, preexec_fn=os.setsid)  # executes command to activate the IR receiver to scan and save IR code.
    sleep(5)  # 5 seconds window to send IR code
    os.killpg(os.getpgid(cmd.pid), signal.SIGTERM)  # kills the IR to file writing command 2 lines above.
    red_led.off()
    if os.stat(captured_key_file_location).st_size > 200:
        print('Scan successful! Remote captured')
        display.draw_text("Scan successful!\nIR key saved to file.")
        sleep(2)
        try:
            os.remove(backup_file)
            print('Cleaning up backup file.')
        except OSError:
            pass
        return True
    else:
        print('Scan failed')  # following logic restores backup key if no key has been scanned
        display.draw_text("Scan failed!")
        os.remove(captured_key_file_location)
        sleep(2)
        if os.path.exists(backup_file):
            display.draw_text("Restoring backup-key.")
            shutil.copyfile(backup_file, captured_key_file_location)
            os.remove(backup_file)
            print('Restoring backup.')
            blink_2_slow(red_led)
            return False


def set_time_limit(time_object, time_type, time_to_add):  # ads a certain time to an input datetime object (shifts the time by x minutes/seconds).
    if time_type == 'minutes':
        return (time_object + datetime.timedelta(minutes=time_to_add)).time()
    if time_type == 'seconds':
        return (time_object + datetime.timedelta(seconds=time_to_add)).time()


def airco_running():  # Doors open has been detected. It has been determined the airco is running. This function checks if the airco can be on with or without limitations. If so it will enforce said limitations
    display.display_status = 1  # arms the display to be reset later on.
    now = datetime.datetime.now().time()
    start = datetime.time(
        8)  # beginning of the time period where the airco can NOT be on unrestricted. (Format (hours, minutes) i.e.: datetime.time(8, 30) is 08:30 AM.)
    end = datetime.time(
        22)  # ending of the time period where the airco can NOT be on unrestricted.     (Format (hours, minutes) i.e.: datetime.time(22, 15) is 10:15 PM.)

    if now < start or now > end:  # Checks if the airco is in the "unrestricted time period". If so, we will not continue further.
        display.draw_text("Airco is allowed to be on.\nExiting restrictive schedule.")
        return None  # skip function

    last_motion = datetime.datetime.now()  # The last motion variable is a date-time (time) variable which contains the last point in time MOTION has been detected. It is set to the current time now for initialisation.
    airco_run_limit = 1  # time in minutes the airco is allowed to run without detecting motion

    last_door_open_time = datetime.datetime.now()  # The last door open variable is a date-time (time) variable which contains the last point in time doors open (airco status) has been detected. It is set to the current time now for initialisation.
    door_open_limit = 10  # amount of seconds doors open is allowed to be not registered to allow to send A/C off signal. This is to prevent actually starting the A/C if it has already been switched on, and in the meantime allowing for door open
    # sensor inaccuracies where it might or might not registered door open continuously.

    door_open_time_limit = set_time_limit(last_door_open_time, 'seconds',
                                          door_open_limit)  # latest moment the shut-off signal can be sent if doors open has not been detected meanwhile to prevent accidentally starting the AC.
    time_limit = set_time_limit(last_motion, 'minutes', airco_run_limit)  # latest date-time moment the airco is allowed to be on

    print('In restricted time. Starting airco control script: ')  # for debugging only
    while True:
        if display.display_status == 1:
            display.draw_text("Monitoring for movement\n\nA/C will shutdown at:\n" + str(time_limit))
            display.display_status = 0
        if now < start or now > end:  # This once again checks if since the time the airco started, we have now entered the "unrestricted" time span. In this case the script is no longer needed.
            break

        if motion_sensor.is_active:  # Motion is detected. time_limit variable will be set to current time + 'airco_run_limit' variable. This will be the new time where the AC will be shutoff if no motion detected.
            print('Motion detected')  # for debugging only
            display.draw_text("Motion detected!\n\n Resetting timer.")
            red_led.on()  # for debugging only
            sleep(1)  # for debugging only
            red_led.off()  # for debugging only
            last_motion = datetime.datetime.now()
            time_limit = set_time_limit(last_motion, 'minutes', airco_run_limit)
            print(f'Time limit reset to {time_limit}')  # debugging only
            continue  # skip rest of the loop because unnecessary because movement has been detected.

        if not magnetic_switch.is_active:
            door_open_time_limit = set_time_limit(datetime.datetime.now(), 'seconds', door_open_limit)

        now = datetime.datetime.now().time()
        if now > time_limit:  # Airco has been on without detected movement for longer than the allowed limit.
            print(f'No motion for the last {airco_run_limit} minutes.')
            display.draw_text(f'No motion for the last\n{airco_run_limit} minutes.\n\nAttempting shutdown.')
            if now < door_open_time_limit:  # If the airco has been registered on the last 10 seconds. We will not shutdown the AC (to prevent accidentally starting the AC instead of stopping it)
                print('Attempting to shut down the AC')
                shutdown_ac()  # send A/C off signal.
                sleep(10)
                check_airco_off()  # check if airco shut down. If not, this function will restart.
                print('Airco is off')  # for debugging only
                display.draw_text('A/C shut down.')
            else:
                print('Airco is already off.')
                display.draw_text("Airco already off.")
            break

        sleep(0.5)


def main():
    display.draw_text("Welcome to AircoPi", "small")
    if not os.path.exists(captured_key_file_location):  # checks if an IR key to shut down the AC has already been captured.
        display.draw_text("No key found.\nPress button when ready\nto scan the IR signal.", "small")
        now = datetime.datetime.now()  # saves current time
        flash_limit = 10  # interval between led flashes in seconds (to remind user he needs to capture key)
        blink_limit = set_time_limit(now, 'seconds', flash_limit)  # sets a date-time object after which the LED's will flash again.

        while True:  # enters a loop to ensure an IR code is captured and saved before the rest of the script can be run.

            now = datetime.datetime.now()
            if scan_button.is_pressed:  # allows for scanning an IR code.
                scan_result = scan_code()
                if scan_result:  # if the scan function returns True, a successful key capture. The loop may be exited.
                    break
            if now.time() > blink_limit:  # checks if the LED's need to be flashed again
                display.draw_text("No key found.\nPress button when ready\nto scan the IR signal.", "small")
                blink_limit = set_time_limit(now, 'seconds', flash_limit)  # sets new time point to flash LED's

    while True:
        if display.display_status == 1:
            display.draw_text('AircoPi standing by ...')
            display.display_status = 0
            print('Display status is now: ' + str(display.display_status))
        if scan_button.is_pressed:  # allows for scanning an IR code.
            scan_code()
        if not magnetic_switch.is_active:
            print('Open door detected. Starting airco logic')
            airco_running()
        if test_button.is_pressed:
            shutdown_ac()
        sleep(0.5)


if __name__ == "__main__":
    main()
