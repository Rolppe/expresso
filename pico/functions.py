import gc
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
                    end = utime.ticks_add(now, int(float(brew_data.get_pre_infusion_time() or 3.0) * 1000))
                    scale_obj = getattr(brew_data, 'tray_scale', None)
                    if scale_obj is not None:
                        th = getattr(brew_data, 'get_pre_infusion_trigger_threshold', lambda: None)()
                        scale_obj.arm_drop_detector(w=brew_data.get_weight(), threshold=th, blanking_ms=0)
                target = ramped
        else:
            target = pre_infusion_pressure
        controller.update(pressure, target)
        brew_data.pressure_filtered = controller.filtered

        drop_allowed = not build_up or utime.ticks_diff(now, ramp_start) >= 3000
        if drop_allowed and getattr(brew_data, 'get_pre_infusion_trigger_mode', lambda: False)() and \
                getattr(getattr(brew_data, 'tray_scale', None), 'drop_detected', lambda: False)():
            print('PI_TRIGGER reason=first_drop')
            break

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
EU_COAST_FAST_S0 = 0.2       # nopean nousun (katkaisun rate >= EU_RATE_FAST) jalkinousu opitaan erikseen (EXPRESSO-ESIUUTTO-
                             # UUTTOASENTO): laitteella nopeat 0,12-0,195 s (o-z, ag), hitaat 0,03-0,11 s. Yhteinen arvo periytyi
                             # hitaasta tilasta: af katkaisi ae:n 0,054:lla 1,79 barissa, jalkinousu 1,42 -> huippu 3,21
EU_COAST_MS = 300            # jalkinousun huippua haetaan enintaan nain kauan katkaisusta
EU_COAST_MIN_MS = 100        # ja vahintaan nain kauan (viive 40 ms + iskun nousu): katkaisuhetkella
                             # ramppi = paine, joten pelkka 'ramppi saavutti paineen' sulki heti
EU_RATE_MIN = 0.5            # bar/s: hitaammasta noususta ei opita jalkinousua
EU_RATE_FAST = 8.0           # bar/s: tata nopeampi nousu ei ole huuhtelu (katkaisun huuhtelusaanto, ks. vaihe 1)
EU_RAMP_BAR_PER_S = 2.0      # sama loppunoston ramppi kuin pre_infusion
EU_RAMP_FF_MAX = 0.5         # rampin oman myotakytkennan yläraja (duty)
EU_GAS_ABS = 1.0             # bar: ilmanpaine, absoluuttinen = mitattu + tama
EU_GAS_EXP = 2.0             # rampin vahvistus G_katkaisu x ((abs sp) / (abs katkaisu))^tama; 0 = ei kaasujoustoa
EU_ABOVE_BAR = 0.3           # kaasujousto vain, kun jalkinousu vei p5:n nain paljon rampin ylle (paine putoaa rampille).
                             # Alhaalta nouseva ramppi ennallaan: vakiojoustoinen malli (smoke 8, 9 lampin) hidastui muuten
                             # (katkaisusta pitoon 1,16-1,18 s, raja 1,1; paine 0,64 bar rampin alla, raja 0,5)
EU_RAMP_LEAD_S = 0.1         # rampin myotakytkenta loppuu, kun p5 on nain monen rampin sekunnin paassa tavoitteesta
                             # (iskun + p5:n viive)
EU_TAU_S = 1.8               # kuristimen vuodon aikavakio pidon ff:n laskuun (laite 25.9.2026: lampin 1,4-1,8,
                             # kylma 2,2 s). Nousudatasta sita ei saa: nousu kiihtyy tayton jalkeen, joten
                             # kahden nousupisteen tau olisi negatiivinen (a/b/c), ja vuoto muuttaa nousua vain
                             # ~0,5 bar/s, kun nousunopeuden kohina on ~1,5 bar/s.
EU_FF_FIRST_X = 0.4          # ensimmainen ajo (ei edellisen pidon tietoa): ff = tama x nousun arvio. Yliarvio maksaa
                             # enemman kuin aliarvio: vuodon tau 2,5-10 s purkaa 0,2 bar ylityksen sekunneissa, mutta
                             # pumppu nostaa vajetta 5-10 bar/s (esiuutto-20260926-a: arvio 0,43, tarve 0,10)
EU_LEARN_SKIP_MS = 2000      # pidon tarve opitaan vasta taman jalkeen (asettunut pito); ennen sita duty seuraa ff:aa
EU_KP, EU_KI = 0.2, 0.3      # sama PI kuin PumpPressureController
EU_KD = 0.05                 # D virheen muutoksesta (asetusarvon nopeus - nousunopeus, bar/s -> duty): jarruttaa, kun
                             # paine lahestyy tavoitetta ramppia nopeammin (kayttaja 26.9.2026: himmennys PID-tyyppiseksi)
EU_KD_G = 0.3                # D:n silmukkavahvistuksen KD*G yläraja rampilla, G katkaisusta (EXPRESSO-ESIUUTTO-UUTTOASENTO):
                             # nousunopeus on 5 jakson keskiarvojen erotus (~0,1 s viive), joten suuri KD*G heiluttaa. Laite
                             # af/ag (G 13-18, tarve 0,14-0,19): 300 ms rajasykli, pidon sd 0,61-0,71, huippu 4,6-5,0 bar
EU_KD_G_HOLD = 0.1           # sama pidossa. Iskun vaste on uuttoasennossa nopeampi kuin katkaisun G nayttaa (kahden osan malli:
                             # nopea osa purkautuu ~0,08 s:ssa), joten raja on rampin rajaa tiukempi. Malli (kohina, 8 siementa):
                             # uuttoasento pidon p5 sd 0,49 -> 0,35, rajasykli pois; lampin, kiinni, avoin ennallaan tai parempi.
                             # D:n poisto pidosta kokonaan heikensi hitaita tiloja (smoke 10 +0,006 -> +0,056, raja 0,06)
EU_KP_TAIL = 0.4             # loppulahestyminen (ramppi tavoitteessa, pito ei alkanut) ja pidon 1. sekunti:
EU_KI_TAIL_X = 3.0           # P ja integraalin kerroin. Katkaisun ff:n virhe (vuodon tau 1,6 vs. EU_TAU_S 1,8
EU_TAIL_HOLD_MS = 1000       # -> -0,04; nousunopeuden kohina sd ~0,05) korjautuu nain ennen pitoa eika sen aikana
EU_LOG_SLOTS = 5             # EU-rivi joka 5. jakso (100 ms)
EU_AVG_N = 5                 # paatosten keskiarvo 5 jaksoa (100 ms); nousunopeus kahdesta perakkaisesta
EU_HOLD_TOL_BAR = 0.1        # pito alkaa, kun ramppi on tavoitteessa ja p5 on tavoite +- tama
EU_HOLD_WAIT_MS = 2000       # ylityksesta pito alkaa viimeistaan nain kauan asetusarvon tavoitteeseen paasysta: laitteella
                             # ylitys 0,6-1,2 bar purkautui kaistalle 0,4-0,8 s:ssa (ao-as), tau_obs 14 s:lla ~2 s
EU_INT_BAND_BAR = 0.3        # ennen pitoa integraali kertyy vain, kun |virhe| < tama
EU_OVER_MS = 1000            # yliampuma = huippu nousussa ja pidon ensimmaisen sekunnin; sen jalkeen on
                             # pidon heittelya (hold_sd). Sama ikkuna kuin esiuutto_analyysi.py
# Vuoronvaraus (EXPRESSO-ESIUUTTO-VUORONVARAUS): laitteella (ah-am 26.9.2026) silmukka pysahtyi 13-28 ms 0,4-1,2 s
# valein, ja kun pysahdys osui releen paallaoloon pidossa, rele jai paalle yli seuraavan tauon (late) -> +0,8-1,0 bar.
# vv=1 (oletus, euv:0 = vanha mittausta varten): vaiheessa 2 asyncio-vuoro ja roskienkeruu vain, kun rele on pois eika
# seuraava jakso iske; automaattinen keruu estetaan keraamalla ennen kuin keko tayttyy. EU_STALL- ja EU_GC-rivit kertovat,
# mika silmukan osa pysahdyksen vei.
EU_STALL_US = 10000          # EU_STALL-rivi, kun vuoro (y), jakson kasittely (k), naytteenotto (s) tai myohastyminen (l) ylittaa.
                             # Laite an (euv:0): automaattinen keruu 0,5-0,8 s valein 15-28 ms (keko 307 kt, kulutus ~500 kt/s;
                             # myos vaa'an 17 ms kierrokset olivat keruita). Vakiot alle rajan: kellon ikkuna (s) ~7 ms, jakso (k) ~5 ms
EU_GC_MS = 300               # hallittu keruu nain usein: 300 ms x 500 kt/s jattaa ~150 kt varaa ennen automaattista.
                             # Ei gc.mem_free():lla: se kay keon lapi 7,3 ms (laite an, chk_max_us)
EU_GC_RISE_FRAC = 0.1        # vaiheessa 1 (rele paalla koko ajan) keruu vain, kun p5 < tama x tavoite: kaukana katkaisusta
EU_IQ_CLOSE_US = 12000       # kellon ikkunan sulku (iq_close + VKELLO-rivi 10-11 ms, laite ao/ap) vain, kun seuraavaan
                             # paatoskohtaan on vahintaan tama, jos rele on paalla tai seuraava jakso iskee: ap:n ainoa late
                             # (661 ms) oli sulku juuri ennen taukoa. Ikkuna pitenee enintaan jakson, ja iq_close kayttaa todellista loppua
EU_PRINT_GAP_MS = 20         # loppurivien vali: USB-CDC:n lahetysjono on 256 tavua ja ylikirjoittuu ilman DTR:aa (EU_END 278
                             # merkkia katkesi, laite ah-am), joten rivit <= 255 ja jono tyhjenee valissa

# Ytimen 1 jaksot (c1x:1, EXPRESSO-C1-JAKSOT vaihe 3, paketit/C1-JAKSOT.md; VAATIMUS: TILAUS-O, TILAUS-L, TILAUS-I):
# ydin 1 nayttee 1 kHz renkaaseen ja kaantaa pumppureleen jonon tapahtumista niiden ajassa (classes._c1_exec). Ydin 0
# ajaa saman silmukan, mutta (1) jakso k kasitellaan, kun renkaassa on nayte t >= kohta (t = nimellinen kohta), ja
# naytteet tulevat renkaasta omilla ajoillaan; (2) kohdan k paatos kirjoitetaan kohtaan k+2 (K1: +1 jakso hyvaksytty),
# ja 10 ms tauko on kaksi tapahtumaa. Jokaisella kohdalla on tapahtuma, joten nalka (CX_STARVE_US) on virhe, ei tauko.
# Etumatka = seuraavan kirjoittamattoman tapahtuman aikaisin hetki (kohdan k+2 tauon paluu) - nyt.
# Esiuutto (vaihe 3) ja uutto bim:1 (vaihe 4, siirtyma ei koske jonoon); oletus 1 (BrewData.eu_c1x), c1x:0 = vanha polku.
EU_C1X_START_MS = 150        # ydin 1 nayttaa ensimmaisen naytteen (CX_N > 0) tassa ajassa, muuten EU_C1X fail ja vanha polku
EU_C1X_GC_LEAD_US = 42000    # hallittu keruu (Pico 2 W:lla ~36-39 ms) vain, kun etumatka on vahintaan tama
EU_C1X_YIELD_LEAD_US = 30000 # asyncio-vuoro vain, kun rengas on luettu ja etumatka vahintaan tama (pisin varaus 28 ms, laite an)
EU_C1X_FILL_US = 22000       # tapahtumien vali enintaan tama: kellon korjaus voi venyttaa kohtien valin ~35 ms:iin
                             # (EU_MIN_SLOT_US + T), joten valiin tayte samalla tilalla ennen ytimen 1 nalkaa (25 ms).
                             # Yli jakson (20 ms): nimellinen vali 19,9-20,1 ms ei saa taytetta
EU_C1X_DEAD_US = 50000       # ei uutta naytetta ytimelta 1 nain kauan -> reason=c1dead
EB_C1X_KP_TAIL = 0.2         # uuton pidon 1. s:n P c1x:lla (vanha polku max(EB_KP, EU_KP_TAIL) = 0,4): paatos toteutuu
                             # jakson myohemmin, ja korotettu P varahtelee pidon alussa (malli 25b kohina, 8 siementa: ylitys
                             # 0,26 -> 0,22, vanha 0,20 +- 0,06; kaanto 0,3 -> 0,6 kaistalle 0,67 -> 0,61 s, vanha 0,60 +- 0,03).
                             # Virheen ennuste jakson eteenpain kokeiltiin mallissa: ylitys 0,28-0,35
EU_C1X_LAG_S = 0.02          # paatos toteutuu jakson myohemmin: katkaisun ennuste p5 + nousu x (jalkinousu + tama), ja
                             # jalkinousun oppi vahentaa sen, jotta opittu coast_s ei riipu polusta. Laite 20.10.2026 (sarja
                             # 3 + 3, katkaisussa ~21 bar/s): ilman tata c1x:n jalkinousu 1,85-1,95 vs vanha 1,42-1,72 bar,
                             # ylitys 0,52 vs 0,16. Mallin 8 barin nousu ~11 bar/s ei nayttanyt sita (ylitys pidon alusta)


def _cx_put(x, ev, wt, ne, utime, t, on):
    """Tapahtuma (t_us, 0/1) ytimen 1 jonoon. Indeksit classes.CX_*: 2 EW, 3 ER. False, jos jono on taynna."""
    w = x[2]
    if w - x[3] >= ne:
        return False
    i = (w % ne) * 2
    ev[i] = t
    ev[i + 1] = on
    wt[w % ne] = utime.ticks_us()
    x[2] = w + 1
    return True


def _c1x_next(utime, clock, s):
    """Kohtaa s seuraava paatoskohta kellon seuraavasta reunasta, kuten vanhan polun slot, mutta nimellisesta kohdasta."""
    n = utime.ticks_add(clock.edge(utime.ticks_add(s, round(clock.T) - EU_OFF_US)), EU_OFF_US)
    while utime.ticks_diff(n, s) < EU_MIN_SLOT_US:
        n = utime.ticks_add(n, round(clock.T))
    return n


