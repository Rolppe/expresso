# ============================================================================
# COMMANDS — one dispatcher for BLE writes and serial "CMD <command>" lines (17.9.2026)
# ============================================================================

from functions import PCAP_GATE_PERIOD_US, PSWEEP_N_MAX, PSWEEP_MULT_MAX, PGAP_SPACING_MAX_MS


def _float_arg(command):
    return float(command.split(':', 1)[1])


def handle_command(brew_data, command):
    """Apply a command. Returns True when a persisted setting changed (caller resends settings)."""
    updated = False

    if command.startswith('pre:'):
        if command == 'pre:on':
            brew_data.set_pre_infusion_mode(True)
            updated = True
        elif command == 'pre:off':
            brew_data.set_pre_infusion_mode(False)
            updated = True

    elif command.startswith('spr:'):
        if command == 'spr:on':
            brew_data.set_pressure_soft_release_time(5)
            brew_data.set_pressure_soft_release_mode(True)
            updated = True
        elif command == 'spr:off':
            brew_data.set_pressure_soft_release_time(0)
            brew_data.set_pressure_soft_release_mode(False)
            updated = True

    elif command.startswith('fhu:'):
        if command == 'fhu:on':
            brew_data.set_fast_heatup_mode(True)
            updated = True
        elif command == 'fhu:off':
            brew_data.set_fast_heatup_mode(False)
            updated = True

    elif command.startswith('pcal:'):
        # Pressure calibration wizard: pcal:run:<pre|brew>, pcal:m:<pre|brew>:<bar>, pcal:save, pcal:end
        parts = command.split(':')
        try:
            if parts[1] == 'run':
                brew_data.request_pressure_calibration(parts[2])
            elif parts[1] == 'm':
                brew_data.pressure_calibration_measured(parts[2], float(parts[3]))
            elif parts[1] == 'save':
                brew_data.pressure_calibration_save()
            elif parts[1] == 'end':
                brew_data.pressure_calibration_end_session()
            elif parts[1] == 'st':
                # The wizard is app-driven and used to say nothing at all on the serial link, so a
                # calibration run from pico_dev.py was flown blind (PCAL-KORJAUS, 19.9.2026).
                st = brew_data.get_pressure_calibration_status()
                print('PCAL_ST state=%s stage=%s gain=%.4f offset=%.3f msg=%s' % (
                    st['pcal_state'], st['pcal_stage'], st['pcal_gain'], st['pcal_offset'],
                    st['pcal_msg']))
        except Exception as e:
            brew_data.pcal_state = 'error'
            brew_data.pcal_msg = 'command failed: ' + str(e)

    elif command.startswith('pcalset:'):
        # pcalset:<gain>:<offset> writes the sensor calibration directly and saves it. The wizard's
        # own run is a locked-line tool: its dosing is a fixed stroke per window, which is too much
        # for a closed circuit (a bar a stroke) and far too little for a flowing one (duty 0.034
        # against the 0.13 a real hold needs, measured 19.9.2026). A calibration measured during
        # ordinary shots therefore needs a way in that does not go through the wizard.
        try:
            parts = command.split(':')
            gain = float(parts[1])
            offset = float(parts[2])
            sensor = brew_data.pressure_sensor
            if not sensor.calibration_valid(gain, offset):
                print('PCALSET_REJECT gain=%.4f offset=%.3f' % (gain, offset))
            else:
                sensor.set_calibration(gain, offset)
                sensor.save_calibration()
                print('PCALSET_OK gain=%.4f offset=%.3f' % (sensor.gain, sensor.offset))
        except Exception as e:
            print('PCALSET_FAIL %s' % e)

    elif command.startswith('pzero:'):
        # Vented zero: heater off, solenoid cycled until the raw value stops moving. A resting
        # reading is not a zero (PCAL-KORJAUS, 19.9.2026).
        brew_data.request_pressure_zero()

    elif command.startswith('pcalw:'):
        # Fine-phase stroke window in ms for the calibration run, not persisted (like fwin:).
        try:
            brew_data.set_pcal_window_ms(_float_arg(command))
        except Exception:
            pass

    elif command.startswith('mcal:'):
        # mcal:<ms 500-5000> | mcal:stop (PWM-1G, TILAUS-F/G/H)
        arg = command.split(':', 1)[1]
        if arg == 'stop':
            brew_data.abort_mains_calibration()
        else:
            try: brew_data.request_mains_calibration(float(arg))
            except Exception: pass

    elif command.startswith('pvent'):
        # pvent — pelkka purkusykli, ei pumppausta perassa (TILAUS-H kohta 3)
        brew_data.request_pressure_vent()

    elif command.startswith('plen:'):
        # plen:<bar>[:<reps>] | plen:stop — tauon pituuden pyyhkaisy (tilaus 20.9.2026)
        arg = command.split(':', 1)[1]
        brew_data.plen_reps = None
        if arg == 'stop':
            brew_data.abort_pressure_len()
        else:
            try:
                parts = arg.split(':')
                if len(parts) > 1: brew_data.plen_reps = min(6, max(1, int(float(parts[1]))))
                brew_data.request_pressure_len(float(parts[0]))
            except Exception:
                brew_data.plen_reps = None

    elif command.startswith('pgap:'):
        # pgap:<bar>[:<n>[:<spacing_ms>]] | pgap:stop — monta 20 ms:n taukoa ja kohdistushaku
        # ajon aikana (tilaus 20.9.2026).
        arg = command.split(':', 1)[1]
        brew_data.pgap_n = None
        brew_data.pgap_spacing_ms = None
        brew_data.pgap_len_ms = None
        brew_data.pgap_phases = None
        brew_data.pgap_lo_us = None
        brew_data.pgap_hi_us = None
        if arg == 'stop':
            brew_data.abort_pressure_gap()
        else:
            try:
                parts = arg.split(':')
                if len(parts) > 1: brew_data.pgap_n = min(60, max(2, int(float(parts[1]))))
                if len(parts) > 2: brew_data.pgap_spacing_ms = max(250, min(PGAP_SPACING_MAX_MS, int(float(parts[2]))))
                if len(parts) > 3: brew_data.pgap_len_ms = max(2, min(60, int(float(parts[3]))))
                if len(parts) > 4: brew_data.pgap_phases = max(2, min(20, int(float(parts[4]))))
                if len(parts) > 6:
                    brew_data.pgap_lo_us = max(0, int(float(parts[5])))
                    brew_data.pgap_hi_us = max(1, int(float(parts[6])))
                brew_data.request_pressure_gap(float(parts[0]))
            except Exception:
                brew_data.pgap_n = None
                brew_data.pgap_spacing_ms = None
                brew_data.pgap_len_ms = None
                brew_data.pgap_phases = None
                brew_data.pgap_lo_us = None
                brew_data.pgap_hi_us = None
    elif command.startswith('vkello:'):
        # vkello:<bar> | vkello:stop — brief VERKKOKELLO
        arg = command.split(':', 1)[1]
        if arg == 'stop':
            brew_data.abort_pressure_clock()
        else:
            try: brew_data.request_pressure_clock(float(arg))
            except Exception: pass
    elif command.startswith('vsweep:'):
        # vsweep:<reps 1-5> | vsweep:stop — taukojen vaihepyyhkaisy kellon reunasta (TILAUS-K/L)
        arg = command.split(':', 1)[1]
        if arg == 'stop':
            brew_data.abort_phase_sweep()
        else:
            try: brew_data.request_phase_sweep(float(arg))
            except Exception: pass
    elif command.startswith('pstep:'):
        # pstep:<bar>[:<hold_ms>[:<tail_ms>]] | pstep:stop — yksi ohitettu verkkojakso
        # tasapainossa (tilaus 20.9.2026). Kentat nollataan joka pyynnolla, kuten psweep:ssa.
        arg = command.split(':', 1)[1]
        brew_data.pstep_hold_ms = None
        brew_data.pstep_tail_ms = None
        if arg == 'stop':
            brew_data.abort_pressure_step()
        else:
            try:
                parts = arg.split(':')
                if len(parts) > 1: brew_data.pstep_hold_ms = max(200, int(float(parts[1])))
                if len(parts) > 2: brew_data.pstep_tail_ms = max(200, int(float(parts[2])))
                brew_data.request_pressure_step(float(parts[0]))
            except Exception:
                brew_data.pstep_hold_ms = None
                brew_data.pstep_tail_ms = None

    elif command.startswith('pcap:'):
        # Raw pressure capture for mains-frequency analysis: pcap:<ms 200-2500>[:<bar>[:<phase_us>]]
        # | pcap:stop. The optional third field is the settling target bar (korjaus 2); classes.py
        # is out of scope this round, so it rides on brew_data as a plain attribute, not a declared
        # field. The optional fourth field is the mains gate phase in microseconds (PWM-1B2-PORTITUS,
        # spec 4) — it requires the target bar, since gating without a target would measure from an
        # unknown state. It resets to None on every request, including stop and bad input, so a
        # stale phase never survives into the next run.
        arg = command.split(':', 1)[1]
        brew_data.pcap_gate_phase_us = None
        if arg == 'stop':
            brew_data.pcap_target_bar = None
            brew_data.stop_pressure_capture()
        else:
            try:
                parts = arg.split(':')
                brew_data.pcap_target_bar = float(parts[1]) if len(parts) > 1 else None
                if len(parts) > 2:
                    if brew_data.pcap_target_bar is None:
                        raise ValueError('gate requires a target bar')
                    brew_data.pcap_gate_phase_us = int(float(parts[2])) % PCAP_GATE_PERIOD_US
                brew_data.request_pressure_capture(float(parts[0]))
            except Exception:
                brew_data.pcap_target_bar = None
                brew_data.pcap_gate_phase_us = None

    elif command.startswith('psweep:'):
        # psweep:<ms 200-2500>:<bar>[:<n 2-8>[:<mult 2-16>]] | psweep:stop (PWM-1B4-PYYHKAISY,
        # spec 5; kerroin PWM-1B6, spec 3). Kentät nollataan None:ksi joka pyynnöllä, myös
        # stop:lla ja virheellisellä syötteellä — kelvoton kerroin hylkää koko pyynnön.
        arg = command.split(':', 1)[1]
        brew_data.psweep_target_bar = None
        brew_data.psweep_n = None
        brew_data.psweep_mult = None
        if arg == 'stop':
            brew_data.abort_pressure_sweep()
        else:
            try:
                parts = arg.split(':')
                if len(parts) < 2:
                    raise ValueError('psweep requires a target bar')
                brew_data.psweep_target_bar = float(parts[1])
                if len(parts) > 2:
                    brew_data.psweep_n = min(PSWEEP_N_MAX, max(2, int(float(parts[2]))))
                if len(parts) > 3:
                    brew_data.psweep_mult = min(PSWEEP_MULT_MAX, max(2, int(float(parts[3]))))
                brew_data.request_pressure_sweep(float(parts[0]))
            except Exception:
                brew_data.psweep_target_bar = None
                brew_data.psweep_n = None
                brew_data.psweep_mult = None

    elif command.startswith('phold:'):
        # Free pump+valve run for restrictor balancing: phold:<s 1-120> | phold:stop.
        arg = command.split(':', 1)[1]
        if arg == 'stop':
            brew_data.stop_pressure_hold()
        else:
            try:
                brew_data.request_pressure_hold(float(arg))
            except Exception:
                pass

    elif command.startswith('klamp:'):
        # Throttle warm-up (24.9.2026): klamp:<s 10-120> | klamp:stop. Continuous pump to the
        # plateau, then that pressure is held until the pump no longer needs limiting.
        arg = command.split(':', 1)[1]
        if arg == 'stop':
            brew_data.stop_throttle_warmup()
        else:
            try:
                brew_data.request_throttle_warmup(float(arg))
            except Exception:
                pass

    elif command.startswith('tshot:'):
        # Remote test shot without the brew switch: tshot:<seconds 5-60> | tshot:stop
        arg = command.split(':', 1)[1]
        if arg == 'stop':
            brew_data.stop_test_shot()
        else:
            try:
                brew_data.request_test_shot(float(arg))
            except Exception:
                pass

    elif command.startswith('dev:'):
        # dev:safe = relays off and no heating/pumping until dev:resume (or reboot)
        if command == 'dev:safe':
            brew_data.set_dev_safe(True)
        elif command == 'dev:resume':
            brew_data.set_dev_safe(False)

    elif command.startswith('pit:'):
        # Pre-infusion time 0-6 s from app slider; 0 s = pre-infusion off
        try:
            t = min(6.0, max(0.0, _float_arg(command)))
            brew_data.set_pre_infusion_time(t)
            brew_data.set_pre_infusion_mode(t > 0)
            updated = True
        except Exception:
            pass

    elif command.startswith('srt:'):
        # Soft pressure release time 0-6 s from app slider; 0 s = off
        try:
            t = min(6.0, max(0.0, _float_arg(command)))
            brew_data.set_pressure_soft_release_time(t)
            brew_data.set_pressure_soft_release_mode(t > 0)
            updated = True
        except Exception:
            pass

    elif command.startswith('pim:'):
        # Pre-infusion method (24.9.2026): 0 = PI with 17 ms window, 1 = phase-tracked (TILAUS-K 1-2).
        # RAM only like the weight limits: every restart and flash returns to 0; TS_START prints it.
        try:
            brew_data.pre_infusion_method = 1 if int(_float_arg(command)) == 1 else 0
            updated = True
        except Exception:
            pass

    elif command.startswith('pip:'):
        try:
            brew_data.set_pre_infusion_pressure(_float_arg(command))
            updated = True
        except Exception:
            pass

    elif command.startswith('bp:'):
        try:
            brew_data.set_brew_pressure(_float_arg(command))
            updated = True
        except Exception:
            pass

    elif command.startswith('wrise:'):
        # How much the tray may gain during a single test shot, 0 = off (18.9.2026)
        try:
            brew_data.set_weight_rise_limit(_float_arg(command))
            updated = True
        except Exception:
            pass

    elif command.startswith('fwin:'):
        # Flow window in ms (18.9.2026): the whole latency/noise trade-off of the flow reading, see
        # scale.FLOW_WINDOW_MS. A measurement knob, not a limit, so it is not persisted and the
        # default returns on every boot.
        try:
            brew_data.set_flow_window_ms(_float_arg(command))
        except Exception:
            pass

    elif command.startswith('fmode:'):
        # Outer flow cascade on/off (VIRTAUSSAATO, 18.9.2026), runtime-only like fwin: — not
        # persisted, so the device is always in pressure control after a boot or a flash.
        arg = command[len('fmode:'):]
        if arg == 'on':
            brew_data.set_flow_mode(True)
        elif arg == 'off':
            brew_data.set_flow_mode(False)
        else:
            brew_data.command_known = False
            return updated

    elif command.startswith('fset:'):
        # Flow target g/s, runtime-only like fmode: (see above).
        try:
            brew_data.set_flow_target(_float_arg(command))
        except Exception:
            pass

    elif command.startswith('wmax:'):
        # Drip-tray weight limit in grams for TEST SHOTS only, 0 = off (18.9.2026). Persisted since
        # devsafe12: the limits are only read on the tshot path, so they cannot leak into normal use,
        # and not persisting them meant the guard was silently off after every boot and flash.
        try:
            brew_data.set_weight_limit(_float_arg(command))
            updated = True
        except Exception:
            pass

    elif command.startswith('bt:'):
        try:
            brew_data.set_brew_temperature(_float_arg(command))
            updated = True
        except Exception:
            pass

    else:
        # Unknown command: the caller must be able to tell. main.py printed CMD_OK for every line it
        # read, so a typo or a command missing from the flashed firmware acknowledged exactly like a
        # real one - that is how wrise:40 was silently ignored on 18.9.2026 while a test shot ran on
        # without its limit.
        brew_data.command_known = False
        return updated
    brew_data.command_known = True
    return updated
