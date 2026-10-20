# ============================================================================
# PUMP RATIO CALCULATOR
# ============================================================================
class PumpRatioCalculator:
    def __init__(self, utime_module, asyncio_module):
        self.utime = utime_module
        self.asyncio = asyncio_module
        self.reset()


    def reset(self):
        now = self.utime.ticks_ms()
        self.pump_on_time = 0
        self.pump_off_time = 0
        self.last_change = now
        self.pump_is_on = False
        self.last_get_ratio_time = now


    def start(self, initial_pump_on=False):
        self.reset()
        if initial_pump_on:
            self.pump_is_on = True


    def set_pump_on(self):
        now = self.utime.ticks_ms()
        if self.pump_is_on:
            return
        self.pump_off_time += self.utime.ticks_diff(now, self.last_change)
        self.pump_is_on = True
        self.last_change = now


    def set_pump_off(self):
        now = self.utime.ticks_ms()
        if not self.pump_is_on:
            return
        self.pump_on_time += self.utime.ticks_diff(now, self.last_change)
        self.pump_is_on = False
        self.last_change = now


    def get_ratio(self):
        
        now = self.utime.ticks_ms()
        if self.pump_is_on:
            current_on = self.pump_on_time + self.utime.ticks_diff(now, self.last_change)
            current_off = self.pump_off_time
        else:
            current_on = self.pump_on_time
            current_off = self.pump_off_time + self.utime.ticks_diff(now, self.last_change)
        
        total = current_on + current_off
        
        if total == 0:
            ratio = 0.0
        else:
            ratio = (current_on / total) * 100
        
        self.pump_on_time = 0
        self.pump_off_time = 0
        self.last_change = now
        
        return round(ratio, 2)
        
        
# ============================================================================
# BREW STATS LOGGER
# ============================================================================

class BrewStatsLogger:
    def __init__(self, utime, asyncio):
        self.asyncio = asyncio_module
        self.pressure = 0
        self.start_time = 0
        self.boiler_temperature = 0
        self.boiler_temperature_ms = None   # ticks_ms of the last read; the heater guard needs it fresh
        self.pump_ratio = 0
        self.resolution = 1 # times in second
        self.file_name = "brew_log.txt"
        
        
# ============================================================================
# BREW DATA 
# ============================================================================

# Thermostat setpoint ceiling (EXPRESSO-TURVA-PIKAKORJAUKSET, 21.9.2026). A failed temperature
# sensor reads 200 C (get_boiler_temperature), so a setpoint at or above that would leave the heater
# on through a sensor fault. Checked in the setters so bt:, BLE and settings.txt all pass through it.
SETPOINT_MAX_C = 150

def _check_setpoint(value):
    # None comes from an old settings.txt without the key and keeps the old behaviour
    if value is not None and not (0 < value <= SETPOINT_MAX_C):
        raise ValueError('setpoint out of range: %s' % value)


###### Class to share data between the cores ####
class BrewData:
    def __init__(self, Pin, ADC, PINS, TARGET_TEMPERATURES, FEATURES, heating_speed_calculator, temperature_sensor, pressure_sensor, utime=None):
        self.heating_speed_calculator = heating_speed_calculator
        self.temperature_sensor       = temperature_sensor
        self.pressure_sensor          = pressure_sensor
        self._boiler_temperature_ms   = None   # ticks_ms of the last read; the heater guard needs it fresh
        self.SWITCH_BREW      = Pin(PINS['SWITCH_BREW'], Pin.IN, Pin.PULL_DOWN)
        self.SWITCH_STEAM     = Pin(PINS['SWITCH_STEAM'], Pin.IN, Pin.PULL_DOWN)
        self.SWITCH_WATER     = Pin(PINS['SWITCH_WATER'], Pin.IN, Pin.PULL_DOWN)
        self.LED_SWITCH_BREW  = Pin(PINS['LED_SWITCH_BREW'], Pin.OUT, value=0)
        self.LED_SWITCH_WATER = Pin(PINS['LED_SWITCH_WATER'], Pin.OUT, value=0)
        self.LED_SWITCH_STEAM = Pin(PINS['LED_SWITCH_STEAM'], Pin.OUT, value=0)
        # Pump and heater only through the relay guard (EXPRESSO-TURVA-TOIMILAITE, 22.9.2026): the
        # raw pins are not kept on the object, so no path can switch them on around the limits.
        # The solenoid is not guarded: opening it only releases pressure.
        from relayguard import RelayGuard, GuardedRelay
        _clock_given = utime is not None
        if utime is None:
            import utime
        self.relay_guard      = RelayGuard(self, utime, self._guard_pressure)
        self.RELAY_PUMP       = GuardedRelay(Pin(PINS['RELAY_PUMP'], Pin.OUT, value=0), self.relay_guard, 'pump')
        self.RELAY_SOLENOID   = Pin(PINS['RELAY_SOLENOID'], Pin.OUT, value=0)
        self.RELAY_HEATER     = GuardedRelay(Pin(PINS['RELAY_HEATER'], Pin.OUT, value=0), self.relay_guard, 'heater')
        self.BACKFLUSH_PHASE_1_temperature = TARGET_TEMPERATURES['BACKFLUSH_PHASE_1']
        self.BACKFLUSH_PHASE_2_temperature = TARGET_TEMPERATURES['BACKFLUSH_PHASE_2']
        self.BACKFLUSH_PHASE_3_temperature = TARGET_TEMPERATURES['BACKFLUSH_PHASE_3']
        self.BACKFLUSH_END_temperature     = TARGET_TEMPERATURES['BACKFLUSH_END']
        self.pressure_soft_release_mode = FEATURES['soft_pressure_release_flag']
        self.fast_heatup_mode           = FEATURES['fast_heatup_mode_flag']
        self.pre_infusion_mode          = FEATURES['pre_infusion_mode_flag']
        self.pressure_soft_release_time = FEATURES['pressure_soft_release_time']
        self.soft_pressure_release_arming_pressure = FEATURES['soft_pressure_release_arming_pressure']
        self.pre_infusion_time  = 0
        self.brew_temperature   = 97
        self.steam_temperature  = 125
        # Standby (VALMIUSTILA, 5.10.2026): after standby_timeout_ms without any switch or app change the
        # IDLE target drops to min(brew, standby_temperature) so the boiler pressure at rest is lower.
        # RAM only (stby:<min>); the latch is cleared by note_activity() only, never by clock wrap.
        self.standby_timeout_ms   = 30 * 60000
        self.standby_temperature  = 90
        self.standby              = False
        self.last_activity_ms     = utime.ticks_ms() if _clock_given else 0
        self.pre_heat_time      = 0
        self.boiler_temperature = 0
        self.brew_pressure      = 8
        self.pre_infusion_pressure = 2.0
        self.pressure           = 0
        self.target_temperature = 0
        self.pump_ratio         = 0
        self.heating_speed      = 0
        self.fast_heatup_mode   = False
        self.setting_changed    = True
        self.mode               = "IDLE"
        # Remote test shot (tshot:<s>) and development safe state (dev:safe)
        self.test_shot_request  = None      # seconds, queued by a command
        self.test_shot_abort    = False
        self.dev_safe           = False
        # Remote pressure capture (pcap:<ms>): raw ADC waveform for mains-frequency analysis
        self.pcap_request       = None      # ms, queued by a command (200-2500)
        self.pcap_abort         = False
        # Remote pressure hold (phold:<s>): free pump+valve run for restrictor balancing
        self.phold_request      = None      # seconds, queued by a command (1-120)
        self.phold_abort        = False
        # Throttle warm-up (klamp:<s>, 24.9.2026): plateau pressure held until the pump is unlimited
        self.klamp_request      = None      # seconds, queued by a command (10-120)
        self.klamp_abort        = False
        # Remote phase sweep (psweep:<ms>:<bar>[:<n>]): PWM-1B4-PYYHKAISY
        self.psweep_request     = None      # ms, queued by a command (200-2500)
        self.psweep_abort       = False
        self.psweep_target_bar  = None      # bar, pakollinen kenttä (spec kohta 5)
        self.psweep_n           = None      # vaihesiirtojen määrä 2-8, oletus 5
        self.psweep_mult        = None      # portin jakso verkkojaksoina 2-16, oletus 2 (PWM-1B6)
        # Mains-frequency calibration (mcal:<ms>): PWM-1G, TILAUS-F/G/H
        self.mcal_request       = None      # ms, queued by a command (500-5000)
        self.mcal_abort         = False
        # Yhden syklin ohitus tasapainossa (pstep:<bar>): kayttajan tilaus 20.9.2026. Viive
        # luetaan ohituskaskyn ja paineessa nakyvan pudotuksen valista, ei portituksesta.
        self.pstep_request      = None      # bar, queued by a command
        self.pstep_abort        = False
        self.pstep_hold_ms      = None      # pito tavoitteessa ennen ohitusta, oletus PSTEP_HOLD_MS
        self.pstep_tail_ms      = None      # tallennus sammutuksen jalkeen, oletus PSTEP_TAIL_MS
        # Monta 20 ms:n taukoa ja kohdistushaku ajon aikana (pgap:<bar>): tilaus 20.9.2026
        self.pgap_request       = None      # bar, queued by a command
        self.pgap_abort         = False
        self.pgap_n             = None      # taukojen maara, oletus PGAP_N_DEFAULT
        self.pgap_spacing_ms    = None      # taukojen vali, oletus PGAP_SPACING_MS
        self.pgap_len_ms        = None      # tauon pituus, oletus koko verkkojakso
        self.pgap_phases        = None      # eri vaiheita kierrossa, oletus PGAP_CYCLE_K
        self.pgap_lo_us         = None      # rajatun vaihealueen alaraja
        self.pgap_hi_us         = None      # ...ja ylaraja; molemmat paatepisteet mukana
        self.vkello_request, self.vkello_abort = None, False  # vkello:<bar>: brief VERKKOKELLO
        self.vsweep_request, self.vsweep_abort = None, False  # vsweep:<reps>: TILAUS-K/L askel 1
        # Tauon pituuden pyyhkaisy (plen:<bar>): kvantisoituuko katkaisu puolijaksoihin
        self.plen_request       = None      # bar, queued by a command
        self.plen_abort         = False
        self.plen_reps          = None      # toistoja per pituus, oletus PLEN_REPS
        # Pelkka purkusykli (pvent:): TILAUS-H kohta 3
        self.pvent_request      = False
        self.pvent_abort        = False
        # Learned pump feed-forward per phase (RAM, from the previous shot's average duty)
        self.learned_ff_pre     = 0.3
        # Esiuuton tapa (pim:, RAM): 0 = PI 17 ms ikkunalla, 1 = vaiheseurattu (TILAUS-K 1-2,
        # 24.9.2026); oletus 1 (EXPRESSO-TEMPSTALE-JA-OLETUS, 28.9.2026: kayttoonottoketjun kohta 3).
        # eu_coast_s = opittu jalkinousu (s) vaiheen 1 katkaisun jalkeen.
        self.pre_infusion_method = 1
        self.eu_coast_s         = 0.3
        # Nopean nousun (>= 8 bar/s) jalkinousu erikseen (EXPRESSO-ESIUUTTO-UUTTOASENTO, = EU_COAST_FAST_S0)
        self.eu_coast_fast_s    = 0.2
        # Edellisen asettuneen pidon G (bar/s dutya kohden); 0 = ei tietoa -> 1. ajon polku (EXPRESSO-ESIUUTTO-FF).
        # learned_ff_pre, eu_g_pre ja eu_coast_s tallentuvat settings.txt:hen (sailyvat kaynnistyksen ja flashin yli).
        self.eu_g_pre           = 0.0
        # Edellisen pidon vuodon tau (s) ff:n laskuun; 0 = ei tietoa -> G-suhde EU_TAU_S:lla (EXPRESSO-ESIUUTTO-AVOIN)
        self.eu_tau_pre         = 0.0
        self.learned_ff_brew    = 0.5
        # Uuton tapa (bim:, RAM, EXPRESSO-UUTTO-8BAR): 0 = vanha uuttosilmukka, 1 = vaiheet 3-4 (TILAUS-K) esiuuton jatkona;
        # oletus 1 kuten pim (EXPRESSO-TEMPSTALE-JA-OLETUS).
        # Uuton opitut arvot erillaan esiuuton arvoista (settings.txt, eb_*): tarve uuttopaineessa, sen suhde saman ajon
        # esiuuton tarpeeseen (0 = ei tietoa -> paineiden suhde), G ja tau katkaisusta, jalkinousu.
        self.brew_method        = 1
        self.eb_ff              = 0.0
        self.eb_x               = 0.0
        self.eb_g               = 0.0
        self.eb_tau             = 0.0
        self.eb_coast_s         = 0.2
        self.pressure_filtered  = 0.0
        # Drip-tray scale (18.9.2026). weight is grams from scale.Scale.update(), None when no
        # scale answered at boot; weight_limit 0 = off, > 0 aborts a test shot before the tray
        # overflows. Test shots only - a real shot has a cup on the scale and needs its own limit.
        self.weight             = None
        self.weight_ms          = 0
        self.weight_a           = 0.0
        self.weight_b           = 0.0
        # Flow (g/s) from the same scale, fitted over a window by scale.Scale.flow(). None when there
        # is no scale or the samples are stale. flow_window_ms is the latency/noise knob (fwin:, not
        # persisted): it is a measurement setting, not a safety limit.
        self.flow               = None
        self.flow_window_ms     = 1000
        # Brew log (EXPRESSO-UUTTOLOKI, 5.10.2026): main.py sets brew_logger and tray_scale. A finished
        # shot waits in pending_brew_log (RAM) until the app acks it; the flags drive bluetooth_handler's
        # multipack and are set by commands (sync, brew_log?, brew_log:ack) and brew_logger.brew_log_service.
        self.brew_logger             = None
        self.tray_scale              = None
        # App tare and scale calibration (scalecal.py, EXPRESSO-WIFI-APPI vaihe 0): weight_g = weight - tare_abs_g
        self.tare_abs_g              = None
        self.scale_cal               = None
        self.pending_brew_log        = None
        self.brew_log_send_requested = False
        self.brew_log_tx_reset       = False
        self.settings_requested      = False
        # Outer flow cascade (VIRTAUSSAATO, 18.9.2026): runtime-only, not persisted (fmode:/fset:
        # never set updated = True), so the device is always in pressure control after a boot.
        self.flow_mode          = False
        self.flow_target        = 2.2
        self.weight_limit       = 0.0
        # Per-shot rise limit. The absolute limit is only as good as the platform's slow
        # behaviour (reseating +-10 g, up to 12 g of settling after a disturbance, 18.9.2026);
        # a shot lasts seconds, so a limit on the rise during it is immune to all of that.
        self.weight_rise_limit  = 0.0
        self.command_known      = True
        # Pressure calibration wizard state (see functions.pressure_calibration_run)
        self.pcal_request       = None      # 'pre' | 'brew' queued by BLE
        self.pcal_cancel        = False
        self.pcal_state         = 'idle'    # idle|queued|running|done|corrected|saved|error
        self.pcal_stage         = ''
        self.pcal_msg           = ''
        self.pcal_target        = 0.0
        self.pcal_window_ms     = 500       # PCAL-KORJAUS: one pump stroke per this window in
                                            # the fine phase; swept to find the steadiest hold
        self.pzero_request      = False     # pzero: vented zero, taken by the main loop
        self.pcal_raw           = {}        # stage -> raw_bar average of the last run
        self.pcal_points        = {}        # stage -> (raw_bar, measured_bar)
    
    
