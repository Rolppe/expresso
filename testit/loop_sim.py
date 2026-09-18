# Compare old vs new brew-loop pump control timing on simple pressure plants.
# Timing from the code: temp read 80 ms (10+65 ms sleep + SPI), pressure read 17 ms (old) / 20 ms (new),
# old loop sleep 50 ms, old pulse 35 ms, BLE task every 200 ms: old reads pressure+temp (97 ms), new 0.
import math
def plant_step(p, pump, dt, P):
    if pump: target, tau = P['pmax'], P['tau_up']
    else: target, tau = 0.0, P['tau_down']
    return p + (target - p) * (1 - math.exp(-dt / tau))

def run(kind, P, target=9.0, T=25.0):
    t = 0.0; p = 0.0; pump = 0; trace = []; next_ble = 0.2; dt = 0.001
    def advance(sec):
        nonlocal t, p
        n = int(round(sec / dt))
        for _ in range(n):
            p = plant_step(p, pump, dt, P); t += dt
            if t >= 3.0: trace.append(p)   # skip ramp-up
    def ble():
        nonlocal next_ble
        if t >= next_ble:
            next_ble += 0.2
            if kind == 'old': advance(0.017 + 0.080)
    while t < T:
        if kind == 'old':
            advance(0.080)                       # get_boiler_temperature
            advance(0.017); meas = p             # get_pressure
            if meas < target - 1: pump = 1
            elif meas < target:
                pump = 1; advance(0.035); pump = 0
            else: pump = 0
            ble(); advance(0.050); ble()
        else:
            advance(0.020); meas = p             # get_pressure (20 ms window)
            if meas < target - 0.15: pump = 1
            elif meas >= target + 0.15: pump = 0
            ble(); advance(0.001)                # sleep_ms(0) + loop overhead
    return min(trace), max(trace), sum(trace)/len(trace)

plants = {
  'puck (tau_up 0.8 s, tau_down 3 s)':  dict(pmax=13.0, tau_up=0.8, tau_down=3.0),
  'fine puck (tau_up 0.5 s, down 6 s)': dict(pmax=13.0, tau_up=0.5, tau_down=6.0),
  'fast (tau_up 0.3 s, down 1.2 s)':    dict(pmax=13.0, tau_up=0.3, tau_down=1.2),
}
for name, P in plants.items():
    for kind in ('old', 'new'):
        mn, mx, avg = run(kind, P)
        print('%-36s %-3s  min %.1f  max %.1f  avg %.2f bar (target 9.0, t>3 s)' % (name, kind, mn, mx, avg))
