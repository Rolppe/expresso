import os

# ============================================================================
#  PRE-INFUSION
# ============================================================================

async def pre_infusion(brew_data, utime, asyncio, pump_ratio_calculator, keep_running=None):
    
    RELAY_PUMP, RELAY_SOLENOID, RELAY_HEATER = brew_data.get_relays()
    SWITCH_BREW = brew_data.get_switch_brew()
    # keep_running: brew switch for a real shot, test-shot condition for tshot (17.9.2026)
    if keep_running is None:
        keep_running = SWITCH_BREW.value
    
    brew_data.set_mode('pre-infusion initialization')
    pressure = brew_data.get_pressure()
    
    last_pump_ratio_time = utime.ticks_ms()
    
    # Get boiler temperature
    boiler_temperature = brew_data.get_boiler_temperature()
    
    # Open solenoid for water to flow to grouphead
    RELAY_SOLENOID.value(1)
    
    # Target pre-infusion pressure (bar), set from app slider (1-4 bar)
    pre_infusion_pressure = brew_data.get_pre_infusion_pressure()
    
    # If theres a pressure in system, let stabilize to pre-infusion pressure
    while pressure > pre_infusion_pressure - 0.1 and keep_running():
        
        brew_data.set_mode('pre-infusion pressure stabilization')
        
        # Read sensor pressure (no temperature read: MAX31865 blocks >= 75 ms)
        pressure = brew_data.get_pressure()

        await asyncio.sleep_ms(20)
        
        
    # ===== PRE-INFUSION: BUILD-UP AND TIMED HOLD ===== #
    # One fast loop (~20 ms): no temperature reads (MAX31865 blocks >= 75 ms), pump by
    # PumpPressureController. Build-up ends when the target is first reached; the timer starts then.
    from classes import PumpPressureController
    # Build-up follows a ramped setpoint instead of a duty ceiling (18.9.2026). History: test shots
    # 3-5 (needle valve) overshot 2.0 -> 4.1-4.5 bar, so devsafe6 capped the duty at 80 % up to half
    # the target and 25 % above it. The first real shot on coffee (06:56:42) showed why that is the
    # wrong shape: against a puck 25 % duty settles at ~1.35 bar and never reaches 2.0, the hold then
    # started on a noise spike in the 16.7 ms average and the restored full duty shot to 3.84 bar.
    # A ramped setpoint keeps the pump continuous while it is far below target (the flush rule) and
    # lets the controller approach the target at a known rate, so the pump+sensor delay costs about
    # RAMP_BAR_PER_S * delay (~0.14 bar) instead of a step response.
    RAMP_BAR_PER_S = 2.0
    brew_data.pressure_sensor.reset_average()
    controller = PumpPressureController(RELAY_PUMP, pump_ratio_calculator, utime,
                                        ff=brew_data.learned_ff_pre, max_duty=1.0)
    brew_data.set_mode('pre-infusion pressure build-up')
    ramp_start = utime.ticks_ms()
    ramp_base = 0.0
    hold_start = None
    build_up = True
    end = None
    last_log = 0
    while keep_running():
        now = utime.ticks_ms()
        pressure = brew_data.get_pressure_average(utime)
        if build_up:
            # While the controller still runs the pump continuously (far below the target) the
            # setpoint stays at the target: rate-limiting there would chop the pump, which is exactly
            # what a flush must never do. The ramp starts from the pressure at which the continuous
            # region ends, so the last stretch is a rate-limited approach, and the hold starts when
            # the ramp is done - not when a noisy sample happens to touch the target.
            ramp_from = pre_infusion_pressure - controller.continuous_error
            if controller.filtered < ramp_from or controller.filtered < pre_infusion_pressure * 0.5:
                ramp_start = now
                ramp_base = controller.filtered
                target = pre_infusion_pressure
            else:
                ramped = ramp_base + RAMP_BAR_PER_S * utime.ticks_diff(now, ramp_start) / 1000.0
                if ramped >= pre_infusion_pressure:
                    ramped = pre_infusion_pressure
                    build_up = False
                    hold_start = now
                    brew_data.set_mode('pre-infusion main')
                    # Duration from app slider (pit:), was a fixed 5 s
                    end = utime.ticks_add(now, int(float(brew_data.get_pre_infusion_time() or 0) * 1000))
                target = ramped
        else:
            target = pre_infusion_pressure
        controller.update(pressure, target)
        brew_data.pressure_filtered = controller.filtered

        if end is not None and utime.ticks_diff(end, now) <= 0:
            break

        if utime.ticks_diff(now, last_pump_ratio_time) >= 1000:
            brew_data.set_pump_ratio(round(pump_ratio_calculator.get_ratio()))
            last_pump_ratio_time = now
        if utime.ticks_diff(now, last_log) >= 100:
            last_log = now
            print('PI %d %.1f %.1f %d %.2f %.1f %.1f %.1f %s' % (now, pressure, target, controller.on,
                                              controller.duty, brew_data.pressure_sensor.window_peak,
                                              brew_data.weight_a, brew_data.weight_b,
                                              weight_flow_log(brew_data)))

        await asyncio.sleep_ms(0)

    controller.stop()
    if hold_start is not None and utime.ticks_diff(utime.ticks_ms(), hold_start) >= 2000:
        brew_data.learned_ff_pre = min(0.9, max(0.05, controller.duty_avg))
    print('PI_END learned_ff_pre=%.2f' % brew_data.learned_ff_pre)


# ============================================================================
#  ESIUUTTO VAIHESEURANNALLA (pim:1) — TILAUS-K vaiheet 1-2 (EXPRESSO-ESIUUTTO-25BAR, 24.9.2026)
# ============================================================================
# VAATIMUS: TILAUS-K, TILAUS-L, TILAUS-G, TILAUS-B, TILAUS-I, TILAUS-J
#
# Vaihe 1 (nosto): pumppu taydella syklilla, kunnes ennuste "jaksokeskipaine + nousunopeus x opittu
#   jalkinousu" yltaa tavoite - EU_CUT_MARGIN_BAR ("korkein tunnettu piste ilman yliampumista").
#   Jalkinousu opitaan joka ajosta (EU_COAST). Nousun I/Q-ikkunat kirjataan (TILAUS-G: syklista
#   kerataan tietoa), mutta ne eivat opeta kelloa: noususta opetettu kello oli 3,6-6,8 ms vaarassa
#   (paatos 24.9.2026, learn=False).
# Vaihe 2 (loppunosto ja pito): iskuja jatetaan valiin. Joka verkkojaksossa on yksi paatoskohta,
#   kellon reuna + EU_OFF_US = 13,6 ms, joka on vsweep-a:n lohkon 8,5-18,7 ms keskikohta (+-5 ms).
#   Delta-sigma paattaa, iskeeko pumppu (TILAUS-L: askel on yksi jakso, luku 2: 1 %). Poistettava
#   isku on 10 ms tauko tasta kohdasta, kun kellon vaihe tunnetaan (2,5 sd < EU_PHASE_OK_US); muuten
#   20 ms tauko, joka nollaylitys-SSR:lla poistaa tasan yhden iskun vaiheesta riippumatta (vsweep-a:
#   20 ms tauko -0,85 bar kaikissa kohdissa). Pidon I/Q-ikkunat opettavat kellon porteilla.
#   Myohastymisvahti (VAIHESEURANTA.md: tuotannossa pakollinen): tauko, jonka alku myohastyisi yli
#   EU_LATE_MAX_US, jaa tekematta, isku menee lapi ja sen velka siirtyy seuraaviin jaksoihin.
# Saadin laskee jaksokeskipaineesta (tasan yksi kellojakso, TILAUS-L 20 ms; vanha 16,7 ms), ja
# pito alkaa vasta, kun rampattu asetusarvo on tavoitteessa (menetelmaohje: laskuri alkaa vasta
# tavoitteesta).
EU_OFF_US = 13600            # paatoskohta kellon reunasta: tauon alku (vsweep-a 8,5-18,7 ms keskikohta)
EU_GAP_US = 10000            # TILAUS-L: pienin tauko, kun vaihe tunnetaan
EU_PHASE_OK_US = 4000        # 2,5 sd alle taman -> 10 ms tauot; marginaali lohkon reunoihin 5 ms
EU_LATE_MAX_US = 300         # = VSWEEP_LATE_MAX_US
EU_MIN_SLOT_US = 15000       # paatoskohtien vali vahintaan (kellon korjaus ei tuplaa paatosta)
EU_YIELD_US = 3000           # asyncio-vuoro vain, kun seuraavaan tapahtumaan on tata enemman
EU_CUT_MARGIN_BAR = 0.3      # ennustettu huippu jaa nain paljon tavoitteen alle
EU_COAST_S0 = 0.3            # jalkinousun oletus (s), varovainen: ensimmainen ajo katkaisee matalalta
                             # (pumpun ja anturin viive 60-80 ms + hydrauliikka), seuraavat oppivat
EU_COAST_MIN, EU_COAST_MAX = 0.03, 0.6
EU_COAST_MS = 300            # jalkinousun huippua haetaan enintaan nain kauan katkaisusta
EU_COAST_MIN_MS = 100        # ja vahintaan nain kauan (viive 40 ms + iskun nousu): katkaisuhetkella
                             # ramppi = paine, joten pelkka 'ramppi saavutti paineen' sulki heti
EU_RATE_MIN = 0.5            # bar/s: hitaammasta noususta ei opita jalkinousua
EU_RAMP_BAR_PER_S = 2.0      # sama loppunoston ramppi kuin pre_infusion
EU_RAMP_FF_MAX = 0.5         # rampin oman myotakytkennan yläraja (duty)
EU_RAMP_LEAD_S = 0.1         # rampin myotakytkenta loppuu nain paljon ennen tavoitetta (iskun + p5:n viive)
EU_KP, EU_KI = 0.2, 0.3      # sama PI kuin PumpPressureController
EU_LOG_SLOTS = 5             # EU-rivi joka 5. jakso (100 ms)
EU_AVG_N = 5                 # paatosten keskiarvo 5 jaksoa (100 ms); nousunopeus kahdesta perakkaisesta
EU_HOLD_TOL_BAR = 0.1        # pito alkaa, kun ramppi on tavoitteessa ja p5 >= tavoite - tama
EU_INT_BAND_BAR = 0.3        # ennen pitoa integraali kertyy vain, kun |virhe| < tama
EU_OVER_MS = 1000            # yliampuma = huippu nousussa ja pidon ensimmaisen sekunnin; sen jalkeen on
                             # pidon heittelya (hold_sd). Sama ikkuna kuin esiuutto_analyysi.py