# ===== SETTERS  ====== #

    # ===== SETTERS MISCELIOUS ====== #
        
    def set_attribute(self, attribute_name, value):
        setattr(self, attribute_name, value)
    
    def set_setting_changed(self):
        print("brew_data.set_setting_changed()")
        self.setting_changed = True
        
        
    # ===== SETTERS - MODES ====== #

    def set_mode(self, mode):
        self.mode = mode
    
    
    def set_fast_heatup_mode(self, enabled):
        self.fast_heatup_mode = enabled
        self.setting_changed = True
        
        
    def set_pre_infusion_mode(self, enabled):
        self.pre_infusion_mode = enabled
        self.setting_changed = True
        
    def set_pressure_soft_release_mode(self, enabled):
        self.pressure_soft_release_mode = enabled    
        self.setting_changed = True
        
    def set_pressure_soft_release_time(self, seconds):
        self.pressure_soft_release_time = seconds
        self.setting_changed = True
        
    # ===== SETTERS - TARGETS ====== #

    def set_target_temperature(self, target_temperature):
        self.target_temperature = target_temperature
        self.set_setting_changed()


    def set_brew_temperature(self, brew_temperature):
        print("set_brew_temperature")
        _check_setpoint(brew_temperature)
        self.brew_temperature = brew_temperature
        self.setting_changed = True


    def set_steam_temperature(self, steam_temperature):
        _check_setpoint(steam_temperature)
        self.steam_temperature = steam_temperature
        self.setting_changed = True


    def set_brew_pressure(self, brew_pressure):
        # App slider range 5-10 bar
        self.brew_pressure   = min(10.0, max(5.0, float(brew_pressure)))
        self.setting_changed = True


    def set_pre_infusion_pressure(self, pre_infusion_pressure):
        # App slider range 1-4 bar
        self.pre_infusion_pressure = min(4.0, max(1.0, float(pre_infusion_pressure)))
        self.setting_changed = True


    # ===== SETTERS - REALTIME DATA ====== #

    def set_boiler_stats(self, target_temperature, heating_speed):
        self.target_temperature = target_temperature
        self.heating_speed = heating_speed
        
        
    def set_heating_speed(self, heating_speed):
        self.heating_speed = heating_speed
    
    
    def set_boiler_temperature(self, boiler_temperature):
        self.boiler_temperature = boiler_temperature
        
        
    def set_pressure(self, pressure):
        self.pressure = pressure
    
    def set_pump_ratio(self, pump_ratio):
        self.pump_ratio = pump_ratio
        print(pump_ratio)
        

    # ===== SETTERS - TIMES ====== #

    def set_pre_infusion_time(self, time):
        self.pre_infusion_time = time
        self.setting_changed = True
    
    
