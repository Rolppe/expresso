# VIRTAUSSAATO-2 — toteutuksen sopimus

Perustelut paketissa `paketit/VIRTAUSSAATO-2.md`. Rivinumerot viittaavat commitiin `4c18f62`.
Tämä korvaa `VIRTAUSSAATO.spec.md`:n luvut 1, 3 ja 6; luvut 2, 4 ja 5 (BrewData, komennot,
`TS_START`) jäävät voimaan sellaisinaan.

## 1. `FlowController` (`pico/classes.py:770-848`) — duty-säätimeksi

```python
class FlowController:
    def __init__(self, utime, target, duty_start, kp=0.03, ki=0.08, p_max=10.5, p_margin=1.0,
                 update_ms=100, stale_limit=3):
```

Tila: `duty = float(duty_start)`, `e_prev = None`, `stale = 0`, `failed = False`, `sat_ms = 0.0`,
`saturated = False`, `last_update = utime.ticks_ms()`. `set_target` ennallaan.

`update(self, flow, pressure)` palauttaa dutyn 0–1 tai `None`:

1. `failed` → `None`. Ohitus `update_ms` ennen edellistä → palauta `self.duty`.
2. `dt` kuten ennen (katkaisu 0,5 s). `flow is None` → `stale += 1`; `stale >= stale_limit` →
   `failed = True`, palauta `None`; muuten palauta `self.duty`.
3. `e = self.target - flow`, `de = 0.0 if e_prev is None else e - e_prev`, `e_prev = e`.
4. Nopeusmuoto: `duty_new = self.duty + kp*de + ki*e*dt`.
5. **Paineikatto:** `cap = (p_max - pressure) / p_margin`, rajattu `[0.0, 1.0]`.
6. `self.duty = min(max(duty_new, 0.0), 1.0, cap)`.
7. Saturaatio (sama vuotava laskuri ja Schmitt-liipaisin kuin ennen, korjaus 3 K7): ehto on
   (`e > 0.1` **ja** `self.duty >= 0.99`) tai (`e > 0.1` **ja** `cap <= self.duty + 0.01`) tai
   (`e < -0.1` **ja** `self.duty <= 0.01`). Tosi → `sat_ms += dt*1000`, epätosi →
   `sat_ms -= 0.5*dt*1000`, rajaus `[0, 2000]`; `saturated` nousee 2000:ssa, laskee 0:ssa,
   välissä säilyttää arvonsa.
8. Palauta `self.duty`.

Ei `p_min`-, `lead`- eikä `rate_bar_s`-parametria: ne olivat kaskadin rakenteita. Rampitusta ei
tarvita, koska duty vaikuttaa paineeseen integroivasti — askel dutyssa ei ole askel paineessa.

## 2. `PumpPressureController.apply_duty(self, duty)` (`pico/classes.py`, uusi metodi)

Ajaa annetun dutyn samalla aikasuhteisella ikkunalla kuin `update`in häntä (`classes.py:731-737`):
sijoittaa `self.duty`, päivittää `self.duty_avg` (sama tau 5 s, `dt` edellisestä kutsusta, katkaisu
0,2 s), pyörittää `window_start`-ikkunaa ja kutsuu `_set(...)`. **Ei** PI-laskentaa, **ei**
`continuous_error`-haaraa, **ei** `integral`-kosketusta. Asettaa `self.filtered = pressure`, kun
`pressure` annetaan: allekirjoitus `apply_duty(self, duty, pressure=None)`.

## 3. `run_shot` (`pico/functions.py:197-258`)

Luonti (`functions.py:200-203`) antaa aloitusdutyn paineohjauksen oppimasta arvosta:

```python
flow_controller = FlowController(utime, brew_data.get_flow_target(), brew_data.learned_ff_brew)
```

Silmukassa:

```python
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
```

Lokirivin kolmas kenttä tulostaa jälleen `brew_pressure`in (virtaustilassa paine ei ole ohjattu
suure); `fsp=` ja `fsat=` säilyvät. Kaikki keskeytysehdot, `brew_data.pressure_filtered`-sijoitus
ja `learned_ff_brew`-päivitys säilyvät ennallaan.

## 4. Simulaatio `testit/flow_ctrl_sim.py` — venttiilialue laajenee

Malli, näytteistys ja kohina ennallaan. Uusi `k`-aikataulu, ajo **44 s**:
`0,50` alussa → **8 s: 0,166** (liian tiukka, saavuttamaton) → **16 s: 0,50** → **26 s: 1,5** →
**35 s: 3,0** (auki; tavoitteen vaatima paine alle 1 bar). Väitteet:

1. Jokaisessa saavutettavassa vaiheessa (`k` = 0,50 / 0,50 / 1,5 / 3,0) virtaus on ±0,3 g/s
   sisällä tavoitteesta 2,0 s kuluttua muutoksesta vaiheen loppuun asti.
2. Vaiheessa `k = 0,166` `fsat` on 1 viimeistään 6,5 s kuluttua ja pysyy 1:nä vaiheen loppuun;
   duty tai paineikatto on tuolloin rajoittava.
3. Paine ei ylitä 12,0 bar missään kohtaa eikä 13,0 bar koskaan.
4. Vaiheissa `k = 1,5` ja `k = 3,0` paine saa laskea vapaasti alle 2 barin — tästä ei tehdä
   väitettä, mutta virtausväite 1 koskee niitä täysimääräisesti. **Tämä on koko paketin syy:
   vanha hyväksyntä ei kattanut tätä aluetta.**
5. `fmode:off` -regressio ennallaan.

Tunnettu rajoite, joka kirjataan simulaation kommenttiin: malli tekee virtauksesta suoraan
verrannollisen dutyyn (`6,7·u` tasapainossa), kun oikeassa pumpussa on minimi-isku ja
takaisinvuotoa. Viritys haetaan siksi uudelleen ensimmäisestä laiteajosta.