async def pre_infusion_phased(brew_data, utime, asyncio, pump_ratio_calculator, keep_running=None):
    import math
    from verkkokello import Verkkokello
    RELAY_PUMP, RELAY_SOLENOID, RELAY_HEATER = brew_data.get_relays()
    if keep_running is None:
        keep_running = brew_data.get_switch_brew().value
    sensor = brew_data.pressure_sensor.pressure_sensor
    gain, offset = brew_data.pressure_sensor.gain, brew_data.pressure_sensor.offset
    target = brew_data.get_pre_infusion_pressure()
    hold_us = int(float(brew_data.get_pre_infusion_time() or 0) * 1000000)
    coast_s = getattr(brew_data, 'eu_coast_s', EU_COAST_S0)
    ff = brew_data.learned_ff_pre

    # Kuten pre_infusion: jaannospaine ensin tavoitteen alle venttiili auki
    brew_data.set_mode('pre-infusion pressure stabilization')
    RELAY_SOLENOID.value(1)
    pressure = brew_data.get_pressure()
    while pressure > target - 0.1 and keep_running():
        pressure = brew_data.get_pressure()
        await asyncio.sleep_ms(20)

    brew_data.set_mode('pre-infusion pressure build-up')
    print('EU_START target=%.2f hold_s=%.1f coast_s=%.3f ff=%.2f off_us=%d' % (
        target, hold_us / 1e6, coast_s, ff, EU_OFF_US))
    t0 = utime.ticks_us()
    clock = Verkkokello(t0)
    clock.iq_start(t0)
    relay = [False]

    def set_relay(on):
        if on != relay[0]:
            relay[0] = on
            RELAY_PUMP.value(1 if on else 0)
            if on: pump_ratio_calculator.set_pump_on()
            else: pump_ratio_calculator.set_pump_off()

    set_relay(True)
    slot = utime.ticks_add(t0, EU_OFF_US)
    phase, reason = 1, 'stop'
    acc, d, integ, pump_next, pend_on = 0.0, 1.0, 0.0, True, None
    cyc_s, cyc_n, hist, next_s = 0.0, 0, [], t0
    sp, last_slot, n_slot = target, None, 0
    cut_t = p_cut = rate_cut = peak = None
    coast_open = False
    ramp_base = ramp_t = hold_t = end_t = None
    strokes = removed = skips10 = skips20 = late = miss = windows = win_low = learned = 0
    p_max, rise_max, h_s, h_ss, h_n, duty_avg = 0.0, 0.0, 0.0, 0.0, 0, ff
    out = []
    ramp_ff = 0.0
    try:
        while True:
            now = utime.ticks_us()
            if pend_on is not None and utime.ticks_diff(pend_on, now) < PCAP_RATE_US:
                while utime.ticks_diff(pend_on, utime.ticks_us()) > 0: pass
                set_relay(True)
                pend_on = None
                now = utime.ticks_us()
            if utime.ticks_diff(slot, now) < PCAP_RATE_US:
                while utime.ticks_diff(slot, utime.ticks_us()) > 0: pass
                t = utime.ticks_us()
                lateness = utime.ticks_diff(t, slot)
                pend_on = None
                # Rele heti: paatos tehtiin edellisessa kohdassa. Kaikki laskenta (myos sd_us:n 3x3-
                # matriisit) vasta taman jalkeen, jottei se viivasta tauon alkua vahdin ohi.
                cur, was_on = pump_next, relay[0]
                skip_late = not cur and was_on and lateness > EU_LATE_MAX_US
                if cur: set_relay(True)
                elif not skip_late: set_relay(False)
                if lateness > clock.T / 2:
                    # Pysahdys (toinen tehtava) ohitti kokonaisia jaksoja: rele pysyi ennallaan
                    extra = int((lateness + clock.T / 2) // clock.T)
                    miss += extra
                    if was_on: strokes += extra
                    else: removed += extra
                # Jaksokeskipaine: naytteet edellisesta paatoskohdasta tahan = yksi kellojakso
                p = cyc_s / cyc_n if cyc_n else (hist[-1] if hist else 0.0)
                cyc_s, cyc_n = 0.0, 0
                brew_data.pressure = p
                brew_data.pressure_filtered = p
                hist.append(p)
                if len(hist) > 2 * EU_AVG_N: hist.pop(0)
                # Paatokset 5 jakson keskiarvosta: yksittaisen jakson keskiarvo heiluu taytossa +-0,5 bar
                # (esiuutto-20260924-c: katkaisu piikista 1,37 bar, rate 16,5 bar/s, todellinen ~0,3 bar)
                p5 = sum(hist[-EU_AVG_N:]) / min(len(hist), EU_AVG_N)
                rate = ((p5 - sum(hist[:EU_AVG_N]) / EU_AVG_N) / (EU_AVG_N * 0.02)
                        if len(hist) == 2 * EU_AVG_N else 0.0)
                dt = 0.02 if last_slot is None else min(0.1, utime.ticks_diff(t, last_slot) / 1e6)
                last_slot = t
                n_slot += 1
                if p > p_max: p_max = p
                if (hold_t is None or utime.ticks_diff(t, hold_t) < EU_OVER_MS * 1000) and p5 > rise_max:
                    rise_max = p5
                if end_t is not None and utime.ticks_diff(t, end_t) >= 0:
                    reason = 'done'; break
                if not keep_running():
                    reason = 'stop'; break

                # Katkaisu vasta taysista keskiarvoista (2 x 5 jaksoa)
                if phase == 1 and len(hist) == 2 * EU_AVG_N and p5 >= target * 0.5 and \
                        p5 + rate * coast_s >= target - EU_CUT_MARGIN_BAR:
                    phase = 2
                    cut_t, p_cut, rate_cut, peak, coast_open = t, p5, rate, p5, True
                    ramp_base, ramp_t, integ, acc = p5, t, 0.0, 0.0
                    # Rampin myotakytkenta (EXPRESSO-ESIUUTTO-PITO): 2 bar/s nousu tarvitsee laitteella
                    # 0,36-0,43 dutya pidon ff:n paalle, ja pelkka P-termi jatti paineen ~0,6 bar rampin
                    # alle ~1 s ajaksi. Iskun vahvistus G = 50 x iskukoko (bar/s dutya kohden) taman ajon
                    # katkaisuhetken noususta taydella dutylla: rate = G - p/tau ja pidossa G*ff*tau = tavoite,
                    # joten G = rate / (1 - p*ff/tavoite). Hitaasta noususta G:ta ei voi arvioida.
                    ramp_ff = 0.0
                    if rate >= EU_RATE_MIN:
                        g = rate / max(0.2, 1.0 - p5 * ff / target)
                        ramp_ff = min(EU_RAMP_FF_MAX, EU_RAMP_BAR_PER_S / g)
                    brew_data.set_mode('pre-infusion final rise')
                    out.append('EU_CUT t_ms=%d p=%.2f rate=%.2f coast_s=%.3f pred=%.2f' % (
                        utime.ticks_diff(t, t0) // 1000, p5, rate, coast_s, p5 + rate * coast_s))
                if phase == 2:
                    if hold_t is None:
                        sp = ramp_base + EU_RAMP_BAR_PER_S * utime.ticks_diff(t, ramp_t) / 1e6
                        if sp >= target:
                            sp = target
                            # Menetelmaohje: laskuri alkaa vasta, kun paine on saavutettu - ei silloin, kun
                            # ramppi on (esiuutto-20260924-b/c: pito alkoi paineessa 1,34 / 1,09 bar)
                            if p5 >= target - EU_HOLD_TOL_BAR:
                                hold_t = t
                                end_t = utime.ticks_add(t, hold_us)
                                brew_data.set_mode('pre-infusion main')
                                out.append('EU_HOLD t_ms=%d p=%.2f' % (utime.ticks_diff(t, t0) // 1000, p5))
                    else:
                        sp = target
                        h_s += p; h_ss += p * p; h_n += 1
                    if coast_open:
                        # Jalkinousun huippu: katkaisusta siihen, kun ramppi saavuttaa paineen
                        if p5 > peak: peak = p5
                        el = utime.ticks_diff(t, cut_t)
                        if (sp >= p5 and el >= EU_COAST_MIN_MS * 1000) or el >= EU_COAST_MS * 1000:
                            coast_open = False
                            # Ei oppia, jos paine ei noussut katkaisun jalkeen: silloin katkaisu ei ollut
                            # nousun keskella (c-ajo: huippu = katkaisu, coast_s puolittui turhaan)
                            learn = rate_cut >= EU_RATE_MIN and peak > p_cut
                            if learn:
                                obs = (peak - p_cut) / rate_cut
                                coast_s += 0.5 * (obs - coast_s)
                                coast_s = max(EU_COAST_MIN, min(EU_COAST_MAX, coast_s))
                            out.append('EU_COAST peak=%.2f rise=%.2f rate=%.2f coast_s=%.3f learn=%d' % (
                                peak, peak - p_cut, rate_cut, coast_s, 1 if learn else 0))
                    e = sp - p
                    # Rampin aikana tasapainoduty skaalautuu paineen mukana (ff on mitattu tavoitteessa).
                    # Rampin myotakytkenta vain, kun paine on rampin alla, ja se loppuu EU_RAMP_LEAD_S ennen
                    # tavoitetta: jalkinousun edella oleva paine ja iskun + p5:n viive (~0,1 s) nostivat
                    # ilman naita rajoja ylityksia (sovitettu malli: yli 0,3 bar 17/48 ajoa, vanha 4/48)
                    uff = ff
                    if hold_t is None and sp < target:
                        uff = ff * sp / target
                        if p5 < sp and sp < target - EU_RAMP_BAR_PER_S * EU_RAMP_LEAD_S:
                            uff += ramp_ff
                    u = uff + EU_KP * e + EU_KI * integ
                    # Integraali vain pidossa tai lahella asetusarvoa: rampin viive kasasi sen c-ajossa
                    # (1,1 bar vajetta 0,5 s) ja se purkautui yliampumana 3,6 bariin
                    if (hold_t is not None or abs(e) < EU_INT_BAND_BAR) and \
                            (0.0 < u < 1.0 or (u >= 1.0 and e < 0) or (u <= 0.0 and e > 0)):
                        integ = max(-1.5, min(1.5, integ + e * dt))
                    u = uff + EU_KP * e + EU_KI * integ
                    d = 0.0 if u < 0.0 else (1.0 if u > 1.0 else u)
                    if hold_t is not None:
                        duty_avg += (d - duty_avg) * (dt / 5.0)

                # Seuraava jakso paatetaan nyt (delta-sigma); tama jakso toimi jo yllä.
                if phase == 2:
                    acc += d
                    pump_next = acc >= 1.0
                    if pump_next: acc -= 1.0
                if cur:
                    strokes += 1
                elif skip_late:
                    # Myohassa: tauko jai tekematta, isku meni lapi, velka siirtyy seuraaviin jaksoihin
                    late += 1; strokes += 1; acc -= 1.0
                else:
                    ok = 2.5 * clock.sd_us(t) < EU_PHASE_OK_US
                    removed += 1
                    if was_on:                # tauko alkoi; perakkainen poisto jatkaa samaa taukoa
                        if ok: skips10 += 1
                        else: skips20 += 1
                    if pump_next and ok:      # 10 ms tauko; muuten rele palaa seuraavassa kohdassa (20 ms)
                        pend_on = utime.ticks_add(slot, EU_GAP_US)

                # Seuraava paatoskohta kellon seuraavasta reunasta. Vali mitataan nimelliseen kohtaan, jolle
                # tama paatos kuului, ei myohastyneeseen t:hen: 5-10 ms myohastyminen siirsi seuraavan
                # paatoksen jaksolla eteenpain, rele pysyi paalla laskematta iskua ja delta-sigma ei tiennyt
                # siita (EXPRESSO-ESIUUTTO-PITO: sovitetussa mallissa 14-24 laskematonta iskua ajossa)
                cur_n = utime.ticks_add(clock.edge(utime.ticks_add(t, -EU_OFF_US)), EU_OFF_US)
                nxt = utime.ticks_add(clock.edge(utime.ticks_add(t, round(clock.T) - EU_OFF_US)), EU_OFF_US)
                while utime.ticks_diff(nxt, cur_n) < EU_MIN_SLOT_US:
                    nxt = utime.ticks_add(nxt, round(clock.T))
                slot = nxt

                if n_slot % EU_LOG_SLOTS == 0:
                    out.append('EU %d %.2f %.2f %d %.2f %d p5=%.2f sd_us=%.0f rm=%d sk10=%d sk20=%d late=%d %s' % (
                        utime.ticks_diff(t, t0) // 1000, p, sp, 1 if relay[0] else 0, d, phase, p5,
                        clock.sd_us(t), removed, skips10, skips20, late, weight_flow_log(brew_data)))
                for line in out: print(line)
                out = []
                now = utime.ticks_us()

            if utime.ticks_diff(now, next_s) >= 0:
                next_s = utime.ticks_add(next_s, PCAP_RATE_US)
                if utime.ticks_diff(now, next_s) > 0: next_s = utime.ticks_add(now, PCAP_RATE_US)
                bar = gain * (sensor.read_u16() * PCAP_RAW_A + PCAP_RAW_B) + offset
                cyc_s += bar; cyc_n += 1
                clock.iq_add(now, bar)
                if clock.iq_ready(now):
                    res = clock.iq_close(now, learn=(phase == 2))
                    clock.iq_start(now)
                    if res is None:
                        win_low += 1          # amplitudi alle AMP_MIN: harvat iskut, ei kellopaivitysta
                    else:
                        z, amp, p_bar, g = res; windows += 1
                        if g == 0: learned += 1
                        out.append('VKELLO w=%d t_ms=%d z_us=%.1f T_us=%.3f d=%.5f sd_us=%.1f amp=%.3f lock=%d p_bar=%.2f gate=%d' % (
                            windows, utime.ticks_diff(now, t0) // 1000, z, clock.T, clock.d,
                            clock.sd_us(now), amp, 1 if clock.locked(now) else 0, p_bar, g))
            wait = utime.ticks_diff(slot, now)
            if pend_on is not None: wait = min(wait, utime.ticks_diff(pend_on, now))
            if wait > EU_YIELD_US:
                await asyncio.sleep_ms(0)
    finally:
        set_relay(False)
        RELAY_PUMP.value(0)
    for line in out: print(line)
    if hold_t is not None and utime.ticks_diff(utime.ticks_us(), hold_t) >= 2000000:
        brew_data.learned_ff_pre = min(0.9, max(0.05, duty_avg))
    brew_data.eu_coast_s = coast_s
    mean = h_s / h_n if h_n else 0.0
    sd = math.sqrt(max(0.0, h_ss / h_n - mean * mean)) if h_n else 0.0
    now = utime.ticks_us()
    print('EU_END reason=%s max=%.2f over=%.2f hold_n=%d hold_mean=%.3f hold_sd=%.3f strokes=%d rm=%d sk10=%d sk20=%d late=%d miss=%d windows=%d win_low=%d learned=%d T_us=%.3f hz=%.4f sd_us=%.0f learned_ff_pre=%.2f coast_s=%.3f' % (
        reason, p_max, rise_max - target, h_n, mean, sd, strokes, removed, skips10, skips20, late, miss, windows,
        win_low, learned, clock.T, 1e6 / clock.T, clock.sd_us(now), brew_data.learned_ff_pre, coast_s))


def weight_flow_log(brew_data):
    """Tail of the 10 Hz log lines: tray weight and flow, or '-' when there is no scale or the
    samples are stale. Appended after the per-cell fields so the positional indices keep meaning."""
    w = brew_data.get_weight()
    f = brew_data.get_flow()
    return 'w=%s f=%s' % ('-' if w is None else '%.1f' % w,
                          '-' if f is None else '%.2f' % f)


# ============================================================================
# SHOT (brew switch or remote test shot)
# ============================================================================

async def run_shot(brew_data, utime, asyncio, pump_ratio_calculator, keep_running, label='PB',
                   limit_weight=False):
    # Pre-infusion, brew loop, soft pressure release, solenoid off. Moved from main.py so a remote
    # test shot (tshot:) runs exactly the brew-switch code path (17.9.2026).
    from classes import PumpPressureController, FlowController
    from preset import FEATURES
    RELAY_PUMP, RELAY_SOLENOID, RELAY_HEATER = brew_data.get_relays()

    brew_data.set_mode('BREW')
    await asyncio.sleep_ms(50)
    RELAY_HEATER.value(0)
    start_time = utime.ticks_ms()
    abort_reason = ''
    over = [0, 0]          # [consecutive samples over the limit, last sample timestamp]
    weight_start = brew_data.get_weight() if limit_weight else None

    def running():
        nonlocal abort_reason
        if abort_reason:
            return False
        # Only while the pump is adding pressure: with the solenoid closed the boiler's own thermal
        # expansion reaches ~14 bar at idle (17.9.2026), and a shot must be allowed to open the
        # solenoid and release it
        if brew_data.pressure_filtered > 13.0 and RELAY_PUMP.value():
            abort_reason = 'overpressure %.1f bar' % brew_data.pressure_filtered
            return False
        # Test shots only: stop before the drip tray overflows (18.9.2026). A real shot has a cup on
        # the same scale, so the switch path passes limit_weight=False and is never stopped by weight.
        if limit_weight:
            limit = brew_data.get_weight_limit()
            rise_limit = brew_data.get_weight_rise_limit()
            if limit > 0 or rise_limit > 0:
                weight = brew_data.get_weight()
                age = utime.ticks_diff(utime.ticks_ms(), brew_data.get_weight_ms())
                # A scale that stops answering leaves brew_data.weight frozen at its last value, so
                # a limit would never fire - the exact case the limits exist for
                if weight is None or age > 2000:
                    abort_reason = 'scale silent %d ms' % age
                    return False
                if rise_limit > 0 and weight_start is None:
                    abort_reason = 'no weight at shot start'
                    return False
                # Two consecutive *samples* over a limit, not two loop iterations: the loop runs at
                # ~1 ms and the scale at ~10 Hz, and single spikes of -16 g were seen in telemetry
                ms = brew_data.get_weight_ms()
                if ms != over[1]:
                    over[1] = ms
                    hit = (limit > 0 and weight >= limit) or \
                          (rise_limit > 0 and weight - weight_start >= rise_limit)
                    over[0] = over[0] + 1 if hit else 0
                if over[0] >= 2:
                    if limit > 0 and weight >= limit:
                        abort_reason = 'tray %.0f g >= limit %.0f g' % (weight, limit)
                    else:
                        abort_reason = 'shot added %.0f g >= %.0f g' % (weight - weight_start, rise_limit)
                    return False
        return keep_running()

    try:
        # ===== PRE-INFUSION ===== #
        if brew_data.get_pre_infusion_mode():
            # pim:1 = vaiheseurattu esiuutto (TILAUS-K 1-2); oletus 0 kunnes todennettu laitteella
            if getattr(brew_data, 'pre_infusion_method', 0) == 1:
                await pre_infusion_phased(brew_data, utime, asyncio, pump_ratio_calculator, running)
            else:
                await pre_infusion(brew_data, utime, asyncio, pump_ratio_calculator, running)

        # ===== BREW LOOP ===== #
        brew_data.set_mode('brew loop initialization')
        last_pump_ratio_time = utime.ticks_ms()
        RELAY_SOLENOID.value(1)
        brew_data.set_mode('brew loop')

        # Fast loop (~20-25 ms): pump decided every iteration by PumpPressureController;
        # boiler temperature (MAX31865 blocks >= 75 ms) only every 2 s for telemetry.
        brew_data.pressure_sensor.reset_average()
        pressure_controller = PumpPressureController(RELAY_PUMP, pump_ratio_calculator, utime,
                                                     ff=brew_data.learned_ff_brew)
        flow_controller = None
        if brew_data.get_flow_mode() and brew_data.get_flow() is not None:
            flow_controller = FlowController(utime, brew_data.get_flow_target(),
                                             brew_data.learned_ff_brew)
        brew_start = utime.ticks_ms()
        last_temperature_read = utime.ticks_ms()
        last_log = 0
        last_loop = utime.ticks_ms()
        max_loop_ms = 0
        loops = 0
        while running():
            now = utime.ticks_ms()
            elapsed_ms = utime.ticks_diff(now, start_time)
            loop_ms = utime.ticks_diff(now, last_loop)
            last_loop = now
            loops += 1
            if loops > 1 and loop_ms > max_loop_ms:
                max_loop_ms = loop_ms

            # ===== HEATER: off 0.1 s, on 0.05 s ===== #
            if (elapsed_ms % 150) < 100:
                RELAY_HEATER.value(0)
            else:
                RELAY_HEATER.value(1)

            if utime.ticks_diff(now, last_temperature_read) >= 2000:
                brew_data.get_boiler_temperature()
                last_temperature_read = utime.ticks_ms()

            # ===== PRESSURE + PUMP ===== #
            pressure = brew_data.get_pressure_average(utime)
            brew_pressure = brew_data.get_brew_pressure()
            target = brew_pressure
            if flow_controller is not None:
                flow_controller.set_target(brew_data.get_flow_target())
                duty = flow_controller.update(brew_data.get_flow(), pressure)
                if duty is None:
                    print('%s_FLOW_OFF reason=scale silent' % label)
                    flow_controller = None
                    pressure_controller.update(pressure, target)
                else:
                    pressure_controller.apply_duty(duty, pressure)
            else:
                pressure_controller.update(pressure, target)
            brew_data.pressure_filtered = pressure_controller.filtered

            if utime.ticks_diff(now, last_pump_ratio_time) >= 1000:
                brew_data.set_pump_ratio(pump_ratio_calculator.get_ratio())
                last_pump_ratio_time = now

            if utime.ticks_diff(now, last_log) >= 100:
                last_log = now
                fsp = brew_data.get_flow_target() if flow_controller is not None else 0.0
                fsat = (1 if flow_controller.saturated else 0) if flow_controller is not None else 0
                print('%s %d %.1f %.1f %d %.2f %.1f %.1f %.1f %s fsp=%.2f fsat=%d' % (
                                                        label, elapsed_ms, pressure, brew_pressure,
                                                        pressure_controller.on, pressure_controller.duty,
                                                        brew_data.pressure_sensor.window_peak,
                                                        brew_data.weight_a, brew_data.weight_b,
                                                        weight_flow_log(brew_data), fsp, fsat))

            # Yield to BLE without adding delay
            await asyncio.sleep_ms(0)

        pressure_controller.stop()
        RELAY_HEATER.value(0)
        if utime.ticks_diff(utime.ticks_ms(), brew_start) >= 8000:
            brew_data.learned_ff_brew = min(0.9, max(0.05, pressure_controller.duty_avg))
        print('%s_END loops=%d max_loop_ms=%d reason=%s learned_ff_brew=%.2f' % (
            label, loops, max_loop_ms, abort_reason or 'stopped', brew_data.learned_ff_brew))

        # ===== PRESSURE SOFT RELEASE ===== #
        RELAY_PUMP.value(0)
        brew_data.set_pump_ratio(0)
        if brew_data.get_pressure() >= brew_data.get_soft_pressure_release_arming_pressure() and brew_data.get_pressure_soft_release_mode():
            brew_data.set_mode('soft pressure release')
            soft_pressure_release_time = brew_data.get_pressure_soft_release_time()
            print("soft release time: " + str(soft_pressure_release_time))
            # App slider sends fractional seconds (srt:), range() would raise TypeError
            await asyncio.sleep_ms(int(float(soft_pressure_release_time) * 1000))

        # ===== PRESSURE DRAIN ===== #
        RELAY_SOLENOID.value(0)
        if FEATURES['after_brew_pressure_drain_flag']:
            brew_data.set_mode('after brew pressure drain')
            pressure = brew_data.get_pressure()
            while pressure > 1.5:
                await asyncio.sleep(0.5)
                RELAY_SOLENOID.value(1)
                await asyncio.sleep(0.5)
                RELAY_SOLENOID.value(0)
                pressure = brew_data.get_pressure()
    finally:
        RELAY_PUMP.value(0)
        RELAY_HEATER.value(0)
        RELAY_SOLENOID.value(0)
    return abort_reason


# ============================================================================
# PRESSURE CALIBRATION RUN
# ============================================================================

# PCAL-KORJAUS 19.9.2026. The old run opened a fixed 10 s window at once and averaged seconds
# 5-10 whether or not the target had been reached, so a slow rise - air in the system, a cold
# machine, a tight restrictor - stored a point measured off a *rising* pressure, and the error
# always pointed the same way. The run is now in phases and the measurement window starts only
# after the pressure has settled (user, 19.9.2026).
# Measured 19.9.2026, closed circuit: ONE pump stroke is worth about 1 bar - at a 2 bar target the
# hold sawtoothed 1.05-2.82 bar, and at 8 bar every run tripped the old 1.0 bar overshoot limit at
# 9.0-9.25. The dose is the pump's, not the software's, so the criteria are on a 1 s average of the
# pressure rather than on the instantaneous reading: the sawtooth is real and it cancels in the mean,
# which is also what a damped reference gauge shows.
PCAL_COARSE_GAP = 1.5       # bar below the target where the full pump cycle stops. Room for one
                            # stroke (~1 bar) plus the reading's own lag: the closed circuit rises
                            # ~3.5 bar/s at full duty, so a late stop is a bar of overshoot that
                            # cannot be undone.
# Settled does NOT mean "at the target": one stroke is worth about a bar, so the hold lands wherever
# the last dose left it, and no band narrower than a dose can be reached on purpose. What the
# calibration needs is a *stable* pressure whose true value the reference gauge reads - the target is
# only where we aim. Settled therefore means the 1 s average stopped drifting, within reach of the aim.
PCAL_DRIFT = 0.15           # bar; allowed change of the 1 s average over one second
PCAL_REACH = 1.5            # bar; how far from the target the settled pressure may be
PCAL_DRIFT_MS = 2000        # ms over which the drift is measured. Not a quiet period: the circuit
                            # leaks back fast enough that holding a pressure needs a stroke about
                            # every window, so silence never comes (machine, 19.9.2026). A creep is
                            # told from a steady sawtooth by the length of the window instead - over
                            # 2 s a creep moves and a sawtooth does not.
PCAL_TOPUP = 0.2            # bar below the target where the fine phase fires one more stroke
PCAL_OVERSHOOT = 1.5        # bar above the target, on the average, that ends the run as a runaway
PCAL_AVG_TAU = 1.0          # s; low-pass that judges *settled* and *overshoot*
PCAL_FAST_TAU = 0.3         # s; low-pass that drives the pump. Faster than PCAL_AVG_TAU so it does
                            # not lag a full-duty rise, slower than the raw reading so a single
                            # noisy sample cannot fire a stroke - and one stroke is worth a whole
                            # bar, so a noise-triggered dose lands the hold a bar off target.
PCAL_SETTLE_MS = 1000       # time inside the band before the hold starts
PCAL_HOLD_MS = 30000        # measurement hold: the gauge is read by eye, so it is long
PCAL_STROKE_MS = 17         # one 60 Hz mains cycle: the smallest dose the pump can give
PCAL_TIMEOUT_MS = 60000     # approach timeout -> reason 'not settled', no point stored


async def pressure_calibration_run(brew_data, utime, asyncio, stage):
    RELAY_PUMP, RELAY_SOLENOID, RELAY_HEATER = brew_data.get_relays()
    SWITCH_BREW, SWITCH_WATER, SWITCH_STEAM = brew_data.get_switches()

    if stage == 'pre':
        target = brew_data.get_pre_infusion_pressure()
    else:
        target = brew_data.get_brew_pressure()

    window_ms = brew_data.get_pcal_window_ms()
    brew_data.pressure_calibration_begin(stage, target)
    brew_data.set_mode('pressure calibration')
    RELAY_HEATER.value(0)
    print('PCAL_START %s target=%.2f window=%d drift=%.2f reach=%.2f' % (
        stage, target, window_ms, PCAL_DRIFT, PCAL_REACH))

    from classes import PumpPressureController, PumpRatioCalculator
    hold_controller = None
    raw_sum = 0.0
    raw_n = 0
    p_min = 99.0
    p_max = -99.0
    p_avg = None
    p_fast = None
    p_ref = None
    ref_t = utime.ticks_ms()
    drift = 99.0
    last_avg = utime.ticks_ms()
    reason = ''
    start = utime.ticks_ms()
    settled_since = None
    hold_start = None
    last_stroke = utime.ticks_add(start, -window_ms)
    try:
        RELAY_SOLENOID.value(1)
        while True:
            now = utime.ticks_ms()
            if SWITCH_BREW.value() or SWITCH_WATER.value() or SWITCH_STEAM.value():
                reason = 'machine switch'
                break
            if brew_data.pcal_cancel:
                reason = 'cancelled'
                break

            pressure = brew_data.get_pressure_average(utime)
            if pressure > 12.0:
                reason = 'overpressure %.1f bar' % pressure
                break
            dt = utime.ticks_diff(now, last_avg) / 1000.0
            last_avg = now
            if p_avg is None:
                p_avg = pressure
                p_fast = pressure
            else:
                a = dt / PCAL_AVG_TAU
                p_avg += (pressure - p_avg) * (1.0 if a > 1.0 else a)
                b = dt / PCAL_FAST_TAU
                p_fast += (pressure - p_fast) * (1.0 if b > 1.0 else b)

            if hold_start is None:
                if utime.ticks_diff(now, start) > PCAL_TIMEOUT_MS:
                    reason = 'not settled'
                    break
                # The pump only adds: in a closed circuit an overshoot is permanent, so it must not
                # start the measurement window - it ends the run instead (user, 19.9.2026).
                if p_avg > target + PCAL_OVERSHOOT or pressure > target + 2.5:
                    reason = 'overshoot %.2f bar' % (p_avg if p_avg > target + PCAL_OVERSHOOT else pressure)
                    break
                # The coarse switch reads the instantaneous pressure, not the average: at a full-duty
                # rise the 1 s low-pass lags by seconds, and a laggy stop overshoots by more than the
                # stroke it was meant to leave room for. The average is used only near the target,
                # where the sawtooth - not the lag - is what has to be filtered out.
                # Each timescale drives what it is good for. The coarse stop reads the fastest
                # value available: stopping a little early is harmless - the fine phase tops up -
                # while stopping late cannot be undone. Judging it on p_fast cost an
                # 'overpressure 12.0 bar' abort on the machine, 19.9.2026.
                if pressure < target - PCAL_COARSE_GAP:
                    RELAY_PUMP.value(1)                 # coarse phase: full cycle
                    settled_since = None
                else:
                    RELAY_PUMP.value(0)                 # fine phase: one stroke per window
                    # The top-up trigger is a control action and reads the instantaneous pressure:
                    # on the laggy average the fine phase keeps dosing while the average catches up,
                    # and each dose is a whole bar. The average judges *settled*; it does not drive.
                    if p_fast < target - PCAL_TOPUP and utime.ticks_diff(now, last_stroke) >= window_ms:
                        last_stroke = now
                        RELAY_PUMP.value(1)
                        await asyncio.sleep_ms(PCAL_STROKE_MS)
                        RELAY_PUMP.value(0)
                    if utime.ticks_diff(now, ref_t) >= PCAL_DRIFT_MS:
                        drift = 99.0 if p_ref is None else abs(p_avg - p_ref)
                        p_ref = p_avg
                        ref_t = now
                    if drift > PCAL_DRIFT or abs(p_avg - target) > PCAL_REACH:
                        settled_since = None
                    elif settled_since is None:
                        settled_since = now
                    elif utime.ticks_diff(now, settled_since) >= PCAL_SETTLE_MS:
                        hold_start = now
                        # The hold is handed to the ordinary pressure controller. Measured
                        # 19.9.2026: one stroke per 500 ms window swings 4.6 bar at an 8 bar target,
                        # while the controller's own time-proportional chopping swings 1.8 bar at
                        # 10 bar and 0.6 bar at 5 bar. The fine phase earns its place in the
                        # approach, where it prevents an overshoot that cannot be undone - not in
                        # the hold, where more frequent, smaller doses win.
                        hold_controller = PumpPressureController(
                            RELAY_PUMP, PumpRatioCalculator(utime, asyncio), utime, ff=0.05)
                        print('PCAL_SETTLED %s t=%.1f p=%.2f drift=%.2f' % (
                            stage, utime.ticks_diff(now, start) / 1000.0, p_avg, drift))
            else:
                hold_controller.update(pressure, target)
                raw_sum += brew_data.get_pressure_raw()
                raw_n += 1
                if pressure < p_min:
                    p_min = pressure
                if pressure > p_max:
                    p_max = pressure
                if utime.ticks_diff(now, hold_start) >= PCAL_HOLD_MS:
                    break

            await asyncio.sleep_ms(0)
    finally:
        if hold_controller is not None:
            hold_controller.stop()
        RELAY_PUMP.value(0)
        RELAY_SOLENOID.value(0)
        brew_data.set_mode('IDLE')

    if reason or raw_n == 0:
        print('PCAL_ABORT %s reason=%s' % (stage, reason or 'no samples'))
        brew_data.pressure_calibration_end(stage, None, reason)
    else:
        # p_min/p_max over the hold are the ripple measurement: one pump stroke is the smallest dose
        # there is, so this is what a longer window has to beat before it is worth anything.
        print('PCAL_END %s raw=%.3f n=%d p_min=%.2f p_max=%.2f window=%d reason=ok' % (
            stage, raw_sum / raw_n, raw_n, p_min, p_max, window_ms))
        brew_data.pressure_calibration_end(stage, raw_sum / raw_n, '')


async def pressure_zero_run(brew_data, utime, asyncio):
    # A resting reading is not a zero: with the solenoid closed the boiler's own thermal expansion
    # reaches ~14 bar at idle (functions.py running(), 17.9.2026), and the after-brew drain stops at
    # 1.5 bar *indicated* - a threshold read from the very calibration under test. The zero is taken
    # vented: heater off, solenoid cycled until the raw value stops moving (user, 19.9.2026).
    RELAY_PUMP, RELAY_SOLENOID, RELAY_HEATER = brew_data.get_relays()
    RELAY_HEATER.value(0)
    RELAY_PUMP.value(0)
    brew_data.set_mode('pressure zero')
    print('PZERO_START')
    prev = None
    stable = 0
    raw = 0.0
    cycles = 0
    try:
        for cycles in range(1, 31):
            RELAY_SOLENOID.value(1)
            await asyncio.sleep_ms(500)
            RELAY_SOLENOID.value(0)
            await asyncio.sleep_ms(500)
            for _ in range(8):
                brew_data.get_pressure_average(utime)
                await asyncio.sleep_ms(20)
            raw = brew_data.get_pressure_raw()
            if prev is not None and abs(raw - prev) < 0.02:
                stable += 1
            else:
                stable = 0
            prev = raw
            if stable >= 3:
                break
    finally:
        RELAY_SOLENOID.value(0)
        RELAY_PUMP.value(0)
        brew_data.set_mode('IDLE')

    sensor = brew_data.pressure_sensor
    offset = -sensor.gain * raw
    if stable < 3:
        print('PZERO_ABORT reason=not stable raw=%.3f cycles=%d' % (raw, cycles))
        return
    if not sensor.calibration_valid(sensor.gain, offset):
        print('PZERO_ABORT reason=rejected gain=%.4f offset=%.3f' % (sensor.gain, offset))
        return
    sensor.set_calibration(sensor.gain, offset)
    sensor.save_calibration()
    print('PZERO_OK raw=%.3f gain=%.4f offset=%.3f cycles=%d' % (raw, sensor.gain, offset, cycles))


# ============================================================================
# PRESSURE CAPTURE — raw ADC waveform for mains-frequency analysis (PWM-1A-VERKKOTAAJUUS, 19.9.2026)
# ============================================================================

PCAP_RATE_US = 1000         # sample period (rule 3): 50/60 Hz separation, 16x oversampled at 60 Hz
PCAP_MAINS_US = 19960        # mitattu verkkojakso: 50,1 Hz kolmesta laiteajosta 19.9.2026.
                             # Oma vakionsa tarkoituksella — viiden 60 Hz -vakion yhdistäminen
                             # yhdeksi lähteeksi on vaihe 1a3, joka ajetaan vaiheen 1c kanssa.
PCAP_GATE_PERIOD_US = 2 * PCAP_MAINS_US   # joka toisen verkkojakson ohitus (paketin sääntö 6)
PCAP_ROW = 20                # raw values per PCAP line (full rows only, see protocol in PUMPPU-PWM.md)
# Factory formula (classes.py:930): raw ADC -> raw_bar. Overpressure and pmax then apply the
# sensor's live gain/offset (classes.py:948, korjaus 1) — calibration is not identity.
PCAP_RAW_A = 0.000314936
PCAP_RAW_B = -3.522929
PCAP_OVER_BAR = 11.0
PCAP_SETTLE_MAX_MS = 15000   # hard cap on the event-driven settling phase (korjaus 2)
PCAP_SETTLE_MIN_MS = 2000    # no termination condition fires before this (korjaus 4, measured): the
                              # pump fills the empty circuit for over a second with no rise at all
PCAP_PLATEAU_MS = 1000       # plateau window: rise below PCAP_PLATEAU_BAR over this span ends settling
PCAP_PLATEAU_BAR = 0.15      # measured: filtered noise sd 0.034 bar -> 1s-apart diff sd ~0.048 bar (korjaus 3)
PCAP_PLATEAU_MIN_BAR = 1.0   # plateau not even tested below this filtered bar (korjaus 4): the fill
                              # phase is a genuine plateau by any rise-based test, and must not qualify
PCAP_FILT_TAU = 0.3          # one-pole low-pass time constant, s (korjaus 3): raw-sample sd is 1.595 bar,
                              # too noisy for either settling test on its own
PCAP_HOLD_MS = 3000          # korjaus 5: dwell after the target/plateau condition fires, before capture
                              # starts — 3*tau (plant tau=1/1.24 s) to 5%, plus PCAP_FILT_TAU's own lag,
                              # rounded up (real_plant_sim.py: GAIN, LEAK = 6.7, 1.24)

MCAL_VENT_ON_MS = 500        # purkusykli (TILAUS-H, spec 2): venttiili paalla
MCAL_VENT_OFF_MS = 200       # ...ja pois, toisto kunnes paine ei enaa laske
MCAL_VENT_MAX_CYCLES = 200   # karkausraja: ylitys on vika, ei normaali lopetus (spec 2)
MCAL_GRID = [49.0 + 0.4 * k for k in range(7)]   # hila 49,0-51,4 Hz (spec 3.5)


def pcap_gate(i, phase_us, period_us=None):
    """1 = pumppu päällä. Päälläolo on aina yksi verkkojakso; `period_us` päättää, kuinka
    pitkään portti on sen jälkeen kiinni (sääntö 14)."""
    p = PCAP_GATE_PERIOD_US if period_us is None else period_us
    return 1 if ((i * PCAP_RATE_US + phase_us) % p) < PCAP_MAINS_US else 0


# ============================================================================
# TRAY GUARD (testikomennot — EXPRESSO-KAUKALOVAHTI, spec kohta 0; kokonaispaino
# EXPRESSO-KAUKALOVAHTI-KOKONAISPAINO 21.9.2026)
# ============================================================================
# wmax on pakollinen ja absoluuttinen: se ei nollaudu ajojen välissä, kun taas wrise mitataan
# kunkin ajon alusta. Neljä peräkkäistä ajoa sai 20.9.2026 kukin oman 250 g:n nousuvaransa ja
# kaukalo tulvi yli, koska wmax oli asettamatta. Siksi pelkkä wrise ei enää riitä ajon aloitukseen,
# eikä ajo ala, jos kaukalo on jo rajalla.

TRAY_STALE_MS = 2000     # lukema vanhentuneeksi; sama arvo kuin tshot-polulla (functions.py:159-161)
TRAY_RESYNC_MS = 300     # kaappauksen jälkeisen tarkistuksen enimmäisodotus tuoreelle lukemalle
                         # (spec 0.2, avoimen vian korjaus): kaappaussilmukka ei anna vuoroa.


def tray_guard_start(brew_data, utime):
    """Ennen releiden kytkentää. Palauttaa (state, None) tai (None, '<syy>')."""
    if brew_data.get_weight_limit() <= 0:
        return None, 'nolimit'
    weight = brew_data.get_weight()
    age = utime.ticks_diff(utime.ticks_ms(), brew_data.get_weight_ms())
    if weight is None or age > TRAY_STALE_MS:
        return None, 'noscale'
    if weight >= brew_data.get_weight_limit():
        return None, 'tray'
    return {'start': weight, 'last_ms': None, 'over': 0}, None


def tray_guard_check(brew_data, utime, state):
    """Ajon aikana. Palauttaa None tai '<syy>'."""
    limit = brew_data.get_weight_limit()
    rise_limit = brew_data.get_weight_rise_limit()
    weight = brew_data.get_weight()
    age = utime.ticks_diff(utime.ticks_ms(), brew_data.get_weight_ms())
    if weight is None or age > TRAY_STALE_MS:
        return 'scalelost'
    # Two consecutive *samples* over a limit, not two loop iterations (spec kohta 1, sama kuin
    # tshot-polku functions.py:169-176): loop runs far faster than the scale, and single spikes of
    # -16 g were seen in telemetry.
    ms = brew_data.get_weight_ms()
    if ms != state['last_ms']:
        state['last_ms'] = ms
        hit = (limit > 0 and weight >= limit) or \
              (rise_limit > 0 and weight - state['start'] >= rise_limit)
        state['over'] = state['over'] + 1 if hit else 0
    if state['over'] >= 2:
        if limit > 0 and weight >= limit:
            return 'tray'
        return 'trayrise'
    return None


def tray_guard_poll(brew_data, utime, state):
    """Tray check inside a capture loop that never yields (pstep/pgap/plen, called ~once a second
    with devsafe.feed()). Reads the scale itself, because scale_reader cannot run meanwhile; before
    this the tray was checked only at the start and the end of a 14-58 s pump run, and the tray
    overflowed on these commands on 20.9.2026 (EXPRESSO-TURVA-TOIMILAITE, 22.9.2026). Two fresh
    samples over the limit are ~2 s at this rate. Returns None or '<reason>'."""
    poll = getattr(brew_data, 'scale_poll', None)
    if poll is not None:
        poll()
    return tray_guard_check(brew_data, utime, state)


def _sweep_break(brew_data, abort_attr):
    """Switch/dev_safe/abort-tarkistus, yhteinen kolmelle kutsujalle. Palauttaa syyn tai None."""
    SWITCH_BREW, SWITCH_WATER, SWITCH_STEAM = brew_data.get_switches()
    if SWITCH_BREW.value() or SWITCH_WATER.value() or SWITCH_STEAM.value():
        return 'switch'
    if brew_data.dev_safe:
        return 'devsafe'
    if getattr(brew_data, abort_attr):
        return 'stop'
    return None


async def tray_guard_recheck(brew_data, utime, asyncio, state):
    """Kaappauksen jälkeinen tarkistus (spec 0.2): odottaa tuoretta weight_ms:ää enintään
    TRAY_RESYNC_MS ennen tray_guard_check:ia."""
    await asyncio.sleep_ms(0)
    last_ms = brew_data.get_weight_ms()
    start = utime.ticks_ms()
    while utime.ticks_diff(utime.ticks_ms(), start) < TRAY_RESYNC_MS:
        if brew_data.get_weight_ms() != last_ms: break
        await asyncio.sleep_ms(10)
    return tray_guard_check(brew_data, utime, state)


async def pcap_settle(brew_data, utime, asyncio, sensor, gain, offset, target, tray_state):
    """Asettumis- ja pitovaihe, irrotettu pressure_capture_run:sta (spec 0.1) niin että
    pressure_sweep_run voi käyttää samaa. Mekaaninen siirto: samat vakiot, keskeytysehdot,
    PCAP_SETTLED-tuloste ja sleep_ms(0) joka kierroksella. Palauttaa (settled, reason, p_filt)."""
    reason = 'ok'
    pmax_bar = -99.0
    settle_t0 = utime.ticks_ms()
    last_t = settle_t0
    p_filt = gain * (sensor.read_u16() * PCAP_RAW_A + PCAP_RAW_B) + offset   # one-pole filter seed
    plateau_t = None          # korjaus 4: unseeded until PCAP_SETTLE_MIN_MS, then the filtered value
    plateau_bar = None
    settled = False
    while not settled:
        r = _sweep_break(brew_data, 'pcap_abort')
        if r: reason = r; break
        tray_reason = tray_guard_check(brew_data, utime, tray_state)
        if tray_reason: reason = tray_reason; break
        bar = gain * (sensor.read_u16() * PCAP_RAW_A + PCAP_RAW_B) + offset
        if bar > pmax_bar: pmax_bar = bar
        if bar > PCAP_OVER_BAR:     # pmax/overpressure stay on the raw sample (korjaus 3)
            reason = 'overpressure'; break
        now = utime.ticks_ms()
        dt = utime.ticks_diff(now, last_t) / 1000.0
        last_t = now
        p_filt += (bar - p_filt) * min(1.0, dt / PCAP_FILT_TAU)
        settle_ms = utime.ticks_diff(now, settle_t0)
        settle_reason = None
        if p_filt < PCAP_PLATEAU_MIN_BAR or plateau_t is None:    # korjaus 4: fill-phase floor
            plateau_t, plateau_bar = now, p_filt
        if settle_ms >= PCAP_SETTLE_MIN_MS:
            if target is not None and p_filt >= target:
                settle_reason = 'target'
            elif utime.ticks_diff(now, plateau_t) >= PCAP_PLATEAU_MS:
                if (p_filt - plateau_bar) < PCAP_PLATEAU_BAR:
                    settle_reason = 'plateau'
                else:
                    plateau_t, plateau_bar = now, p_filt
        if settle_reason is None and settle_ms >= PCAP_SETTLE_MAX_MS:
            settle_reason = 'timeout'
        if settle_reason is not None:
            # Hold phase (korjaus 5): pump stays on for PCAP_HOLD_MS while p_filt keeps tracking.
            reach_ms = settle_ms
            hold_start_bar = p_filt
            hold_t0 = utime.ticks_ms()
            hold_last_t = hold_t0
            aborted = False
            hold_ms = 0
            while True:
                r = _sweep_break(brew_data, 'pcap_abort')
                if r: reason = r; aborted = True; break
                tray_reason = tray_guard_check(brew_data, utime, tray_state)
                if tray_reason: reason = tray_reason; aborted = True; break
                hold_bar = gain * (sensor.read_u16() * PCAP_RAW_A + PCAP_RAW_B) + offset
                if hold_bar > pmax_bar: pmax_bar = hold_bar
                if hold_bar > PCAP_OVER_BAR:
                    reason = 'overpressure'; aborted = True; break
                hold_now = utime.ticks_ms()
                hold_dt = utime.ticks_diff(hold_now, hold_last_t) / 1000.0
                hold_last_t = hold_now
                p_filt += (hold_bar - p_filt) * min(1.0, hold_dt / PCAP_FILT_TAU)
                hold_ms = utime.ticks_diff(hold_now, hold_t0)
                if hold_ms >= PCAP_HOLD_MS: break
                await asyncio.sleep_ms(0)
            if aborted: break
            drift = p_filt - hold_start_bar
            print('PCAP_SETTLED bar=%.2f peak=%.2f reach_ms=%d hold_ms=%d drift=%.2f reason=%s' % (
                p_filt, pmax_bar, reach_ms, hold_ms, drift, settle_reason))
            settled = True
            break
        await asyncio.sleep_ms(0)
    return settled, reason, p_filt


async def _pcap_capture(brew_data, utime, asyncio, sensor, gain, offset, n, phase_us, abort_attr,
                         restore_pump=False, period_us=None):
    """Kaappaussilmukka + PCAP-rivit, yhteinen pressure_capture_run:lle ja pyyhkäisyn segmenteille.
    PCAP_END jää kutsujalle (syy voi vielä muuttua). Palauttaa (reason, count, elapsed, pmax_bar, last_bar).
    `period_us` on portin jakso (sääntö 14); `None` pitää `pressure_capture_run`:n käytöksen
    sanatarkasti entisenä, koska `pcap_gate`:n oma oletus on sama."""
    from array import array
    RELAY_PUMP, RELAY_SOLENOID, RELAY_HEATER = brew_data.get_relays()
    buf = array('H', bytes(2 * n))
    row_t = []
    count = 0
    pmax_bar = -99.0
    elapsed = 0
    last_bar = None
    t0 = utime.ticks_us()
    next_t = t0
    pump_state = 1     # RELAY_PUMP is already on from settling/trim (spec 3)
    reason = None
    for i in range(n):
        reason = _sweep_break(brew_data, abort_attr)
        if reason: break
        if phase_us is not None:
            g = pcap_gate(i, phase_us, period_us)
            if g != pump_state: RELAY_PUMP.value(g); pump_state = g
        while utime.ticks_diff(next_t, utime.ticks_us()) > 0: pass
        v = sensor.read_u16()
        elapsed = utime.ticks_diff(utime.ticks_us(), t0)
        buf[i] = v
        if i % PCAP_ROW == 0: row_t.append(elapsed)
        count += 1
        bar = gain * (v * PCAP_RAW_A + PCAP_RAW_B) + offset
        last_bar = bar
        if bar > pmax_bar: pmax_bar = bar
        next_t = utime.ticks_add(next_t, PCAP_RATE_US)
        if bar > PCAP_OVER_BAR: reason = 'overpressure'; break
    reason = reason or 'ok'
    if restore_pump and phase_us is not None and pump_state != 1:
        RELAY_PUMP.value(1)    # pump back on before the trim step that follows (psweep only)
    full_rows = count // PCAP_ROW
    for r in range(full_rows):
        row_start = r * PCAP_ROW
        vals = ' '.join(str(buf[row_start + j]) for j in range(PCAP_ROW))
        print('PCAP %d %d %s' % (row_start, row_t[r], vals))
        if (r + 1) % 10 == 0: await asyncio.sleep_ms(0)   # yield to watchdog (korjaus 3)
    return reason, count, elapsed, pmax_bar, last_bar


async def pressure_capture_run(brew_data, utime, asyncio, ms):
    RELAY_PUMP, RELAY_SOLENOID, RELAY_HEATER = brew_data.get_relays()
    SWITCH_BREW, SWITCH_WATER, SWITCH_STEAM = brew_data.get_switches()
    n = int(ms)
    # Target bar is optional (pcap:<ms>[:<bar>]); classes.py/main.py are out of scope this round, so
    # it travels as a plain attribute on brew_data set by commands.py, not a declared field.
    target = getattr(brew_data, 'pcap_target_bar', None)
    # Gate phase is optional too (pcap:<ms>:<bar>:<phase_us>), same plain-attribute path as target
    # (PWM-1B2-PORTITUS, spec 3-4).
    phase_us = getattr(brew_data, 'pcap_gate_phase_us', None)
    sensor = brew_data.pressure_sensor.pressure_sensor
    gain = brew_data.pressure_sensor.gain
    offset = brew_data.pressure_sensor.offset
    if phase_us is not None:
        print('PCAP_START rate=%d n=%d settle=%s gain=%.4f offset=%.3f gate=on period_us=%d on_us=%d phase_us=%d' % (
            1000000 // PCAP_RATE_US, n, 'target' if target is not None else 'plateau', gain, offset,
            PCAP_GATE_PERIOD_US, PCAP_MAINS_US, phase_us))
    else:
        print('PCAP_START rate=%d n=%d settle=%s gain=%.4f offset=%.3f gate=off' % (
            1000000 // PCAP_RATE_US, n, 'target' if target is not None else 'plateau', gain, offset))
    if SWITCH_BREW.value() or SWITCH_WATER.value() or SWITCH_STEAM.value():
        print('PCAP_END n=0 dur_us=0 pmax=0.00 reason=switch'); return
    if brew_data.dev_safe:
        print('PCAP_END n=0 dur_us=0 pmax=0.00 reason=devsafe'); return
    tray_state, tray_reason = tray_guard_start(brew_data, utime)
    if tray_reason:
        print('PCAP_END n=0 dur_us=0 pmax=0.00 reason=%s' % tray_reason); return

    count = 0
    pmax_bar = -99.0
    elapsed = 0
    brew_data.set_mode('pressure capture')
    try:
        RELAY_SOLENOID.value(1)     # solenoid before pump, like every other pumping path (korjaus 1)
        RELAY_PUMP.value(1)
        # Settling is event-driven (korjaus 2), extracted to pcap_settle (spec 0.1) so it's shared.
        settled, reason, p_filt = await pcap_settle(
            brew_data, utime, asyncio, sensor, gain, offset, target, tray_state)
        if settled:
            # Tray guard just before and just after the capture loop, never inside it (spec 2): the
            # loop busy-waits. Before stays direct; after uses tray_guard_recheck (spec 0.2 fix).
            tray_reason = tray_guard_check(brew_data, utime, tray_state)
            if tray_reason:
                reason = tray_reason
            else:
                reason, count, elapsed, pmax_bar, _ = await _pcap_capture(
                    brew_data, utime, asyncio, sensor, gain, offset, n, phase_us, 'pcap_abort')
                if reason == 'ok':
                    tray_reason = await tray_guard_recheck(brew_data, utime, asyncio, tray_state)
                    if tray_reason: reason = tray_reason
    finally:
        RELAY_PUMP.value(0)
        RELAY_SOLENOID.value(0)
        brew_data.set_mode('IDLE')
        brew_data.pcap_abort = False
    print('PCAP_END n=%d dur_us=%d pmax=%.2f reason=%s' % (
        count, elapsed if count else 0, pmax_bar if count else 0.00, reason))


# PHASE SWEEP (PWM-1B4-PYYHKAISY, säännöt 10-13): segmentit ref, p_0..p_{n-1}, ref, trimmaus väliin.
PSWEEP_N_DEFAULT = 5         # vaihesiirtojen määrä, kun kenttää ei anneta (sääntö 10)
PSWEEP_N_MAX = 8
PSWEEP_TRIM_BAR = 0.3        # kuollut alue tavoitteen ympärillä (sääntö 13)
PSWEEP_TRIM_MS = 8000        # trimmausaskeleen enimmäiskesto
PSWEEP_TRIM_PRINT_MS = 500   # ei omaa tulostetta askeleen aikana; yksi rivi lopuksi
PSWEEP_MULT_DEFAULT = 2      # portin jakso verkkojaksoina; 2 = entinen 1-paalla-1-pois
PSWEEP_MULT_MAX = 16


def psweep_phases(n, period_us=None):
    """Tasavälein portin jakson yli, ensimmäinen 0 (sääntö 10)."""
    p = PCAP_GATE_PERIOD_US if period_us is None else period_us
    return [k * p // n for k in range(n)]


async def _psweep_segment(brew_data, utime, asyncio, sensor, gain, offset, tray_state, seg, ms,
                           phase_us, period_us, mult):
    """Yksi pyyhkäisyn segmentti: kelvollinen pcap-loki (spec 3) plus seg=<k>, kaappaus jaettua
    _pcap_capture:a käyttäen. Tray guard suorana ennen, tray_guard_recheck:llä jälkeen (spec 0.2).
    `period_us`/`mult` ovat portin jakso kertoimineen (sääntö 14); referenssisegmentin otsikko
    (`gate=off`) ei muutu. Palauttaa (reason, viimeinen bar tai None)."""
    n = int(ms)
    if phase_us is not None:
        print('PCAP_START rate=%d n=%d settle=target gain=%.4f offset=%.3f seg=%d gate=on period_us=%d on_us=%d phase_us=%d mult=%d' % (
            1000000 // PCAP_RATE_US, n, gain, offset, seg, period_us, PCAP_MAINS_US, phase_us, mult))
    else:
        print('PCAP_START rate=%d n=%d settle=target gain=%.4f offset=%.3f seg=%d gate=off' % (
            1000000 // PCAP_RATE_US, n, gain, offset, seg))
    tray_reason = tray_guard_check(brew_data, utime, tray_state)
    if tray_reason:
        reason, count, elapsed, pmax_bar, last_bar = tray_reason, 0, 0, 0.00, None
    else:
        reason, count, elapsed, pmax_bar, last_bar = await _pcap_capture(
            brew_data, utime, asyncio, sensor, gain, offset, n, phase_us, 'psweep_abort',
            restore_pump=True, period_us=period_us)
        if reason == 'ok':
            tray_reason = await tray_guard_recheck(brew_data, utime, asyncio, tray_state)
            if tray_reason: reason = tray_reason
    print('PCAP_END n=%d dur_us=%d pmax=%.2f seg=%d reason=%s' % (
        count, elapsed if count else 0, pmax_bar if count else 0.00, seg, reason))
    return reason, last_bar


async def _psweep_trim(brew_data, utime, asyncio, sensor, gain, offset, target, tray_state,
                        prev_seg, seed_bar):
    """Trimmausaskel segmenttien väliin (spec 4, sääntö 13): palauttaa paineen kuolleeseen
    alueeseen, sama suodin kuin asettumisessa, alkuarvona edellisen segmentin viimeinen lukema."""
    RELAY_PUMP, RELAY_SOLENOID, RELAY_HEATER = brew_data.get_relays()
    reason = 'ok'
    p_filt = seed_bar
    t0 = utime.ticks_ms()
    last_t = t0
    while True:
        if p_filt > target + PSWEEP_TRIM_BAR:
            RELAY_PUMP.value(0); RELAY_SOLENOID.value(1)
        elif p_filt < target - PSWEEP_TRIM_BAR:
            RELAY_PUMP.value(1); RELAY_SOLENOID.value(0)
        else:
            break
        await asyncio.sleep_ms(2)
        r = _sweep_break(brew_data, 'psweep_abort')
        if r: reason = r; break
        tray_reason = tray_guard_check(brew_data, utime, tray_state)
        if tray_reason: reason = tray_reason; break
        now = utime.ticks_ms()
        dt = utime.ticks_diff(now, last_t) / 1000.0
        last_t = now
        bar = gain * (sensor.read_u16() * PCAP_RAW_A + PCAP_RAW_B) + offset
        # Ylipaineraja, jota trimmauksessa ei ollut (EXPRESSO-TURVA-PIKAKORJAUKSET 21.9.2026):
        # pumppu kay tassa taydella teholla, kunnes suodin nousee kuolleeseen alueeseen.
        if bar > PCAP_OVER_BAR: reason = 'overpressure'; break
        p_filt += (bar - p_filt) * min(1.0, dt / PCAP_FILT_TAU)
        if utime.ticks_diff(now, t0) >= PSWEEP_TRIM_MS: reason = 'timeout'; break
    ms_elapsed = utime.ticks_diff(utime.ticks_ms(), t0)
    # Takaisin NORMAALIAJON tilaan: pressure_sweep_run avaa venttiilin value(1):lla ennen pumppua,
    # joten trimmauksen on jatettava se samaan tilaan. Tassa oli value(0), jolloin ensimmaisen
    # trimmauksen jalkeiset segmentit ajettiin eri venttiilitilassa kuin segmentti 0 — loydetty
    # 20.9.2026, ja se voi selittaa saman paivan pyyhkaisyajojen ylipainekatkot.
    # Vain kun ajo jatkuu (ok/timeout, ks. pressure_sweep_run): keskeytyksen, ylipaineen tai
    # kaukalovahdin jalkeen pumppu jaa pois eika sita kytketa takaisin (21.9.2026).
    if reason in ('ok', 'timeout'):
        RELAY_SOLENOID.value(1)
        RELAY_PUMP.value(1)
    else:
        RELAY_PUMP.value(0)
    print('PSWEEP_TRIM seg=%d bar=%.2f ms=%d reason=%s' % (prev_seg, p_filt, ms_elapsed, reason))
    return reason


async def pressure_sweep_run(brew_data, utime, asyncio, ms):
    """Vaihesiirtopyyhkäisy yhtenä laitekomentona (PWM-1B4, säännöt 10-13): ref, p_0..p_{n-1}, ref."""
    SWITCH_BREW, SWITCH_WATER, SWITCH_STEAM = brew_data.get_switches()
    RELAY_PUMP, RELAY_SOLENOID, RELAY_HEATER = brew_data.get_relays()
    seg_ms = int(ms)
    target = getattr(brew_data, 'psweep_target_bar', None)
    n = getattr(brew_data, 'psweep_n', None) or PSWEEP_N_DEFAULT
    mult = getattr(brew_data, 'psweep_mult', None) or PSWEEP_MULT_DEFAULT
    period_us = mult * PCAP_MAINS_US
    sensor = brew_data.pressure_sensor.pressure_sensor
    gain = brew_data.pressure_sensor.gain
    offset = brew_data.pressure_sensor.offset
    print('PSWEEP_START segs=%d n=%d ms=%d target=%.2f period_us=%d on_us=%d mult=%d' % (
        n + 2, n, seg_ms, target if target is not None else 0.0, period_us, PCAP_MAINS_US, mult))
    if SWITCH_BREW.value() or SWITCH_WATER.value() or SWITCH_STEAM.value():
        print('PSWEEP_END segs=0 dur_ms=0 reason=switch'); return
    if brew_data.dev_safe:
        print('PSWEEP_END segs=0 dur_ms=0 reason=devsafe'); return
    tray_state, tray_reason = tray_guard_start(brew_data, utime)
    if tray_reason: print('PSWEEP_END segs=0 dur_ms=0 reason=%s' % tray_reason); return
    segs_done = 0
    reason = 'ok'
    dur_ms = 0
    brew_data.set_mode('pressure sweep')
    try:
        RELAY_SOLENOID.value(1)     # solenoid before pump, like every other pumping path
        RELAY_PUMP.value(1)
        settled, reason, p_filt = await pcap_settle(
            brew_data, utime, asyncio, sensor, gain, offset, target, tray_state)
        if settled:
            dur_t0 = utime.ticks_ms()      # dur_ms on asettumisen jälkeinen kesto (spec 2.7)
            phase_list = [None] + list(psweep_phases(n, period_us)) + [None]  # ref, p_0..p_{n-1}, ref
            last_bar = p_filt
            for k, phase_us in enumerate(phase_list):
                seg_reason, seg_last_bar = await _psweep_segment(
                    brew_data, utime, asyncio, sensor, gain, offset, tray_state, k, seg_ms,
                    phase_us, period_us, mult)
                segs_done += 1
                if seg_last_bar is not None:
                    last_bar = seg_last_bar
                if seg_reason != 'ok':
                    reason = seg_reason
                    break
                if k < len(phase_list) - 1:    # trim between segments (spec 2.6); timeout continues
                    trim_reason = await _psweep_trim(
                        brew_data, utime, asyncio, sensor, gain, offset, target, tray_state, k, last_bar)
                    if trim_reason not in ('ok', 'timeout'):
                        reason = trim_reason
                        break
            dur_ms = utime.ticks_diff(utime.ticks_ms(), dur_t0)
    finally:
        RELAY_PUMP.value(0)
        RELAY_SOLENOID.value(0)
        brew_data.set_mode('IDLE')
        brew_data.psweep_abort = False
    print('PSWEEP_END segs=%d dur_ms=%d reason=%s' % (segs_done, dur_ms, reason))


# ============================================================================
# PRESSURE STEP — yksi ohitettu sykli tasapainossa (kayttajan tilaus 20.9.2026)
# ============================================================================
# Tilaus sanatarkasti: "Sinä ajat tallennus päällä kunnes 7 bar on saavutettu. pidät 7 bar
# paineen. Tiputat 1 sykli ja pois jatka 7 bar 1 sekunnin ajan. tämän sammutat pumpun ja mittaat
# viiveen" ja "sinä tunnistat datasta yhden tippuneen syklin ja mittaat viiveen mikä tämän syklin
# tiputtamisen ja paineessa näkyvä 1 syklin pudotuksen välinen viive on".
#
# Ero pyyhkaisyyn (saannot 10-14): tassa ei portiteta lainkaan. Pumppu kay taydella teholla koko
# ajon, yhta verkkojaksoa lukuun ottamatta, joten paine ei valu eika trimmausta tarvita — juuri ne
# kaatoivat vaiheen 1b laiteajon 20.9.2026 (ks. PUMPPU-PWM.md). Mitattava suure on viive
# ohituskaskysta paineessa nakyvaan pudotukseen, ja toinen riippumaton luku saadaan pumpun
# sammutuksesta ajon lopussa.
PSTEP_MAX_N = 14000          # koko ajon naytekatto 1 kHz:lla (28 KB puskuri)
PSTEP_REACH_MAX_MS = 20000   # tavoitteeseen on paastava tassa ajassa, muuten reason=noreach
PSTEP_MIN_MS = 2000          # tavoitetta ei testata ennen tata (sama perustelu kuin
                              # PCAP_SETTLE_MIN_MS): suodin siemennetaan yhdesta raakanaytteesta,
                              # jonka hajonta on 1,595 bar, ja mitattu vika 20.9.2026 oli juuri
                              # tama — yksi korkea siemen antoi reach=0 kun paine oli 0,4 bar.
                              # 2 s:ssa yksinapasuodin (tau 0,3 s) on asettunut siemenestaan.
PSTEP_HOLD_MS = 1000         # pito tavoitteessa ennen ohitettua syklia
PSTEP_RUN_MS = 1000          # tilaus: ohituksen jalkeen jatketaan sekunti ennen sammutusta
PSTEP_TAIL_MS = 1500         # tallennus jatkuu sammutuksen jalkeen
PSTEP_FEED_MASK = 0x3FF      # devsafe.feed() joka 1024. nayte: silmukka ei anna vuoroa 8 s:n
                              # laitteistovahdille, joten se ruokitaan kasin (pcap busy-waittaa
                              # vain 2,5 s eika tarvitse tata; tama ajo kestaa yli 8 s)


async def pressure_step_run(brew_data, utime, asyncio, target):
    """Yksi ohitettu verkkojakso tasapainossa, tallennus paalla koko ajon (tilaus 20.9.2026).

    Vaiheet yhdessa 1 kHz:n silmukassa, koska ohituskaskyn hetki on mitattava suure eika se saa
    joutua eri silmukkaan kuin naytteet: nousu tavoitteeseen -> pito -> yksi jakso pois ->
    PSTEP_RUN_MS -> pumppu pois -> hanta. Naytevali on PCAP_RATE_US = 1000 us, joten naytteen
    indeksi on millisekunti; PSTEP_MARK-rivi kertoo kolmen tapahtuman indeksit."""
    from array import array
    import devsafe
    RELAY_PUMP, RELAY_SOLENOID, RELAY_HEATER = brew_data.get_relays()
    sensor = brew_data.pressure_sensor.pressure_sensor
    gain = brew_data.pressure_sensor.gain
    offset = brew_data.pressure_sensor.offset
    hold_ms = getattr(brew_data, 'pstep_hold_ms', None) or PSTEP_HOLD_MS
    tail_ms = getattr(brew_data, 'pstep_tail_ms', None) or PSTEP_TAIL_MS
    print('PSTEP_START rate=%d target=%.2f hold_ms=%d run_ms=%d tail_ms=%d notch_us=%d gain=%.4f offset=%.3f' % (
        1000000 // PCAP_RATE_US, target, hold_ms, PSTEP_RUN_MS, tail_ms, PCAP_MAINS_US, gain, offset))
    r = _sweep_break(brew_data, 'pstep_abort')
    if r:
        print('PSTEP_END n=0 dur_us=0 pmax=0.00 reason=%s' % r); return
    tray_state, tray_reason = tray_guard_start(brew_data, utime)
    if tray_reason:
        print('PSTEP_END n=0 dur_us=0 pmax=0.00 reason=%s' % tray_reason); return

    buf = array('H', bytes(2 * PSTEP_MAX_N))
    i_reach = i_notch = i_stop = -1
    notch_pending = False
    pmax_bar = -99.0
    count = 0
    elapsed = 0
    reason = 'ok'
    brew_data.set_mode('pressure step')
    try:
        RELAY_SOLENOID.value(1)     # solenoid before pump, like every other pumping path
        RELAY_PUMP.value(1)
        t0 = next_t = utime.ticks_us()
        p_filt = gain * (sensor.read_u16() * PCAP_RAW_A + PCAP_RAW_B) + offset
        alpha = (PCAP_RATE_US / 1000000.0) / PCAP_FILT_TAU    # kiintea naytevali, ei ticks-mittausta
        notch_t0 = 0
        for i in range(PSTEP_MAX_N):
            while utime.ticks_diff(next_t, utime.ticks_us()) > 0: pass
            v = sensor.read_u16()
            buf[i] = v
            count = i + 1
            elapsed = utime.ticks_diff(utime.ticks_us(), t0)
            next_t = utime.ticks_add(next_t, PCAP_RATE_US)
            bar = gain * (v * PCAP_RAW_A + PCAP_RAW_B) + offset
            if bar > pmax_bar: pmax_bar = bar
            if bar > PCAP_OVER_BAR: reason = 'overpressure'; break
            p_filt += (bar - p_filt) * alpha
            if (i & PSTEP_FEED_MASK) == 0:
                devsafe.feed()                       # 8 s laitteistovahti, ks. PSTEP_FEED_MASK
                r = _sweep_break(brew_data, 'pstep_abort') or tray_guard_poll(brew_data, utime, tray_state)
                if r: reason = r; break
            if notch_pending:
                # Takaisin paalle tasan yhden verkkojakson jalkeen. Tarkistus kerran naytteessa,
                # joten katkon pituus on 19,96 ms +- 1 ms; se riittaa tasan yhden iskun ohitukseen.
                if utime.ticks_diff(utime.ticks_us(), notch_t0) >= PCAP_MAINS_US:
                    RELAY_PUMP.value(1); notch_pending = False
            if i_reach < 0:
                if i >= PSTEP_MIN_MS and p_filt >= target:
                    i_reach = i
                elif i >= PSTEP_REACH_MAX_MS:
                    reason = 'noreach'; break
            elif i_notch < 0:
                if i - i_reach >= hold_ms:
                    i_notch = i
                    RELAY_PUMP.value(0)              # <- mitattava kaskyhetki
                    notch_t0 = utime.ticks_us()
                    notch_pending = True
            elif i_stop < 0:
                if i - i_notch >= PSTEP_RUN_MS:
                    i_stop = i
                    RELAY_PUMP.value(0)              # <- toinen, riippumaton askel
            elif i - i_stop >= tail_ms:
                break
    except Exception:
        reason = 'error'
    finally:
        RELAY_PUMP.value(0)
        RELAY_SOLENOID.value(0)
        brew_data.set_mode('IDLE')
        brew_data.pstep_abort = False
    tray_reason = await tray_guard_recheck(brew_data, utime, asyncio, tray_state)
    if tray_reason and reason == 'ok': reason = tray_reason
    print('PSTEP_MARK reach=%d notch=%d stop=%d n=%d' % (i_reach, i_notch, i_stop, count))
    full_rows = count // PCAP_ROW
    for r_i in range(full_rows):
        row_start = r_i * PCAP_ROW
        vals = ' '.join(str(buf[row_start + j]) for j in range(PCAP_ROW))
        print('PSTEP %d %s' % (row_start, vals))
        if (r_i + 1) % 10 == 0: await asyncio.sleep_ms(0)   # yield to watchdog while printing
    print('PSTEP_END n=%d dur_us=%d pmax=%.2f reason=%s' % (count, elapsed, pmax_bar, reason))


# ============================================================================
# PRESSURE GAP — monta 20 ms:n taukoa, kohdistus haetaan ajon aikana (tilaus 20.9.2026)
# ============================================================================
# Tilaus: "ajat pumppua täydellä teholla kunnes paine on noin 7 bar. jatkat pumpun ajoa ja teet
# noin 5 kappaletta 20ms taukoja jotka kohdistetaan pumpun täyden syklin kattavaksi. tauot
# tapahtuvat noin puolen sekunnin välein siten että seuraava yrittää korjata edellisen virheen
# perusteella kohtaa".
#
# Mittari on pudotuksen syvyys: tauko, joka peittaa yhden iskun kokonaan, poistaa sen kokonaan ja
# antaa syvimman pudotuksen; kahden iskun valiin osuva tauko vaimentaa molempia osittain ja jaa
# matalaksi. Syvyydessa ei ole etumerkkia, joten kolme ensimmaista taukoa kartoittavat jakson
# kolmanneksin ja kaksi viimeista tarkentavat parhaan ymparilta — nekin edellisten tuloksen
# perusteella, kuten tilaus sanoo.
#
# Vaihereferenssi on ajon alku ja jakso PCAP_MAINS_US. Jos verkon todellinen jakso poikkeaa
# tasta, kohdistus ajautuu ajon aikana: 20.9.2026 mitattu 50,027-50,161 Hz on 19936-19989 us, eli
# enintaan 29 us/jakso, ja viiden tauon ajossa (100 jaksoa) enintaan 2,9 ms. Siksi jokainen
# PGAP-rivi tulostaa seka kasketyn vaiheen etta mitatun pohjan kohdan: ajautuma nakyy niista.
PGAP_N_DEFAULT = 5
PGAP_N_MAX = 12
PGAP_SPACING_MS = 500        # tilaus: noin puolen sekunnin valein
PGAP_SPACING_MAX_MS = 2000   # valin ylaraja (EXPRESSO-TURVA-PIKAKORJAUKSET 21.9.2026): ennen tata
                             # vali oli vain alarajattu, joten pgap saattoi pumpata rajatta
PGAP_RUN_MAX_MS = 120000     # koko ajon katto kaynnistyksesta, sama kuin PHOLD_MAX_S: pisin
                             # hyvaksytty testiajo. Tarkistetaan ajossa, ei vain komennossa.
PGAP_RESP_MS = 200           # vasteikkuna tauon jalkeen, josta pohja etsitaan
PGAP_BASE_MS = 20            # tauon edelta luettu perustaso, yksi verkkojakso
PGAP_SMOOTH_N = 5            # lyhyt keskiarvo pohjan etsintaan: vaimentaa kohinaa, ei kuoppaa
PGAP_BASE_N = 80             # perustason ikkuna: NELJA verkkojaksoa (4 x 19,96 ms ~ 80 ms).
                              # Yksi jakso ei kelpaa: kun ikkuna jaetaan kahtia kulmakertoimen
                              # laskemiseksi, puolikkaat ovat vareilyn kaksi puoliskoa ja
                              # kulmakerroin mittaa vareilya eika trendia — mitattu 20.9.2026,
                              # slope=-0,036 bar/nayte eli 36 bar/s, ja syvyys jai nollaksi.
                              # Kaksi jaksoa per puolikas (40 ms vs 39,92 ms) kumoaa vareilyn.
PGAP_SMOOTH_N = 5            # lyhyt keskiarvo pohjan etsintaan
PGAP_TRIM_BAR = 0.3          # purku, jos perustaso karkaa tavoitteesta yli taman
PGAP_SETTLE_MS = 150         # purun jalkeen odotetaan tama ennen seuraavaa taukoa: pumppu on
                              # taalla taysilla purun valissa, joten palautuminen on nopeaa —
                              # toisin kuin pyyhkaisyssa, jossa portitettu pumppu ei palauttanut
                              # purettua painetta lainkaan (mitattu vika 20.9.2026)
PGAP_CYCLE_MIN_N = 8         # tasta ylospain vaiheet kierratetaan: nelja vaihetta perakkain
                              # toistuvasti, jolloin perustason ajautuma jakautuu tasan kaikille
                              # vaiheille eika voi teeskennella optimia (mitattu vika 20.9.2026:
                              # perustaso nousi 7,58 -> 8,24 bar yhden viiden tauon ajon aikana)
PGAP_CYCLE_K = 4             # montako eri vaihetta kierratetaan


async def pressure_gap_run(brew_data, utime, asyncio, target):
    """Taukoja kierratetyilla vaiheilla tasapainossa (tilaus 20.9.2026).

    Aaltomuotoa ei tallenneta: syvyys lasketaan laitteella, joten muistia ei kulu ja taukojen
    maara ei ole puskurin rajoittama. Tauon pituus on parametri, koska koko jakson mittainen tauko
    poistaa molemmat puolijaksot eika siten reagoi vaiheeseen lainkaan — vaiheen mittaamiseen
    tarvitaan puolijaksoa lyhyempi tauko (kayttajan huomio 20.9.2026)."""
    import devsafe
    RELAY_PUMP, RELAY_SOLENOID, RELAY_HEATER = brew_data.get_relays()
    sensor = brew_data.pressure_sensor.pressure_sensor
    gain = brew_data.pressure_sensor.gain
    offset = brew_data.pressure_sensor.offset
    n_gaps = getattr(brew_data, 'pgap_n', None) or PGAP_N_DEFAULT
    spacing = getattr(brew_data, 'pgap_spacing_ms', None) or PGAP_SPACING_MS
    period = PCAP_MAINS_US
    gap_ms = getattr(brew_data, 'pgap_len_ms', None)
    gap_us = int(gap_ms * 1000) if gap_ms else period
    n_phases = getattr(brew_data, 'pgap_phases', None) or PGAP_CYCLE_K
    lo = getattr(brew_data, 'pgap_lo_us', None)
    hi = getattr(brew_data, 'pgap_hi_us', None)
    if lo is not None and hi is not None and n_phases > 1:
        # Rajattu vaihealue, molemmat paatepisteet mukana: tiheampi haku sielta, missa edellinen
        # ajo antoi viitteita (kayttajan tilaus 20.9.2026).
        phases = [lo + (k * (hi - lo)) // (n_phases - 1) for k in range(n_phases)]
    else:
        phases = [(k * period) // n_phases for k in range(n_phases)]
    print('PGAP_START rate=%d target=%.2f n=%d spacing_ms=%d gap_us=%d period_us=%d phases=%d gain=%.4f offset=%.3f' % (
        1000000 // PCAP_RATE_US, target, n_gaps, spacing, gap_us, period, n_phases, gain, offset))
    r = _sweep_break(brew_data, 'pgap_abort')
    if r:
        print('PGAP_END n=0 gaps=0 pmax=0.00 reason=%s' % r); return
    tray_state, tray_reason = tray_guard_start(brew_data, utime)
    if tray_reason:
        print('PGAP_END n=0 gaps=0 pmax=0.00 reason=%s' % tray_reason); return

    base_ring = [0.0] * PGAP_BASE_N
    sm = [0.0] * PGAP_SMOOTH_N
    pmax_bar = -99.0
    gaps_done = 0
    reason = 'ok'
    reached = False
    brew_data.set_mode('pressure gap')
    try:
        RELAY_SOLENOID.value(1)
        RELAY_PUMP.value(1)
        t0 = next_t = utime.ticks_us()
        p_filt = gain * (sensor.read_u16() * PCAP_RAW_A + PCAP_RAW_B) + offset
        alpha = (PCAP_RATE_US / 1000000.0) / PCAP_FILT_TAU
        gap_off_t = 0
        gap_pending = False
        gap_at = -1
        cur_phase = phases[0]
        base_bar = 0.0
        trough_v = 99.0
        trough_at = 0
        next_gap_j = 0
        j = 0
        while True:
            while utime.ticks_diff(next_t, utime.ticks_us()) > 0: pass
            now = utime.ticks_us()
            v = sensor.read_u16()
            next_t = utime.ticks_add(next_t, PCAP_RATE_US)
            bar = gain * (v * PCAP_RAW_A + PCAP_RAW_B) + offset
            if bar > pmax_bar: pmax_bar = bar
            if bar > PCAP_OVER_BAR: reason = 'overpressure'; break
            p_filt += (bar - p_filt) * alpha
            if (j & PSTEP_FEED_MASK) == 0:
                devsafe.feed()
                r = _sweep_break(brew_data, 'pgap_abort') or tray_guard_poll(brew_data, utime, tray_state)
                if r: reason = r; break
                if utime.ticks_diff(now, t0) > PGAP_RUN_MAX_MS * 1000: reason = 'timeout'; break
            if not reached:
                if j >= PSTEP_MIN_MS and p_filt >= target:
                    reached = True; j = 0; next_gap_j = PGAP_BASE_N + 30
                elif j >= PSTEP_REACH_MAX_MS:
                    reason = 'noreach'; break
                j += 1
                continue
            base_ring[j % PGAP_BASE_N] = bar
            sm[j % PGAP_SMOOTH_N] = bar
            if gap_pending and utime.ticks_diff(now, gap_off_t) >= gap_us:
                RELAY_PUMP.value(1); gap_pending = False
            if gap_at >= 0:
                if j - gap_at >= PGAP_SMOOTH_N:
                    sv = sum(sm) / PGAP_SMOOTH_N
                    # Vajaus suhteessa perustason suoraan, ei vakioon: paine nousee vasteikkunan
                    # aikana noin 0,3 bar, ja ilman tata se meni suoraan hajontaan (mitattu
                    # 20.9.2026 — mittari antoi jopa negatiivisia syvyyksia).
                    dv = (base_bar + slope * (j - gap_at)) - sv
                    if dv > trough_v: trough_v, trough_at = dv, j
                if j - gap_at >= PGAP_RESP_MS:
                    print('PGAP k=%d phase_us=%d len_ms=%d start=%d base_bar=%.3f slope=%.4f depth_bar=%.3f trough_ms=%d' % (
                        gaps_done, cur_phase, gap_us // 1000, gap_at, base_bar, slope,
                        trough_v, trough_at - gap_at))
                    gaps_done += 1
                    gap_at = -1
                    if gaps_done >= n_gaps: break
                    cur_phase = phases[gaps_done % n_phases]
            elif j >= next_gap_j:
                # Aloitus TARKALLEEN kasketyssa vaiheessa. Pelkka naytekohtainen tarkistus antaisi
                # 1 ms:n epatarkkuuden, mika on enemman kuin vaiheaskel (832 us) — vierekkaiset
                # vaiheet osuisivat samaan kohtaan. Siksi silmukka havaitsee ikkunan ETUKATEEN ja
                # odottaa jaljella olevat mikrosekunnit (enintaan 1 ms kerran tauon alussa).
                off = utime.ticks_diff(now, t0) % period
                delta = cur_phase - off
                if 0 <= delta < PCAP_RATE_US:
                    # Perustason suora: ikkunan kaksi puoliskoa antavat kulmakertoimen, jolla
                    # vasteen nousu vahennetaan pois (sama periaate kuin pstep_read.py:ssa).
                    h = PGAP_BASE_N // 2
                    m1 = sum(base_ring[(j - PGAP_BASE_N + 1 + q) % PGAP_BASE_N] for q in range(h)) / h
                    m2 = sum(base_ring[(j - h + 1 + q) % PGAP_BASE_N] for q in range(h)) / h
                    slope = (m2 - m1) / h
                    base_bar = m2 + slope * ((h - 1) / 2.0)
                    trough_v = -99.0        # suurin vajaus suoraan nahden; alkuarvo salli myos
                                            # negatiivisen tuloksen, jotta nolla ei peita vikaa
                    trough_at = j
                    while utime.ticks_diff(utime.ticks_us(), now) < delta: pass
                    gap_at = j
                    RELAY_PUMP.value(0)
                    gap_off_t = utime.ticks_us()
                    gap_pending = True
                    next_gap_j = j + spacing
            j += 1
    except Exception:
        reason = 'error'
    finally:
        RELAY_PUMP.value(0)
        RELAY_SOLENOID.value(0)
        brew_data.set_mode('IDLE')
        brew_data.pgap_abort = False
    tray_reason = await tray_guard_recheck(brew_data, utime, asyncio, tray_state)
    if tray_reason and reason == 'ok': reason = tray_reason
    print('PGAP_END gaps=%d pmax=%.2f reason=%s' % (gaps_done, pmax_bar, reason))


# ============================================================================
# VERKKOKELLO — sisainen verkkojaksokello, taydella paineella (brief VERKKOKELLO)
# ============================================================================

VKELLO_REACH_MAX_MS = 40000  # nousun katto: tasanne tuli 19,2 s:ssa (vkello-20260923-a), 2x marginaali;
                             # PSTEP_REACH_MAX_MS 20000 katkaisi lahes (EXPRESSO-VERKKOKELLO-KORJAUS)
# Taukosarja (EXPRESSO-VERKKOKELLO-LAITETESTI2 23.9.2026, kayttaja: vetta kului liikaa, kaukalo ja
# sailio tyhjennettiin/taytettiin joka ajon valissa). Kolme erillista ajoa = kolme nousua (35 %
# pumppuajasta, ei ikkunoita) -> yksi ajo, sarja kolmesti. Paineportin kanssa lukko palaa
# (replay e/g/h) 0,5-2 s tauon jalkeen k6-13 (<= 2,1 s), 5 s tauon jalkeen k12-16 (<= 2,6 s):
# 3 s / 4 s kaynti jattaa lukittuja ikkunoita virheen havaitsemiseen. Pumppua ~54 s / ~110 g
# (ennen 3 ajoa x ~30 s / ~190 g).
VKELLO_SERIES = 3
VKELLO_PAUSES_MS = (500, 1000, 2000, 5000)
VKELLO_ON_MS = 3000
VKELLO_ON_LONG_MS = 4000     # kun tauko >= VKELLO_LONG_PAUSE_MS
VKELLO_LONG_PAUSE_MS = 5000

async def pressure_clock_run(brew_data, utime, asyncio, target):
    """Kello lukkiutuu I/Q-mittauksella taydella paineella, sitten taukosarja 0,5/1/2/5 s
    VKELLO_SERIES kertaa (VERKKOKELLO.brief.md, Do 3). Nousun ikkunat tulostetaan VKELLO_R-riveina
    paivittamatta kelloa (TILAUS-G-aineisto). Sama rakenne kuin pressure_gap_run."""
    import devsafe
    from verkkokello import Verkkokello
    RELAY_PUMP, RELAY_SOLENOID, RELAY_HEATER = brew_data.get_relays()
    sensor = brew_data.pressure_sensor.pressure_sensor
    gain, offset = brew_data.pressure_sensor.gain, brew_data.pressure_sensor.offset
    r = _sweep_break(brew_data, 'vkello_abort')
    if r: print('VKELLO_END T_us=0 hz=0.00 windows=0 reason=%s' % r); return
    tray_state, tray_reason = tray_guard_start(brew_data, utime)
    if tray_reason: print('VKELLO_END T_us=0 hz=0.00 windows=0 reason=%s' % tray_reason); return
    windows, reason, clock = 0, 'ok', None
    brew_data.set_mode('vkello')
    try:
        # TILAUS-H: paineinen jarjestelma puretaan kayttajan syklilla ennen mittausta.
        RELAY_PUMP.value(0)
        cycles, bar = await _mcal_vent(brew_data, utime, asyncio, sensor, gain, offset)
        print('VKELLO_VENT cycles=%d bar=%.2f' % (cycles, bar))
        if cycles >= MCAL_VENT_MAX_CYCLES: reason = 'vent_runaway'
        else: RELAY_SOLENOID.value(1); RELAY_PUMP.value(1)
        t0 = next_t = utime.ticks_us(); clock = Verkkokello(t0)
        # Nousu paattyy, kun paine lakkaa nousemasta (kayttaja 23.9.2026: paine on kuristimen
        # seuraus, ei asetettava taso — sama tasannesaanto kuin pcap_settle). target > 0 lopettaa
        # nousun myos saavutettuna; vkello:0 = pelkka tasanne.
        reached, j, rise_reason = False, 0, None
        p_filt = gain * (sensor.read_u16() * PCAP_RAW_A + PCAP_RAW_B) + offset
        alpha = (PCAP_RATE_US / 1000000.0) / PCAP_FILT_TAU
        plateau_j, plateau_bar = 0, p_filt
        clock.iq_start(t0); rise_w = 0
        while not reached and reason == 'ok':
            while utime.ticks_diff(next_t, utime.ticks_us()) > 0: pass
            now = utime.ticks_us()
            next_t = utime.ticks_add(next_t, PCAP_RATE_US)
            bar = gain * (sensor.read_u16() * PCAP_RAW_A + PCAP_RAW_B) + offset
            if bar > PCAP_OVER_BAR: reason = 'overpressure'; break
            p_filt += (bar - p_filt) * alpha
            clock.iq_add(now, bar)
            if clock.iq_ready(now):
                res = clock.iq_close(now, learn=False)
                clock.iq_start(now)
                if res is not None:
                    rise_w += 1
                    print('VKELLO_R w=%d t_ms=%d z_us=%.1f amp=%.3f p_bar=%.2f' % (
                        rise_w, utime.ticks_diff(now, t0) // 1000, res[0], res[1], res[2]))
            if (j & PSTEP_FEED_MASK) == 0:
                devsafe.feed(); r = _sweep_break(brew_data, 'vkello_abort') or tray_guard_poll(brew_data, utime, tray_state)
                if r: reason = r; break
                if utime.ticks_diff(utime.ticks_us(), t0) > PGAP_RUN_MAX_MS * 1000: reason = 'timeout'; break
            if p_filt < PCAP_PLATEAU_MIN_BAR:
                plateau_j, plateau_bar = j, p_filt   # tayttovaihe ei ole tasanne (pcap korjaus 4)
            if j >= PSTEP_MIN_MS:
                if target > 0 and p_filt >= target: rise_reason = 'target'
                elif j - plateau_j >= PCAP_PLATEAU_MS:
                    if p_filt - plateau_bar < PCAP_PLATEAU_BAR: rise_reason = 'plateau'
                    else: plateau_j, plateau_bar = j, p_filt
            if rise_reason is not None:
                reached = True
                print('VKELLO_RISE bar=%.2f reach_ms=%d reason=%s' % (p_filt, j, rise_reason))
            elif j >= VKELLO_REACH_MAX_MS: reason = 'noreach'; break
            j += 1
        schedule = [(None, 4000)] + [(p, VKELLO_ON_LONG_MS if p >= VKELLO_LONG_PAUSE_MS else VKELLO_ON_MS)
                                     for _ in range(VKELLO_SERIES) for p in VKELLO_PAUSES_MS]
        for pause_ms, on_ms in schedule:
            if reason != 'ok': break
            if pause_ms is not None:
                RELAY_PUMP.value(0)  # tauolla pois; solenoidia ei avata (avattu jo ajon alussa)
                p0, j3 = utime.ticks_us(), 0
                while utime.ticks_diff(utime.ticks_us(), p0) < pause_ms * 1000:
                    if (j3 & PSTEP_FEED_MASK) == 0:
                        devsafe.feed(); r = _sweep_break(brew_data, 'vkello_abort') or tray_guard_poll(brew_data, utime, tray_state)
                        if r: reason = r; break
                        if utime.ticks_diff(utime.ticks_us(), t0) > PGAP_RUN_MAX_MS * 1000: reason = 'timeout'; break
                    j3 += 1
                if reason != 'ok': break
                RELAY_PUMP.value(1)
            on0 = next_t = utime.ticks_us()
            clock.iq_start(on0); first_z, j2 = None, 0
            while utime.ticks_diff(utime.ticks_us(), on0) < on_ms * 1000:
                while utime.ticks_diff(next_t, utime.ticks_us()) > 0: pass
                now = utime.ticks_us()
                next_t = utime.ticks_add(next_t, PCAP_RATE_US)
                bar = gain * (sensor.read_u16() * PCAP_RAW_A + PCAP_RAW_B) + offset
                if bar > PCAP_OVER_BAR: reason = 'overpressure'; break
                if (j2 & PSTEP_FEED_MASK) == 0:
                    devsafe.feed(); r = _sweep_break(brew_data, 'vkello_abort') or tray_guard_poll(brew_data, utime, tray_state)
                    if r: reason = r; break
                    if utime.ticks_diff(now, t0) > PGAP_RUN_MAX_MS * 1000: reason = 'timeout'; break
                clock.iq_add(now, bar)
                if clock.iq_ready(now):
                    traja0 = clock.traja
                    res = clock.iq_close(now)
                    clock.iq_start(now)
                    if res is not None:
                        z, amp, p_bar, g = res; windows += 1
                        if first_z is None: first_z = z
                        print('VKELLO w=%d t_ms=%d z_us=%.1f T_us=%.3f d=%.5f sd_us=%.1f amp=%.3f lock=%d p_bar=%.2f gate=%d' % (
                            windows, utime.ticks_diff(now, t0) // 1000, z, clock.T, clock.d,
                            clock.sd_us(now), amp, 1 if clock.locked(now) else 0, p_bar, g))
                        if clock.traja > traja0: print('VKELLO_TRAJA')
                j2 += 1
            if reason != 'ok': break
            if pause_ms is not None:
                print('VKELLO_RESTART pause_ms=%d z1_us=%.1f' % (pause_ms, first_z if first_z is not None else 0.0))
    except Exception:
        reason = 'error'
    finally:
        RELAY_PUMP.value(0); RELAY_SOLENOID.value(0)
        brew_data.set_mode('IDLE'); brew_data.vkello_abort = False
    tray_reason = await tray_guard_recheck(brew_data, utime, asyncio, tray_state)
    if tray_reason and reason == 'ok': reason = tray_reason
    t_us = clock.T if clock is not None else 0.0
    hz = (1000000.0 / t_us) if t_us else 0.0
    gated, pgated, rebased = (clock.gated, clock.pgated, clock.rebased) if clock is not None else (0, 0, 0)
    print('VKELLO_END T_us=%.3f hz=%.4f windows=%d gated=%d pgated=%d rebased=%d reason=%s' % (
        t_us, hz, windows, gated, pgated, rebased, reason))


# ============================================================================
# VAIHEPYYHKAISY (vsweep:<reps>) — TILAUS-K/L askel 1 (kayttaja 24.9.2026)
# ============================================================================
# Kysymys: missa kohdassa verkkojaksoa (verkkokellon reunasta) 10 ms tauko poistaa pumpun iskun ja
# kuinka jyrkka raja on. Pumppu iskee vain toisella puolijaksolla (TILAUS-L: "10ms ... vaikuttaa
# 20ms ajan"), joten alle jakson tauon vaikutus riippuu vaiheesta: plen 20.9.2026 antoi alle 20 ms
# tauoille ~puolet 20 ms:n kuopasta, mutta ilman kelloa vaihe jai selvittamatta. Jyrkka raja =
# taukokohdistus on vaihemittaus (TILAUS-K vaiheet 2 ja 4); samalla SSR-tyyppi ja puolijaksot.
#
# Mittari ei ole kuopan syvyys: 1b-sarjassa (pgap q1-q4) se mittasi painetrendia (r 0,85
# kulmakertoimen kanssa). Tassa keskipaine 100 ms (5 jaksoa, vareily kumoutuu) ennen taukoa ja
# 30-130 / 130-230 ms sen alusta (pohja 64-68 ms, plen), ja trendi saadaan tyhjista vertailuista
# (ehto SHAM, ei taukoa). Ehdot kierretaan (STRIDE), joten ajautuma jakautuu tasan.
# Kello pysyy synkronissa: jokaisen tauon valissa yksi puhdas I/Q-ikkuna, joka paivittaa kellon
# (VKELLO-rivit samassa muodossa kuin vkello, jotta vkello_analyysi voi rekonstruoida kayran).

VSWEEP_GAP_US = 10000        # TILAUS-L: pienin tauko
VSWEEP_FULL_US = 20000       # positiivinen vertailu: koko jakso poistaa aina yhden iskun
VSWEEP_STEP_US = 1000        # kohdan askel kellon reunasta
VSWEEP_N_OFF = 20            # kohdat 0..19 ms
VSWEEP_SHAM = VSWEEP_N_OFF   # ehto 20: ei taukoa (trendin vertailu)
VSWEEP_FULL = VSWEEP_N_OFF + 1   # ehto 21: 20 ms tauko kohdassa 0
VSWEEP_N_COND = VSWEEP_N_OFF + 2
VSWEEP_STRIDES = (7, 5, 9, 3, 13)   # toisto r: ehto = i*STRIDES[r] mod 22 (syt 1). Kiintea askel antoi
                             # jokaiselle ehdolle aina saman edeltajan, ja edellisen kuopan palautuminen
                             # (tau ~0,8 s, tauot 0,4 s valein) naytti jarjestelmallisena (vsweep_smoke:
                             # tyhja vertailu +0,045 bar)
VSWEEP_PRE_N = 200           # 2 x 100 naytetta = 2 x 5 jaksoa ennen taukoa: taso ja trendi
VSWEEP_POST1 = (30, 130)     # ms tauon alusta
VSWEEP_POST2 = (130, 230)
VSWEEP_DMIN = (20, 150)      # 5 naytteen keskiarvon minimi tassa valissa (vertailuksi)
VSWEEP_LEAD_US = 2000        # tauon aloitus vahintaan nain pitkalla edelle (tuoreesta ajasta)
VSWEEP_LATE_MAX_US = 300     # myohassa enemman -> taukoa ei tehda, vaan se siirtyy seuraavaan jaksoon.
                             # vsweep-20260924-a: sarjatulostus ja 200 naytteen summat ennen ajoitusta
                             # myohastyttivat taukoa 1,4-18,6 ms kaskysta (tulos pelastui act_us:lla)
VSWEEP_LOCK_MIN_W = 25       # tasanteella nain monta paivittavaa ikkunaa ennen ensimmaista taukoa: 12:lla
                             # sd ~395 us eli juuri LOCK_US-rajalla (2,5 sd), ja taukojen vasteajat kasvattavat
                             # sen yli (vsweep_smoke: 29/44 taukoa lukitsematta)
VSWEEP_LOCK_MAX_MS = 10000   # lukko tasanteelta nain ajassa, muuten nolock
VSWEEP_REPS_MAX = 5


async def pressure_phase_sweep_run(brew_data, utime, asyncio, reps):
    import devsafe
    from verkkokello import Verkkokello
    RELAY_PUMP, RELAY_SOLENOID, RELAY_HEATER = brew_data.get_relays()
    sensor = brew_data.pressure_sensor.pressure_sensor
    gain, offset = brew_data.pressure_sensor.gain, brew_data.pressure_sensor.offset
    reps = max(1, min(VSWEEP_REPS_MAX, int(reps)))
    n_trials = reps * VSWEEP_N_COND
    r = _sweep_break(brew_data, 'vsweep_abort')
    if r: print('VSWEEP_END trials=0 windows=0 reason=%s' % r); return
    tray_state, tray_reason = tray_guard_start(brew_data, utime)
    if tray_reason: print('VSWEEP_END trials=0 windows=0 reason=%s' % tray_reason); return
    trials, windows, reason, clock, late = 0, 0, 'ok', None, 0
    brew_data.set_mode('vsweep')
    try:
        # TILAUS-H: purku ennen pumppua, sitten nousu tasanteeseen (sama saanto kuin vkello)
        RELAY_PUMP.value(0)
        cycles, bar = await _mcal_vent(brew_data, utime, asyncio, sensor, gain, offset)
        print('VSWEEP_VENT cycles=%d bar=%.2f' % (cycles, bar))
        if cycles >= MCAL_VENT_MAX_CYCLES: reason = 'vent_runaway'
        else: RELAY_SOLENOID.value(1); RELAY_PUMP.value(1)
        t0 = next_t = utime.ticks_us(); clock = Verkkokello(t0)
        p_filt = gain * (sensor.read_u16() * PCAP_RAW_A + PCAP_RAW_B) + offset
        alpha = (PCAP_RATE_US / 1000000.0) / PCAP_FILT_TAU
        plateau_j, plateau_bar, j, rise_done = 0, p_filt, 0, False
        ring = [0.0] * VSWEEP_PRE_N
        half_n = VSWEEP_PRE_N // 2
        sm = [0.0] * PGAP_SMOOTH_N
        state, lock_w, lock_t = 'iq', 0, None
        cond = gap_len = off_us = 0
        target = t_off = t_on = 0
        pre = pre0 = act = 0.0
        s1 = s2 = 0.0; n1 = n2 = 0; dmin = 99.0
        while reason == 'ok':
            while utime.ticks_diff(next_t, utime.ticks_us()) > 0: pass
            now = utime.ticks_us()
            next_t = utime.ticks_add(next_t, PCAP_RATE_US)
            bar = gain * (sensor.read_u16() * PCAP_RAW_A + PCAP_RAW_B) + offset
            if bar > PCAP_OVER_BAR: reason = 'overpressure'; break
            if (j & PSTEP_FEED_MASK) == 0:
                devsafe.feed(); r = _sweep_break(brew_data, 'vsweep_abort') or tray_guard_poll(brew_data, utime, tray_state)
                if r: reason = r; break
                if utime.ticks_diff(now, t0) > PGAP_RUN_MAX_MS * 1000: reason = 'timeout'; break
            ring[j % VSWEEP_PRE_N] = bar
            sm[j % PGAP_SMOOTH_N] = bar
            j += 1
            if not rise_done:
                p_filt += (bar - p_filt) * alpha
                if p_filt < PCAP_PLATEAU_MIN_BAR:
                    plateau_j, plateau_bar = j, p_filt   # tayttovaihe ei ole tasanne
                if j >= PSTEP_MIN_MS and j - plateau_j >= PCAP_PLATEAU_MS:
                    if p_filt - plateau_bar < PCAP_PLATEAU_BAR:
                        rise_done, lock_t = True, now
                        print('VSWEEP_RISE bar=%.2f reach_ms=%d reason=plateau' % (p_filt, j))
                        clock.iq_start(now)
                    else:
                        plateau_j, plateau_bar = j, p_filt
                if not rise_done and j >= VKELLO_REACH_MAX_MS: reason = 'noreach'
                continue
            if state == 'iq':
                clock.iq_add(now, bar)
                if clock.iq_ready(now):
                    res = clock.iq_close(now)
                    if res is not None:
                        z, amp, p_bar, g = res; windows += 1
                        print('VKELLO w=%d t_ms=%d z_us=%.1f T_us=%.3f d=%.5f sd_us=%.1f amp=%.3f lock=%d p_bar=%.2f gate=%d' % (
                            windows, utime.ticks_diff(now, t0) // 1000, z, clock.T, clock.d,
                            clock.sd_us(now), amp, 1 if clock.locked(now) else 0, p_bar, g))
                        if g == 0: lock_w += 1
                    if lock_t is not None:
                        if lock_w >= VSWEEP_LOCK_MIN_W and clock.locked(now):
                            print('VSWEEP_LOCK windows=%d sd_us=%.1f T_us=%.3f ms=%d' % (
                                lock_w, clock.sd_us(now), clock.T, utime.ticks_diff(now, lock_t) // 1000))
                            lock_t = None
                        elif utime.ticks_diff(now, lock_t) > VSWEEP_LOCK_MAX_MS * 1000:
                            reason = 'nolock'; break
                    if lock_t is None:
                        # Seuraava tauko: kohta kellon reunasta, vahintaan LEAD_US edella
                        rep, i = divmod(trials, VSWEEP_N_COND)
                        cond = (i * VSWEEP_STRIDES[rep % len(VSWEEP_STRIDES)]) % VSWEEP_N_COND
                        if cond == VSWEEP_SHAM: off_us, gap_len = 0, 0
                        elif cond == VSWEEP_FULL: off_us, gap_len = 0, VSWEEP_FULL_US
                        else: off_us, gap_len = cond * VSWEEP_STEP_US, VSWEEP_GAP_US
                        # Tuore aika: VKELLO-rivin tulostus on jo voinut vieda millisekunteja
                        t_now = utime.ticks_us()
                        target = utime.ticks_add(clock.edge(t_now), off_us)
                        while utime.ticks_diff(target, t_now) < VSWEEP_LEAD_US:
                            target = utime.ticks_add(target, round(clock.T))
                        state = 'wait'
                    else:
                        clock.iq_start(now)
                continue
            if state == 'wait':
                if utime.ticks_diff(target, now) < PCAP_RATE_US:
                    while utime.ticks_diff(target, utime.ticks_us()) > 0: pass
                    t_off = utime.ticks_us()
                    if utime.ticks_diff(t_off, target) > VSWEEP_LATE_MAX_US:
                        # Myohassa: ei taukoa vaaraan kohtaan, vaan sama kohta seuraavassa jaksossa
                        late += 1
                        while utime.ticks_diff(target, t_off) < VSWEEP_LEAD_US:
                            target = utime.ticks_add(target, round(clock.T))
                        continue
                    if gap_len > 0: RELAY_PUMP.value(0)
                    # Perustaso vasta kaynnistyksen jalkeen, jottei summa viivasta ajoitusta; tauon
                    # loppu tarkistetaan seuraavalla naytteella. ring[(j - 1) % N] on viimeinen
                    # nayte ennen taukoa (seuraava nayte kirjoittaa vanhimman yli).
                    pre0 = sum(ring[(j - VSWEEP_PRE_N + q) % VSWEEP_PRE_N] for q in range(half_n)) / half_n
                    pre = sum(ring[(j - half_n + q) % VSWEEP_PRE_N] for q in range(half_n)) / half_n
                    t_on = utime.ticks_add(t_off, gap_len)
                    act = utime.ticks_diff(t_off, clock.edge(t_off)) % clock.T
                    s1 = s2 = 0.0; n1 = n2 = 0; dmin = 99.0
                    state = 'gap' if gap_len > 0 else 'resp'
                continue
            if state == 'gap' and utime.ticks_diff(t_on, now) < PCAP_RATE_US:
                while utime.ticks_diff(t_on, utime.ticks_us()) > 0: pass
                RELAY_PUMP.value(1)
                state = 'resp'
            el = utime.ticks_diff(now, t_off) // 1000
            if VSWEEP_POST1[0] <= el < VSWEEP_POST1[1]: s1 += bar; n1 += 1
            elif VSWEEP_POST2[0] <= el < VSWEEP_POST2[1]: s2 += bar; n2 += 1
            if VSWEEP_DMIN[0] <= el < VSWEEP_DMIN[1]:
                v = sum(sm) / PGAP_SMOOTH_N
                if v < dmin: dmin = v
            if state == 'resp' and el >= VSWEEP_POST2[1]:
                print('VSWEEP k=%d cond=%d off_us=%d len_us=%d act_us=%.0f pre0=%.3f pre=%.3f post1=%.3f post2=%.3f dmin=%.3f sd_us=%.0f lock=%d T_us=%.3f' % (
                    trials, cond, off_us, gap_len, act, pre0, pre, s1 / max(1, n1), s2 / max(1, n2),
                    dmin, clock.sd_us(now), 1 if clock.locked(now) else 0, clock.T))
                trials += 1
                if trials >= n_trials: break
                state = 'iq'
                clock.iq_start(now)
    except Exception as e:
        reason = 'error'
        print('VSWEEP_ERR %r' % (e,))
    finally:
        RELAY_PUMP.value(0); RELAY_SOLENOID.value(0)
        brew_data.set_mode('IDLE'); brew_data.vsweep_abort = False
    tray_reason = await tray_guard_recheck(brew_data, utime, asyncio, tray_state)
    if tray_reason and reason == 'ok': reason = tray_reason
    print('VSWEEP_END trials=%d windows=%d late=%d T_us=%.3f hz=%.4f reason=%s' % (
        trials, windows, late, clock.T if clock else 0.0, (1e6 / clock.T) if clock else 0.0, reason))


# ============================================================================
# PRESSURE GAP LENGTH — kvantisoituuko tauko puolijaksoihin? (tilaus 20.9.2026)
# ============================================================================
# Kysymys ei ole hydraulinen vaan sahkoinen: "kohdistuksen tarkoitus ei ole vaikuttaa paineeseen
# vaan saada jakso hallintaan etta sita voidaan muokata oikeasta kohtaa ettei se riko pumppua".
# Pumppu on pelkka GPIO (GP11) eika koodissa ole nollaylityksen tunnistusta; ajuri on SSR-40DA,
# jonka tyyppi on kirjattu tarkistamattomaksi (KAYTTAJAN-TIEDOT.md:186).
#
# Nollaylitys-SSR napsauttaa kytkennat verkon nollakohtiin, jolloin tauon TODELLINEN pituus
# kvantisoituu puolijaksoihin (9,98 ms) riippumatta kasketysta pituudesta, ja poistettujen iskujen
# maara — siis pudotuksen syvyys — nousee portaittain. Vapaavaiheinen ajuri antaisi tasaisen
# ramppin. Tama ajo erottaa ne toisistaan avaamatta konetta.
#
# Aaltomuotoa ei tallenneta: syvyys lasketaan laitteella, joten muistia ei kulu ja taukoja mahtuu
# kymmenia samaan ajoon.
PLEN_MIN_MS = 6
PLEN_MAX_MS = 36
PLEN_STEP_MS = 2
PLEN_REPS = 2
PLEN_SPACING_MS = 400
PLEN_RESP_MS = 200           # vasteikkuna tauon alusta
PLEN_BASE_N = 20             # perustaso: yksi verkkojakso ennen taukoa
PLEN_SMOOTH_N = 5            # lyhyt keskiarvo pohjan etsintaan


async def pressure_len_run(brew_data, utime, asyncio, target):
    """Tauon pituuden pyyhkaisy: kvantisoituuko katkaisu puolijaksoihin (tilaus 20.9.2026)."""
    import devsafe
    RELAY_PUMP, RELAY_SOLENOID, RELAY_HEATER = brew_data.get_relays()
    sensor = brew_data.pressure_sensor.pressure_sensor
    gain = brew_data.pressure_sensor.gain
    offset = brew_data.pressure_sensor.offset
    reps = getattr(brew_data, 'plen_reps', None) or PLEN_REPS
    lengths = list(range(PLEN_MIN_MS, PLEN_MAX_MS + 1, PLEN_STEP_MS))
    plan = []
    for _ in range(reps):       # kierratetty: ajautuma jakautuu tasan kaikille pituuksille
        plan.extend(lengths)
    print('PLEN_START rate=%d target=%.2f lengths=%d reps=%d spacing_ms=%d half_cycle_us=%d gain=%.4f offset=%.3f' % (
        1000000 // PCAP_RATE_US, target, len(lengths), reps, PLEN_SPACING_MS,
        PCAP_MAINS_US // 2, gain, offset))
    r = _sweep_break(brew_data, 'plen_abort')
    if r:
        print('PLEN_END gaps=0 pmax=0.00 reason=%s' % r); return
    tray_state, tray_reason = tray_guard_start(brew_data, utime)
    if tray_reason:
        print('PLEN_END gaps=0 pmax=0.00 reason=%s' % tray_reason); return

    base_ring = [0.0] * PLEN_BASE_N
    sm = [0.0] * PLEN_SMOOTH_N
    pmax_bar = -99.0
    gaps_done = 0
    reason = 'ok'
    reached = False
    brew_data.set_mode('pressure gap length')
    try:
        RELAY_SOLENOID.value(1)
        RELAY_PUMP.value(1)
        next_t = utime.ticks_us()
        p_filt = gain * (sensor.read_u16() * PCAP_RAW_A + PCAP_RAW_B) + offset
        alpha = (PCAP_RATE_US / 1000000.0) / PCAP_FILT_TAU
        gap_off_t = 0
        gap_pending = False
        gap_at = -1
        cur_len_ms = plan[0]
        base_bar = 0.0
        trough_v = 99.0
        trough_at = 0
        next_gap_j = 0
        venting = False
        vents = 0
        j = 0
        while True:
            while utime.ticks_diff(next_t, utime.ticks_us()) > 0: pass
            now = utime.ticks_us()
            v = sensor.read_u16()
            next_t = utime.ticks_add(next_t, PCAP_RATE_US)
            bar = gain * (v * PCAP_RAW_A + PCAP_RAW_B) + offset
            if bar > pmax_bar: pmax_bar = bar
            if bar > PCAP_OVER_BAR: reason = 'overpressure'; break
            p_filt += (bar - p_filt) * alpha
            if (j & PSTEP_FEED_MASK) == 0:
                devsafe.feed()
                r = _sweep_break(brew_data, 'plen_abort') or tray_guard_poll(brew_data, utime, tray_state)
                if r: reason = r; break
            if not reached:
                if j >= PSTEP_MIN_MS and p_filt >= target:
                    reached = True; j = 0; next_gap_j = PLEN_BASE_N + 30
                elif j >= PSTEP_REACH_MAX_MS:
                    reason = 'noreach'; break
                j += 1
                continue
            base_ring[j % PLEN_BASE_N] = bar
            sm[j % PLEN_SMOOTH_N] = bar
            if gap_pending and utime.ticks_diff(now, gap_off_t) >= cur_len_ms * 1000:
                RELAY_PUMP.value(1); gap_pending = False
            if gap_at >= 0:
                if j - gap_at >= PLEN_SMOOTH_N:
                    s = sum(sm) / PLEN_SMOOTH_N
                    if s < trough_v: trough_v, trough_at = s, j
                if j - gap_at >= PLEN_RESP_MS:
                    print('PLEN k=%d len_ms=%d base_bar=%.3f depth_bar=%.3f trough_ms=%d' % (
                        gaps_done, cur_len_ms, base_bar, base_bar - trough_v, trough_at - gap_at))
                    gaps_done += 1
                    gap_at = -1
                    if gaps_done >= len(plan): break
                    cur_len_ms = plan[gaps_done]
            elif j >= next_gap_j:
                base_bar = sum(base_ring) / PLEN_BASE_N
                trough_v = 99.0
                gap_at = j
                RELAY_PUMP.value(0)
                gap_off_t = now
                gap_pending = True
                next_gap_j = j + PLEN_SPACING_MS
            j += 1
    except Exception:
        reason = 'error'
    finally:
        RELAY_PUMP.value(0)
        RELAY_SOLENOID.value(0)
        brew_data.set_mode('IDLE')
        brew_data.plen_abort = False
    tray_reason = await tray_guard_recheck(brew_data, utime, asyncio, tray_state)
    if tray_reason and reason == 'ok': reason = tray_reason
    print('PLEN_END gaps=%d pmax=%.2f reason=%s' % (gaps_done, pmax_bar, reason))


async def _mcal_vent(brew_data, utime, asyncio, sensor, gain, offset):
    """Purkusykli (TILAUS-H, spec 2): palauttaa (cycles, bar); cycles==MCAL_VENT_MAX_CYCLES on vika."""
    RELAY_PUMP, RELAY_SOLENOID, RELAY_HEATER = brew_data.get_relays()
    bar = prev_end = gain * (sensor.read_u16() * PCAP_RAW_A + PCAP_RAW_B) + offset
    cycles = 0
    while True:
        cycles += 1
        RELAY_SOLENOID.value(1); await asyncio.sleep_ms(MCAL_VENT_ON_MS)
        RELAY_SOLENOID.value(0); await asyncio.sleep_ms(MCAL_VENT_OFF_MS)
        bar = gain * (sensor.read_u16() * PCAP_RAW_A + PCAP_RAW_B) + offset
        if prev_end - bar < PCAP_PLATEAU_BAR or cycles >= MCAL_VENT_MAX_CYCLES: break
        prev_end = bar
    print('MAINSCAL_VENT cycles=%d bar=%.2f' % (cycles, bar))
    return cycles, bar

async def pressure_vent_run(brew_data, utime, asyncio):
    """Pelkka purkusykli, oma komentonsa (TILAUS-H kohta 3, tekematta 19.9.2026 asti).

    `mcal` purkaa paineen mutta kaynnistaa heti sen jalkeen pumpun, koska se mittaa taajuuden
    paineen noususta. Purkukomentona se siis kumoaa itsensa — kayttajan havainto 20.9.2026, ja
    se toistui kolmesti taman istunnon aikana. Tama komento purkaa eika pumppaa."""
    RELAY_PUMP, RELAY_SOLENOID, RELAY_HEATER = brew_data.get_relays()
    sensor = brew_data.pressure_sensor.pressure_sensor
    gain = brew_data.pressure_sensor.gain
    offset = brew_data.pressure_sensor.offset
    r = _sweep_break(brew_data, 'pvent_abort')
    if r:
        print('PVENT_END cycles=0 bar=0.00 reason=%s' % r); return
    brew_data.set_mode('pressure vent')
    reason = 'ok'
    cycles, bar = 0, 0.0
    try:
        RELAY_PUMP.value(0)          # pumppu pois ENNEN purkua ja se jaa pois
        cycles, bar = await _mcal_vent(brew_data, utime, asyncio, sensor, gain, offset)
        if cycles >= MCAL_VENT_MAX_CYCLES: reason = 'vent_runaway'
    except Exception:
        reason = 'error'
    finally:
        RELAY_PUMP.value(0)
        RELAY_SOLENOID.value(0)
        brew_data.set_mode('IDLE')
        brew_data.pvent_abort = False
    print('PVENT_END cycles=%d bar=%.2f reason=%s' % (cycles, bar, reason))


async def mains_calibrate(brew_data, utime, asyncio, ms=2000):
    """Ajonaikainen verkkotaajuuden ja vaiheen mittaus paineväreilystä (TILAUS-F/G/H, spec 3)."""
    from math import cos, sin, atan2, pi
    RELAY_PUMP, RELAY_SOLENOID, RELAY_HEATER = brew_data.get_relays()
    SWITCH_BREW, SWITCH_WATER, SWITCH_STEAM = brew_data.get_switches()

    def mcal_break():
        if SWITCH_BREW.value() or SWITCH_WATER.value() or SWITCH_STEAM.value(): return 'switch'
        if brew_data.dev_safe: return 'devsafe'
        if getattr(brew_data, 'mcal_abort', False): return 'stop'
        return None

    reason = mcal_break()
    if reason: print('MAINSCAL_END reason=%s' % reason); return
    # Kaukalovahti (EXPRESSO-KAUKALOVAHTI-KOKONAISPAINO): mcal pumppaa, joten se on testikomento
    # siinä missä pcap. Spec PWM-1G jätti vahdin pois (paketit/TURVAKATO.md kohta 3).
    tray_state, reason = tray_guard_start(brew_data, utime)
    if reason: print('MAINSCAL_END reason=%s' % reason); return
    sensor, gain, offset = brew_data.pressure_sensor.pressure_sensor, brew_data.pressure_sensor.gain, brew_data.pressure_sensor.offset
    n = int(ms)
    brew_data.set_mode('mains calibration')
    try:
        cycles, _ = await _mcal_vent(brew_data, utime, asyncio, sensor, gain, offset)
        if cycles >= MCAL_VENT_MAX_CYCLES:
            print('MAINSCAL_END reason=vent_runaway'); return
        RELAY_SOLENOID.value(1); RELAY_PUMP.value(1)
        fs_nom = 1e6 / PCAP_RATE_US
        ws = [2 * pi * f / fs_nom for f in MCAL_GRID]
        coeffs = [2 * cos(w) for w in ws]
        s1, s2 = [0.0] * len(MCAL_GRID), [0.0] * len(MCAL_GRID)
        count, elapsed = 0, 0
        t0 = next_t = utime.ticks_us()
        for i in range(n):
            reason = mcal_break()
            if reason: break
            while utime.ticks_diff(next_t, utime.ticks_us()) > 0: pass
            x = float(sensor.read_u16())
            # Ylipaineraja, jota mcal:ssa ei ollut (EXPRESSO-TURVA-PIKAKORJAUKSET 21.9.2026):
            # sama raja ja sama raakanaytteen tarkistus kuin pcap:ssa.
            if gain * (x * PCAP_RAW_A + PCAP_RAW_B) + offset > PCAP_OVER_BAR:
                reason = 'overpressure'; break
            elapsed = utime.ticks_diff(utime.ticks_us(), t0); count += 1
            for k in range(len(MCAL_GRID)):
                s0 = x + coeffs[k] * s1[k] - s2[k]
                s2[k], s1[k] = s1[k], s0
            next_t = utime.ticks_add(next_t, PCAP_RATE_US)
        if not reason:
            # Kaappaussilmukka ei anna vuoroa, joten vaaka tarkistetaan heti sen jälkeen (kuten pcap).
            RELAY_PUMP.value(0)
            reason = await tray_guard_recheck(brew_data, utime, asyncio, tray_state)
        reason = reason or 'ok'
        if reason != 'ok' or count == 0:
            print('MAINSCAL_END reason=%s' % reason); return
        amps, bins = [], []
        for k in range(len(MCAL_GRID)):
            re, im = s1[k] - s2[k] * cos(ws[k]), s2[k] * sin(ws[k])
            amps.append((re * re + im * im) ** 0.5); bins.append((re, im))
        peak = amps.index(max(amps))
        delta = 0.0
        if 0 < peak < len(MCAL_GRID) - 1:
            a0, a1, a2 = amps[peak - 1], amps[peak], amps[peak + 1]
            denom = a0 - 2 * a1 + a2
            if denom: delta = 0.5 * (a0 - a2) / denom
        fs_meas = count / (elapsed / 1e6)
        f = (MCAL_GRID[peak] + delta * (MCAL_GRID[1] - MCAL_GRID[0])) * (fs_meas / fs_nom)
        re, im = bins[peak]
        period_us = 1e6 / f
        phase_us = (atan2(-im, re) / (2 * pi) * period_us) % period_us
        amp = amps[peak]
        ranked = sorted(amps, reverse=True)
        conf = ranked[0] / ranked[1] if ranked[1] else 0.0
        brew_data.mains_hz, brew_data.mains_period_us, brew_data.mains_phase_us = f, period_us, phase_us
        print('MAINSCAL f=%.3f phase_us=%.0f amp=%.3f conf=%.2f n=%d ms=%d' % (
            f, phase_us, amp, conf, count, elapsed // 1000))
    finally:
        RELAY_PUMP.value(0); RELAY_SOLENOID.value(0)
        brew_data.set_mode('IDLE')
        brew_data.mcal_abort = False

PHOLD_PRINT_MS = 500        # PHOLD-rivin tulostusväli, ms (spec 1)
PHOLD_MAX_S = 120           # ajon enimmäispituus, s (spec 2.6) — pyyntö rajataan jo classes.py:ssä


async def pressure_hold_run(brew_data, utime, asyncio, seconds):
    RELAY_PUMP, RELAY_SOLENOID, RELAY_HEATER = brew_data.get_relays()
    SWITCH_BREW, SWITCH_WATER, SWITCH_STEAM = brew_data.get_switches()

    sensor = brew_data.pressure_sensor.pressure_sensor
    gain = brew_data.pressure_sensor.gain
    offset = brew_data.pressure_sensor.offset
    reason = 'ok'
    p_filt = None
    prev_filt = None
    last_print = None
    first_print = True
    tray_state, tray_reason = tray_guard_start(brew_data, utime)
    if tray_reason:
        print('PHOLD_END reason=%s bar=0.00' % tray_reason); return
    brew_data.set_mode('pressure hold')
    print('PHOLD_START s=%d' % seconds)
    try:
        # Solenoid open before the pump (spec 2.1), same order as pressure_capture_run
        # (functions.py:583-584): a closed circuit cannot be held at any bar by the restrictor.
        RELAY_SOLENOID.value(1)
        RELAY_PUMP.value(1)

        start_t = utime.ticks_ms()
        last_t = start_t
        first_bar = gain * (sensor.read_u16() * PCAP_RAW_A + PCAP_RAW_B) + offset
        p_filt = first_bar
        prev_filt = first_bar
        last_print = start_t

        while True:
            if SWITCH_BREW.value() or SWITCH_WATER.value() or SWITCH_STEAM.value():
                reason = 'switch'
                break
            if brew_data.dev_safe:
                reason = 'devsafe'
                break
            if brew_data.phold_abort:
                reason = 'stop'
                break
            tray_reason = tray_guard_check(brew_data, utime, tray_state)
            if tray_reason:
                reason = tray_reason
                break
            bar = gain * (sensor.read_u16() * PCAP_RAW_A + PCAP_RAW_B) + offset
            # Overpressure stays on the raw sample (spec 2.5, same rule as pcap): a safety limit
            # must react immediately, not with the filter's lag.
            if bar > PCAP_OVER_BAR:
                reason = 'overpressure'
                break
            now = utime.ticks_ms()
            dt = utime.ticks_diff(now, last_t) / 1000.0
            last_t = now
            p_filt += (bar - p_filt) * min(1.0, dt / PCAP_FILT_TAU)

            elapsed_ms = utime.ticks_diff(now, start_t)
            if elapsed_ms >= seconds * 1000:
                reason = 'ok'
                break

            print_dt = utime.ticks_diff(now, last_print)
            if print_dt >= PHOLD_PRINT_MS:
                if first_print:
                    slope = 0.00
                    first_print = False
                else:
                    slope = (p_filt - prev_filt) / (print_dt / 1000.0) if print_dt > 0 else 0.00
                print('PHOLD t=%d bar=%.2f filt=%.2f slope=%.2f' % (elapsed_ms, bar, p_filt, slope))
                prev_filt = p_filt
                last_print = now

            # Non-blocking yield (spec 2.4): 120 s must not starve BLE nor the watchdog task,
            # and 5 ms is still 60x oversampling for the 0.3 s filter.
            await asyncio.sleep_ms(5)
    except Exception:
        # One development command must not crash main.py's loop (korjaus 1B). PHOLD_END below is
        # the host's only signal of what happened, since pico_dev.py phold waits on that marker.
        reason = 'error'
    finally:
        RELAY_PUMP.value(0)
        RELAY_SOLENOID.value(0)
        brew_data.set_mode('IDLE')
        brew_data.phold_abort = False
        print('PHOLD_END reason=%s bar=%.2f' % (reason, p_filt if p_filt is not None else 0.00))


# ============================================================================
# KURISTIMEN LAMMITYS (klamp:<s>) — kayttaja 24.9.2026, KAYTTAJAN-TIEDOT "Kuristin lammitetaan"
# ============================================================================
# Kylma kuristin nosti paineen yli PCAP_OVER_BAR:n (vkello-20260924-a). Kayttajan menetelma:
# pumppu kay jatkuvasti, kunnes keskipaineen merkittava kasvu pysahtyy; sen hetken paine on
# tavoite (ei vakio), ja sita pidetaan rajoittamalla pumppua, kunnes rajoitusta ei enaa tarvita.

KLAMP_MIN_S = 10             # pyynnon alaraja: nousu + tasanne + DONE_MS mahtuu
KLAMP_MAX_S = 120            # ajon katto, sama kuin PHOLD_MAX_S
KLAMP_RISE_MAX_MS = 40000    # nousun katto, sama kuin VKELLO_REACH_MAX_MS
KLAMP_DONE_DUTY = 0.95       # "pumppua ei tarvitse rajoittaa": dutyn keskiarvo vahintaan tama...
KLAMP_DONE_MS = 3000         # ...yhtajaksoisesti nain kauan
KLAMP_DUTY_TAU = 1.0         # dutyn keskiarvon aikavakio, s: 100 ms ikkunan on/off-kvantisointi pois
KLAMP_PRINT_MS = 500


async def throttle_warmup_run(brew_data, utime, asyncio, pump_ratio_calculator, seconds):
    from classes import PumpPressureController
    RELAY_PUMP, RELAY_SOLENOID, RELAY_HEATER = brew_data.get_relays()
    sensor = brew_data.pressure_sensor.pressure_sensor
    gain = brew_data.pressure_sensor.gain
    offset = brew_data.pressure_sensor.offset
    reason = 'ok'
    target = None
    duty_avg = 0.0
    p_filt = 0.0
    r = _sweep_break(brew_data, 'klamp_abort')
    if r:
        print('KLAMP_END reason=%s target=0.00 duty_avg=0.00 ms=0' % r); return
    tray_state, tray_reason = tray_guard_start(brew_data, utime)
    if tray_reason:
        print('KLAMP_END reason=%s target=0.00 duty_avg=0.00 ms=0' % tray_reason); return
    brew_data.set_mode('throttle warmup')
    print('KLAMP_START s=%d' % seconds)
    start = utime.ticks_ms()
    try:
        # Venttiili ennen pumppua (sama jarjestys kuin phold): suljettua piiria ei voi lammittaa.
        RELAY_SOLENOID.value(1)
        RELAY_PUMP.value(1)
        pump_ratio_calculator.set_pump_on()
        brew_data.pressure_sensor.reset_average()
        p_filt = brew_data.get_pressure_average(utime)
        plateau_ms, plateau_bar = 0, p_filt
        controller = None
        done_since = None
        last_t = start
        last_print = start
        while True:
            r = _sweep_break(brew_data, 'klamp_abort')
            if r:
                reason = r; break
            tray_reason = tray_guard_check(brew_data, utime, tray_state)
            if tray_reason:
                reason = tray_reason; break
            # Turvaraja raa'asta naytteesta (spec 2.5 kuten pcap/phold), ei suodatetusta
            bar = gain * (sensor.read_u16() * PCAP_RAW_A + PCAP_RAW_B) + offset
            if bar > PCAP_OVER_BAR:
                reason = 'overpressure'; break
            now = utime.ticks_ms()
            elapsed = utime.ticks_diff(now, start)
            dt = utime.ticks_diff(now, last_t) / 1000.0
            last_t = now
            pressure = brew_data.get_pressure_average(utime)
            p_filt += (pressure - p_filt) * min(1.0, dt / PCAP_FILT_TAU)
            if elapsed >= seconds * 1000:
                reason = 'timeout'; break

            if controller is None:
                # Vaihe 1: jatkuva pumppu, tasanne kuten vkello/pcap_settle (tayttovaihe ei kelpaa)
                if p_filt < PCAP_PLATEAU_MIN_BAR:
                    plateau_ms, plateau_bar = elapsed, p_filt
                elif elapsed >= PCAP_SETTLE_MIN_MS and elapsed - plateau_ms >= PCAP_PLATEAU_MS:
                    if p_filt - plateau_bar < PCAP_PLATEAU_BAR:
                        target = p_filt
                        print('KLAMP_RISE bar=%.2f reach_ms=%d reason=plateau' % (target, elapsed))
                        # Tasanteessa tayden pumpun duty on maaritelmallisesti 1: saadin aloittaa
                        # siita (ff 1.0), ei oppimastaan uuton ff:sta.
                        controller = PumpPressureController(RELAY_PUMP, pump_ratio_calculator, utime,
                                                            ff=1.0)
                        duty_avg = 1.0
                    else:
                        plateau_ms, plateau_bar = elapsed, p_filt
                if controller is None and elapsed >= KLAMP_RISE_MAX_MS:
                    reason = 'noreach'; break
            else:
                # Vaihe 2: pida tavoite; valmis, kun pumppua ei tarvitse rajoittaa
                controller.update(pressure, target)
                duty_avg += (controller.duty - duty_avg) * min(1.0, dt / KLAMP_DUTY_TAU)
                if duty_avg >= KLAMP_DONE_DUTY:
                    if done_since is None:
                        done_since = now
                    elif utime.ticks_diff(now, done_since) >= KLAMP_DONE_MS:
                        reason = 'done'; break
                else:
                    done_since = None
            brew_data.pressure_filtered = p_filt

            if utime.ticks_diff(now, last_print) >= KLAMP_PRINT_MS:
                last_print = now
                print('KLAMP t=%d bar=%.2f filt=%.2f target=%.2f duty=%.2f duty_avg=%.2f' % (
                    elapsed, pressure, p_filt, target if target is not None else 0.0,
                    controller.duty if controller is not None else 1.0, duty_avg))
            await asyncio.sleep_ms(5)
    except Exception:
        reason = 'error'
    finally:
        RELAY_PUMP.value(0)
        RELAY_SOLENOID.value(0)
        pump_ratio_calculator.set_pump_off()
        brew_data.set_mode('IDLE')
        brew_data.klamp_abort = False
    print('KLAMP_END reason=%s target=%.2f duty_avg=%.2f ms=%d' % (
        reason, target if target is not None else 0.0, duty_avg, utime.ticks_diff(utime.ticks_ms(), start)))


# ============================================================================
# FAST HEATUP
# ============================================================================

async def fast_heatup(utime, asyncio, brew_data):
    # asyncio comes in as a parameter like in every other run function: this file does not import
    # it, so the old signature crashed with NameError right after switching the pump on
    # (EXPRESSO-TURVA-PIKAKORJAUKSET, 21.9.2026). The finally below turns every relay off on any exit.

    RELAY_PUMP, RELAY_SOLENOID, RELAY_HEATER = brew_data.get_relays()

    try:
        # Fill the boiler
        RELAY_SOLENOID.value(1)
        RELAY_PUMP.value(1)
        await asyncio.sleep(2)
        RELAY_PUMP.value(0)
        RELAY_SOLENOID.value(0)

        # Heat the boiler
        RELAY_HEATER.value(1)
        while brew_data.get_boiler_temperature() < 85:
            await asyncio.sleep(1)
        while brew_data.get_boiler_temperature() < 110:
            RELAY_HEATER.value(1)
            await asyncio.sleep(1)
            RELAY_HEATER.value(0)
            await asyncio.sleep(1.5)
        while brew_data.get_boiler_temperature() < 115:
            RELAY_HEATER.value(1)
            await asyncio.sleep(1)
            RELAY_HEATER.value(0)
            await asyncio.sleep(2)

        # keep the temperature
        for i in range(200):
            if brew_data.get_boiler_temperature() < 115:
                RELAY_HEATER.value(1)
                await asyncio.sleep(1)
                RELAY_HEATER.value(0)
                await asyncio.sleep(2)
            else:
                await asyncio.sleep(1)
            await asyncio.sleep(1)

        # Cool the boiler to under 105 celsius
        while brew_data.get_boiler_temperature() > 99:
            await asyncio.sleep(1)

        # Fill the boiler
        RELAY_SOLENOID.value(1)
        RELAY_PUMP.value(1)
        await asyncio.sleep(0.5)
        RELAY_PUMP.value(0)
        RELAY_SOLENOID.value(0)

        # Sleep while boiler stabilizes
        await asyncio.sleep(15)
    finally:
        RELAY_PUMP.value(0)
        RELAY_SOLENOID.value(0)
        RELAY_HEATER.value(0)


# ============================================================================
# PRINT VALUES
# ============================================================================

def print_values(brew_data):
 
    # Get state of data
    boiler_temperature = brew_data.get_boiler_temperature()
    mode               = brew_data.get_mode()
    heating_speed      = brew_data.get_heating_speed()
    
    RELAY_PUMP, RELAY_SOLENOID, RELAY_HEATER = brew_data.get_relays()
    SWITCH_BREW, SWITCH_WATER, SWITCH_STEAM  = brew_data.get_switches()
    
    # Print values
    print('Mode: ', mode)
    print('Boiler temperature: ', boiler_temperature)
    print('heating_speed: ',      heating_speed)
    print('switch_brew: ',        SWITCH_BREW.value())
    print('switch_water: ',       SWITCH_WATER.value()) 
    print('switch_steam: ',       SWITCH_STEAM.value())
    print('RELAY_HEATER: ',       RELAY_HEATER.value())
    print('RELAY_SOLENOID: ',     RELAY_SOLENOID.value())
    print('RELAY_PUMP: ',         RELAY_PUMP.value())
    print('')


# ============================================================================
# SAVE SETTINGS
# ============================================================================

def save_settings(brew_data, json_module):
    # Get settings from brew_data object
    brew_temperature           = brew_data.get_brew_temperature()
    steam_temperature          = brew_data.get_steam_temperature()
    pre_infusion_time          = brew_data.get_pre_infusion_time()
    pressure_soft_release_time = brew_data.get_pressure_soft_release_time()
    pre_heat_time              = brew_data.get_pre_heat_time()
    pre_infusion_mode          = brew_data.get_pre_infusion_mode()
    pressure_soft_release_mode = brew_data.get_pressure_soft_release_mode()
    fast_heatup_mode           = brew_data.get_fast_heatup_mode()
    brew_pressure              = brew_data.get_brew_pressure()
    pre_infusion_pressure      = brew_data.get_pre_infusion_pressure()
    
    # Form the data
    data = {
        'brew_temperature'          : brew_temperature,
        'steam_temperature'         : steam_temperature,
        'pre_infusion_time'         : pre_infusion_time,
        'pressure_soft_release_time': pressure_soft_release_time,
        'pre_infusion_mode'         : pre_infusion_mode,
        'pressure_soft_release_mode': pressure_soft_release_mode,
        'fast_heatup_mode'          : fast_heatup_mode,
        'brew_pressure'             : brew_pressure,
        'pre_infusion_pressure'     : pre_infusion_pressure,
        # Test-shot weight limits (18.9.2026). Persisted after all: they are read only when
        # run_shot gets limit_weight=True, which happens for tshot and never for the brew switch,
        # so a stored limit cannot affect a real shot. Not persisting them meant the protection was
        # silently off after every restart and flash - a memory burden on the user, not a safeguard.
        'weight_limit'              : brew_data.get_weight_limit(),
        'weight_rise_limit'         : brew_data.get_weight_rise_limit()
    }
    
    # Save data to file in json format
    with open('settings.txt', 'w') as file:
        json_module.dump(data, file)
    
    print("save_settings")


# ============================================================================
# LOAD SETTINGS
# ============================================================================

def load_settings(json_module, brew_data):
    
    # Get values from file to variables
    try:
        with open('settings.txt', 'r') as file:
            data = json_module.load(file)
            
            brew_temperature           = data.get('brew_temperature')
            steam_temperature          = data.get('steam_temperature')
            pre_infusion_time          = data.get('pre_infusion_time')
            pressure_soft_release_time = data.get('pressure_soft_release_time')
            pre_infusion_mode          = data.get('pre_infusion_mode')
            pressure_soft_release_mode = data.get('pressure_soft_release_mode')
            fast_heatup_mode           = data.get('fast_heatup_mode')
        
        # Set settings to brew_data object
        brew_data.set_brew_temperature(brew_temperature)
        brew_data.set_steam_temperature(steam_temperature)
        brew_data.set_pre_infusion_time(pre_infusion_time)
        brew_data.set_pressure_soft_release_time(pressure_soft_release_time)
        brew_data.set_pre_infusion_mode(pre_infusion_mode)
        brew_data.set_pressure_soft_release_mode(pressure_soft_release_mode)
        brew_data.set_fast_heatup_mode(fast_heatup_mode)
        
        # Pressures were added 17.9.2026: older settings.txt has no keys -> keep defaults
        if data.get('brew_pressure') is not None:
            brew_data.set_brew_pressure(data.get('brew_pressure'))
        if data.get('pre_infusion_pressure') is not None:
            brew_data.set_pre_infusion_pressure(data.get('pre_infusion_pressure'))
        # Weight limits added 18.9.2026: same rule, a file without the keys keeps the defaults (off)
        if data.get('weight_limit') is not None:
            brew_data.set_weight_limit(data.get('weight_limit'))
        if data.get('weight_rise_limit') is not None:
            brew_data.set_weight_rise_limit(data.get('weight_rise_limit'))
        
        print('Loaded settings: brew_temperature, steam_temperature, pre_infusion_time, pressure_soft_release_time, pre_infusion_mode, pressure_soft_release_mode, fast_heatup_mode')
        return True
    
    # If data is not available: remove settings file and return False
    except (OSError, ValueError):   # ValueError = JSON syntax error 
        try:
            os.remove('settings.txt')
            print('settings.txt deleted pecause of error')
        except OSError:
            print('tried to delete settings.txt pecause of error but theres error in file deleting process')
        
        return False





