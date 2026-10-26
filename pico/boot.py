# RELAYS OFF FIRST (EXPRESSO-TURVAKATO-NOLLAUSIKKUNA, devsafe 17.9.2026 / 26.10.2026):
# Relays (pump=11, solenoid=12, heater=13) driven off at the very beginning of boot.py before any other import, sleep or operation.
import devsafe
devsafe.relays_off()

from machine import Pin
import time

switch_brew = Pin(7, Pin.IN, Pin.PULL_DOWN)
switch_water = Pin(8, Pin.IN, Pin.PULL_DOWN)
switch_steam = Pin(9, Pin.IN, Pin.PULL_DOWN)

time.sleep(0.1)  # Power switch now is working bit slow method so giving some time