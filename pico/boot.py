#import ugit
from machine import Pin
import time
from  boot_bluetooth_test import run_ble_test
import utime
import json
import bluetooth

switch_brew = Pin(7, Pin.IN, Pin.PULL_DOWN)
switch_water = Pin(8, Pin.IN, Pin.PULL_DOWN)
switch_steam = Pin(9, Pin.IN, Pin.PULL_DOWN)

# Import BLEHandler
# from bluetooth_class_test import BLEHandler

time.sleep(0.1)  # Power switch now is working bit slow method so giving some time

# If Water switch is on at the start, Check for updates from github
# if switch_water.value():
#     # try:
#     # ugit.pull_all()
#     # except (TypeError) as err_obj:
#     # print("Ugit error:" + str(err_obj))
#     pass

# if switch_water.value():
#     run_ble_test(utime, json, bluetooth, time, BLEHandler)
    
    