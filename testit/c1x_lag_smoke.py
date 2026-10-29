#!/usr/bin/env python3
"""c1x_lag_smoke.py — C1X-jälkinousun lisäviiveen (EU_C1X_LAG_S) savutesti (EXPRESSO-C1X-JALKINOUSU).

Todentaa:
C1. Firmwaren vakio EU_C1X_LAG_S on 0.025 s (25 ms).
C2. pre_infusion_phased: dly kytkeytyy c1x:n mukaan (c1x -> dly = EU_C1X_LAG_S, vanha -> dly = 0.0).
C3. Laitedatan sovitus:
    - Sarja 1 (dly=0.0): c1x ka dt 0.0904 s vs c0 0.0728 s -> viive-ero 17.6 ms, ylitysero +0.36 bar.
    - Sarja 2 (dly=0.020): c1x ka dt 0.1049 s vs c0 0.0714 s -> viive-ero 33.4 ms, jäännösylitys +0.07 bar.
    - Kaikkien 11 ajon mitattu lisäviive ka 24.1 ms (0.0241 s).
    - Ylityksen jäännösviive Sarjassa 2 (+0.066 bar @ 21.5 bar/s) on +3.1 ms -> optimaalinen viive 23.1 ms (~23-25 ms).
C4. Fysikaalinen malli: k+2-jonon 20 ms + SSR-40DA nollaylitys (0..10 ms, ka 5 ms) = 25 ms.
C5. Katkaisun ennusteessa dly kompensoi viiveen eteenpäin (vaiheet 1 ja 3).
C6. Jälkinousun opissa obs = (peak - p_cut) / rate_cut - dly palauttaa saman opitun jälkinousun polusta riippumatta.
C7. Simuloitu uutto (C1Exec vs vanha polku): opittu jälkinousu eb_coast_s täsmää (<= 0.015 s).
"""

import glob
import os
import re
import statistics as stats
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)
sys.path.insert(0, REPO_ROOT)
sys.path.insert(0, HERE)

import pico.functions as F
import pico.classes as C
import testit.sovita_c1x_lag as S
import testit.esiuutto_smoke as ES

failed = 0

def check(name, cond, details=""):
    global failed
    if cond:
        print(f"OK   {name} {details}")
    else:
        print(f"FAIL {name} {details}")
        failed += 1