# ===== GETTERS ====== #
    
    # ===== GETTERS MISCELIOUS ====== #
    
    def get_setting_changed(self):
        setting_changed = self.setting_changed
        self.setting_changed = False
        
        return setting_changed
    

    def get_attribute(self, attribute_name):
            return getattr(self, attribute_name)
        

    # ===== GETTERS - MODES ====== #
    
    def get_mode(self):
        mode = self.mode
        
        return mode
     
 
    def get_fast_heatup_mode(self):
        fast_heatup_mode = self.fast_heatup_mode
        
        return fast_heatup_mode
    
    
    def get_pre_infusion_mode(self):
        pre_infusion_mode = self.pre_infusion_mode
        
        return pre_infusion_mode
    

    def get_pressure_soft_release_mode(self):
        pressure_soft_release = self.pressure_soft_release_mode
    
        return pressure_soft_release
    
    
    # ===== GETTERS - TARGETS ====== #

    def get_brew_pressure(self):
        brew_pressure = self.brew_pressure
        
        return brew_pressure


    def get_pre_infusion_pressure(self):
        pre_infusion_pressure = self.pre_infusion_pressure
        
        return pre_infusion_pressure
    

    def get_brew_temperature(self):
        brew_temperature = self.brew_temperature
        
        return brew_temperature
    

    def get_steam_temperature(self):
        steam_temperature = self.steam_temperature
        
        return steam_temperature
    
    
    def note_activity(self, now_ms, reason):
        self.last_activity_ms = now_ms
        self.relay_guard.user_retry(now_ms, reason)   # a person is here: retry a no-rise latch (V-154-SYY)
        if self.standby:
            self.standby = False
            print('STBY_OFF reason=%s' % reason)

    def update_standby(self, now_ms):
        # Latch: once on it stays on until note_activity(); a negative ticks_diff (ticks_ms wrap,
        # valid only ~6 days) therefore cannot release it.
        if self.standby_timeout_ms > 0 and not self.standby and self.mode == 'IDLE':
            import utime
            idle_ms = utime.ticks_diff(now_ms, self.last_activity_ms)
            if idle_ms >= self.standby_timeout_ms:
                self.standby = True
                print('STBY_ON idle_s=%d target=%s' % (idle_ms // 1000, min(self.brew_temperature, self.standby_temperature)))

    def get_target_temperature(self):
        if self.mode == "BREW":
            target_temperature = self.brew_temperature
        elif self.mode == "IDLE":
            target_temperature = self.brew_temperature
            if self.standby:
                target_temperature = min(self.brew_temperature, self.standby_temperature)
        elif self.mode == "STEAM":
            target_temperature = self.steam_temperature
        elif self.mode == "WATER":
            target_temperature = self.brew_temperature
        elif self.mode == "BACKFLUSH_PHASE_1":
            target_temperature = self.BACKFLUSH_PHASE_1_temperature
        elif self.mode == "BACKFLUSH_PHASE_2":
            target_temperature = self.BACKFLUSH_PHASE_2_temperature
        elif self.mode == "BACKFLUSH_PHASE_3":
            target_temperature = self.BACKFLUSH_PHASE_3_temperature
        elif self.mode == "BACKFLUSH_END":
            target_temperature = self.BACKFLUSH_END_temperature
        else:
            target_temperature = self.brew_temperature
        
        return target_temperature
    
    def get_soft_pressure_release_arming_pressure(self):
        pressure = self.soft_pressure_release_arming_pressure
        
        return pressure
    
    # ===== GETTERS - REALTIME DATA ====== #
    
    # ===== TEST SHOT AND DEV SAFE ====== #

    def request_test_shot(self, seconds):
        if self.dev_safe:
            return False
        self.test_shot_request = min(60.0, max(5.0, float(seconds)))
        self.test_shot_abort = False
        return True

    def take_test_shot_request(self):
        seconds = self.test_shot_request
        self.test_shot_request = None
        return seconds

    def stop_test_shot(self):
        self.test_shot_request = None
        self.test_shot_abort = True

    def set_dev_safe(self, enabled):
        self.dev_safe = enabled
        if enabled:
            self.stop_test_shot()
            self.pcal_request = None
            self.pcal_cancel = True

    # ===== PRESSURE CALIBRATION ====== #

    def request_pressure_calibration(self, stage):
        if stage not in ('pre', 'brew') or self.pcal_state in ('queued', 'running'):
            return False
        self.pcal_request = stage
        self.pcal_cancel = False
        self.pcal_stage = stage
        self.pcal_state = 'queued'
        self.pcal_msg = ''
        return True

    def take_pressure_calibration_request(self):
        stage = self.pcal_request
        self.pcal_request = None
        return stage

    def pressure_calibration_begin(self, stage, target):
        self.pcal_stage = stage
        self.pcal_target = target
        self.pcal_state = 'running'
        self.pcal_msg = ''

    def pressure_calibration_end(self, stage, raw_average, reason):
        if raw_average is None:
            self.pcal_state = 'error'
            self.pcal_msg = 'stopped: ' + (reason or 'no samples')
        else:
            self.pcal_raw[stage] = raw_average
            self.pcal_state = 'done'
            self.pcal_msg = 'raw %.2f bar' % raw_average

    def pressure_calibration_measured(self, stage, measured):
        raw = self.pcal_raw.get(stage)
        if raw is None:
            self.pcal_state = 'error'
            self.pcal_msg = 'run the test first'
            return
        self.pcal_points[stage] = (raw, measured)
        sensor = self.pressure_sensor
        if 'pre' in self.pcal_points and 'brew' in self.pcal_points and \
                abs(self.pcal_points['brew'][0] - self.pcal_points['pre'][0]) > 1.0:
            (r1, m1), (r2, m2) = self.pcal_points['pre'], self.pcal_points['brew']
            gain = (m2 - m1) / (r2 - r1)
            offset = m1 - gain * r1
        else:
            gain = sensor.gain
            offset = measured - gain * raw
        if not sensor.calibration_valid(gain, offset):
            self.pcal_state = 'error'
            self.pcal_msg = 'rejected gain %.3f offset %.2f' % (gain, offset)
            del self.pcal_points[stage]
            return
        sensor.set_calibration(gain, offset)
        self.pcal_stage = stage
        self.pcal_state = 'corrected'
        self.pcal_msg = 'gauge %.1f / target %.1f bar' % (measured, self.pcal_target)

    def get_pcal_window_ms(self):
        return getattr(self, 'pcal_window_ms', 500)

    def set_pcal_window_ms(self, ms):
        # Fine-phase window: how often a single stroke may fire. A measurement knob like fwin:, not
        # persisted, so a swept value cannot survive a reboot into normal use.
        try:
            ms = int(ms)
        except (TypeError, ValueError):
            return self.get_pcal_window_ms()
        if ms < 100:
            ms = 100
        elif ms > 2000:
            ms = 2000
        self.pcal_window_ms = ms
        return self.pcal_window_ms

    def request_pressure_zero(self):
        self.pzero_request = True

    def take_pressure_zero_request(self):
        if not self.pzero_request:
            return False
        self.pzero_request = False
        return True

    def request_pressure_capture(self, ms=2000):
        if self.dev_safe:
            return False
        self.pcap_request = min(2500, max(200, int(ms)))
        self.pcap_abort = False
        return True

    def take_pressure_capture_request(self):
        ms = self.pcap_request
        self.pcap_request = None
        return ms

    def stop_pressure_capture(self):
        self.pcap_request = None
        self.pcap_abort = True

    def request_pressure_sweep(self, ms=2000):
        if self.dev_safe:
            return False
        self.psweep_request = min(2500, max(200, int(ms)))
        self.psweep_abort = False
        return True

    def take_pressure_sweep_request(self):
        ms = self.psweep_request
        self.psweep_request = None
        return ms

    def abort_pressure_sweep(self):
        self.psweep_request = None
        self.psweep_abort = True

    def request_mains_calibration(self, ms=2000):
        if self.dev_safe: return False
        self.mcal_request = min(5000, max(500, int(ms)))
        self.mcal_abort = False
        return True

    def take_mains_calibration_request(self):
        ms, self.mcal_request = self.mcal_request, None
        return ms

    def request_pressure_step(self, target):
        if self.dev_safe: return False
        self.pstep_request = float(target)
        self.pstep_abort = False
        return True

    def take_pressure_step_request(self):
        target, self.pstep_request = self.pstep_request, None
        return target

    def abort_pressure_step(self):
        self.pstep_request = None
        self.pstep_abort = True

    def request_pressure_gap(self, target):
        if self.dev_safe: return False
        self.pgap_request = float(target)
        self.pgap_abort = False
        return True

    def take_pressure_gap_request(self):
        target, self.pgap_request = self.pgap_request, None
        return target

    def abort_pressure_gap(self):
        self.pgap_request = None
        self.pgap_abort = True

    def request_pressure_clock(self, target):
        if self.dev_safe: return False
        self.vkello_request, self.vkello_abort = float(target), False
        return True

    def take_pressure_clock_request(self):
        target, self.vkello_request = self.vkello_request, None
        return target

    def abort_pressure_clock(self):
        self.vkello_request, self.vkello_abort = None, True

    def request_phase_sweep(self, reps):
        if self.dev_safe: return False
        self.vsweep_request, self.vsweep_abort = max(1, min(5, int(reps))), False
        return True

    def take_phase_sweep_request(self):
        reps, self.vsweep_request = self.vsweep_request, None
        return reps

    def abort_phase_sweep(self):
        self.vsweep_request, self.vsweep_abort = None, True

    def request_pressure_len(self, target):
        if self.dev_safe: return False
        self.plen_request = float(target)
        self.plen_abort = False
        return True

    def take_pressure_len_request(self):
        target, self.plen_request = self.plen_request, None
        return target

    def abort_pressure_len(self):
        self.plen_request = None
        self.plen_abort = True

    def request_pressure_vent(self):
        if self.dev_safe: return False
        self.pvent_request = True
        self.pvent_abort = False
        return True

    def take_pressure_vent_request(self):
        r, self.pvent_request = self.pvent_request, False
        return r

    def abort_mains_calibration(self):
        self.mcal_request, self.mcal_abort = None, True

    def request_pressure_hold(self, seconds=30):
        if self.dev_safe:
            return False
        self.phold_request = min(120, max(1, int(seconds)))
        self.phold_abort = False
        return True

    def take_pressure_hold_request(self):
        seconds = self.phold_request
        self.phold_request = None
        return seconds

    def stop_pressure_hold(self):
        self.phold_request = None
        self.phold_abort = True

    def request_throttle_warmup(self, seconds=60):
        if self.dev_safe:
            return False
        self.klamp_request = min(120, max(10, int(seconds)))
        self.klamp_abort = False
        return True

    def take_throttle_warmup_request(self):
        seconds = self.klamp_request
        self.klamp_request = None
        return seconds

    def stop_throttle_warmup(self):
        self.klamp_request = None
        self.klamp_abort = True

    def pressure_calibration_save(self):
        self.pressure_sensor.save_calibration()
        self.pcal_state = 'saved'
        self.pcal_msg = 'saved'

    def pressure_calibration_end_session(self):
        # Leaving the wizard: unsaved changes are dropped by reloading the file
        self.pcal_cancel = True
        self.pcal_request = None
        self.pressure_sensor.load_calibration()
        self.pcal_raw = {}
        self.pcal_points = {}
        self.pcal_state = 'idle'
        self.pcal_stage = ''
        self.pcal_msg = ''

    def get_pressure_calibration_status(self):
        return {
            'pcal_state' : self.pcal_state,
            'pcal_stage' : self.pcal_stage,
            'pcal_msg'   : self.pcal_msg[:40],
            'pcal_gain'  : round(self.pressure_sensor.gain, 4),
            'pcal_offset': round(self.pressure_sensor.offset, 3),
        }

    def _guard_pressure(self):
        # Relay guard's own reading (timer callback): a short ADC burst, independent of whatever
        # the running path reads or does not read. Same factory formula and calibration as above.
        # Returns (bar, raw_bar): raw_bar is uncalibrated, for the sensor plausibility check.
        ps = self.pressure_sensor
        s = 0
        for _ in range(4):
            s += ps.pressure_sensor.read_u16()
        raw_bar = (s / 4) * 0.000314936 - 3.522929
        return ps.gain * raw_bar + ps.offset, raw_bar

    def get_pressure_raw(self):
        return self.pressure_sensor.last_raw_bar

    def get_pressure_average(self, utime):
        # Non-blocking 100 ms rolling average for pump control; also updates the telemetry value
        self.pressure = self.pressure_sensor.sample_average(utime)
        return self.pressure

    def get_pressure(self):
        self.pressure = self.pressure_sensor.get_pressure()
        pressure = self.pressure
        
        return pressure


    def get_boiler_temperature(self):
        # During a shot core 1 reads (TemperatureSensor.c1_on): the properties below give its reading and time
        if not self.temperature_sensor.c1_active():
            self.boiler_temperature = self.temperature_sensor.read_temperature()
            self.boiler_temperature_ms = self.relay_guard.utime.ticks_ms()
        boiler_temperature = self.boiler_temperature
        
        return boiler_temperature

    # Boiler temperature and the ticks_ms of its reading (EXPRESSO-TEMPSTALE-JA-OLETUS): while core 1 reads during a
    # shot, its latest reading, so the relay guard sees it fresh without the shot loop reading anything
    @property
    def boiler_temperature(self):
        t = self.temperature_sensor.c1_temperature()
        return self._boiler_temperature if t is None else t

    @boiler_temperature.setter
    def boiler_temperature(self, t):
        self._boiler_temperature = t

    @property
    def boiler_temperature_ms(self):
        ms = self.temperature_sensor.c1_ms()
        return self._boiler_temperature_ms if ms is None else ms

    @boiler_temperature_ms.setter
    def boiler_temperature_ms(self, ms):
        self._boiler_temperature_ms = ms
    

    def get_heating_speed(self):
        self.heating_speed = self.heating_speed_calculator.get_heating_speed(self.boiler_temperature)
        heating_speed = self.heating_speed
        
        return heating_speed
    
    
    def get_boiler_stats(self):
        boiler_temperature = self.boiler_temperature
        brew_temperature   = self.brew_temperature
        steam_temperature  = self.steam_temperature
        heating_speed      = self.heating_speed
        
        return boiler_temperature, brew_temperature, steam_temperature, heating_speed
    
    def get_weight(self):
        return self.weight

    def get_weight_ms(self):
        return self.weight_ms

    def get_flow(self):
        return self.flow

    def get_flow_window_ms(self):
        return self.flow_window_ms

    def set_flow_window_ms(self, ms):
        try:
            ms = int(ms)
        except (TypeError, ValueError):
            return self.flow_window_ms
        if ms < 200:
            ms = 200
        elif ms > 3000:
            ms = 3000
        self.flow_window_ms = ms
        return self.flow_window_ms

    def get_flow_mode(self):
        return getattr(self, 'flow_mode', False)

    def set_flow_mode(self, enabled):
        self.flow_mode = bool(enabled)
        return self.flow_mode

    def get_flow_target(self):
        return getattr(self, 'flow_target', 2.2)

    def set_flow_target(self, g_s):
        try:
            g_s = float(g_s)
        except (TypeError, ValueError):
            return self.get_flow_target()
        if g_s < 0.5:
            g_s = 0.5
        elif g_s > 5.0:
            g_s = 5.0
        self.flow_target = g_s
        return self.flow_target

    def get_weight_limit(self):
        return self.weight_limit

    def get_weight_rise_limit(self):
        return self.weight_rise_limit

    def set_weight_rise_limit(self, grams):
        try:
            grams = float(grams)
        except (TypeError, ValueError):
            return self.weight_rise_limit
        if grams < 0:
            grams = 0.0
        elif grams > 5000:
            grams = 5000.0
        self.weight_rise_limit = grams
        self.setting_changed = True
        return self.weight_rise_limit

    def set_weight_limit(self, grams):
        try:
            grams = float(grams)
        except (TypeError, ValueError):
            return self.weight_limit
        if grams < 0:
            grams = 0.0
        elif grams > 5000:
            grams = 5000.0
        self.weight_limit = grams
        self.setting_changed = True
        return self.weight_limit

    def get_pump_ratio(self):
        pump_ratio = self.pump_ratio
        
        return pump_ratio
    
    # ===== GETTERS - TIMES ====== #
    
    def get_pressure_soft_release_time(self):
        time = self.pressure_soft_release_time
        
        return time
    
    
    def get_pre_infusion_time(self):
        time = self.pre_infusion_time
        
        return time
    
    
    def get_pre_heat_time(self):
        pre_heat_time = self.pre_heat_time
        
        return pre_heat_time
    
    
    # ===== GETTERS - SWITCHES ====== #
    
    def get_switch_brew(self):
        SWITCH_BREW = self.SWITCH_BREW
        
        return SWITCH_BREW
    
    
    def get_switch_water(self):
        SWITCH_WATER = self.SWITCH_WATER
        
        return SWITCH_WATER
    
    
    def get_switch_steam(self):
        SWITCH_STEAM = self.SWITCH_STEAM
        
        return SWITCH_STEAM
    
    
    def get_switches(self):
        SWITCH_BREW  = self.SWITCH_BREW
        SWITCH_WATER = self.SWITCH_WATER
        SWITCH_STEAM = self.SWITCH_STEAM
        
        return SWITCH_BREW, SWITCH_WATER, SWITCH_STEAM
    
    
    # ===== GETTERS - LEDS ====== #
    
    def get_leds(self):
        LED_SWITCH_BREW  = self.LED_SWITCH_BREW  
        LED_SWITCH_WATER = self.LED_SWITCH_WATER 
        LED_SWITCH_STEAM = self.LED_SWITCH_STEAM
        
        return LED_SWITCH_BREW, LED_SWITCH_WATER, LED_SWITCH_STEAM
    
    
    # ===== GETTERS - RELAYS ====== #
    
    def get_relays(self):
        RELAY_PUMP     = self.RELAY_PUMP
        RELAY_SOLENOID = self.RELAY_SOLENOID
        RELAY_HEATER   = self.RELAY_HEATER
        
        return RELAY_PUMP, RELAY_SOLENOID, RELAY_HEATER

# ============================================================================
# PUMP PRESSURE CONTROLLER
# ============================================================================

class PumpPressureController:
    """Pump pressure control, called every loop (~20-25 ms) (17.9.2026).

    History: the old loops decided the pump only every ~0.2-0.3 s (MAX31865 read >= 75 ms per
    iteration, 50 ms sleep, 35 ms pulses) -> overshoot and droop to ~6 bar. The first fix was fast
    on/off control (mode 'bang'); a real shot on a coffee puck (17.9.2026, target 8 bar) still swung
    6.1-10.0 bar (sd 0.61) because pump and sensor react with ~60-80 ms delay.

    Mode 'pi' (default): duty = ff + kp*e + ki*integral, clamped 0..1, applied as time-proportional
    on/off inside a 100 ms window in whole ~17 ms steps (one 60 Hz mains cycle). Integral has
    anti-windup (frozen while the duty is saturated). Fitted simulation: true pressure sd 0.5 -> 0.26.
    """
    def __init__(self, relay, pump_ratio_calculator, utime, mode='pi', band=0.3, min_switch_ms=17,
                 kp=0.2, ki=0.3, ff=0.5, window_ms=100, step_ms=17, max_duty=1.0,
                 continuous_error=1.0):
        # Steps of one 60 Hz mains cycle (~17 ms, one pump stroke): the machine runs on 60 Hz (user)
        self.relay = relay
        self.ratio = pump_ratio_calculator
        self.utime = utime
        self.mode = mode
        self.band = band
        self.min_switch_ms = min_switch_ms
        self.kp = kp
        self.ki = ki
        self.ff = ff
        self.window_ms = window_ms
        self.step_ms = step_ms
        self.max_duty = max_duty
        # Never chop the pump while the pressure is far below the target (user, 18.9.2026): a flush
        # with no puck never leaves ~0.5 bar, and time-proportional control at max_duty < 1 would
        # pulse the pump for the whole flush. The relay is held on, no window, when the error is
        # above this or the pressure is under half the target (the absolute limit alone would leave
        # low targets - the slider goes down to 1 bar - chopping during a flush).
        self.continuous_error = continuous_error
        self.integral = 0.0
        self.duty = 0.0
        self.filtered = 0.0
        # Slow average of the applied duty (tau 5 s): learned feed-forward for the next shot
        self.duty_avg = ff
        self.on = False
        now = utime.ticks_ms()
        # Allow the first switch immediately
        self.last_switch = utime.ticks_add(now, -min_switch_ms)
        self.last_update = now
        self.window_start = utime.ticks_add(now, -window_ms)
        relay.value(0)
        pump_ratio_calculator.set_pump_off()

    def _set(self, on, now, force=False):
        if on == self.on:
            return
        if not force and self.utime.ticks_diff(now, self.last_switch) < self.min_switch_ms:
            return
        self.on = on
        self.last_switch = now
        self.relay.value(1 if on else 0)
        if on:
            self.ratio.set_pump_on()
        else:
            self.ratio.set_pump_off()

    def update(self, pressure, target):
        now = self.utime.ticks_ms()
        # Input is already the 100 ms rolling average (PressureSensor.sample_average)
        self.filtered = pressure
        if self.mode == 'bang':
            # Band centred on the target so the mean pressure equals the target
            if pressure < target - self.band / 2:
                self._set(True, now)
            elif pressure >= target + self.band / 2:
                self._set(False, now)
            return self.on

        dt = self.utime.ticks_diff(now, self.last_update) / 1000.0
        self.last_update = now
        if dt > 0.2:
            dt = 0.2
        error = target - pressure
        if error > self.continuous_error or pressure < target * 0.5:
            # Far below the target: run the pump continuously, no time-proportional window. The
            # integral is left untouched (anti-windup) and the window is restarted so the first
            # window after the hand-over to PI control is a full one.
            self.duty = 1.0
            self.duty_avg += (self.duty - self.duty_avg) * (dt / 5.0)
            self.window_start = now
            self._set(True, now, force=True)
            return self.on
        duty = self.ff + self.kp * error + self.ki * self.integral
        # Anti-windup against the *applied* limit, not a fixed 1.0: the pre-infusion build-up runs
        # at max_duty 0.25 near the target, and comparing to 1.0 let the integral grow for the whole
        # slow step. It then discharged the moment the hold restored max_duty 1.0 -> the measured
        # 2.0 -> 3.84 bar overshoot on a real shot (18.9.2026 06:56:42).
        if 0.0 < duty < self.max_duty or (duty >= self.max_duty and error < 0) or (duty <= 0.0 and error > 0):
            self.integral += error * dt
            if self.integral > 1.5:
                self.integral = 1.5
            elif self.integral < -1.5:
                self.integral = -1.5
        duty = self.ff + self.kp * error + self.ki * self.integral
        self.duty = 0.0 if duty < 0.0 else (self.max_duty if duty > self.max_duty else duty)
        self.duty_avg += (self.duty - self.duty_avg) * (dt / 5.0)

        if self.utime.ticks_diff(now, self.window_start) >= self.window_ms:
            self.window_start = now
        on_ms = int(self.duty * self.window_ms / self.step_ms + 0.5) * self.step_ms
        self._set(self.utime.ticks_diff(now, self.window_start) < on_ms, now, force=True)
        return self.on

    def apply_duty(self, duty, pressure=None):
        """Apply a duty computed elsewhere (outer FlowController, VIRTAUSSAATO-2 18.9.2026) through
        the same time-proportional window as update()'s tail. No PI, no continuous_error branch, no
        integral: the caller already decided the duty."""
        now = self.utime.ticks_ms()
        if pressure is not None:
            self.filtered = pressure
        dt = self.utime.ticks_diff(now, self.last_update) / 1000.0
        self.last_update = now
        if dt > 0.2:
            dt = 0.2
        self.duty = duty
        self.duty_avg += (self.duty - self.duty_avg) * (dt / 5.0)
        if self.utime.ticks_diff(now, self.window_start) >= self.window_ms:
            self.window_start = now
        on_ms = int(self.duty * self.window_ms / self.step_ms + 0.5) * self.step_ms
        self._set(self.utime.ticks_diff(now, self.window_start) < on_ms, now, force=True)
        return self.on

    def stop(self):
        self.on = False
        self.relay.value(0)
        self.ratio.set_pump_off()


# ============================================================================
# FLOW CONTROLLER (outer duty loop, VIRTAUSSAATO-2 18.9.2026)
# ============================================================================

class FlowController:
    """Outer flow loop: PI on flow (g/s) that outputs a pump duty (0-1) directly, with pressure
    only as a ceiling override, applied via PumpPressureController.apply_duty. See
    paketit/VIRTAUSSAATO-2.spec.md. Replaces the pressure-setpoint cascade (VIRTAUSSAATO.spec.md):
    that cascade asked for a *pressure*, and an open valve needs a *high* duty to hold pressure
    low, so the cascade asked for the wrong quantity (paketit/VIRTAUSSAATO-2.md)."""
    def __init__(self, utime, target, duty_start, kp=0.17, ki=0.13, p_max=10.5, p_margin=3.0,
                 update_ms=100, stale_limit=3):
        self.utime = utime
        self.target = target
        self.kp = kp
        self.ki = ki
        self.p_max = p_max
        self.p_margin = p_margin
        self.update_ms = update_ms
        self.stale_limit = stale_limit
        self.duty = float(duty_start)
        self.e_prev = None
        self.e_avg = None
        self.stale = 0
        self.failed = False
        self.sat_ms = 0.0
        self.saturated = False
        self.last_update = utime.ticks_ms()

    def set_target(self, target):
        self.target = target

    def update(self, flow, pressure):
        if self.failed:
            return None
        now = self.utime.ticks_ms()
        if self.utime.ticks_diff(now, self.last_update) < self.update_ms:
            return self.duty
        dt = self.utime.ticks_diff(now, self.last_update) / 1000.0
        if dt > 0.5:
            dt = 0.5
        self.last_update = now
        if flow is None:
            self.stale += 1
            if self.stale >= self.stale_limit:
                self.failed = True
                return None
            return self.duty
        self.stale = 0
        e = self.target - flow
        de = 0.0 if self.e_prev is None else e - self.e_prev
        self.e_prev = e
        duty_new = self.duty + self.kp * de + self.ki * e * dt
        # Pressure ceiling override (VIRTAUSSAATO-2 rule 2), not a setpoint: cap is how much duty
        # headroom is left before p_max, and the applied duty is min(duty_pi, duty_cap).
        cap = (self.p_max - pressure) / self.p_margin
        cap = 0.0 if cap < 0.0 else (1.0 if cap > 1.0 else cap)
        self.duty = min(max(duty_new, 0.0), 1.0, cap)
        # VIRTAUSSAATO-2.correction-5.md K8: fsat measures the filtered error, not "is the cap
        # binding right now" (that was unobservable in the log and noise-driven: duty wobbles
        # around the cap, and every dip leaked the counter dry). e_avg is a 1.0 s low-pass on e;
        # the 0.2 g/s threshold is 3x the filtered noise floor (scale noise 0.21 g/s -> ~0.07 g/s
        # after the 1.0 s filter). The lower branch (duty pinned at 0) is gone: the pump is the
        # only water source, so zero duty is zero flow, not a state the flag needs to catch.
        # sat_ms stays a leaky counter and saturated a Schmitt trigger (correction-3 K7, unchanged).
        self.e_avg = e if self.e_avg is None else self.e_avg + (e - self.e_avg) * min(1.0, dt / 1.0)
        if self.e_avg > 0.2:
            self.sat_ms += dt * 1000
        else:
            self.sat_ms -= 0.5 * dt * 1000
        self.sat_ms = 0.0 if self.sat_ms < 0.0 else (2000.0 if self.sat_ms > 2000.0 else self.sat_ms)
        if self.sat_ms >= 2000:
            self.saturated = True
        elif self.sat_ms <= 0:
            self.saturated = False
        return self.duty


# ============================================================================
# PRESSURE MONITOR
# ============================================================================

class PressureSensor:
    def __init__(self, utime, asyncio_module, Pin, PINS, ADC):
        
        self.pressure_sensor  = ADC(Pin(PINS['PRESSURE_ADC']))
        self.asyncio          = asyncio_module
        self.utime            = utime
        self.number_of_cycles = 1
        self.time_start       = 0
        # Calibration (17.9.2026): bar = gain * raw_bar + offset, raw_bar from the factory formula.
        # Set with the app's pressure calibration wizard, stored in pressure_cal.json.
        self.gain             = 1.0
        self.offset           = 0.0
        self.last_raw_bar     = 0.0
        self.load_calibration()


    CAL_FILE = 'pressure_cal.json'

    # Rolling average for pump control (17.9.2026). The vibratory pump delivers pressure in mains
    # strokes; the machine runs on 60 Hz (user), so the averaging window is one cycle, 1/60 s, as in
    # get_pressure(). sample_average() is the non-blocking version: a short ADC burst every loop
    # iteration, averaged over all bursts of the last cycle. (A 100 ms window was too long, and a 20 ms
    # window assumed 50 Hz.)
    WINDOW_US = 16667

    def sample_average(self, utime, window_us=None, burst=8):
        window_us = window_us or self.WINDOW_US
        s = 0
        for _ in range(burst):
            s += self.pressure_sensor.read_u16()
        raw_bar = (s / burst) * 0.000314936 - 3.522929
        now = utime.ticks_us()
        buf = getattr(self, '_avg_buf', None)
        if buf is None:
            buf = []
            self._avg_buf = buf
        buf.append((now, raw_bar))
        while len(buf) > 1 and utime.ticks_diff(now, buf[0][0]) > window_us:
            buf.pop(0)
        total = 0.0
        peak = -99.0
        for _, v in buf:
            total += v
            if v > peak:
                peak = v
        avg_raw = total / len(buf)
        self.last_raw_bar = avg_raw
        self.window_peak = round(self.gain * peak + self.offset, 1)
        return round(self.gain * avg_raw + self.offset, 2)

    def reset_average(self):
        self._avg_buf = []

    @staticmethod
    def calibration_valid(gain, offset):
        return 0.5 <= gain <= 1.5 and -3.0 <= offset <= 3.0

    def load_calibration(self):
        import json
        try:
            with open(self.CAL_FILE, 'r') as f:
                data = json.load(f)
            gain = float(data.get('gain', 1.0))
            offset = float(data.get('offset', 0.0))
            if self.calibration_valid(gain, offset):
                self.gain, self.offset = gain, offset
            else:
                self.gain, self.offset = 1.0, 0.0
        except Exception:
            self.gain, self.offset = 1.0, 0.0

    def set_calibration(self, gain, offset):
        self.gain = gain
        self.offset = offset

    def save_calibration(self):
        import json
        with open(self.CAL_FILE, 'w') as f:
            json.dump({'gain': self.gain, 'offset': self.offset}, f)


    def get_pressure(self):
        
        pressure_sensor = self.pressure_sensor
        utime = self.utime
        # Running sum, no list: the list grew to ~2000 samples (8 kB) per call and a fragmented heap
        # could not allocate it -> MemoryError killed main (28.9.2026, kuri2; vika 14).
        total = 0

        start = utime.ticks_us()
        end = utime.ticks_add(start, 16667) # one 60 Hz mains cycle (pump stroke), as in the original
        cycle_counter = 0
        # Make timed cycle for collecting sensor values
        while utime.ticks_diff(end, utime.ticks_us()) > 0:
            total += pressure_sensor.read_u16()
            cycle_counter += 1

        # Calculate average for one cycle
        cycle_average = round(total / cycle_counter)
            
        # Convert pressure to bar (factory formula), then apply calibration
        raw_bar = cycle_average * 0.000314936 - 3.522929
        self.last_raw_bar = raw_bar
        pressure_bar = round(self.gain * raw_bar + self.offset, 1)
        
        return pressure_bar
    
    
    def get_pressure_while(self, measure_time):
    
        pressure_sensor = self.pressure_sensor
        utime = self.utime
        pressure = 0
        number_of_cycles = self.number_of_cycles
        pressure_cycle_values = []
        pressure_measurements_values = []
        
        # Calculate time used for measurements 
        count_of_full_measurements = measure_time / (0.017 * number_of_cycles) # Later number of cycles could be calculated based of time given
        
        # Make for loop timed for whole measurement
        for x in range(count_of_full_measurements):
            
            # Make for loop for averaging measurement values
            for y in range(number_of_cycles):
                
                start = utime.ticks_us()
                end = utime.ticks_add(start, 17000) # one cycle == one Hz
                cycle_counter = 0
                # Make timed cycle for collecting sensor values
                while utime.ticks_diff(end, utime.ticks_us()) > 0:
                    
                    # Read value of the sensor
                    pressure_sensor_value = pressure_sensor.read_u16()
                    
                    # Add value to lisr
                    pressure_measurements_values.append(pressure_sensor_value)
                    
                    #increment cycle counter
                    cycle_counter += 1
                
                # Calculate average for one cycle
                cycle_average = round(sum(pressure_measurements_values) / cycle_counter)
                
                # Add cycle average to list
                pressure_cycle_values.append(cycle_average)

                # Reset measurement list
                pressure_measurements_values.clear()
                
            # Calculate pressure value from averages
            pressure = round(sum(pressure_cycle_values) / len(pressure_cycle_values))
            
            # Reset pressure_cycle_values list
            pressure_cycle_values.clear()
            
            # Convert pressure to bar
            pressure_bar = round((pressure * 0.000314936 - 3.522929),1)
            
            # Print pressure
            #print("Pressure: " +str(pressure_bar) +" Bar")
    

# ============================================================================
# THERMOSTAT
# ============================================================================

class Thermostat:
    def __init__(self, brew_data, TARGET_TEMPERATURES, RELAY_HEATER, temperature_sensor):
        self.cycle_count = 0
        self.brew_data = brew_data
        self.brew_mode = ""
        self.TARGET_TEMPERATURES = TARGET_TEMPERATURES
        self.RELAY_HEATER = RELAY_HEATER
        self.state = 'NOT READY'
        self.temperature_sensor = temperature_sensor

        
    def run(self): # def run(self, brew_data, switch_steam, RELAY_HEATER):
        
        # Get brew mode
        mode               = self.brew_data.get_mode()
        heating_speed      = self.brew_data.get_heating_speed()
        boiler_temperature = self.temperature_sensor.read_temperature()
        target_temperature = self.brew_data.get_target_temperature()
        

        # Nullify negative heating speed values
        if heating_speed < 0:
            heating_speed = 0
            
        # If boiler temperature is lower than target temperature - heating speed
        if (boiler_temperature < (target_temperature - (heating_speed * 2))):
            
            # Start heating the boiler          
            if (Thermostat.heat_cycler(self, boiler_temperature, target_temperature)):
                #print("target_temperature" + str(target_temperature))
                self.RELAY_HEATER.value(1)
            else:
                self.RELAY_HEATER.value(0)
                
        # Othervice, stop heating the boiler
        else:
            self.RELAY_HEATER.value(0)
    
  
        if abs(target_temperature - boiler_temperature) <= 1:
            self.state = 'READY' 
        elif boiler_temperature > target_temperature: 
            self.state = 'TEMPERATURE HIGH' 
        else:
            self.state = 'NOT READY'
    
    
    def get_state(self):
        state = self.state
        return state
    

    def heat_cycler(self, temperature, target_temperature):
        return_bool = False
        cycle_count = self.cycle_count
        
        # Calculate temperature difference
        temperature_difference = int((temperature - target_temperature) *100)
    
        # Calculate heating ratio of cycle from distance to target temperature
        if (abs(temperature_difference / 9) > cycle_count):
            return_bool = True
        else:
            return_bool = False
        
        if (cycle_count >= 90):
            cycle_count = 0
        else:
            cycle_count = cycle_count +10
        
        self.cycle_count = cycle_count
        
        if return_bool:
            return True
        else:
            return False


# ============================================================================
# HEATING SPEED CALCULATOR
# ============================================================================

class HeatingSpeedCalculator:
    def __init__(self, utime_module, asyncio_module):
        self.temperature_begin = 20.0
        self.asyncio = asyncio_module
        self.utime = utime_module
        self.time_start = 0
        self.first_measure_flag = True
   
   
    # Function to calculate heating speed
    def get_heating_speed(self, temperature_now):
        
        # Get time now
        time_now = self.utime.ticks_ms()
        
        # Calculate time between now and starting point
        time_between = self.utime.ticks_diff(time_now, self.time_start)
        
        if time_between == 0:
            return self.heating_speed
        
        # Set time now as start time
        self.time_start = time_now

        # Calculate temperature change between now and starting point
        temperature_between = temperature_now - self.temperature_begin
        
        # Set temperature now to start temperature
        self.temperature_begin = temperature_now
        
        # Calculate heating speed
        self.heating_speed = temperature_between / time_between * 10000 # * self.heating_speed_multiplier
        
        # Round heating speed
        heating_speed = round(self.heating_speed, 2)
        
        # If first measure: set speed to 0 and reset flag
        if self.first_measure_flag:
            self.first_measure_flag = False
            heating_speed = 0
            
        # If value is unacceptale, place error
        if heating_speed > 100 or heating_speed < -100:
            heating_speed = 0
            
        return heating_speed
  

# ============================================================================
# TEMPERATURE SENSOR
# ============================================================================

# Boiler temperature on core 1 while a shot runs (EXPRESSO-TEMPSTALE-JA-OLETUS, 28.9.2026). A whole MAX31865 reading
# blocks >= 75 ms, which the shot loops cannot take, and without a reading the relay guard blocks the heater after 10 s
# (GUARD_TRIP heater reason=tempstale in every bim:1 run, 28.9.2026). Reading it in short steps inside the shot loop
# cost the smoke's pump control (case 10 hold mean +0.029 -> +0.067 bar), so core 1 reads it instead: run_shot hands it
# the sensor (c1_on) and takes it back (c1_off). Since C1-JAKSOT vaihe 2 (20.10.2026) core 1 reads at rest too
# (c1_rest_on at boot): core 0's read_rtd slept 75 ms twice a main loop round (HB lmax_us 175-295 ms, l100 ~330/min),
# so a shot's c1_on/c1_off only marks its counts and core 1 keeps the sensor; c1_take gives it back to core 0 (ystall's
# tests without the temperature, or core 1 stopped). Core 1 runs with the heap locked
# (an allocation there could start a GC in the middle of a pump loop) and only integers: the 7-reading average is in
# 0.01 C, converted with a table built on core 0 from the driver's own formula (interpolation error < 0.01 C).
TEMP_C1_BIAS_MS  = 10         # the driver's read_rtd gaps
TEMP_C1_CONV_MS  = 65
TEMP_C1_EVERY_MS = 250        # a reading this often; the relay guard's limit is 10 s
TEMP_C1_STOP_MS  = 300        # c1_off waits this long for a reading in progress to end
TEMP_C1_RAW_LO   = 4096       # conversion table: raw 4096..16384 in steps of 256 (about -85..+330 C)
TEMP_C1_RAW_N    = 48
TEMP_C1_MIN_CDEG = 200        # read_temperature's 2..200 C
TEMP_C1_MAX_CDEG = 20000
# c1 state (array 'i'), shared by the cores: every field one word, written by one core only (WANT, T0 core 0; the rest
# core 1, RI and GAP also core 0 while core 1 is idle). NBAD and LAST: bad readings in a row and the time of the last good
# one, kept here so that the reading loop and the executor share _c1_put.
# RST (0 sets, 1 clears): a shot started from the rest reading, so core 1 starts GAP, BAD and LAST again.
C1_WANT, C1_IDLE, C1_SEQ, C1_CDEG, C1_MS, C1_BAD, C1_GAP, C1_ERR, C1_RI, C1_RUN, C1_T0, C1_NBAD, C1_LAST, C1_RST = range(14)
# Core 1 never sleeps (EXPRESSO-C1-JAKSOT vaihe 2): a sleep_ms on core 1 stretched core 0's collections at rest from
# ~20 ms to 80-600 ms and its sleep_ms(0) turns to 65 ms during a reading (GC-UUTTO, 20.10.2026), so every wait on core 1
# spins on ticks_us.
# Core 1 executor (EXPRESSO-C1-JAKSOT vaihe 1, paketit/C1-JAKSOT.md; WANT 3): 1 kHz samples into a ring that core 0
# reads, relay events from a queue that core 0 fills ahead. Rings in array('i'): samples (t_us, raw) and events
# (t_us, on). Indices only grow; position = index % size. Writer of each field in brackets.
CX_NS = 256                   # samples: 256 ms of slack for core 0
CX_NE = 64                    # events
CX_SW, CX_SR, CX_EW, CX_ER, CX_N, CX_GMAX, CX_OVF, CX_NEV, CX_LMAX, CX_LATE, CX_STARVE, CX_ARMED, CX_LAST, \
    CX_DRY, CX_PIN, CX_LIDX, CX_LWR, CX_TEMP, CX_TS, CX_TC, CX_TR = range(21)
# SW (1) sample write, SR (0) sample read, EW (0) event write, ER (1) event read, N/GMAX/OVF (1) samples, gap max us,
# ring overruns, NEV/LMAX/LATE (1) events done, lateness max us, events > CX_LATE_US late, STARVE (1) cycles without
# an event, ARMED (0) starvation counted from the first event, LAST (1) time of the last event, DRY (0) 1 = record
# only, PIN (1) the relay state the executor last set (dry: the state it would have set), LIDX/LWR (1) the latest
# event's index and its write time minus its due time (us; > 0 = core 0 wrote it late), from cx_wt (0), TEMP (0)
# 1 = the executor also reads the boiler temperature (c1_on(3)), TS/TC/TR (1) the longest part of bias on, conversion
# start, and result and average (us, K3; rtd_part 0-6, _c1_put as part 7)
CX_LATE_US = 300              # = EU_LATE_MAX_US
CX_STARVE_US = 25000          # a mains cycle and a margin without an event
# Temperature between samples (vaihe 2): a MAX31865 step runs only when the next sample and the next relay event are
# both further than this, so it delays neither (K3: each step must take < 0.5 ms; one byte at 50 kHz, ~0.2 ms)
CX_TROOM_US = 700


#### Class for reading pt100 sensor temperature with max31865 ####
class TemperatureSensor:
    def __init__(self, max31865, PINS, MAX31865_CONFIG):
        self.temperature_sensor = max31865.MAX31865(
            # ref_resistor arvoksi noin 438.0 tai rtd_nominal arvoksi noin 100.7
            #  OG = rtd_nominal = 102.5, ref_resistor = 430.0
            wires        = MAX31865_CONFIG['NUMBER_OF_WIRES'],
            rtd_nominal  = MAX31865_CONFIG['RTD_NOMINAL'],
            ref_resistor = MAX31865_CONFIG['REF_RESISTOR'],
            pin_sck      = PINS['TEMP_SCK'],
            pin_mosi     = PINS['TEMP_MOSI'],
            pin_miso     = PINS['TEMP_MISO'],
            pin_cs       = PINS['TEMP_CS'],
            )
        self.temps = [0, 0, 0, 0, 0 ,0 ,0]
        self.temps_i = 0
        self.c1 = None


    # Function to get temperature from sensor
    def read_temperature(self):
        
        # During a shot core 1 owns the sensor: its latest average, or the last one of core 0 until core 1 has one
        if self.c1_active():
            t = self.c1_temperature()
            return t if t is not None else round(sum(self.temps) / len(self.temps), 2)

        # Create value for sifting bias of the temperature
        temperature_bias = 0
        
        # Get 7 temperature samples to list and calculate average to avoid the noise
        fault_counter = 0
        temp = self.temperature_sensor.temperature
        
        # Value error handling
        while (temp < 2 or temp > 200):
            print("Temperature sensor error")
            temp = self.temperature_sensor.temperature
            fault_counter += 1
            if fault_counter > 5:
                print("Permanent sensor error")
                return 200            
        
        self.temps[self.temps_i] = temp
        
        self.temps_i += 1
        
        if self.temps_i >= 7:
            self.temps_i = 0          

        # Calculate temperature average
        temperature = round((sum(self.temps) / len(self.temps)), 2)
                
        # Bias temperature value
        temperature = temperature + temperature_bias
        
        return temperature

    # ----- core 1 (EXPRESSO-TEMPSTALE-JA-OLETUS) -----
    def c1_start(self, utime):
        """Starts the core 1 reader once at boot; it idles until c1_on. Without _thread the sensor stays core 0's."""
        from array import array
        drv = self.temperature_sensor
        self.c1_utime = utime
        self.c1_ring = array('i', [0] * 7)
        self.c1_tab = array('i', [int(drv.temperature_from_rtd(TEMP_C1_RAW_LO + (k << 8)) * 100 + 0.5)
                                  for k in range(TEMP_C1_RAW_N + 1)])
        self.c1_seq0 = 0
        self.c1_log0 = 0              # C1_SEQ at the latest c1_on: c1_log's readings of a shot
        self.c1_rest = 0              # 1 = core 1 reads at rest too (c1_rest_on)
        st = array('i', [0] * 14)
        st[C1_IDLE] = st[C1_RUN] = 1
        self.c1 = st
        # ystall bit 64 (EXPRESSO-GC-UUTTO, TILAUS-O): core 1 jitter test, WANT 2. [0] ms asked; core 1 writes
        # [1] n, [2] max gap us, [3] gaps > 1.5 ms, [4] > 2 ms, [5] > 5 ms, [6] done
        self.c1_test = array('i', [0] * 7)
        self.c1_adc = None
        self.cx = array('i', [0] * 21)
        self.cx_wt = array('i', [0] * CX_NE)       # core 0's write time of each event slot
        self.cx_samp = array('i', [0] * (2 * CX_NS))
        self.cx_ev = array('i', [0] * (2 * CX_NE))
        self.cx_pin = None            # the pump's raw Pin (not GuardedRelay); dry runs leave it alone
        try:
            import _thread
            _thread.stack_size(6144)
            _thread.start_new_thread(self._c1_main, ())
            print('TEMP_C1 ready')
        except Exception as e:
            self.c1 = None
            print('TEMP_C1 none: %s' % e)

    def c1_reads(self):
        """True while core 1 owns the sensor: the reading loop (WANT 1) or the executor with TEMP (WANT 3)."""
        st = self.c1
        return st is not None and (st[C1_WANT] == 1 or (st[C1_WANT] == 3 and self.cx[CX_TEMP] == 1))

    def c1_active(self):
        return self.c1_reads() and self.c1[C1_RUN] == 1

    def c1_on(self, want=1):
        """Hands the sensor to core 1 (run_shot start). Its average goes on from core 0's readings. want 3: the
        executor reads it between its samples (cx set up by the caller, TEMP set here)."""
        st = self.c1
        if st is None or st[C1_RUN] == 0:
            return False
        if st[C1_WANT] == 1 and self.c1_rest:
            # Core 1 already reads (rest): it keeps the sensor and its average; the shot's counts start here. WANT 3
            # takes over after the reading in progress (the loop looks at WANT only between readings)
            st[C1_T0] = self.c1_utime.ticks_ms()
            self.c1_log0 = st[C1_SEQ]
            st[C1_RST] = 1
            if want == 3:
                self.cx[CX_TEMP] = 1
                st[C1_WANT] = 3
            return True
        if st[C1_WANT] != 0:
            return False
        ring = self.c1_ring
        for k in range(7):
            ring[k] = int(self.temps[k] * 100 + 0.5)
        st[C1_RI], st[C1_GAP], st[C1_BAD] = self.temps_i, 0, 0
        st[C1_T0] = self.c1_utime.ticks_ms()
        self.c1_seq0 = self.c1_log0 = st[C1_SEQ]
        if want == 3:
            self.cx[CX_TEMP] = 1
            st[C1_WANT] = 3
        else:
            st[C1_WANT] = 1
        return True

    def c1_off(self):
        """Ends a shot's use of core 1 (run_shot end) and the executor if it was reading. At rest core 1 keeps the
        sensor and goes back to its reading loop (the executor first finishes a half reading); otherwise c1_take."""
        st = self.c1
        if not self.c1_reads():
            return
        if self.c1_rest and st[C1_RUN] == 1:
            st[C1_WANT] = 1
            self.cx[CX_TEMP] = 0
            return
        self.c1_take()

    def c1_rest_on(self):
        """Core 1 reads the temperature at rest too (boot, and after c1_take): core 0 never waits for the chip."""
        if self.c1_on(1):
            self.c1_rest = 1
            print('TEMP_C1 rest')

    def c1_take(self):
        """Takes the sensor back to core 0: waits for a reading in progress, then core 0 goes on from core 1's
        average. Also ends the executor if it was reading. WANT stays 0 until c1_on or c1_rest_on."""
        st = self.c1
        if not self.c1_reads():
            return
        utime = self.c1_utime
        st[C1_WANT] = 0
        t0 = utime.ticks_ms()
        # Core 1 sets IDLE to 0 before it looks at WANT, and touches the SPI bus only after seeing WANT 1, so IDLE 1
        # seen here after WANT 0 means the bus is free
        while st[C1_IDLE] == 0 and st[C1_RUN] == 1:
            if utime.ticks_diff(utime.ticks_ms(), t0) > TEMP_C1_STOP_MS:
                print('TEMP_C1 stuck: idle not seen in %d ms' % TEMP_C1_STOP_MS)
                break
        ring = self.c1_ring
        for k in range(7):
            self.temps[k] = ring[k] / 100
        self.temps_i = st[C1_RI]
        self.cx[CX_TEMP] = 0

    def c1_temperature(self):
        """Core 1's latest average (C) since c1_on, else None."""
        st = self.c1
        if not self.c1_reads() or st[C1_SEQ] == self.c1_seq0:
            return None
        return st[C1_CDEG] / 100

    def c1_ms(self):
        """ticks_ms of core 1's latest reading since c1_on, else None."""
        st = self.c1
        if not self.c1_reads() or st[C1_SEQ] == self.c1_seq0:
            return None
        return st[C1_MS]

    def c1_log(self):
        """Fields for the shot's _END line: readings since c1_on, longest gap between them (ms), bad readings, 1 if
        core 1 stopped on an error; n=-1 without core 1."""
        st = self.c1
        if st is None:
            return 'c1_n=-1'
        return 'c1_n=%d c1_gap_ms=%d c1_bad=%d c1_err=%d' % (
            st[C1_SEQ] - self.c1_log0, st[C1_GAP], st[C1_BAD], st[C1_ERR])

    def _c1_main(self):
        import micropython
        st = self.c1
        micropython.heap_lock()
        try:
            self._c1_loop(st, self.c1_ring, self.c1_tab, self.temperature_sensor, self.c1_utime)
        except BaseException:
            # An allocation (heap locked) or an SPI error: stop, and core 0 reads the sensor again. During a shot the
            # relay guard then blocks the heater after 10 s (tempstale), as before this reader.
            st[C1_ERR] = 1
        micropython.heap_unlock()
        st[C1_IDLE] = 1
        st[C1_RUN] = 0

    def _c1_jitter(self, utime):
        """TILAUS-O feasibility (20.10.2026): a 1 kHz integer loop on core 1 with the heap locked, reading the pressure
        ADC like the shot loop, while core 0 collects. Records its own sample gaps; no relay is touched."""
        r = self.c1_test
        adc = self.c1_adc
        prev = utime.ticks_us()
        nxt = prev
        end = utime.ticks_add(prev, r[0] * 1000)
        n = gmax = g15 = g2 = g5 = 0
        while utime.ticks_diff(end, prev) > 0:
            nxt = utime.ticks_add(nxt, 1000)
            while utime.ticks_diff(nxt, utime.ticks_us()) > 0:
                pass
            now = utime.ticks_us()
            g = utime.ticks_diff(now, prev)
            prev = now
            if n:
                if g > gmax:
                    gmax = g
                if g > 1500:
                    g15 += 1
                if g > 2000:
                    g2 += 1
                if g > 5000:
                    g5 += 1
            if adc is not None:
                adc.read_u16()
            n += 1
        # One store per field: a 5-target assignment builds a tuple, which raised MemoryError with the heap locked
        # and ended the core 1 thread (c1_err=1, 1cd1bbf 20.10.2026)
        r[1] = n
        r[2] = gmax
        r[3] = g15
        r[4] = g2
        r[5] = g5
        r[6] = 1

    def _c1_put(self, st, ring, tab, raw, now):
        """One MAX31865 result into core 1's 7-reading average (0.01 C). Returns 1 for a good reading, 0 for a bad one
        (as read_temperature: the caller retries at once, and the sixth bad one in a row reads 200 C = heater guard
        overtemp). Shared by the reading loop and the executor."""
        if st[C1_RST]:
            st[C1_RST] = 0
            st[C1_GAP] = 0
            st[C1_BAD] = 0
            st[C1_LAST] = 0
        c = -1
        if TEMP_C1_RAW_LO <= raw < TEMP_C1_RAW_LO + (TEMP_C1_RAW_N << 8):
            j = (raw - TEMP_C1_RAW_LO) >> 8
            a = tab[j]
            c = a + (((tab[j + 1] - a) * (raw - TEMP_C1_RAW_LO - (j << 8)) + 128) >> 8)
        if c < TEMP_C1_MIN_CDEG or c > TEMP_C1_MAX_CDEG:
            st[C1_BAD] += 1
            b = st[C1_NBAD] + 1
            if b > 5:
                b = 0
                st[C1_CDEG] = TEMP_C1_MAX_CDEG
                st[C1_MS] = now
                st[C1_SEQ] += 1
            st[C1_NBAD] = b
            return 0
        st[C1_NBAD] = 0
        i = st[C1_RI]
        ring[i] = c
        i += 1
        if i >= 7:
            i = 0
        st[C1_RI] = i
        s = 0
        for k in range(7):
            s += ring[k]
        last = st[C1_LAST]
        gap = self.c1_utime.ticks_diff(now, last if last else st[C1_T0])
        if gap > st[C1_GAP]:
            st[C1_GAP] = gap
        st[C1_LAST] = now
        st[C1_CDEG] = (s + 3) // 7
        st[C1_MS] = now
        st[C1_SEQ] += 1
        return 1

    def _c1_exec(self, st, utime):
        """EXPRESSO-C1-JAKSOT: samples at 1 kHz and carries out relay events at their times while WANT is 3; with TEMP
        also reads the boiler temperature in steps between them (vaihe 2). Heap locked: integers, array stores and
        calls that return small ints only (no tuples, no floats)."""
        x = self.cx
        sm = self.cx_samp
        ev = self.cx_ev
        wt = self.cx_wt
        adc = self.c1_adc
        pin = None if x[CX_DRY] else self.cx_pin
        tt = x[CX_TEMP]
        drv = self.temperature_sensor
        ring = self.c1_ring
        tab = self.c1_tab
        tph = 0                       # next part: rtd_part 0-1 bias, 2-3 conversion, 4-6 result; 7 _c1_put
        traw = 0                      # part 6's raw reading for part 7
        prev = utime.ticks_us()
        nxt = prev
        tdue = prev                   # the next step not before this
        tst = prev                    # start of the reading in progress (TEMP_C1_EVERY_MS from here)
        x[CX_LAST] = prev
        while st[C1_WANT] == 3:
            nxt = utime.ticks_add(nxt, 1000)
            now = utime.ticks_us()
            while utime.ticks_diff(nxt, now) > 0:
                r = x[CX_ER]
                room = CX_TROOM_US + 1
                if r != x[CX_EW]:
                    i = (r % CX_NE) * 2
                    d = utime.ticks_diff(now, ev[i])
                    if d >= 0:
                        on = ev[i + 1]
                        if pin is not None:
                            pin.value(on)
                        x[CX_PIN] = on
                        if d > x[CX_LMAX]:
                            x[CX_LMAX] = d
                            x[CX_LIDX] = r
                            x[CX_LWR] = utime.ticks_diff(wt[r % CX_NE], ev[i])
                        if d > CX_LATE_US:
                            x[CX_LATE] += 1
                        x[CX_ER] = r + 1
                        x[CX_NEV] += 1
                        x[CX_LAST] = now
                        now = utime.ticks_us()
                        continue
                    room = -d
                elif x[CX_ARMED] and utime.ticks_diff(now, x[CX_LAST]) > CX_STARVE_US:
                    x[CX_STARVE] += 1
                    x[CX_LAST] = now
                if tt and room > CX_TROOM_US and utime.ticks_diff(now, tdue) >= 0 and \
                        utime.ticks_diff(nxt, now) > CX_TROOM_US:
                    if tph < 7:
                        raw = drv.rtd_part(tph)
                    if tph < 2:
                        if tph == 0:
                            tst = now
                        else:
                            tdue = utime.ticks_add(now, TEMP_C1_BIAS_MS * 1000)
                        k = CX_TS
                    elif tph < 4:
                        if tph == 3:
                            tdue = utime.ticks_add(now, TEMP_C1_CONV_MS * 1000)
                        k = CX_TC
                    else:
                        # the average apart from the SPI parts (K3: part 6 and _c1_put together took 0.86 ms, 20.10.2026)
                        if tph == 6:
                            traw = raw
                        elif tph == 7 and self._c1_put(st, ring, tab, traw, utime.ticks_ms()):
                            tdue = utime.ticks_add(tst, TEMP_C1_EVERY_MS * 1000)
                        k = CX_TR
                    tph = tph + 1 if tph < 7 else 0
                    d = utime.ticks_diff(utime.ticks_us(), now)
                    if d > x[k]:
                        x[k] = d
                now = utime.ticks_us()
            raw = adc.read_u16() if adc is not None else 0
            w = x[CX_SW]
            if w - x[CX_SR] >= CX_NS:
                x[CX_OVF] += 1
            i = (w % CX_NS) * 2
            sm[i] = now
            sm[i + 1] = raw
            x[CX_SW] = w + 1
            g = utime.ticks_diff(now, prev)
            prev = now
            if x[CX_N] and g > x[CX_GMAX]:
                x[CX_GMAX] = g
            x[CX_N] += 1
        # A reading left half way: finish its parts (CS back up, the conversion ended) before core 0 or the reading
        # loop takes the chip (c1_off waits for IDLE, which core 1 sets only after this returns); the result is dropped
        while tt and 0 < tph < 7:
            while utime.ticks_diff(tdue, utime.ticks_us()) > 0:
                pass
            drv.rtd_part(tph)
            if tph == 1:
                tdue = utime.ticks_add(utime.ticks_us(), TEMP_C1_BIAS_MS * 1000)
            elif tph == 3:
                tdue = utime.ticks_add(utime.ticks_us(), TEMP_C1_CONV_MS * 1000)
            tph = tph + 1 if tph < 6 else 0
        if pin is not None:
            pin.value(0)
        x[CX_PIN] = 0

    def _c1_loop(self, st, ring, tab, drv, utime):
        while st[C1_WANT] >= 0:
            st[C1_IDLE] = 0
            if st[C1_WANT] == 2:
                self._c1_jitter(utime)
                st[C1_WANT] = 0
                continue
            if st[C1_WANT] == 3:
                self._c1_exec(st, utime)
                continue
            if st[C1_WANT] == 0:
                st[C1_NBAD] = 0
                st[C1_LAST] = 0
                st[C1_IDLE] = 1
                while st[C1_WANT] == 0:
                    pass
                continue
            t0 = utime.ticks_us()
            drv.rtd_start()
            while utime.ticks_diff(utime.ticks_us(), t0) < TEMP_C1_BIAS_MS * 1000:
                pass
            t = utime.ticks_us()
            drv.rtd_convert()
            while utime.ticks_diff(utime.ticks_us(), t) < TEMP_C1_CONV_MS * 1000:
                pass
            if not self._c1_put(st, ring, tab, drv.rtd_result(), utime.ticks_ms()):
                continue
            while st[C1_WANT] == 1 and utime.ticks_diff(utime.ticks_us(), t0) < TEMP_C1_EVERY_MS * 1000:
                pass

