# ============================================================================
# YSTALL — asyncio-vuoron katkot ilman pumppua (EXPRESSO-GC-UUTTO, 20.10.2026)
# ============================================================================
# Testiuutoissa b ja c (28c6685) EU-silmukan vuoro (sleep_ms(0)) kesti ~60 ms 500 ms:n ruudukossa, task=-:0, eli
# yksikaan tehtava ei ollut kaynnissa; ajossa a ja ennen muutosta ei. Tama toistaa uuton vuororakenteen ilman
# releita: silmukka pyorii 1 ms:n tahdissa ja antaa vuoron kuten EU-silmukka, ja bitit valitsevat ymparistön:
#   1 = DIAGNET uuttotahdissa (diag.quiet, 500 ms, taydet paketit) kuten run_shot
#   2 = hallittu gc.collect() 300 ms valein kuten EU_GC_MS
#   4 = DIAGNETin vanha lahetys (take + head + data) A/B-vertailuun
#   8 = releen vahdin kutsu (Timer -1, 100 ms) palaa heti ajon ajan (kayttajan lupa 20.10.2026; dev_run on jo
#       sammuttanut lammittimen eika pumppu kay). Ajastin jaa kayntiin: uusi Timer(-1) voi saada ENOMEMin, kun
#       ytimen 1 silmukka kay (main.py, 5.10.2026), joten pysaytys ja uudelleenkaynnistys ei ole turvallinen.
#  16 = Wi-Fi-radio pois ajon ajan (wlan.active(False), kayttaja 20.10.2026): erottaa cyw43/lwIP:n osuuden levon
#       100 ms:n porraskeruista. Sarjalinkki (Zero) ei kayta radiota; DIAGNET liittyy uudelleen itse (_join).
#  32 = ydin 1 lukee lampotilaa kuten uutossa (TemperatureSensor.c1_on/c1_off, sama kuin run_shot): levossa ydin 1
#       nukkuu 2 ms:n silmukassa, uutossa se lukee, ja uutossa keruu on ~19 ms, levossa 80-600 ms (20.10.2026)
# Rivit: YSTALL (vuoro > YS_LOG_US), YS_GC (keruu > YS_LOG_US), YSTALL_END (yhteenveto). Releisiin ei kosketa.

import gc

YS_LOG_US = 10000
YS_GC_MS = 300
YS_TICK_US = 1000


async def ystall_run(brew_data, utime, asyncio, seconds, mode):
    import diagnet
    diag = getattr(brew_data, 'diag', None)
    tb = getattr(brew_data, 'tbusy', None)
    quiet0, legacy0 = (diag.quiet if diag is not None else False), diagnet.LEGACY_SEND
    if diag is not None and mode & 1:
        diag.quiet = True
    diagnet.LEGACY_SEND = bool(mode & 4)
    guard = getattr(brew_data, 'relay_guard', None)
    guard_off = False
    if mode & 8 and guard is not None:
        guard.paused = True
        guard_off = True
    wlan = getattr(diag, 'wlan', None) if diag is not None else None
    radio_off = False
    if mode & 16 and wlan is not None:
        wlan.active(False)
        radio_off = True
    tsens = getattr(brew_data, 'temperature_sensor', None)
    c1_run = False
    if mode & 32 and tsens is not None:
        c1_run = bool(tsens.c1_on())
    t0 = utime.ticks_us()
    end = utime.ticks_add(t0, int(seconds * 1000000))
    gc_t = t0
    n = y10 = y50 = y_max = gc_n = gc_max = 0
    print('YSTALL_START s=%d mode=%d free=%d' % (seconds, mode, gc.mem_free()))
    try:
        while utime.ticks_diff(end, utime.ticks_us()) > 0:
            if tb is not None:
                tb[0] = '-'
                tb[1] = 0
            c0 = utime.ticks_us()
            await asyncio.sleep_ms(0)
            c1 = utime.ticks_diff(utime.ticks_us(), c0)
            n += 1
            if c1 > y_max:
                y_max = c1
            if c1 > YS_LOG_US:
                y10 += 1
                if c1 > 50000:
                    y50 += 1
                print('YSTALL t_ms=%d us=%d task=%s:%d' % (utime.ticks_diff(c0, t0) // 1000, c1,
                                                          tb[0] if tb is not None else '?', tb[1] if tb is not None else 0))
            if mode & 2 and utime.ticks_diff(utime.ticks_us(), gc_t) >= YS_GC_MS * 1000:
                g0 = utime.ticks_us()
                gc.collect()
                gc_t = utime.ticks_us()
                g1 = utime.ticks_diff(gc_t, g0)
                gc_n += 1
                if g1 > gc_max:
                    gc_max = g1
                if g1 > YS_LOG_US:
                    print('YS_GC t_ms=%d us=%d' % (utime.ticks_diff(g0, t0) // 1000, g1))
            # EU-silmukan tapaan pyoritaan seuraavaan naytteeseen asti (1 kHz), vuoro vasta sen jalkeen
            nxt = utime.ticks_add(utime.ticks_us(), YS_TICK_US)
            while utime.ticks_diff(nxt, utime.ticks_us()) > 0:
                pass
    finally:
        if c1_run:
            tsens.c1_off()
        if guard_off:
            guard.paused = False
        if radio_off:
            try:
                wlan.active(True)
                diag._join(utime.ticks_ms())
            except Exception:
                pass
        if diag is not None:
            diag.quiet = quiet0
        diagnet.LEGACY_SEND = legacy0
    print('YSTALL_END s=%d mode=%d n=%d y10=%d y50=%d y_max_us=%d gc_n=%d gc_max_us=%d free=%d guard_off=%d radio_off=%d c1=%d' % (
        seconds, mode, n, y10, y50, y_max, gc_n, gc_max, gc.mem_free(), 1 if guard_off else 0, 1 if radio_off else 0,
        1 if c1_run else 0))