async def _c1x_start(brew_data, utime, asyncio, relay, sensor):
    """Ytimen 1 toteuttaja kayntiin (c1_on(3), lampotila naytteiden valeissa). Palauttaa TemperatureSensorin tai None
    (EU_C1X fail -rivi, vanha polku)."""
    import classes as CL
    ts = getattr(brew_data, 'temperature_sensor', None)
    x, st = getattr(ts, 'cx', None), getattr(ts, 'c1', None)
    if x is None or st is None or st[CL.C1_RUN] != 1:
        print('EU_C1X fail reason=noc1')
        return None
    for k in range(len(x)):
        x[k] = 0
    ts.cx_ok[0] = 0
    ts.cx_pin = getattr(relay, 'pin', relay)     # GuardedRelayn oma pinni (turva_toimilaite_smoke A1/A2)
    ts.c1_adc = sensor
    if not ts.c1_on(3):
        print('EU_C1X fail reason=want want=%d' % st[CL.C1_WANT])
        return None
    t0 = utime.ticks_ms()
    while x[CL.CX_N] == 0:
        if utime.ticks_diff(utime.ticks_ms(), t0) > EU_C1X_START_MS:
            ts.c1_off()
            print('EU_C1X fail reason=start')
            return None
        await asyncio.sleep_ms(1)
    return ts

# ============================================================================
#  UUTTO VAIHESEURANNALLA (bim:1) - TILAUS-K vaiheet 3-4 (EXPRESSO-UUTTO-8BAR, 27.9.2026)
# ============================================================================
# VAATIMUS: TILAUS-K, TILAUS-L, TILAUS-I, TILAUS-J, TILAUS-B, TILAUS-C, TILAUS-F, TILAUS-G
#
# Esiuuton pidon lopusta (end_t) silmukka ei paaty, vaan jatkuu samana silmukkana (kello, delta-sigma, vuoronvaraus,
# myohastymisvahti ja hallittu keruu katkeamatta):
# Vaihe 3 (nousu uuttopaineeseen): taysi sykli, kunnes p5 + nousunopeus x opittu jalkinousu (eb_coast_s) >= tavoite -
#   EB_CUT_MARGIN_BAR; sitten ramppi ja loppulahestyminen kuten vaiheessa 2 (TILAUS-K: "yliampumisen ehkaisy samoin").
# Vaihe 4 (pito): delta-sigma ja PI(D) kuten vaihe 2, kunnes keep_running() on epatosi (kytkin, tshot, turvarajat).
# Uuton ff, G, tau ja jalkinousu opitaan erillaan esiuuton arvoista (eb_ff, eb_x, eb_g, eb_tau, eb_coast_s, settings.txt).
# Laitemalli (testit/uutto8_sovitus.py, 8 ajoa 24.-26.9.2026): jousto vakio + kaasu/p_abs^2 (c0 0,03), vuoto ~ p^0,8,
# pumpun kayraa (pmax 15 bar) nousudata ei tue. Pidon tarve = vuoto / (50 x iskun tilavuus), jousto supistuu pois, joten
# saman ajon esiuuton tarve x (uuttopaine / esiuuttopaine)^0,8 on uuton tarpeen paras ensiarvio (sama kuristin samassa
# ajossa). Isku 8 barissa 0,34-0,93 bar, p/vuoto 8 barissa 0,18-1,8 s, tarve 8 barissa 0,26-1,01; vanha saadin mallissa
# toistaa laitteen TS-pidon keskipaineen (rms 0,19 bar, 7 ajoa) ja ~1 barin pudotukset (min 6,1-6,6).
EB_LEAK_N = 0.8              # vuodon eksponentti: ensiarvion kerroin (uuttopaine / esiuuttopaine)^tama, kunnes eb_x opittu
EB_CUT_MARGIN_BAR = 0.3      # sama kuin EU_CUT_MARGIN_BAR
EB_COAST_S0 = 0.2            # jalkinousun oletus: nousu 2,5 -> 8 on aina nopea (TS-rivit 7-21 bar/s), sama kuin EU_COAST_FAST_S0
EB_RAMP_BAR_PER_S = 4.0      # loppunoston ramppi kuten vaiheessa 2, mutta 4 bar/s: vuoto 8 barissa on nopea (p/vuoto 0,2-1,8 s),
                             # joten nousu jaksaa rampin. Malli (4 kuristintilaa, 6 siementa, kohina): katkaisusta pitoon
                             # 1,6-1,8 -> 1,0-1,2 s, ylitys ja pidon alun notkahdus samat kuin 2 bar/s:lla
EB_TAU_MIN, EB_TAU_MAX = 0.05, 30.0
EB_KP, EB_KI_X = 0.2, 3.0    # P ja integraalin kerroin (EU_KI x tama) vaiheissa 3-4 (TILAUS-C: kuristimen kaanto). Malli (kaanto
                             # tarve 0,3 -> 0,6 -> 0,2 askeleena, kohina, 6 siementa): kaistalle +-0,3 bar KI x 1: 1,5-1,6 s,
                             # x 2: 0,8-0,9, x 3: 0,6, x 4: 0,5 s; pidon sd 0,095 / 0,093 / 0,105 / 0,110. KP 0,3-0,5 heiluttaa
                             # (sd 0,16-0,20, notkahdus pidon alussa -0,9...-1,1): iskun vahvistus 8 barissa ~3 x 2,5 barin
EB_GC_RISE_FRAC = 0.5        # vaiheen 3 taydella nousulla keruu vain nousun alkupuoliskolla (rele paalla joka tapauksessa,
                             # kuten vaihe 1): kaukana katkaisusta, ettei pysahdys osu katkaisuun
# Kello (kayttajan valinta a 27.9.2026: lukitus vaiheen 3 nousussa). Taydella pumpulla nousevan paineen vareilyn viive
# poikkeaa nousunopeuden mukaan (testit/vkello_dpdt.py, 510 ikkunaa, 4 ajoa: 2-4 bar/s -613 us, 4-7 -961, 7-12 -1091;
# ajojen valinen ero sd ~850 us), joten kiintea korjaus ei ole harhaton (vkello_rise_learn: noususta opetettu kello
# -3,9 / +3,6 / -6,8 ms vaarassa lukituksi ilmoitettuna). Alle 2 bar/s nousevissa ikkunoissa poikkeama on +8 us (n 270,
# -0,5...0,5 bar/s) ja +128 us (n 79, 0,5-2 bar/s), eli LOCK_US:n (1000) alla. Siksi vaiheissa 3-4 ikkuna opettaa vain,
# kun sen keskipaine nousi edellisesta ikkunasta alle EB_CLK_RATE bar/s: vaiheen 3 taysi nousu ei opeta (gate=-1),
# rampin loppu ja loppulahestyminen opettavat, joten kello lukittuu ennen pitoa.
EB_CLK_RATE = 2.0            # bar/s
EB_HEAT_OFF_MS, EB_HEAT_ON_MS = 100, 50   # lammittimen pulssitus kuten vanhassa uuttosilmukassa (pois 100 ms, paalla 50 ms)
# Uuton lammitys virtauksesta (TILAUS-N, TILAUS-R, kayttaja 21.10.2026), vaiheet 1-4: jokainen pumpun isku tuo kattilaan
# kylmaa vetta, jonka lammitys maksaa brew_heat_k ms lammitinaikaa nollapaineessa; iskun tilavuus pienenee paineen mukana
# (EP5, ~0 BH_PMAX barissa). Lammitin on paalla, kun kertymaa on jaljella. Jaannos maksetaan uuton jalkeen ja kerroin
# opitaan tasaantuneesta lampotilasta (classes.Thermostat, BH_*). Vanha uuttosilmukka (bim:0) pulssittaa yha EB_HEAT.
BH_PMAX = 15.0
# Taytto: ennen kuin paine nousee BH_FILL_BAR:iin, kertymaan lasketaan enintaan BH_FILL_MAX iskua. Hoyryn jalkeen
# pumppu taydentaa ensin vajaata kattilaa (kayttaja 21.10.2026: s3 555 iskua, normaali 89-101), ja kuuman kattilan
# varastolampo lammittaa sen veden: kertyma ilman kattoa ylitti +8 C. Katon ylitys estaa opin (bh_nolearn).
BH_FILL_BAR = 1.0
BH_FILL_MAX = 120
# Vapaa virtaus (kahva irti, huuhtelu; kayttaja 21.10.2026): paine ei nouse BH_FILL_BAR:iin, joten koko ajo olisi
# tayttoa ja katto maksaisi 15 s:n huuhtelusta 120 iskua 747:sta. Kaukalo erottaa: kun sen paino on noussut ajon
# alusta BH_FREE_G, vesi kulkee kattilan lapi, ja katon ylittavat iskut lasketaan. Vanha tai puuttuva lukema = katto.
BH_FREE_G = 10.0
BH_STEAM_NOLEARN_MS = 1200000   # hoyrysta alle 20 min: ei oppia (kattila vajaa, runko kuuma)
BH_START_US = 200000  # ensimmainen lampotilalukema valmis (ydin 1: 80 ms c1_on:sta); kertyma siirtyy
BH_K0_MS = 70.0      # kun brew_dataa ei ole luotu classes.BrewDatana (testit); sama kuin classes.BH_K0_MS
EB_RATIO_MS = 1000           # set_pump_ratio 1 s valein kuten vanhassa uuttosilmukassa


def _bh_tray(brew_data, utime):
    """Kaukalon paino g tai None, jos lukemaa ei ole tai se on vanha (TRAY_STALE_MS)."""
    try:
        w = brew_data.get_weight()
        if w is None or utime.ticks_diff(utime.ticks_ms(), brew_data.get_weight_ms()) > TRAY_STALE_MS:
            return None
        return w
    except Exception:
        return None
# Vuoronvaraus vaiheissa 3-4 (vv=1): 8 barin tarve 0,3-0,9 tekee tauoista yksittaisia 10 ms taukoja (rele palaa kesken jakson),
# joten vaiheen 2 saanto (vuoro ja keruu vain, kun rele on pois eika seuraava jakso iske) ei paastaisi vuoroa koskaan: keko
# tayttyisi (automaattinen keruu 15-28 ms releen ollessa paalla -> late) ja muut tehtavat (vaaka, BLE) nalkiintyisivat.
# Lisaksi sallitaan vuoro ja keruu, kun rele on paalla ja seuraavakin jakso iskee (ei pend_on): alle 2 jakson (40 ms)
# pysahdys myohastyttaa vain seuraavan iskevan jakson kasittelyn, eika seuraavaa taukoa. Mitattu pisin pysahdys 28 ms
# (laite an). Malli (smoke 19, keruu + 13-28 ms varaukset 5/s): ilman tata late 2-4 ja automaattisia keruita 11-13/ajo.


