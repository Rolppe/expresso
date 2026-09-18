# boot_bluetooth_test.py



def run_ble_test(utime, json, bluetooth, time, BLEHandler):
    # Initialize BLE
    ble = bluetooth.BLE()
    ble_handler = BLEHandler(ble)

    # Dummy values initialization
    dummy_temp = 20.0
    dummy_pressure = 0.0
    dummy_heating_speed = 0.0
    dummy_mode = 'idle'
    dummy_brew_temperature = 92.0
    dummy_steam_temperature = 130.0
    dummy_pre_infusion_time = 5
    dummy_pressure_soft_release_time = 0
    dummy_pre_heat_time = 0

    #### MAIN LOOP ####
    while True:
        # Simulate changing dummy values
        dummy_temp += 0.1  # Increment temperature
        if dummy_temp > 100:
            dummy_temp = 20.0
        dummy_pressure += 0.1  # Increment pressure
        if dummy_pressure > 10:
            dummy_pressure = 0.0
        dummy_heating_speed += 0.01  # Increment heating speed
        if dummy_heating_speed > 5:
            dummy_heating_speed = 0.0
        # Cycle modes for testing
        modes = ['idle', 'brew', 'steam', 'water', 'pre-infusion', 'fast_heatup']
        dummy_mode = modes[(modes.index(dummy_mode) + 1) % len(modes)]
        
        # Send data via BLE if connected
        if ble_handler._connections:
            data = {
                'temp': dummy_temp,
                'pressure': dummy_pressure,
                'heating_speed': dummy_heating_speed,
                'mode': dummy_mode,
                'brew_temperature': dummy_brew_temperature,
                'steam_temperature': dummy_steam_temperature,
                'pre_infusion_time': dummy_pre_infusion_time,
                'pressure_soft_release_time': dummy_pressure_soft_release_time,
                'pre_heat_time': dummy_pre_heat_time
            }
            ble_handler.send_data(data)
        
        time.sleep(0.1)  # Short delay