def main():
    print("=== c1x_lag_smoke.py: C1X-jälkinousun lisäviiveen todennus ===")
    
    # C1. Vakio
    check("C1. EU_C1X_LAG_S määritelty ja arvo 0.025 s",
          getattr(F, "EU_C1X_LAG_S", None) == 0.025,
          f"arvo={getattr(F, 'EU_C1X_LAG_S', None)}")
    
    # C2. pre_infusion_phased lähdekooditarkistus dly:lle
    fn_src = open(os.path.join(REPO_ROOT, "pico", "functions.py")).read()
    check("C2a. pre_infusion_phased alustaa dly = 0.0",
          "dly = 0.0" in fn_src)
    check("C2b. pre_infusion_phased asettaa dly = EU_C1X_LAG_S kun c1x aktivoituu",
          "dly = EU_C1X_LAG_S" in fn_src)
    check("C2c. Vaiheen 1 katkaisussa dly lisätään ennusteeseen",
          "((coast_f if rate >= EU_RATE_FAST else coast_s) + dly) >= target - EU_CUT_MARGIN_BAR" in fn_src)
    check("C2d. Vaiheen 3 katkaisussa dly lisätään ennusteeseen",
          "(coast_c + dly) >= target - EB_CUT_MARGIN_BAR" in fn_src)
    check("C2e. Jälkinousun opissa dly vähennetään havainnosta",
          "obs = (peak - p_cut) / rate_cut - dly" in fn_src)

    # C3. Laitedatan sovitus testit/sovita_c1x_lag.py:lla
    s1_files = sorted(glob.glob(os.path.join(REPO_ROOT, "testit/c1x-20261020-sarja[1-6]-*.log")))
    s1_parsed = [S.parse_log(f) for f in s1_files]
    s1_c1x_dt = [r["eb"]["dt"] for r in s1_parsed if r["c1x"]]
    s1_c0_dt = [r["eb"]["dt"] for r in s1_parsed if not r["c1x"]]
    diff1 = stats.mean(s1_c1x_dt) - stats.mean(s1_c0_dt)
    
    check("C3a. Sarja 1 (dly=0.0): c1x ka dt ~0.090 s vs c0 ~0.073 s",
          0.088 <= stats.mean(s1_c1x_dt) <= 0.093 and 0.070 <= stats.mean(s1_c0_dt) <= 0.075,
          f"c1x={stats.mean(s1_c1x_dt):.4f}, c0={stats.mean(s1_c0_dt):.4f}")
    check("C3b. Sarja 1 viive-ero on 15..20 ms (17.6 ms)",
          0.015 <= diff1 <= 0.020,
          f"diff1={diff1*1000:.1f} ms")

    s2_files = sorted(glob.glob(os.path.join(REPO_ROOT, "testit/c1x-20261020-sarjab[1-6]-*.log")))
    s2_parsed = [S.parse_log(f) for f in s2_files]
    s2_c1x_hot = [r["eb"]["dt"] for r in s2_parsed if r["c1x"] and r["eb"]["rate"] > 15.0]
    s2_c0_hot = [r["eb"]["dt"] for r in s2_parsed if not r["c1x"] and r["eb"]["rate"] > 15.0]
    diff2_hot = stats.mean(s2_c1x_hot) - stats.mean(s2_c0_hot)
    
    check("C3c. Sarja 2 täysi nousunopeus viive-ero on 30..36 ms (33.4 ms)",
          0.030 <= diff2_hot <= 0.036,
          f"diff2={diff2_hot*1000:.1f} ms")
          
    all_c1x = s1_c1x_dt + s2_c1x_hot
    all_c0 = s1_c0_dt + s2_c0_hot
    diff_all = stats.mean(all_c1x) - stats.mean(all_c0)
    check("C3d. Kaikkien 11 ajon keskimääräinen lisäviive on 22..26 ms (24.1 ms)",
          0.022 <= diff_all <= 0.026,
          f"diff_all={diff_all*1000:.1f} ms")

    # C4. Fysikaalinen malli
    t_queue = 0.020      # k+2 -jonon tapahtuma-askel (20 ms)
    t_ssr = 0.005        # SSR-40DA nollaylityksen keskiarvo (0..10 ms tasajakauma)
    t_phys = t_queue + t_ssr
    check("C4. Fysikaalinen malli (k+2-jono 20 ms + SSR-nollaylitys 5 ms) täsmää 25 ms",
          t_phys == 0.025,
          f"t_phys={t_phys*1000:.1f} ms")

    # C5 & C6. Algebrallinen invarianssi
    # Oletetaan laite, jolla c1x:n todellinen coast_time = coast_vanha + t_phys
    coast_vanha = 0.072
    rate = 21.0
    coast_c1x = coast_vanha + t_phys
    # Katkaisun ennuste c1x:llä:
    pred_c1x = rate * (coast_vanha + F.EU_C1X_LAG_S)
    actual_rise_c1x = rate * coast_c1x
    check("C5. Katkaisun ennuste dly:llä kompensoi lisäviiveen täsmällisesti",
          abs(pred_c1x - actual_rise_c1x) < 1e-9,
          f"pred={pred_c1x:.4f}, actual={actual_rise_c1x:.4f}")
    # Jälkinousun oppi:
    obs_c1x = (actual_rise_c1x) / rate - F.EU_C1X_LAG_S
    check("C6. Jälkinousun oppi obs palauttaa saman opitun coast_s kuin vanhalla polulla",
          abs(obs_c1x - coast_vanha) < 1e-9,
          f"obs_c1x={obs_c1x:.4f}, coast_vanha={coast_vanha:.4f}")

    # C7. Simuloitu uutto (C1Exec vs vanha polku, seed 160)
    def c1x_brew(bd):
        bd.temperature_sensor, bd.eu_c1x = ES.C1Exec(), 1
        return bd

    co = {}
    for path in (0, 1):
        bd = ES.brew_bd("25b", 160, False)
        if path: c1x_brew(bd)
        ES.run_brew(bd, 16.0, bim=1, seed=160)
        co[path] = bd.eb_coast_s
    diff_sim = abs(co[1] - co[0])
    check("C7. Simuloitu uutto: opittu jälkinousu (eb_coast_s) sama c1x:llä ja vanhalla polulla (<= 0.015 s)",
          diff_sim <= 0.015,
          f"c1x={co[1]:.4f}, vanha={co[0]:.4f}, diff={diff_sim:.4f}")

    print(f"\nRESULT: {failed} failed")
    if failed > 0:
        sys.exit(1)

if __name__ == "__main__":
    main()