async def pre_infusion_phased(brew_data, utime, asyncio, pump_ratio_calculator, keep_running=None, brew=False):
    # brew=True (bim:1, run_shot): esiuuton jalkeen vaiheet 3-4 samassa silmukassa; palauttaa (jaksot, pisin jakson
    # vali ms) vaiheista 3-4 run_shotin <label>_END-riville. brew=False: esiuutto kuten ennen, palauttaa None.
    import math
    from verkkokello import Verkkokello
    RELAY_PUMP, RELAY_SOLENOID, RELAY_HEATER = brew_data.get_relays()
    if keep_running is None:
        keep_running = brew_data.get_switch_brew().value
    sensor = brew_data.pressure_sensor.pressure_sensor
    gain, offset = brew_data.pressure_sensor.gain, brew_data.pressure_sensor.offset
    target = brew_data.get_pre_infusion_pressure()
    hold_us = int(float(brew_data.get_pre_infusion_time() or 0) * 1000000)
    if hold_us == 0 and brew_data.get_pre_infusion_mode():
        hold_us = 3000000
    coast_s = getattr(brew_data, 'eu_coast_s', EU_COAST_S0)
    coast_f = getattr(brew_data, 'eu_coast_fast_s', EU_COAST_FAST_S0)
    ff = brew_data.learned_ff_pre
    vv = getattr(brew_data, 'eu_vv', 1)
    tb = getattr(brew_data, 'tbusy', None)     # main.py: pisin tehtavan kierros, nollataan ennen vuoroa
    g_prev = getattr(brew_data, 'eu_g_pre', 0.0)
    tau_prev = getattr(brew_data, 'eu_tau_pre', 0.0)

    # Kuten pre_infusion: jaannospaine ensin tavoitteen alle venttiili auki
    brew_data.set_mode('pre-infusion pressure stabilization')
    RELAY_SOLENOID.value(1)
    pressure = brew_data.get_pressure()
    while pressure > target - 0.1 and keep_running():
        pressure = brew_data.get_pressure()
        await asyncio.sleep_ms(20)

    brew_data.set_mode('pre-infusion pressure build-up')
    # Ytimen 1 jaksot (c1x:1, ks. EU_C1X_*): esiuutto ja uutto. Rengas, jono ja CX_OK sidotaan paikallisiin nimiin
    c1t = None
    if getattr(brew_data, 'eu_c1x', 0) == 1:
        c1t = await _c1x_start(brew_data, utime, asyncio, RELAY_PUMP, sensor)
    c1x = c1t is not None
    guard = getattr(RELAY_PUMP, 'guard', None)
    gc.collect()                  # pumppu pois: tyhja keko alkuun
    free0 = gc.mem_free()
    gc_t = utime.ticks_us()
    print('EU_START target=%.2f hold_s=%.1f coast_s=%.3f coast_f=%.3f ff=%.2f off_us=%d vv=%d fr0=%d c1x=%d' % (
        target, hold_us / 1e6, coast_s, coast_f, ff, EU_OFF_US, vv, free0 // 1024, 1 if c1x else 0))
    t0 = utime.ticks_us()
    clock = Verkkokello(t0)
    clock.iq_start(t0)
    relay = [False]
    pump_out = None if c1x else RELAY_PUMP      # c1x: ydin 1 kaantaa pinnin, set_relay vain kirjaa tilan
    dly = 0.0                     # c1x: paatoksen lisaviive (s) katkaisun ennusteessa ja jalkinousun opissa (EU_C1X_LAG_S)

    def set_relay(on):
        if on != relay[0]:
            relay[0] = on
            if pump_out is not None: pump_out.value(1 if on else 0)
            if on: pump_ratio_calculator.set_pump_on()
            else: pump_ratio_calculator.set_pump_off()

    slot = utime.ticks_add(t0, EU_OFF_US)
    cx = cx_ok = None
    smp, ts_, slot1, q_dl, cq, lag_max, cyc_min, late_c1, fill_n = False, 0, 0, 0, [], 0, 9999, 0, 0
    if c1x:
        import classes as CL
        cx, cx_ok, cx_ev, cx_wt, cx_sm = c1t.cx, c1t.cx_ok, c1t.cx_ev, c1t.cx_wt, c1t.cx_samp
        cx_ne, cx_ns = CL.CX_NE, CL.CX_NS
        i_sw, i_sr, i_late, i_starve = CL.CX_SW, CL.CX_SR, CL.CX_LATE, CL.CX_STARVE
        # K4: CX_OK vain, jos vahti sallii pumpun (allow kaynnistaa myos 180 s:n ajorajan)
        if guard is not None and ('all' in guard.block or not guard.allow('pump')):
            c1t.c1_off()
            print('EU_C1X fail reason=guard')
            c1x, pump_out = False, RELAY_PUMP
        else:
            cx[i_sr] = cx[i_sw]                   # vakautuksen aikaiset naytteet pois
            cx_ok[0] = 1
            if guard is not None: guard.relays['pump'].c1_ok = cx_ok    # = RELAY_PUMP (GuardedRelay)
            # Kuten vanha polku: pumppu heti paalle ja vaihe 1 paalla; kohdat slot ja slot1 jonoon (40 ms)
            # Paalle heti kirjoitushetkella: t0:aan kirjoitettuna se myohastyi 1,8 ms (laite c1x-20261020-hold2, lidx 0)
            _cx_put(cx, cx_ev, cx_wt, cx_ne, utime, utime.ticks_us(), 1)
            slot1 = _c1x_next(utime, clock, slot)
            for te in (slot, slot1):
                _cx_put(cx, cx_ev, cx_wt, cx_ne, utime, te, 1)
            cq = [[True, True, False], [True, True, False]]     # kohdittain [paalla, paalla ennen kohtaa, vaihe ok]
            q_dl = utime.ticks_add(slot1, EU_GAP_US)
            c1_seen = utime.ticks_us()
            dly = EU_C1X_LAG_S
            cx[CL.CX_ARMED] = 1
    set_relay(True)
    phase, reason = 1, 'stop'
    acc, d, integ, pump_next, pend_on = 0.0, 1.0, 0.0, True, None
    cyc_s, cyc_n, hist, next_s = 0.0, 0, [], t0
    sp, last_slot, n_slot = target, None, 0
    cut_t = p_cut = rate_cut = peak = None
    coast_open = False
    ramp_base = ramp_t = hold_t = end_t = sp_t = None
    ramp_done = ramp_above = False
    strokes = removed = skips10 = skips20 = late = miss = windows = win_low = learned = 0
    p_max, rise_max, h_s, h_ss, h_n, duty_avg = 0.0, 0.0, 0.0, 0.0, 0, ff
    out = []
    ramp_ff = 0.0
    g_cut, ff_rate, ff_carry, dh_s, dh_n = 0.0, 0.0, 0.0, 0.0, 0
    kd, kd_h, l_s0, l_r0, coast_c = EU_KD, EU_KD, None, 0, coast_s
    stall_n = gc_n = gc_max = k_max = s_max = y_max = late_max = 0
    # Vaiheet 3-4 (brew, EXPRESSO-UUTTO-8BAR): vaihe 1-2 -muuttujat alustetaan siirtymassa uudelleen uuton arvoilla.
    # ds = delta-sigma kaytossa (vaihe 2, vaihe 3 katkaisun jalkeen, vaihe 4); vaiheessa 2 sama kuin phase == 2.
    stage_b, ds, tgt_pre, ramp_r, tag = False, False, target, EU_RAMP_BAR_PER_S, 'EU'
    kp_n, ki_n, kp_t, ki_t = EU_KP, 1.0, EU_KP_TAIL, EU_KI_TAIL_X     # P ja integraalin kerroin: normaali, loppulahestyminen
    q, pre_ok, b_slots, b_gap, tb0, heat, ratio_t, p_wp, t_wp = [], False, 0, 0, None, None, None, None, None
    hk0 = getattr(brew_data, 'brew_heat_k', BH_K0_MS) * 1000.0   # lammitysaika us / isku nollapaineessa (classes.BrewData)
    hk1 = hk0 / BH_PMAX
    hc, hsum, hc_t = 0.0, 0.0, None           # kertyma us, kertyma yhteensa, edellinen jakso
    bh_w0 = _bh_tray(brew_data, utime)
    bh_fill = [0, False, False]               # tayton iskut, paine noussut, vapaa virtaus (kaukalo nousee)

    def _bh_add(p):
        # Iskun lammitystarve us (BH_*): taytossa enintaan BH_FILL_MAX iskua, ellei kaukalo nouse (BH_FREE_G)
        if not bh_fill[1]:
            if p >= BH_FILL_BAR:
                bh_fill[1] = True
            else:
                bh_fill[0] += 1
                if bh_fill[0] > BH_FILL_MAX and not bh_fill[2]:
                    w = _bh_tray(brew_data, utime)
                    if bh_w0 is None or w is None or w - bh_w0 < BH_FREE_G:
                        return 0.0
                    bh_fill[2] = True
                    print('BH_FREE fill=%d tray_g=%.1f' % (bh_fill[0], w - bh_w0))
        return hk0 - hk1 * p if p < BH_PMAX else 0.0
    eb_coast = getattr(brew_data, 'eb_coast_s', EB_COAST_S0)
    eb_x = getattr(brew_data, 'eb_x', 0.0)
    eb_g = getattr(brew_data, 'eb_g', 0.0)
    eb_tau = getattr(brew_data, 'eb_tau', 0.0)
    try:
        while True:
            now = utime.ticks_us()
            if c1x:
                # Seuraava rengasnayte: kohta kasitellaan ensimmaisen kohdan jalkeisen naytteen kohdalla
                due = False
                smp = cx[i_sr] != cx[i_sw]
                if smp:
                    ts_ = cx_sm[(cx[i_sr] % cx_ns) * 2]
                    due = utime.ticks_diff(ts_, slot) >= 0
                    c1_seen = now
                elif utime.ticks_diff(now, c1_seen) > EU_C1X_DEAD_US:
                    reason = 'c1dead'; break
            else:
                if pend_on is not None and utime.ticks_diff(pend_on, now) < PCAP_RATE_US:
                    while utime.ticks_diff(pend_on, utime.ticks_us()) > 0: pass
                    set_relay(True)
                    pend_on = None
                    now = utime.ticks_us()
                due = utime.ticks_diff(slot, now) < PCAP_RATE_US
            if due:
                if c1x:
                    t = slot
                    lag = utime.ticks_diff(now, slot)
                    if lag > lag_max: lag_max = lag
                    if cx[i_starve]:
                        reason, miss = 'starve', cx[i_starve]
                        out.append('EU_STARVE t_ms=%d starve=%d lag_us=%d' % (utime.ticks_diff(t, t0) // 1000, miss, lag))
                        break
                    if cx_ok[0] == 0:
                        reason = 'guard'; break
                    # Kohdassa k toteutunut: jonon FIFO (ydin 1 kaantaa ajallaan; myohassa > CX_LATE_US = late)
                    qe = cq.pop(0)
                    cur, was_on, skip_late = qe[0], qe[1], False
                    if cx[i_late] != late_c1:
                        late += cx[i_late] - late_c1; late_c1 = cx[i_late]
                    set_relay(cur)
                else:
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
                    if lateness > late_max: late_max = lateness
                    if lateness > EU_STALL_US:
                        stall_n += 1
                        out.append('EU_STALL t_ms=%d sec=l us=%d rel=%d' % (
                            utime.ticks_diff(t, t0) // 1000, lateness, 1 if was_on else 0))
                    if lateness > clock.T / 2:
                        # Pysahdys (toinen tehtava) ohitti kokonaisia jaksoja: rele pysyi ennallaan
                        extra = int((lateness + clock.T / 2) // clock.T)
                        miss += extra
                        if was_on: strokes += extra
                        else: removed += extra
                # Jaksokeskipaine: naytteet edellisesta paatoskohdasta tahan = yksi kellojakso
                if c1x and cyc_n < cyc_min: cyc_min = cyc_n
                p = cyc_s / cyc_n if cyc_n else (hist[-1] if hist else 0.0)
                cyc_s, cyc_n = 0.0, 0
                brew_data.pressure = p
                brew_data.pressure_filtered = p
                hist.append(p)
                if len(hist) > 2 * EU_AVG_N: hist.pop(0)
                # Paatokset 5 jakson keskiarvosta: yksittaisen jakson keskiarvo heiluu taytossa +-0,5 bar
                # (esiuutto-20260924-c: katkaisu piikista 1,37 bar, rate 16,5 bar/s, todellinen ~0,3 bar)
                # Summat indekseilla, ei viipaleilla (EXPRESSO-GC-UUTTO): kaksi listaa jaksoa kohden pois keosta.
                # Sama summausjarjestys kuin sum():lla, joten p5 ja rate eivat muutu.
                nh = len(hist)
                s5 = 0
                for i in range(nh - EU_AVG_N if nh > EU_AVG_N else 0, nh): s5 += hist[i]
                p5 = s5 / min(nh, EU_AVG_N)
                rate = 0.0
                if nh == 2 * EU_AVG_N:
                    s5 = 0
                    for i in range(EU_AVG_N): s5 += hist[i]
                    rate = (p5 - s5 / EU_AVG_N) / (EU_AVG_N * 0.02)
                dt = 0.02 if last_slot is None else min(0.1, utime.ticks_diff(t, last_slot) / 1e6)
                if stage_b:
                    b_slots += 1
                    gap_ms = utime.ticks_diff(t, last_slot) // 1000
                    if gap_ms > b_gap: b_gap = gap_ms
                last_slot = t
                n_slot += 1
                if p > p_max: p_max = p
                if (hold_t is None or utime.ticks_diff(t, hold_t) < EU_OVER_MS * 1000) and p5 > rise_max:
                    rise_max = p5
                scale_obj = getattr(brew_data, 'tray_scale', None)
                drop_allowed = hold_t is not None or utime.ticks_diff(t, t0) >= 3000000
                drop_trig = (not stage_b and drop_allowed and
                             getattr(brew_data, 'get_pre_infusion_trigger_mode', lambda: False)() and
                             getattr(scale_obj, 'drop_detected', lambda: False)())
                if (end_t is not None and utime.ticks_diff(t, end_t) >= 0) or drop_trig:
                    reason = 'drop' if drop_trig else 'done'
                    if not brew: break
                    # Siirtyma vaiheeseen 3 (EXPRESSO-UUTTO-8BAR): silmukka jatkuu. Esiuuton loppurivit ja oppi kuten
                    # ajon lopussa (samat luvut: tama jakso ei viela ole laskuissa), rivit jonoon ja tulostus enintaan
                    # yksi jaksoa kohden (USB-CDC:n 256 tavun jono). gc.mem_free() kay keon lapi 7,3 ms (laite an), joten
                    # EU_VV fr_end=-1 siirtymassa.
                    l1, l2, pre_ok = _eu_end(brew_data, clock, t, reason, target, hold_t, l_s0, l_r0, strokes, removed,
                                             rate_cut, p_cut, g_cut, coast_s, coast_f, h_s, h_ss, h_n, dh_s, dh_n, p_max,
                                             rise_max, skips10, skips20, late, miss, windows, win_low, learned, kd)
                    q = [l1, l2, 'EU_VV vv=%d stall=%d gc_n=%d gc_max_us=%d fr0=%d fr_end=-1 k_max_us=%d s_max_us=%d '
                         'y_max_us=%d late_max_us=%d' % (vv, stall_n, gc_n, gc_max, free0 // 1024, k_max, s_max, y_max,
                                                          late_max)]
                    if drop_trig:
                        q.append('EU_TRIGGER t_ms=%d w=%s' % (
                            utime.ticks_diff(t, t0) // 1000,
                            '%.2f' % brew_data.get_weight() if brew_data.get_weight() is not None else '-'))
                    stage_b, phase, tag, ramp_r, reason = True, 3, 'EB', EB_RAMP_BAR_PER_S, 'stop'
                    kp_n, ki_n, kp_t, ki_t = EB_KP, EB_KI_X, max(EB_KP, EU_KP_TAIL), max(EB_KI_X, EU_KI_TAIL_X)
                    if c1x: kp_t = EB_C1X_KP_TAIL
                    target = brew_data.get_brew_pressure()
                    # Uuton tarpeen ensiarvio taman ajon esiuuton tarpeesta (sama kuristin samassa ajossa): tarve ~ p^0,8
                    # (testit/uutto8_sovitus.py, EB_LEAK_N). Edellisen uuton suhde uuton ja esiuuton tarpeen valilla (eb_x)
                    # korvaa sen, kun se on opittu.
                    x = eb_x if eb_x > 0.0 else (target / tgt_pre) ** EB_LEAK_N
                    ff = min(1.0, max(0.05, brew_data.learned_ff_pre * x))
                    coast_c, cut_t, p_cut, rate_cut, peak, coast_open = eb_coast, None, None, None, None, False
                    ramp_base = ramp_t = hold_t = end_t = sp_t = None
                    ramp_done = ramp_above = False
                    sp, integ, acc, d, pump_next, ramp_ff, g_cut, kd, kd_h = target, 0.0, 0.0, 1.0, True, 0.0, 0.0, EU_KD, EU_KD
                    strokes = removed = skips10 = skips20 = late = miss = windows = win_low = learned = 0
                    p_max, rise_max, h_s, h_ss, h_n, duty_avg = 0.0, 0.0, 0.0, 0.0, 0, ff
                    dh_s, dh_n, l_s0, l_r0 = 0.0, 0, None, 0
                    stall_n = gc_n = gc_max = k_max = s_max = y_max = late_max = 0
                    # Paineen tason muutos 2,5 -> 8 bar on pysyva, ei transientti: porttien viitteet alusta
                    clock.gate_reset()
                    tb0, ratio_t = t, t
                    brew_data.set_mode('brew loop')
                    q.append('EB_START t_ms=%d target=%.2f ff=%.2f x=%.2f ff_pre=%.2f pre_ok=%d coast_s=%.3f g=%.2f tau=%.2f' % (
                        utime.ticks_diff(t, t0) // 1000, target, ff, x, brew_data.learned_ff_pre, 1 if pre_ok else 0,
                        coast_c, eb_g, eb_tau))
                if not keep_running():
                    reason = 'stop'; break

                # Katkaisu vasta taysista keskiarvoista (2 x 5 jaksoa). Huuhtelusaanto (p5 >= 1/2 tavoite) ei koske nopeaa
                # nousua: huuhtelu (tasapaino G*tau < 1/2 tavoite) nousee >= EU_RATE_FAST bar/s paineessa >= 1/4 tavoite vain,
                # jos G > EU_RATE_FAST / (1 - 1/2) = 16 bar/s; laitteella G <= 12,5 (EXPRESSO-ESIUUTTO-ALKU 26.9.2026: taysi
                # jarjestelma, nousu 11,5 bar/s, katkaisu vasta 1,3-1,6 barissa -> huippu 3,4-4,3 bar)
                if phase == 1 and len(hist) == 2 * EU_AVG_N and \
                        (p5 >= target * 0.5 or (p5 >= target * 0.25 and rate >= EU_RATE_FAST)) and \
                        p5 + rate * ((coast_f if rate >= EU_RATE_FAST else coast_s) + dly) >= target - EU_CUT_MARGIN_BAR:
                    phase = 2
                    cut_t, p_cut, rate_cut, peak, coast_open = t, p5, rate, p5, True
                    coast_c = coast_f if rate >= EU_RATE_FAST else coast_s
                    ramp_base, ramp_t, integ, acc = p5, t, 0.0, 0.0
                    # Iskun vahvistus G = 50 x iskukoko (bar/s dutya kohden) taman ajon katkaisuhetken
                    # noususta taydella dutylla: rate = G - p/tau, joten G = rate + p/tau. Pidon tarve on
                    # tavoite / (G*tau), mutta tau on kuristimen vuoto, eika nousu nae sita (vuoto on nousussa
                    # pieni pumppuun verrattuna). Laitteella tarve 0,09-0,37 ja tau_obs 1,4-10 s kuristimen
                    # asennon ja lampotilan mukaan (25.-26.9.2026). Siksi (EXPRESSO-ESIUUTTO-FF):
                    # - tau edellisen ajon pidosta: ff = edellisen pidon tarve x G_edellinen / G_nyt (kylma/lampin
                    #   kuristin muuttaa G:ta: 25.9. c-ajo opittu 0,30 -> tarve 0,15);
                    # - enintaan nousun arvio tavoite / (G*EU_TAU_S) ja ilman edellista ajoa EU_FF_FIRST_X kertaa
                    #   se: yliarvio (26.9. a: 0,43 vs. 0,10) purkautuu hitaasti, vaje korjautuu nopeasti.
                    # - rampin myotakytkenta 2 bar/s / G (EXPRESSO-ESIUUTTO-PITO): pelkka P-termi jatti paineen
                    #   ~0,6 bar rampin alle ~1 s ajaksi.
                    # Hitaasta noususta G:ta ei voi arvioida: silloin opittu ff ja ei rampin myotakytkentaa.
                    ramp_ff, g = 0.0, 0.0
                    if rate >= EU_RATE_MIN:
                        g = rate + p5 / EU_TAU_S
                        ff_rate = target / (g * EU_TAU_S)
                        if g_prev > 0.0 and tau_prev > 0.0:
                            # EXPRESSO-ESIUUTTO-AVOIN: tau edellisen ajon pidosta. ff = tavoite / (G*tau) = tavoite /
                            # (rate*tau + p5), sama kuin edellisen tarve x G-suhde, kun molemmat G:t lasketaan
                            # edellisen tau:lla. EU_TAU_S:n G-suhde ja yläraja aliarvioivat avoimella kuristimella
                            # (laite l-n: tau 0,35-0,9 s, tarve 0,65, ff 0,21-0,35 -> pidon 2 ensimmaista s p5 2,28-2,37).
                            # Ei alarajaa: kuristimen kaanto avoimesta lahes kiinni yliarvioi yhden ajon (malli over 0,43 ->
                            # 0,86), mutta niin kova vastapaine ei ole todellinen uutto (kayttaja 26.9.2026)
                            ff_carry = target / (rate * tau_prev + p5)
                            ff = ff_carry
                        elif g_prev > 0.0:
                            ff_carry = ff * g_prev / g
                            ff = min(ff_rate, ff_carry)
                        else:
                            ff = EU_FF_FIRST_X * ff_rate
                        ff = min(0.9, max(0.05, ff))
                        duty_avg = ff
                        ramp_ff = min(EU_RAMP_FF_MAX, EU_RAMP_BAR_PER_S / g)
                    g_cut = g
                    if g > 0.0: kd, kd_h = min(EU_KD, EU_KD_G / g), min(EU_KD, EU_KD_G_HOLD / g)
                    brew_data.set_mode('pre-infusion final rise')
                    out.append('EU_CUT t_ms=%d p=%.2f rate=%.2f coast_s=%.3f pred=%.2f g=%.2f ff=%.2f ffr=%.2f ffc=%.2f tau=%.2f' % (
                        utime.ticks_diff(t, t0) // 1000, p5, rate, coast_c, p5 + rate * coast_c, g, ff, ff_rate,
                        ff_carry, tau_prev))
                # Vaihe 3: katkaisu kuten vaiheessa 1 (ennuste p5 + nousunopeus x jalkinousu). ff on jo valittu siirtymassa;
                # G = rate + p5/tau taman ajon noususta, tau siita, etta pidon tarve ff = tavoite / (G tau): tau = (tavoite/ff
                # - p5) / rate (sama kuin EU_END tau_obs). Hitaasta noususta G:ta ei saa: edellisen uuton eb_g.
                if phase == 3 and cut_t is None and len(hist) == 2 * EU_AVG_N and \
                        p5 + rate * (coast_c + dly) >= target - EB_CUT_MARGIN_BAR:
                    cut_t, p_cut, rate_cut, peak, coast_open = t, p5, rate, p5, True
                    ramp_base, ramp_t, integ, acc = p5, t, 0.0, 0.0
                    tau_c, g = eb_tau, eb_g
                    if rate >= EU_RATE_MIN and target / ff > p5:
                        tau_c = min(EB_TAU_MAX, max(EB_TAU_MIN, (target / ff - p5) / rate))
                        g = rate + p5 / tau_c
                    ramp_ff = min(EU_RAMP_FF_MAX, ramp_r / g) if g > 0.0 else 0.0
                    g_cut = g
                    if g > 0.0: kd, kd_h = min(EU_KD, EU_KD_G / g), min(EU_KD, EU_KD_G_HOLD / g)
                    out.append('EB_CUT t_ms=%d p=%.2f rate=%.2f coast_s=%.3f pred=%.2f g=%.2f ff=%.2f tau=%.2f' % (
                        utime.ticks_diff(t, t0) // 1000, p5, rate, coast_c, p5 + rate * coast_c, g, ff, tau_c))
                ds = phase == 2 or phase == 4 or (phase == 3 and cut_t is not None)
                if ds:
                    if hold_t is None:
                        # Paine ehti tavoitteeseen ennen ramppia (jalkinousu): ramppi on tehty, eika paine putoa sen
                        # huipusta rampille (laite ao-as 27.9.2026). Vasta jalkinousun ikkunan jalkeen: sen nopea osa
                        # (uuttoasento, purku 0,08 s) nostaa p5:n hetkeksi tavoitteeseen, ja pito alkoi transientista
                        if not ramp_done and not coast_open and p5 >= target - EU_HOLD_TOL_BAR:
                            ramp_done = True
                            out.append('%s_RAMP_DONE t_ms=%d p=%.2f sp=%.2f' % (tag, utime.ticks_diff(t, t0) // 1000, p5, sp))
                        sp = target if ramp_done else ramp_base + ramp_r * utime.ticks_diff(t, ramp_t) / 1e6
                        if sp >= target:
                            sp = target
                            if sp_t is None: sp_t = t
                            # Menetelmaohje: laskuri alkaa vasta, kun paine on saavutettu - ei silloin, kun
                            # ramppi on (esiuutto-20260924-b/c: pito alkoi paineessa 1,34 / 1,09 bar), eika
                            # yliampumasta ("jos sita tapahtuu niin se ei aloita laskuria"; laite ao: pito alkoi 3,45:ssa).
                            # Varalla EU_HOLD_WAIT_MS: kuristin ilman vuotoa ei purkaisi ylitysta koskaan
                            if p5 >= target - EU_HOLD_TOL_BAR and (
                                    p5 <= target + EU_HOLD_TOL_BAR or
                                    utime.ticks_diff(t, sp_t) >= EU_HOLD_WAIT_MS * 1000):
                                hold_t = t
                                if stage_b:
                                    phase = 4         # uuton pito jatkuu, kunnes keep_running() on epatosi
                                else:
                                    end_t = utime.ticks_add(t, hold_us)
                                    brew_data.set_mode('pre-infusion main')
                                    if scale_obj is not None:
                                        th = getattr(brew_data, 'get_pre_infusion_trigger_threshold', lambda: None)()
                                        scale_obj.arm_drop_detector(w=brew_data.get_weight(), threshold=th, blanking_ms=0)
                                out.append('%s_HOLD t_ms=%d p=%.2f wait_ms=%d' % (
                                    tag, utime.ticks_diff(t, t0) // 1000, p5, utime.ticks_diff(t, sp_t) // 1000))
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
                                obs = (peak - p_cut) / rate_cut - dly
                                coast_c = max(EU_COAST_MIN, min(EU_COAST_MAX, coast_c + 0.5 * (obs - coast_c)))
                                if stage_b: pass              # uuton jalkinousu erikseen (eb_coast_s), ei esiuuton arvoihin
                                elif rate_cut >= EU_RATE_FAST: coast_f = coast_c
                                else: coast_s = coast_c
                            out.append('%s_COAST peak=%.2f rise=%.2f rate=%.2f coast_s=%.3f fast=%d learn=%d' % (
                                tag, peak, peak - p_cut, rate_cut, coast_c, 1 if rate_cut >= EU_RATE_FAST else 0,
                                1 if learn else 0))
                    e = sp - p
                    # Rampin aikana tasapainoduty skaalautuu paineen mukana (ff on mitattu tavoitteessa).
                    # Rampin myotakytkenta vain, kun paine on rampin alla, ja se loppuu, kun p5 on EU_RAMP_LEAD_S
                    # rampin sekuntia tavoitteen alla: jalkinousun edella oleva paine ja iskun + p5:n viive (~0,1 s)
                    # nostivat ilman naita rajoja ylityksia (sovitettu malli: yli 0,3 bar 17/48 ajoa, vanha 4/48).
                    # Raja paineesta eika rampista (EXPRESSO-ESIUUTTO-FF 26.9.2026): rampin mukaan lopetettu
                    # myotakytkenta jatti paineen ~0,25 bar tavoitteen alle, ja loppu vei pelkalla P-termilla
                    # 0,4-0,6 s (sovitettu malli: katkaisusta pitoon 1,2-1,3 s -> 0,63-0,72 s).
                    uff = ff
                    kp, ki_x = kp_n, ki_n
                    kd_r = kd
                    if hold_t is None:
                        if sp < target:
                            uff = ff * sp / target
                        # Kaasujousto (EXPRESSO-ESIUUTTO-RAMPIN-LOPPU): iskun vaikutus kasvaa absoluuttisen paineen
                        # nelion mukaan, joten katkaisun G aliarvioi vahvistuksen rampin paassa. Laite ao-as: G 9-10
                        # katkaisussa (~1,4 bar) = isku ~0,2 bar, pidossa isku +0,35-0,45 bar. Jalkinousu vei paineen
                        # rampin ylle, paine putosi rampille 2,0-2,3 bariin, ja 2 bar/s / G + D antoivat 2-3 iskun ryopyn
                        # (ylitys 0,36-1,32). Malli (esiuutto_smoke-Plant gas_bar) toistaa laitteen vain kaasujoustolla.
                        if p5 >= sp + EU_ABOVE_BAR: ramp_above = True
                        gx = ((EU_GAS_ABS + sp) / (EU_GAS_ABS + p_cut)) ** EU_GAS_EXP if ramp_above and sp > p_cut else 1.0
                        if g_cut > 0.0: kd_r = min(EU_KD, EU_KD_G / (g_cut * gx))
                        if p5 < sp and p5 < target - ramp_r * EU_RAMP_LEAD_S:
                            uff += ramp_ff / gx
                    if (hold_t is None and sp >= target) or \
                            (hold_t is not None and utime.ticks_diff(t, hold_t) < EU_TAIL_HOLD_MS * 1000):
                        kp, ki_x = kp_t, ki_t
                    # D: virheen derivaatta = rampin nopeus - paineen nousunopeus (rate: 5 jakson keskiarvojen erotus,
                    # sama kuin katkaisussa). Rampilla sita seuraava paine antaa nollan.
                    dterm = (kd_r if hold_t is None else kd_h) * ((ramp_r if hold_t is None and sp < target else 0.0) - rate)
                    u = uff + kp * e + EU_KI * integ + dterm
                    # Integraali vain pidossa, rampin paatyttya tai lahella asetusarvoa: rampin viive kasasi sen
                    # c-ajossa (1,1 bar vajetta 0,5 s) ja se purkautui yliampumana 3,6 bariin. Rampin paatyttya
                    # kaista ei rajaa: liian pienella ff:lla P-termi jatti paineen ~0,8 bar tavoitteen alle,
                    # integraali ei kertynyt, pito ei alkanut eika ajo paattynyt (esiuutto_smoke 26.9.2026)
                    if (hold_t is not None or sp >= target or abs(e) < EU_INT_BAND_BAR) and \
                            (-1.0 < u < 1.0 or (u >= 1.0 and e < 0) or (u <= -1.0 and e > 0)):
                        integ = integ + e * dt * ki_x
                        # Hidas osa (ff + integraali) on pidon tarve eika voi olla negatiivinen: -1...1-delta-sigman kanssa
                        # integraali valui ylityksessa syvalle (laite r 26.9.2026: pito 2,7 -> 1,44 bar, ka 2,01).
                        # Ylaraja samoin hitaasta osasta (EXPRESSO-ESIUUTTO-AVOIN): vanha integ <= 1,5 salli vain
                        # +0,45, joten avoimen kuristimen tarve 0,65 jai 1. ajon ff 0,09:lla saavuttamatta (malli: pito 2,27)
                        if integ < -uff / EU_KI: integ = -uff / EU_KI
                        if integ > (1.0 - uff) / EU_KI: integ = (1.0 - uff) / EU_KI
                    u = uff + kp * e + EU_KI * integ + dterm
                    # Delta-sigma saa myos negatiivisen tarpeen (-1..1, EXPRESSO-ESIUUTTO-ALKU 26.9.2026): pidon
                    # tarve 0,05 on lahella nollaa, ja jaksokohinan (sd 0,25 bar) P- ja D-termi heiluttavat u:ta
                    # sen molemmin puolin. Nollaan rajattu duty tasasuuntasi kohinan lisaiskuiksi, eika integraali
                    # voinut korjata sita (anti-windup esti laskun, kun u <= 0): pidon 2 s keskiarvo +0,1...+0,4 bar
                    # (laite g 2,61; sovitettu malli +0,16, max +0,39 -> +0,04, max +0,13).
                    us = -1.0 if u < -1.0 else (1.0 if u > 1.0 else u)
                    d = 0.0 if us < 0.0 else us
                    if hold_t is not None:
                        duty_avg += (us - duty_avg) * (dt / 5.0)
                        if utime.ticks_diff(t, hold_t) >= EU_LEARN_SKIP_MS * 1000:
                            dh_s += us; dh_n += 1
                            if l_s0 is None: l_s0, l_r0 = strokes, removed

                # Seuraava jakso paatetaan nyt (delta-sigma); tama jakso toimi jo yllä.
                if ds:
                    acc = max(-1.0, acc + us)
                    pump_next = acc >= 1.0
                    if pump_next: acc -= 1.0
                # sd_us(t) kerran jaksossa ja vain, kun sita kaytetaan (EXPRESSO-GC-UUTTO): tauon ok ja EU-rivi
                sd_t = None
                if c1x:
                    # Sama kirjanpito kuin alla, mutta kohdan k tauon vaihe (ok) paatettiin jo kohdassa k-1
                    if cur:
                        strokes += 1
                        hx = _bh_add(p); hc += hx; hsum += hx
                    else:
                        removed += 1
                        if was_on:
                            if qe[2]: skips10 += 1
                            else: skips20 += 1
                    # Kohta k+1 on jonossa. Sen 10 ms tauko paatetaan nyt, kun k+2:n paatos (pump_next) tiedetaan,
                    # ja k+2 kirjoitetaan jonoon. Jokaisella kohdalla on tapahtuma (nalka = virhe).
                    qe = cq[0]
                    gap = False
                    if not qe[0] and (qe[1] or pump_next):
                        sd_t = clock.sd_us(t)
                        qe[2] = 2.5 * sd_t < EU_PHASE_OK_US
                        gap = pump_next and qe[2]
                    s2 = _c1x_next(utime, clock, slot1)
                    te, on = slot1, 1 if qe[0] else 0
                    if gap:
                        te, on = utime.ticks_add(slot1, EU_GAP_US), 1
                        put_ok = _cx_put(cx, cx_ev, cx_wt, cx_ne, utime, te, 1)
                    else:
                        put_ok = True
                    if put_ok and utime.ticks_diff(s2, te) > EU_C1X_FILL_US:
                        fill_n += 1
                        put_ok = _cx_put(cx, cx_ev, cx_wt, cx_ne, utime, utime.ticks_add(te, utime.ticks_diff(s2, te) // 2), on)
                    if not (put_ok and _cx_put(cx, cx_ev, cx_wt, cx_ne, utime, s2, 1 if pump_next else 0)):
                        reason = 'c1full'; break
                    # Vahti jokaisesta paalle-tapahtumasta (ajoraja ja pump_last_want, K4); kielto nollasi CX_OK:n (_trip)
                    if (pump_next or gap) and guard is not None and ('all' in guard.block or not guard.allow('pump')):
                        cx_ok[0] = 0
                    cq.append([pump_next, qe[0] or gap, False])
                    slot, slot1 = slot1, s2
                    q_dl = utime.ticks_add(s2, EU_GAP_US)
                else:
                    if cur:
                        strokes += 1
                        hx = _bh_add(p); hc += hx; hsum += hx
                    elif skip_late:
                        # Myohassa: tauko jai tekematta, isku meni lapi, velka siirtyy seuraaviin jaksoihin
                        late += 1; strokes += 1; acc -= 1.0
                        hx = _bh_add(p); hc += hx; hsum += hx
                    else:
                        ok = False
                        if was_on or pump_next:
                            sd_t = clock.sd_us(t)
                            ok = 2.5 * sd_t < EU_PHASE_OK_US
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
                    w = brew_data.get_weight()
                    f = brew_data.get_flow()
                    out.append('EU %d %.2f %.2f %d %.2f %d p5=%.2f sd_us=%.0f rm=%d sk10=%d sk20=%d late=%d w=%s f=%s' % (
                        utime.ticks_diff(t, t0) // 1000, p, sp, 1 if relay[0] else 0, d, phase, p5,
                        clock.sd_us(t) if sd_t is None else sd_t, removed, skips10, skips20, late,
                        '-' if w is None else '%.1f' % w,
                        '-' if f is None else '%.2f' % f))
                # Lammitin iskujen kertymasta (BH_*), kaikissa vaiheissa: paalla, kun kertymaa on jaljella
                if hc_t is not None and heat:
                    hc -= utime.ticks_diff(t, hc_t)
                hc_t = t
                hv = 1 if hc > 0.0 and utime.ticks_diff(t, t0) >= BH_START_US else 0
                if hv or hv != heat:       # paalla kirjoitetaan joka jaksolla: vahti tarkistaa lukeman ian
                    heat = hv
                    RELAY_HEATER.value(hv)
                if stage_b:
                    # set_pump_ratio 1 s valein kuten vanhassa uuttosilmukassa
                    if utime.ticks_diff(t, ratio_t) >= EB_RATIO_MS * 1000:
                        ratio_t = t
                        brew_data.set_pump_ratio(pump_ratio_calculator.get_ratio())
                    # Esiuuton loppurivit siirtymasta: enintaan yksi jaksoa kohden ja vain, jos jakson rivit mahtuvat
                    # USB-CDC:n 256 tavun jonoon (EU_PRINT_GAP_MS), eika silmukka pysahdy releen ollessa paalla
                    out_len = 0
                    for x in out: out_len += len(x) + 1
                    if q and out_len + len(q[0]) < 256:
                        out.append(q.pop(0))
                for line in out: print(line)
                del out[:]
                k_us = utime.ticks_diff(utime.ticks_us(), t)
                if k_us > k_max: k_max = k_us
                if k_us > EU_STALL_US:
                    stall_n += 1
                    out.append('EU_STALL t_ms=%d sec=k us=%d rel=%d' % (
                        utime.ticks_diff(t, t0) // 1000, k_us, 1 if relay[0] else 0))
                # Hallittu keruu: rele pois ja seuraava jakso tauko, joten keruun pysahdys vain pidentaa taukoa.
                # Vaiheissa 3-4 myos, kun rele on paalla ja seuraava jakso iskee (on_run, ks. vuoronvaraus EB_RATIO_MS:n alla)
                on_run = stage_b and relay[0] and pump_next and pend_on is None
                # c1x: releen tilaehdot pois, keruu aina riittavalla etumatkalla (ydin 1 kaantaa jonosta keruun ajan)
                c1 = 0
                if vv and utime.ticks_diff(t, gc_t) >= EU_GC_MS * 1000 and \
                        ((c1x and utime.ticks_diff(q_dl, utime.ticks_us()) >= EU_C1X_GC_LEAD_US) or
                         (not c1x and phase == 1 and p5 < target * EU_GC_RISE_FRAC) or
                         (not c1x and phase == 3 and cut_t is None and p5 < tgt_pre + EB_GC_RISE_FRAC * (target - tgt_pre)) or
                         (not c1x and ds and (on_run or not (relay[0] or pump_next or pend_on is not None)))):
                    c0 = utime.ticks_us()
                    gc.collect()
                    gc_t = utime.ticks_us()
                    c1 = utime.ticks_diff(gc_t, c0)
                    gc_n += 1
                    if c1 > gc_max: gc_max = c1
                    out.append('EU_GC t_ms=%d us=%d rel=%d' % (utime.ticks_diff(c0, t0) // 1000, c1, 1 if relay[0] else 0))
                now = utime.ticks_us()

            # c1x: rengasnayte omalla ajallaan tq (ei, jos se kuuluu jo seuraavaan kohtaan: kasitellaan ensin)
            if (c1x and smp and utime.ticks_diff(ts_, slot) < 0) or (not c1x and utime.ticks_diff(now, next_s) >= 0):
                s0 = now
                if c1x:
                    r = cx[i_sr]
                    j = (r % cx_ns) * 2
                    tq, raw = cx_sm[j], cx_sm[j + 1]
                    cx[i_sr] = r + 1
                else:
                    next_s = utime.ticks_add(next_s, PCAP_RATE_US)
                    if utime.ticks_diff(now, next_s) > 0: next_s = utime.ticks_add(now, PCAP_RATE_US)
                    tq, raw = now, sensor.read_u16()
                bar = gain * (raw * PCAP_RAW_A + PCAP_RAW_B) + offset
                cyc_s += bar; cyc_n += 1
                clock.iq_add(tq, bar)
                iq_lead_ok = (utime.ticks_diff(q_dl, utime.ticks_us()) >= 25000) if c1x else (
                    not (vv and ds and (relay[0] or pump_next or pend_on is not None) and
                         utime.ticks_diff(slot, now) < EU_IQ_CLOSE_US))
                if clock.iq_ready(tq) and c1 == 0 and iq_lead_ok:
                    lrn = phase == 2
                    if stage_b:
                        # Vaiheet 3-4: ikkuna opettaa vain, kun sen keskipaine nousi edellisesta alle EB_CLK_RATE bar/s
                        # (ks. EB_CLK_RATE: nousunopeuden viiveharha). Vaiheen 3 taysi nousu jaa lokiin gate=-1.
                        pw = clock.iq_sum / clock.iq_n if clock.iq_n else 0.0
                        lrn = p_wp is not None and (pw - p_wp) * 1e6 < EB_CLK_RATE * utime.ticks_diff(tq, t_wp)
                        p_wp, t_wp = pw, tq
                    res = clock.iq_close(tq, learn=lrn)
                    clock.iq_start(tq)
                    if res is None:
                        win_low += 1          # amplitudi alle AMP_MIN: harvat iskut, ei kellopaivitysta
                    else:
                        z, amp, p_bar, g = res; windows += 1
                        if g == 0: learned += 1
                        sd_w = clock.sd_us(tq)
                        out.append('VKELLO w=%d t_ms=%d z_us=%.1f T_us=%.3f d=%.5f sd_us=%.1f amp=%.3f lock=%d p_bar=%.2f gate=%d' % (
                            windows, utime.ticks_diff(tq, t0) // 1000, z, clock.T, clock.d,
                            sd_w, amp, 1 if clock.locked(tq, sd_w) else 0, p_bar, g))
                now = utime.ticks_us()
                s0 = utime.ticks_diff(now, s0)
                if s0 > s_max: s_max = s0
                if s0 > EU_STALL_US:
                    stall_n += 1
                    out.append('EU_STALL t_ms=%d sec=s us=%d rel=%d' % (
                        utime.ticks_diff(now, t0) // 1000, s0, 1 if relay[0] else 0))
            if c1x:
                # Vuoro, kun rengas on luettu ja etumatka riittaa toisen tehtavan varaukseen; releen tila ei rajaa
                yld = cx[i_sr] == cx[i_sw] and utime.ticks_diff(q_dl, now) >= EU_C1X_YIELD_LEAD_US
            else:
                wait = utime.ticks_diff(slot, now)
                if pend_on is not None: wait = min(wait, utime.ticks_diff(pend_on, now))
                # vv=1: vaiheessa 2 vuoro vain, kun rele on pois eika seuraava jakso iske. Vuoron yli venyva toinen tehtava
                # vain pidentaa taukoa; ennen rele jai paalle ja isku meni lapi (late). Vaiheessa 1 rele on paalla joka tapauksessa.
                # Vaiheissa 3-4 myos, kun rele on paalla ja seuraavakin jakso iskee (ks. vuoronvaraus EB_RATIO_MS:n alla).
                yld = wait > EU_YIELD_US and (not vv or not ds or not (relay[0] or pump_next or pend_on is not None) or
                                              (stage_b and relay[0] and pump_next and pend_on is None))
            if yld:
                if tb is not None:
                    tb[0] = '-'
                    tb[1] = 0
                c0 = utime.ticks_us()
                await asyncio.sleep_ms(0)
                c1 = utime.ticks_diff(utime.ticks_us(), c0)
                if c1 > y_max: y_max = c1
                if c1 > EU_STALL_US:
                    stall_n += 1
                    out.append('EU_STALL t_ms=%d sec=y us=%d rel=%d task=%s:%d' % (
                        utime.ticks_diff(c0, t0) // 1000, c1, 1 if relay[0] else 0,
                        tb[0] if tb is not None else '?', tb[1] if tb is not None else 0))
    finally:
        if c1x:
            # Lupa ensin (ydin 1 ei kaanna enaa paalle), sitten pinni ja toteuttaja pois (_c1_exec kaantaa pinnin 0:aan
            # ennen kesken jaaneen lampotilaluvun loppua)
            cx_ok[0] = 0
            cx[CL.CX_ARMED] = 0
            RELAY_PUMP.value(0)
            c1t.c1_off()
            c1t.cx_pin = None             # _c1_mainin virhepolku ei kaanna pumppua lepoluvun aikana (exec sitoi pinnin)
            if guard is not None: guard.relays['pump'].c1_ok = None
        set_relay(False)
        RELAY_PUMP.value(0)
        RELAY_HEATER.value(0)
        # Jaannos ja summa uuton jalkeiselle maksulle ja opille (classes.Thermostat)
        brew_data.bh_credit_us = getattr(brew_data, 'bh_credit_us', 0.0) + (hc if hc > 0.0 else 0.0)
        brew_data.bh_sum_us = getattr(brew_data, 'bh_sum_us', 0.0) + hsum
        brew_data.bh_fill_n = bh_fill[0]
        if bh_fill[0] > BH_FILL_MAX:
            brew_data.bh_nolearn = 1      # myos vapaa virtaus: taytto ja lapivirtaus sekaisin, ei oppia
    if not stage_b:
        for line in out:
            print(line)
            await asyncio.sleep_ms(EU_PRINT_GAP_MS)
        if c1x:
            late_max = cx[CL.CX_LMAX]
        now = utime.ticks_us()
        l1, l2, _ = _eu_end(brew_data, clock, now, reason, target, hold_t, l_s0, l_r0, strokes, removed, rate_cut, p_cut,
                            g_cut, coast_s, coast_f, h_s, h_ss, h_n, dh_s, dh_n, p_max, rise_max, skips10, skips20, late, miss,
                            windows, win_low, learned, kd)
        # Kolme rivia <= 255 merkkia (EU_PRINT_GAP_MS): yksi 278 merkin rivi katkesi siirrossa
        print(l1)
        await asyncio.sleep_ms(EU_PRINT_GAP_MS)
        print(l2)
        await asyncio.sleep_ms(EU_PRINT_GAP_MS)
        print('EU_VV vv=%d stall=%d gc_n=%d gc_max_us=%d fr0=%d fr_end=%d k_max_us=%d s_max_us=%d y_max_us=%d late_max_us=%d' % (
            vv, stall_n, gc_n, gc_max, free0 // 1024, gc.mem_free() // 1024, k_max, s_max, y_max, late_max))
        if c1x:
            await asyncio.sleep_ms(EU_PRINT_GAP_MS)
            # Ytimen 1 kirjanpito (classes.CX_*): naytteet, pisin nayteval, ylivuodot, tapahtumat (tehty / kirjoitettu),
            # myohastymat, nalka, ytimen 0 pisin kasittelyviive kohdasta, pienin naytemaara jaksossa, taytteet
            print('EU_C1X n=%d gmax_us=%d ovf=%d nev=%d written=%d lmax_us=%d late=%d starve=%d lidx=%d lwr_us=%d '
                  'lag_max_us=%d cyc_min=%d fill=%d' % (cx[CL.CX_N], cx[CL.CX_GMAX], cx[CL.CX_OVF], cx[CL.CX_NEV], cx[CL.CX_EW],
                                                       cx[CL.CX_LMAX], cx[CL.CX_LATE], cx[CL.CX_STARVE], cx[CL.CX_LIDX],
                                                       cx[CL.CX_LWR], lag_max, cyc_min, fill_n))
        return (0, 0) if brew else None
    # Uuton loppu (vaiheet 3-4). Jonoon jaaneet esiuuton rivit ensin.
    for line in q + out:
        print(line)
        await asyncio.sleep_ms(EU_PRINT_GAP_MS)
    # Uuton tarve pidon 2 s:sta loppuun kuten esiuutossa (iskuosuus), omille avaimilleen (eb_*): esiuuton arvot pysyvat.
    # eb_x = uuton tarve / saman ajon esiuuton tarve (vain, jos esiuutto oppi tassa ajossa): seuraavan ajon ff:n kerroin.
    # tau = (tavoite / tarve - p_katkaisu) / nousunopeus kuten EU_END tau_obs; G katkaisusta.
    u_mean = dh_s / dh_n if dh_n else 0.0
    l_n = (strokes - l_s0) + (removed - l_r0) if l_s0 is not None else 0
    need, tau_obs = 0.0, 0.0
    if hold_t is not None and l_n >= 50:
        need = (strokes - l_s0) / l_n
        brew_data.eb_ff = min(1.0, max(0.05, need))
        if pre_ok: brew_data.eb_x = brew_data.eb_ff / brew_data.learned_ff_pre
        if g_cut > 0.0: brew_data.eb_g = g_cut
        if rate_cut is not None and rate_cut >= EU_RATE_MIN:
            tau_obs = (target / brew_data.eb_ff - p_cut) / rate_cut
            brew_data.eb_tau = min(EB_TAU_MAX, max(EB_TAU_MIN, tau_obs))
        brew_data.set_setting_changed()
    brew_data.eb_coast_s = coast_c
    mean = h_s / h_n if h_n else 0.0
    sd = math.sqrt(max(0.0, h_ss / h_n - mean * mean)) if h_n else 0.0
    now = utime.ticks_us()
    print('EB_END reason=%s max=%.2f over=%.2f hold_n=%d hold_mean=%.3f hold_sd=%.3f strokes=%d rm=%d sk10=%d sk20=%d late=%d miss=%d' % (
        reason, p_max, rise_max - target, h_n, mean, sd, strokes, removed, skips10, skips20, late, miss))
    await asyncio.sleep_ms(EU_PRINT_GAP_MS)
    if learned:
        brew_data.mains_T_us = clock.T      # kuri-kuvion jakso (TILAUS-M): viimeisin opittu verkkojakso
    print('EB_END2 windows=%d win_low=%d learned=%d T_us=%.3f hz=%.4f sd_us=%.0f eb_ff=%.2f eb_x=%.2f eb_g=%.2f eb_tau=%.2f coast_s=%.3f need=%.3f u_mean=%.2f kd=%.3f' % (
        windows, win_low, learned, clock.T, 1e6 / clock.T, clock.sd_us(now), getattr(brew_data, 'eb_ff', 0.0),
        getattr(brew_data, 'eb_x', 0.0), getattr(brew_data, 'eb_g', 0.0), getattr(brew_data, 'eb_tau', 0.0), coast_c, need,
        u_mean, kd))
    await asyncio.sleep_ms(EU_PRINT_GAP_MS)
    if c1x:
        late_max = cx[CL.CX_LMAX]
    print('EB_VV vv=%d stall=%d gc_n=%d gc_max_us=%d fr_end=%d k_max_us=%d s_max_us=%d y_max_us=%d late_max_us=%d' % (
        vv, stall_n, gc_n, gc_max, gc.mem_free() // 1024, k_max, s_max, y_max, late_max))
    if c1x:
        # Kuten EU_C1X, koko ajo (esiuutto + uutto). TS_ENDin max_loop_ms = ytimen 0 pisin kasittelyviive: c1x:lla jakson
        # vali nimellisista kohdista on aina ~20 ms, eika se kerro silmukan pysahdyksista
        await asyncio.sleep_ms(EU_PRINT_GAP_MS)
        print('EB_C1X n=%d gmax_us=%d ovf=%d nev=%d written=%d lmax_us=%d late=%d starve=%d lidx=%d lwr_us=%d '
              'lag_max_us=%d cyc_min=%d fill=%d' % (cx[CL.CX_N], cx[CL.CX_GMAX], cx[CL.CX_OVF], cx[CL.CX_NEV], cx[CL.CX_EW],
                                                   cx[CL.CX_LMAX], cx[CL.CX_LATE], cx[CL.CX_STARVE], cx[CL.CX_LIDX],
                                                   cx[CL.CX_LWR], lag_max, cyc_min, fill_n))
        return (b_slots, lag_max // 1000)
    return (b_slots, b_gap)


def _eu_end(brew_data, clock, now, reason, target, hold_t, l_s0, l_r0, strokes, removed, rate_cut, p_cut, g_cut, coast_s,
            coast_f, h_s, h_ss, h_n, dh_s, dh_n, p_max, rise_max, skips10, skips20, late, miss, windows, win_low, learned, kd):
    """Esiuuton oppi ja EU_END/EU_END2-rivit: ajon lopussa (pim:1) tai siirtymassa uuttoon (bim:1). Palauttaa
    (EU_END, EU_END2, opittiinko pidon tarve). Erillinen funktio eika sulkeuma: sulkeuman kaappaamat muuttujat olisivat
    silmukassa solumuuttujia (hitaampi haku joka jaksossa)."""
    import math
    # Pidon toteutunut duty ja katkaisun nousu antavat vuodon aikavakion jalkikateen: G*tau = tavoite/duty
    # ja G = rate + p/tau -> tau = (tavoite/duty - p) / rate. Vain lokiin (EU_TAU_S:n tarkistus ajoista).
    # Pidon tarve asettuneesta pidosta (>= 1 s EU_LEARN_SKIP_MS:n jalkeen): 5 s:n liukuva duty_avg jai ff:n
    # puolelle (26.9. b: ff 0,22, tarve ~0,09, duty_avg 0,14). Lyhyt pito ei korvaa edellista tietoa (26.9. c:
    # 2,3 s pito nollasi sen, ja seuraava ajo meni 1. ajon polkuun). Tallennus settings.txt:hen.
    # Tarve on toteutunut iskuosuus eika u:n keskiarvo (EXPRESSO-ESIUUTTO-UUTTOASENTO): delta-sigman kertyma rajataan
    # -1:een, joten heilunnan negatiiviset u:t painoivat keskiarvon alle iskuosuuden (laite af/ag: u 0,06 / 0,05,
    # iskut 0,19 / 0,14) ja seuraavan ajon ff ja tau vinoon. Tasaisessa pidossa ne ovat samat (ab 0,65 / 0,65).
    tau_obs, u_mean = 0.0, (dh_s / dh_n if dh_n else 0.0)
    l_n = (strokes - l_s0) + (removed - l_r0) if l_s0 is not None else 0
    ok = hold_t is not None and l_n >= 50
    if ok:
        need = (strokes - l_s0) / l_n
        brew_data.learned_ff_pre = min(0.9, max(0.05, need))
        brew_data.eu_g_pre = g_cut
        brew_data.set_setting_changed()
        if rate_cut is not None and rate_cut >= EU_RATE_MIN and need > 0.0:
            tau_obs = (target / need - p_cut) / rate_cut
        # Seuraavan ajon tau rajatusta tarpeesta (EXPRESSO-ESIUUTTO-AVOIN): raaka tarve voi olla ~0 (-1...1-delta-sigma,
        # laite u: tau_obs 180), ja rajatusta tau toistaa taman ajon ff:n, kun seuraava nousee samoin
        brew_data.eu_tau_pre = 0.0
        if g_cut > 0.0:
            brew_data.eu_tau_pre = min(30.0, max(0.1, (target / brew_data.learned_ff_pre - p_cut) / rate_cut))
    brew_data.eu_coast_s = coast_s
    brew_data.eu_coast_fast_s = coast_f
    mean = h_s / h_n if h_n else 0.0
    sd = math.sqrt(max(0.0, h_ss / h_n - mean * mean)) if h_n else 0.0
    l1 = 'EU_END reason=%s max=%.2f over=%.2f hold_n=%d hold_mean=%.3f hold_sd=%.3f strokes=%d rm=%d sk10=%d sk20=%d late=%d miss=%d' % (
        reason, p_max, rise_max - target, h_n, mean, sd, strokes, removed, skips10, skips20, late, miss)
    if learned:
        brew_data.mains_T_us = clock.T      # kuri-kuvion jakso (TILAUS-M): viimeisin opittu verkkojakso
    l2 = 'EU_END2 windows=%d win_low=%d learned=%d T_us=%.3f hz=%.4f sd_us=%.0f learned_ff_pre=%.2f coast_s=%.3f coast_f=%.3f tau_obs=%.2f u_mean=%.2f kd=%.3f' % (
        windows, win_low, learned, clock.T, 1e6 / clock.T, clock.sd_us(now), brew_data.learned_ff_pre, coast_s, coast_f,
        tau_obs, u_mean, kd)
    return l1, l2, ok


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
    brew_data.shot_peak_pressure = 0.0
    abort_reason = ''
    over = [0, 0]          # [consecutive samples over the limit, last sample timestamp]
    weight_start = brew_data.get_weight() if limit_weight else None

    def running():
        nonlocal abort_reason
        if abort_reason:
            return False
        p_cur = max(getattr(brew_data, 'pressure_filtered', 0.0), getattr(brew_data, 'pressure', 0.0))
        if p_cur > getattr(brew_data, 'shot_peak_pressure', 0.0):
            brew_data.shot_peak_pressure = p_cur
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

    # Kattilan lampotila lukee uuton ajan toinen ydin (EXPRESSO-TEMPSTALE-JA-OLETUS, classes.TemperatureSensor.c1_*):
    # uuttosilmukat eivat voi pysahtya MAX31865:n >= 75 ms:n lukuun, ja ilman lukemaa rele-vahti esti lammittimen
    # 10 s:n jalkeen (GUARD_TRIP heater reason=tempstale, 28.9.2026). Palautus finallyssa, ennen paasilmukan lukua.
    tsens = brew_data.temperature_sensor
    tsens.c1_on()
    # Wi-Fi hiljaiseksi koko pumppuajon ajaksi, myos testiuutossa (EXPRESSO-WIFI-AIKAIKKUNA 20.10.2026):
    # diagnet ja wifilink harventavat lahetyksensa, kun diag.in_shot() on tosi
    diag = getattr(brew_data, 'diag', None)
    if diag is not None:
        diag.quiet = True
    scale = getattr(brew_data, 'tray_scale', None)
    arm_drop = getattr(scale, 'arm_drop_detector', None)
    if arm_drop is not None:
        th = getattr(brew_data, 'get_pre_infusion_trigger_threshold', lambda: None)()
        arm_drop(threshold=th, blanking_ms=1800)
    # Uuttoloki (EXPRESSO-UUTTOLOKI): vain kytkimen uutto (PB), ei testiuutto. Naytteet ottaa BLE-tehtava
    # (brew_logger.brew_log_service), joten uuttosilmukoiden ajoitus ei muutu.
    brew_log = getattr(brew_data, 'brew_logger', None) if label == 'PB' else None
    if brew_log is not None:
        brew_log.start(start_time, brew_data.get_weight(), scale.scale_meta() if scale is not None else None)
    try:
        # ===== PRE-INFUSION ===== #
        # bim:1 (EXPRESSO-UUTTO-8BAR) = vaiheet 3-4 esiuuton jatkona samassa silmukassa: vain pim:1:n, paalla olevan
        # esiuuton ja painetilan (virtaustila pois) kanssa. Muuten vanha uuttosilmukka tavulleen ennallaan (bim:0 +
        # pim:1 = hyvaksytty esiuutto ja vanha uutto, A/B-vertailu).
        phased_brew = False
        # Edellisen uuton maksu tai oppi kesken (esim. kytkimen napautus heti uuton jalkeen, kahvi 21.10.2026 09.12):
        # summat jatkuvat, muuten oppi laskisi virheen vain uusimman ajon summasta (k 67,2 -> 70,5)
        th = getattr(brew_data, 'thermostat', None)
        if not (getattr(brew_data, 'bh_arm', 0) or (th is not None and th.bh_phase is not None)):
            brew_data.bh_credit_us = brew_data.bh_sum_us = 0.0
            brew_data.bh_nolearn = 0
        brew_data.bh_arm = 0
        if brew_data.get_pre_infusion_mode():
            # pim:1 = vaiheseurattu esiuutto (TILAUS-K 1-2); oletus 1 (EXPRESSO-TEMPSTALE-JA-OLETUS)
            if getattr(brew_data, 'pre_infusion_method', 0) == 1:
                phased_brew = getattr(brew_data, 'brew_method', 0) == 1 and not brew_data.get_flow_mode()
                st = await pre_infusion_phased(brew_data, utime, asyncio, pump_ratio_calculator, running,
                                               brew=phased_brew)
            else:
                await pre_infusion(brew_data, utime, asyncio, pump_ratio_calculator, running)

        if phased_brew:
            # Uutto ajettiin pre_infusion_phased:ssa (vaiheet 3-4). Sama <label>_END-rivi kuin vanhalla polulla
            # (pico_dev.py shot pysahtyy siihen): loops = jaksot, max_loop_ms = pisin jaksovali. learned_ff_brew on
            # vanhan saatimen arvo, tama polku ei muuta sita. Kattilan lampotila luetaan kerran nyt, pumppu pois
            # (MAX31865 blokkaa >= 75 ms, joten sita ei lueta vaiheissa 3-4).
            brew_data.get_boiler_temperature()
            print('%s_END loops=%d max_loop_ms=%d reason=%s learned_ff_brew=%.2f %s' % (
                label, st[0], st[1], abort_reason or 'stopped', brew_data.learned_ff_brew, tsens.c1_log()))
        else:
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
            print('%s_END loops=%d max_loop_ms=%d reason=%s learned_ff_brew=%.2f %s' % (
                label, loops, max_loop_ms, abort_reason or 'stopped', brew_data.learned_ff_brew, tsens.c1_log()))

        # Uuton jalkeinen lammitys (classes.Thermostat BH_*): 1 = jaannoksen maksu ja oppi, 2 = vain maksu
        # (keskeytys tai vanha uuttosilmukka, jonka iskut eivat kerryta)
        if brew_data.bh_sum_us > 0.0:
            if not phased_brew or abort_reason: brew_data.bh_nolearn = 1
            st = getattr(brew_data, 'bh_steam_t', None)
            if st is not None and utime.ticks_diff(utime.ticks_ms(), st) < BH_STEAM_NOLEARN_MS: brew_data.bh_nolearn = 1
            brew_data.bh_arm = 2 if getattr(brew_data, 'bh_nolearn', 0) else 1
            print('BH_END sum_ms=%d left_ms=%d k=%.1f arm=%d fill=%d' % (
                brew_data.bh_sum_us // 1000, brew_data.bh_credit_us // 1000, getattr(brew_data, 'brew_heat_k', BH_K0_MS),
                brew_data.bh_arm, getattr(brew_data, 'bh_fill_n', -1)))

        # ===== PRESSURE SOFT RELEASE ===== #
        RELAY_PUMP.value(0)
        brew_data.set_pump_ratio(0)
        log_reason = 'abort' if abort_reason else 'switch_off'
        if brew_data.get_pressure() >= brew_data.get_soft_pressure_release_arming_pressure() and brew_data.get_pressure_soft_release_mode():
            brew_data.set_mode('soft pressure release')
            soft_pressure_release_time = brew_data.get_pressure_soft_release_time()
            print("soft release time: " + str(soft_pressure_release_time))
            # App slider sends fractional seconds (srt:), range() would raise TypeError
            await asyncio.sleep_ms(int(float(soft_pressure_release_time) * 1000))
            log_reason = 'spr_end'

        # ===== PRESSURE DRAIN ===== #
        # Loki loppuu ennen kuin solenoidi purkaa ryhman paineen kaukaloon (elokuun brew_logger)
        if brew_log is not None and brew_log.is_active():
            brew_log.end_session(utime.ticks_ms(), brew_data.get_weight(), log_reason)
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
        tsens.c1_off()
        if diag is not None:
            diag.quiet = False
        if brew_log is not None and brew_log.is_active():
            brew_log.end_session(utime.ticks_ms(), brew_data.get_weight(), 'error')
        reset_drop = getattr(scale, 'reset_drop_detector', None)
        if reset_drop is not None:
            reset_drop()
    try:
        dur_ms = utime.ticks_diff(utime.ticks_ms(), start_time)
        peak_p = getattr(brew_data, 'shot_peak_pressure', 0.0)
        if hasattr(brew_data, 'record_brew_completed'):
            brew_data.record_brew_completed(utime.ticks_ms(), peak_p, dur_ms)
    except Exception:
        pass
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
# KURISTIMEN SAATOTILA (kuri:1)
# ============================================================================

KURI_FILT_TAU = 1.0          # s: mittarin kaltainen keskiarvo kayttajan tavoitteelle
KURI_CYCLES = 50             # iskut jaetaan tasaisesti 50 jakson (1 s) kehykseen
# Vaihelukittu kytkenta (kuri6, kayttaja 28.9.2026: "pumppu teki ylimaaraisia iskuja ja jatti valista ... kytkenta tapahtuu
# vaarassa kohtaa"). SSR on nollaylityskytkeva ja pumppu iskee vain aktiivisella puolijaksolla, joten isku tapahtuu, jos
# releen ohjaus on paalla aktiivisen puolijakson alkavassa nollakohdassa Z. vsweep-a: Z = kellon reuna + ~18,6 ms
# (10 ms tauon poistava lohko 8,5-18,7 ms). Paatos jakson Z:lle tehdaan Z - 10 ms:ssa = reuna + 8,6 ms, jolloin se saa
# myohastya tai aikaistua ~10 ms vaihtamatta iskua. kuri2-5 kytkivat mielivaltaisessa vaiheessa: reuna lahella Z:aa ja
# 15-28 ms keruu tai tehtavan vuoro -> isku tuplaantui tai jai pois.
KURI_OFF_US = EU_OFF_US - 5000       # 8 600 us kellon reunasta
KURI_PHASE_OK_US = 5000      # 2,5 x kellon sd alle taman -> kuvio kayttoon; siihen asti taysi sykli (ei kytkentoja)
KURI_ERR_US = 9000           # paatos yli taman myohassa voi vaihtaa iskun -> err
KURI_GC_SLOTS = 15           # hallittu keruu joka 15. paatoskohdassa (~300 ms, vrt. EU_GC_MS)
KURI_PRINT_SLOTS = 10        # KURI-rivi joka 10. paatoskohdassa (~200 ms)
KURI_SKIP_US = 2000          # raskas tyo vain ajallaan olleen paatoksen jalkeen: myohastymat eivat kasaannu


async def throttle_set_run(brew_data, utime, asyncio, pump_ratio_calculator, switch_on):
    """Kuristimen saatotila (kayttaja 28.9.2026, KAYTTAJAN-TIEDOT TILAUS-M): kun kuri:<n> on paalla, uuttonappi ajaa
    pumppua n iskua sekunnissa (1-50, tasaisesti 50 jaksolle) ilman paineensaatoa niin kauan kuin nappi on paalla, ja
    kayttaja kaantaa kuristimen annettuun paineeseen.

    Kytkenta on lukittu verkon vaiheeseen kuten uutossa (TILAUS-A/B/J): Verkkokello oppii vaiheen paineen vareilysta.
    Ennen lukitusta pumppu kay taydella syklilla (ei kytkentoja, joten ei vaaria iskuja); kun 2,5 sd < KURI_PHASE_OK_US,
    jokainen paatos tehdaan kohdassa kellon reuna + KURI_OFF_US (positiivisten nollakohtien puolivali). Paatoskohdan
    jalkeen tehdaan yksi raskas tyo: kellon ikkunan sulku, hallittu keruu tai yksi asyncio-vuoro (ja tulostus); kukin
    mahtuu ~10 ms toleranssiin. err = paatokset yli KURI_ERR_US myohassa (voivat vaihtaa iskun).

    Alussa ja lopussa purkusykli (_mcal_vent, TILAUS-H): loukkuun jaanyt paine esti kuri4:n jalkeisen kaynnistyksen.
    Rajat: kaukalovahti (wmax), raaka paine PCAP_OVER_BAR ja dev_safe; releen vartio toimii kuten aina. Lammitin pois."""
    from verkkokello import Verkkokello
    RELAY_PUMP, RELAY_SOLENOID, RELAY_HEATER = brew_data.get_relays()
    sensor = brew_data.pressure_sensor.pressure_sensor
    gain = brew_data.pressure_sensor.gain
    offset = brew_data.pressure_sensor.offset
    RELAY_HEATER.value(0)
    reason = 'switch'
    p_filt = p_max = raw_max = 0.0
    strokes = err = late_max = windows = learned = n_slot = 0
    lock_ms = -1
    clock = None
    rate = min(KURI_CYCLES, max(1, int(getattr(brew_data, 'throttle_set', 25))))
    start = utime.ticks_ms()
    tray_state, tray_reason = tray_guard_start(brew_data, utime)
    if tray_reason:
        reason = tray_reason
    else:
        brew_data.set_mode('KURI')
        relay = [False]

        def set_relay(on):
            if on != relay[0]:
                relay[0] = on
                RELAY_PUMP.value(1 if on else 0)
                if on: pump_ratio_calculator.set_pump_on()
                else: pump_ratio_calculator.set_pump_off()

        try:
            RELAY_PUMP.value(0)
            _cycles, vent_bar = await _mcal_vent(brew_data, utime, asyncio, sensor, gain, offset)
            print('KURI_START rate=%d off_us=%d wmax=%.0f w=%.1f vent_bar=%.2f' % (
                rate, KURI_OFF_US, brew_data.get_weight_limit(), brew_data.get_weight(), vent_bar))
            # Venttiili ennen pumppua kuten klamp: paine nousee vain kuristimen kautta.
            RELAY_SOLENOID.value(1)
            gc.collect()
            t0 = utime.ticks_us()
            clock = Verkkokello(t0)
            clock.iq_start(t0)
            set_relay(True)               # taysi sykli, kunnes kello on lukittu
            slot = utime.ticks_add(t0, 20000)
            next_s = t0
            cyc_s, cyc_n, p = 0.0, 0, 0.0
            phase_ok, iq_due, gc_due, pr_due, j = False, False, False, False, 0
            while True:
                now = utime.ticks_us()
                if utime.ticks_diff(slot, now) < PCAP_RATE_US:
                    while utime.ticks_diff(slot, utime.ticks_us()) > 0:
                        pass
                    t = utime.ticks_us()
                    lag = utime.ticks_diff(t, slot)
                    # Paatos heti (seuraava Z): kaikki laskenta vasta taman jalkeen
                    if phase_ok:
                        on = (j + 1) * rate // KURI_CYCLES > j * rate // KURI_CYCLES
                        j += 1
                        if lag > late_max: late_max = lag
                        if lag > KURI_ERR_US: err += 1
                    else:
                        on = True
                    set_relay(on)
                    if on: strokes += 1
                    n_slot += 1
                    if cyc_n:
                        p = cyc_s / cyc_n
                    cyc_s, cyc_n = 0.0, 0
                    p_filt += (p - p_filt) * min(1.0, 0.02 / KURI_FILT_TAU)
                    if p_filt > p_max: p_max = p_filt
                    brew_data.pressure = p
                    brew_data.pressure_filtered = p_filt
                    if not switch_on():
                        reason = 'switch'; break
                    if brew_data.dev_safe:
                        reason = 'devsafe'; break
                    tray_reason = tray_guard_check(brew_data, utime, tray_state)
                    if tray_reason:
                        reason = tray_reason; break
                    # Seuraava paatoskohta: lukittuna kellon reunasta (nimellisesta kohdasta, ei myohastyneesta t:sta)
                    if not phase_ok and 2.5 * clock.sd_us(t) < KURI_PHASE_OK_US:
                        phase_ok = True
                        lock_ms = utime.ticks_diff(utime.ticks_ms(), start)
                    if phase_ok:
                        nxt = utime.ticks_add(clock.edge(utime.ticks_add(slot, round(clock.T) - KURI_OFF_US)), KURI_OFF_US)
                        while utime.ticks_diff(nxt, slot) < EU_MIN_SLOT_US:
                            nxt = utime.ticks_add(nxt, round(clock.T))
                    else:
                        nxt = utime.ticks_add(slot, round(clock.T))
                    slot = nxt
                    # Yksi raskas tyo paatoskohdan jalkeen, vain jos paatos oli ajallaan (muuten seuraavassa kohdassa)
                    if n_slot % KURI_GC_SLOTS == 0:
                        gc_due = True
                    if n_slot % KURI_PRINT_SLOTS == 0:
                        pr_due = True
                    if lag > KURI_SKIP_US:
                        pass
                    elif iq_due:
                        iq_due = False
                        res = clock.iq_close(t, learn=True)
                        clock.iq_start(utime.ticks_us())
                        if res is not None:
                            windows += 1
                            if res[3] == 0: learned += 1
                    elif gc_due:
                        gc_due = False
                        gc.collect()
                    else:
                        if pr_due:
                            pr_due = False
                            print('KURI t=%d bar=%.2f filt=%.2f w=%.1f n=%d lock=%d sd=%d err=%d lmax=%d' % (
                                utime.ticks_diff(utime.ticks_ms(), start), p, p_filt, brew_data.get_weight() or 0.0,
                                strokes, 1 if phase_ok else 0, clock.sd_us(t), err, late_max))
                        await asyncio.sleep_ms(0)
                    continue
                if utime.ticks_diff(now, next_s) >= 0:
                    next_s = utime.ticks_add(next_s, PCAP_RATE_US)
                    if utime.ticks_diff(now, next_s) > 0: next_s = utime.ticks_add(now, PCAP_RATE_US)
                    bar = gain * (sensor.read_u16() * PCAP_RAW_A + PCAP_RAW_B) + offset
                    if bar > raw_max: raw_max = bar
                    if bar > PCAP_OVER_BAR:
                        reason = 'overpressure'; break
                    cyc_s += bar; cyc_n += 1
                    clock.iq_add(now, bar)
                    if clock.iq_ready(now): iq_due = True
        except Exception as e:
            reason = 'error'
            print('KURI_ERROR %s' % e)
        finally:
            RELAY_PUMP.value(0)
            relay[0] = False
            pump_ratio_calculator.set_pump_off()
            # Purku lopuksi (kayttaja 28.9.2026: loukkuun jaanyt paine esti seuraavan saadon)
            try:
                await _mcal_vent(brew_data, utime, asyncio, sensor, gain, offset)
            except Exception:
                pass
            RELAY_SOLENOID.value(0)
    if clock is not None and learned:
        brew_data.mains_T_us = clock.T
    print('KURI_END reason=%s filt=%.2f filt_max=%.2f raw_max=%.2f n=%d lock_ms=%d win=%d learned=%d err=%d lmax=%d ms=%d' % (
        reason, p_filt, p_max, raw_max, strokes, lock_ms, windows, learned, err, late_max,
        utime.ticks_diff(utime.ticks_ms(), start)))
    # Raja laukesi napin ollessa yha paalla: odota vapautusta, ettei uuttopolku kaynnisty heti peraan.
    while switch_on():
        await asyncio.sleep_ms(50)
    brew_data.set_mode('IDLE')


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
        'pre_infusion_trigger_mode' : getattr(brew_data, 'get_pre_infusion_trigger_mode', lambda: False)(),
        'pre_infusion_trigger_threshold': getattr(brew_data, 'get_pre_infusion_trigger_threshold', lambda: 0.25)(),
        'idle_pressure_equalize_mode': getattr(brew_data, 'get_idle_pressure_equalize_mode', lambda: False)(),
        'pressure_soft_release_mode': pressure_soft_release_mode,
        'fast_heatup_mode'          : fast_heatup_mode,
        'brew_pressure'             : brew_pressure,
        'pre_infusion_pressure'     : pre_infusion_pressure,
        'steam_pressure_low'        : getattr(brew_data, 'get_steam_valve_trigger', lambda: getattr(brew_data, 'steam_pressure_low', 1.8))(),
        'steam_valve_trigger'       : getattr(brew_data, 'get_steam_valve_trigger', lambda: getattr(brew_data, 'steam_valve_trigger', 1.8))(),
        'steam_valve_release'       : getattr(brew_data, 'get_steam_valve_release', lambda: getattr(brew_data, 'steam_valve_release', 2.1))(),
        'steam_pressure_high'       : getattr(brew_data, 'get_steam_pressure_high', lambda: getattr(brew_data, 'steam_pressure_high', 2.5))(),
        'steam_temperature_max'     : getattr(brew_data, 'get_steam_temperature_max', lambda: 140.0)(),
        # Test-shot weight limits (18.9.2026). Persisted after all: they are read only when
        # run_shot gets limit_weight=True, which happens for tshot and never for the brew switch,
        # so a stored limit cannot affect a real shot. Not persisting them meant the protection was
        # silently off after every restart and flash - a memory burden on the user, not a safeguard.
        'weight_limit'              : brew_data.get_weight_limit(),
        'weight_rise_limit'         : brew_data.get_weight_rise_limit(),
        # Esiuuton opittu pidon tarve, G ja jalkinousu (EXPRESSO-ESIUUTTO-FF 26.9.2026): ilman niita
        # jokainen kaynnistyksen tai flashin jalkeinen ajo on 1. ajo, joka yliarvioi (laite 26.9. c/d: 2,73-2,76 bar)
        'eu_ff_pre'                 : brew_data.learned_ff_pre,
        'eu_g_pre'                  : brew_data.eu_g_pre,
        'eu_tau_pre'                : brew_data.eu_tau_pre,
        'eu_coast_s'                : brew_data.eu_coast_s,
        'eu_coast_fast_s'           : brew_data.eu_coast_fast_s,
        # Uuton opitut arvot omilla avaimillaan (EXPRESSO-UUTTO-8BAR 27.9.2026), eivat koske esiuuton arvoihin
        'eb_ff'                     : getattr(brew_data, 'eb_ff', 0.0),
        'eb_x'                      : getattr(brew_data, 'eb_x', 0.0),
        'eb_g'                      : getattr(brew_data, 'eb_g', 0.0),
        'eb_tau'                    : getattr(brew_data, 'eb_tau', 0.0),
        'eb_coast_s'                : getattr(brew_data, 'eb_coast_s', EB_COAST_S0)
    }
    
    # Save data to file in json format atomically (tmp + rename)
    # A crash or reset mid-write must not corrupt or truncate settings.txt (wmax-pysyvyys)
    tmp_filename = 'settings.txt.tmp'
    filename = 'settings.txt'
    try:
        with open(tmp_filename, 'w') as file:
            json_module.dump(data, file)
        try:
            os.rename(tmp_filename, filename)
        except OSError:
            try:
                os.remove(filename)
            except OSError:
                pass
            os.rename(tmp_filename, filename)
    except Exception as e:
        print('save_settings failed: %r' % e)
        return False
    
    print("save_settings")
    return True


# ============================================================================
# LOAD SETTINGS
# ============================================================================

def load_settings(json_module, brew_data):
    filename = 'settings.txt'
    tmp_filename = 'settings.txt.tmp'
    data = None
    
    # Try reading settings.txt first; fall back to settings.txt.tmp if missing or corrupted
    try:
        with open(filename, 'r') as file:
            data = json_module.load(file)
    except (OSError, ValueError, Exception) as e:
        # If settings.txt is missing or corrupted, check if a valid settings.txt.tmp exists
        print('settings.txt could not be loaded: %r' % e)
        try:
            with open(tmp_filename, 'r') as file:
                candidate = json_module.load(file)
            if isinstance(candidate, dict):
                data = candidate
                print('settings.txt: recovered from %s' % tmp_filename)
                try:
                    os.rename(tmp_filename, filename)
                except OSError:
                    try:
                        os.remove(filename)
                    except OSError:
                        pass
                    try:
                        os.rename(tmp_filename, filename)
                    except OSError:
                        pass
        except Exception:
            pass
    
    if not isinstance(data, dict):
        # We NEVER delete settings.txt on error! Keep file intact to avoid losing limits/settings (wmax-pysyvyys)
        print('settings.txt: no valid data loaded, keeping defaults (file preserved)')
        return False
    
    # Set settings to brew_data object safely
    brew_temperature           = data.get('brew_temperature')
    steam_temperature          = data.get('steam_temperature')
    pre_infusion_time          = data.get('pre_infusion_time')
    pressure_soft_release_time = data.get('pressure_soft_release_time')
    pre_infusion_mode          = data.get('pre_infusion_mode')
    pressure_soft_release_mode = data.get('pressure_soft_release_mode')
    fast_heatup_mode           = data.get('fast_heatup_mode')

    # A setpoint over SETPOINT_MAX_C keeps its default; it must not take the whole file (and wmax) with it
    for setter, value in ((brew_data.set_brew_temperature, brew_temperature),
                          (brew_data.set_steam_temperature, steam_temperature)):
        if value is not None:
            try:
                setter(value)
            except ValueError as e:
                print('settings.txt: %s, default kept' % e)
    if pre_infusion_time is not None:
        try:
            brew_data.set_pre_infusion_time(pre_infusion_time)
        except Exception as e:
            print('settings.txt pre_infusion_time: %s' % e)
    if pressure_soft_release_time is not None:
        try:
            brew_data.set_pressure_soft_release_time(pressure_soft_release_time)
        except Exception as e:
            print('settings.txt pressure_soft_release_time: %s' % e)
    if pre_infusion_mode is not None:
        try:
            brew_data.set_pre_infusion_mode(pre_infusion_mode)
        except Exception as e:
            print('settings.txt pre_infusion_mode: %s' % e)
    if pressure_soft_release_mode is not None:
        try:
            brew_data.set_pressure_soft_release_mode(pressure_soft_release_mode)
        except Exception as e:
            print('settings.txt pressure_soft_release_mode: %s' % e)
    if fast_heatup_mode is not None:
        try:
            brew_data.set_fast_heatup_mode(fast_heatup_mode)
        except Exception as e:
            print('settings.txt fast_heatup_mode: %s' % e)
    
    # Pressures were added 17.9.2026: older settings.txt has no keys -> keep defaults
    if data.get('brew_pressure') is not None:
        try:
            brew_data.set_brew_pressure(data.get('brew_pressure'))
        except Exception as e:
            print('settings.txt brew_pressure: %s' % e)
    if data.get('pre_infusion_pressure') is not None:
        try:
            brew_data.set_pre_infusion_pressure(data.get('pre_infusion_pressure'))
        except Exception as e:
            print('settings.txt pre_infusion_pressure: %s' % e)
    p_trig = data.get('steam_valve_trigger', data.get('steam_pressure_low'))
    if p_trig is not None and hasattr(brew_data, 'set_steam_valve_trigger'):
        try:
            brew_data.set_steam_valve_trigger(p_trig)
        except Exception as e:
            print('settings.txt steam_valve_trigger: %s' % e)
    elif p_trig is not None and hasattr(brew_data, 'set_steam_pressure_low'):
        try:
            brew_data.set_steam_pressure_low(p_trig)
        except Exception as e:
            print('settings.txt steam_pressure_low: %s' % e)
    if data.get('steam_valve_release') is not None and hasattr(brew_data, 'set_steam_valve_release'):
        try:
            brew_data.set_steam_valve_release(data.get('steam_valve_release'))
        except Exception as e:
            print('settings.txt steam_valve_release: %s' % e)
    if data.get('steam_pressure_high') is not None and hasattr(brew_data, 'set_steam_pressure_high'):
        try:
            brew_data.set_steam_pressure_high(data.get('steam_pressure_high'))
        except Exception as e:
            print('settings.txt steam_pressure_high: %s' % e)
    if data.get('steam_temperature_max') is not None and hasattr(brew_data, 'set_steam_temperature_max'):
        try:
            brew_data.set_steam_temperature_max(data.get('steam_temperature_max'))
        except Exception as e:
            print('settings.txt steam_temperature_max: %s' % e)
    # Weight limits added 18.9.2026: same rule, a file without the keys keeps the defaults (off)
    if data.get('weight_limit') is not None:
        try:
            brew_data.set_weight_limit(data.get('weight_limit'))
        except Exception as e:
            print('settings.txt weight_limit: %s' % e)
    if data.get('weight_rise_limit') is not None:
        try:
            brew_data.set_weight_rise_limit(data.get('weight_rise_limit'))
        except Exception as e:
            print('settings.txt weight_rise_limit: %s' % e)
    # Esiuuton opitut arvot 26.9.2026: sama saanto
    if data.get('pre_infusion_trigger_mode') is not None and hasattr(brew_data, 'set_pre_infusion_trigger_mode'):
        try:
            brew_data.set_pre_infusion_trigger_mode(data.get('pre_infusion_trigger_mode'))
        except Exception as e:
            print('settings.txt pre_infusion_trigger_mode: %s' % e)
    if data.get('pre_infusion_trigger_threshold') is not None and hasattr(brew_data, 'set_pre_infusion_trigger_threshold'):
        try:
            brew_data.set_pre_infusion_trigger_threshold(data.get('pre_infusion_trigger_threshold'))
        except Exception as e:
            print('settings.txt pre_infusion_trigger_threshold: %s' % e)
    if data.get('idle_pressure_equalize_mode') is not None and hasattr(brew_data, 'set_idle_pressure_equalize_mode'):
        try:
            brew_data.set_idle_pressure_equalize_mode(data.get('idle_pressure_equalize_mode'))
        except Exception as e:
            print('settings.txt idle_pressure_equalize_mode: %s' % e)
    if data.get('eu_ff_pre') is not None:
        brew_data.learned_ff_pre = data.get('eu_ff_pre')
    if data.get('eu_g_pre') is not None:
        brew_data.eu_g_pre = data.get('eu_g_pre')
    if data.get('eu_tau_pre') is not None:
        brew_data.eu_tau_pre = data.get('eu_tau_pre')
    if data.get('eu_coast_s') is not None:
        brew_data.eu_coast_s = data.get('eu_coast_s')
    if data.get('eu_coast_fast_s') is not None:
        brew_data.eu_coast_fast_s = data.get('eu_coast_fast_s')
    # Uuton opitut arvot 27.9.2026 (EXPRESSO-UUTTO-8BAR): sama saanto, vanha tiedosto -> oletukset
    for key in ('eb_ff', 'eb_x', 'eb_g', 'eb_tau', 'eb_coast_s'):
        if data.get(key) is not None:
            setattr(brew_data, key, data.get(key))
    
    print('Loaded settings: brew_temperature, steam_temperature, pre_infusion_time, pressure_soft_release_time, pre_infusion_mode, pressure_soft_release_mode, fast_heatup_mode')
    return True







# Hot water switch limit: run ends after this many ms (käyttäjä 7.10.2026, TURVAKATO kohta 4)
HOT_WATER_MAX_MS = 1000


async def hot_water_run(brew_data, thermostat, utime, asyncio):
    """Hot water switch loop. The thermostat drives the heater; the run ends on time or when the
    relay guard cuts the pump. Returns the end reason: 'time', 'pump' or 'switch'."""
    RELAY_PUMP, RELAY_SOLENOID, RELAY_HEATER = brew_data.get_relays()
    SWITCH_BREW, SWITCH_WATER, SWITCH_STEAM  = brew_data.get_switches()

    brew_data.set_mode('WATER')
    RELAY_PUMP.value(1)

    # The temperature is read at least once a second so the relay guard's heater limits see a
    # fresh value (EXPRESSO-TURVA-TOIMILAITE, 22.9.2026)
    start = utime.ticks_ms()
    brew_data.get_boiler_temperature()
    last_temperature_read = start
    reason = None
    while (SWITCH_WATER.value()):
        now = utime.ticks_ms()
        if utime.ticks_diff(now, last_temperature_read) >= 1000:
            brew_data.get_boiler_temperature()
            last_temperature_read = now
        if reason is None:
            if utime.ticks_diff(now, start) >= HOT_WATER_MAX_MS:
                reason = 'time'
            elif RELAY_PUMP.value() == 0:
                reason = 'pump'
            else:
                thermostat.run()
            if reason is not None:
                RELAY_PUMP.value(0)
                RELAY_HEATER.value(0)
                print('HOT_WATER_END reason=%s' % reason)
        await asyncio.sleep_ms(50)

    RELAY_PUMP.value(0)
    RELAY_HEATER.value(0)
    brew_data.note_activity(utime.ticks_ms(), 'switch')
    return reason or 'switch'
