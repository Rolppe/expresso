# MUUTETAAN NIMEKSI PRESETS

# ============================================================================
# FEATURES
# ============================================================================

# EXPRESSO-DIAGNET (20.10.2026, paketit/DIAGNET.md): stdout and shot samples as UDP to the palvelin
# collector, which publishes to Home Assistant. enabled False = Wi-Fi off as before.
DIAGNET = {'enabled': True, 'host': '192.0.2.11', 'port': 47210}

# EXPRESSO-WIFI-AIKAIKKUNA (user 20.10.2026): bluetooth off for now so it does not slow the Pico; the app
# uses the Wi-Fi link (wifilink.py). enabled True brings the BLE task and advertising back.
BLE = {'enabled': False}

FEATURES = {
    # Core features
    'pid_control_flag'               : True,   # PID temperature control (standby/steam)
    'pressure_control_flag'          : True,   # Dynamic pressure control
    'fast_heatup_mode_flag'          : False,
    'pre_infusion_mode_flag'         : True,
    'after_brew_pressure_drain_flag' : False,
    'print_values_flag'              : False,
    'soft_pressure_release_flag'     : True,
    
    'pre_infusion_pressure_buildup_time'         : 0,
    'pre_infusion_time'                          : 5,
    'pressure_soft_release_time'                 : 4,
    'brew_pressure_bar'                          : 9,
    'soft_pressure_release_arming_pressure'      : 3,
    'steam_pressure_low_bar'                     : 1.8,
    'steam_valve_trigger_bar'                    : 1.8,
    'steam_valve_release_bar'                    : 2.1,
    'steam_pressure_high_bar'                    : 2.5,
    'steam_temperature_max_c'                    : 140.0,
    'idle_pressure_equalize_flag'                : False,
    'idle_pressure_equalize_threshold_bar'       : 0.5,
    'idle_pressure_equalize_interval_s'          : 30,
    'idle_pressure_equalize_pulse_ms'            : 100,
    'idle_pressure_equalize_max_over_temp_c'     : 0.1,
    'standby_startup_timeout_min'                : 120,
    'standby_brew_timeout_min'                   : 30,
    'pre_infusion_trigger_flag'                  : False,
    'pre_infusion_trigger_threshold_g'           : 0.25
    }

# ============================================================================
# HARDWARE CONFIGURATION - GPIO PINS
# ============================================================================

PINS = {
    # Input switch's
    'SWITCH_BREW'      : 7,
    'SWITCH_WATER'     : 8,
    'SWITCH_STEAM'     : 9,
    
    # Switch led's
    'LED_SWITCH_BREW'  : 14,
    'LED_SWITCH_WATER' : 15,
    'LED_SWITCH_STEAM' : 16,
    
    # Output relays
    'RELAY_PUMP'       : 11,
    'RELAY_SOLENOID'   : 12,
    'RELAY_HEATER'     : 13,
    
    # Temperature MAX31865 (SPI)
    'TEMP_SCK'         : 6,
    'TEMP_MOSI'        : 3,
    'TEMP_MISO'        : 4,
    'TEMP_CS'          : 5,
    
    # Pressure sensor (ADC)
    'PRESSURE_ADC'     : 28
    }

# ============================================================================
# TEMPERATURE SENSOR MAX31865 CONFIGURATION
# ============================================================================

MAX31865_CONFIG = {
    'NUMBER_OF_WIRES'    : 3, 
    'RTD_NOMINAL'        : 100,
    'REF_RESISTOR'       : 430.0
    }

# ============================================================================
# TEMPERATURES Celsius
# ============================================================================

TARGET_TEMPERATURES = {
    'IDLE'    : 98,
    'BREW'    : 98, 
    'STEAM'   : 135,
    'PID_CAL' : 100,
    
    # Backflush program temperatures
    'BACKFLUSH_PHASE_1' : 95,
    'BACKFLUSH_PHASE_2' : 100,
    'BACKFLUSH_PHASE_3' : 110,
    'BACKFLUSH_END'     : 98
    }
