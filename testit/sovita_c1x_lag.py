#!/usr/bin/env python3
"""sovita_c1x_lag.py — C1X-jälkinousun lisäviiveen (EU_C1X_LAG_S) sovitus laitedatasta (EXPRESSO-C1X-JALKINOUSU).

Aineisto:
- testit/c1x-20261020-sarja{1..6}-c1x{1,0}.log (Sarja 1: dly = 0.0)
- testit/c1x-20261020-sarjab{1..6}-c1x{1,0}.log (Sarja 2: dly = 0.02)
- testit/c1x-20261020-shot1.log (c1x:1) vs testit/c1x-20261020-shot2-vanha.log (c1x:0)
"""

import glob
import os
import re
import statistics as stats

TESTIT_DIR = os.path.dirname(os.path.abspath(__file__))

def parse_log(path):
    with open(path) as f:
        content = f.read()
    
    is_c1x = "c1x1" in path or "shot1" in path or "c1x=1" in content
    
    eb_cut = re.search(r"EB_CUT t_ms=(\d+) p=([\d.]+) rate=([\d.]+) coast_s=([\d.]+)", content)
    eb_coast = re.search(r"EB_COAST peak=([\d.]+) rise=([\d.]+) rate=([\d.]+) coast_s=([\d.]+)", content)
    eb_end = re.search(r"EB_END .*? over=([\d.]+) .*? late=(\d+) miss=(\d+)", content)
    
    res = {
        "file": os.path.basename(path),
        "c1x": is_c1x,
        "eb": None
    }
    
    if eb_cut and eb_coast:
        p_cut = float(eb_cut.group(2))
        rate_cut = float(eb_cut.group(3))
        peak = float(eb_coast.group(1))
        rise = float(eb_coast.group(2))
        rate_coast = float(eb_coast.group(3))
        over = float(eb_end.group(1)) if eb_end else None
        dt = rise / rate_cut if rate_cut > 0 else 0.0
        res["eb"] = {
            "p_cut": p_cut,
            "rate": rate_cut,
            "peak": peak,
            "rise": rise,
            "dt": dt,
            "over": over
        }
    return res

def main():
    print("=== EXPRESSO-C1X-JALKINOUSU: Sovitus laitedatasta ===")
    
    # 1. Sarja 1 (dly = 0.0)
    s1_files = sorted(glob.glob(os.path.join(TESTIT_DIR, "c1x-20261020-sarja[1-6]-*.log")))
    s1_parsed = [parse_log(f) for f in s1_files]
    
    print("\n--- Sarja 1 (20.10.2026, dly = 0.0) ---")
    s1_c1x_dt = []
    s1_c0_dt = []
    s1_c1x_over = []
    s1_c0_over = []
    for r in s1_parsed:
        eb = r["eb"]
        tag = "c1x:1" if r["c1x"] else "c1x:0"
        print(f"  {r['file']}: {tag} p_cut={eb['p_cut']:.2f} bar, rate={eb['rate']:.2f} bar/s, rise={eb['rise']:.2f} bar -> dt={eb['dt']:.4f} s, over={eb['over']:.2f} bar")
        if r["c1x"]:
            s1_c1x_dt.append(eb["dt"])
            s1_c1x_over.append(eb["over"])
        else:
            s1_c0_dt.append(eb["dt"])
            s1_c0_over.append(eb["over"])
            
    print(f"  Sarja 1 c1x:1 dt ka = {stats.mean(s1_c1x_dt):.4f} s (sd = {stats.stdev(s1_c1x_dt):.4f})")
    print(f"  Sarja 1 c1x:0 dt ka = {stats.mean(s1_c0_dt):.4f} s (sd = {stats.stdev(s1_c0_dt):.4f})")
    diff1 = stats.mean(s1_c1x_dt) - stats.mean(s1_c0_dt)
    print(f"  Sarja 1 dt ero (c1x - c0) = {diff1:.4f} s ({diff1*1000:.1f} ms)")
    print(f"  Sarja 1 ylitys ka: c1x = {stats.mean(s1_c1x_over):.2f} bar, c0 = {stats.mean(s1_c0_over):.2f} bar (ero {stats.mean(s1_c1x_over)-stats.mean(s1_c0_over):+.2f} bar)")
    
    # 2. Sarja 2 (dly = 0.02)
    s2_files = sorted(glob.glob(os.path.join(TESTIT_DIR, "c1x-20261020-sarjab[1-6]-*.log")))
    s2_parsed = [parse_log(f) for f in s2_files]
    
    print("\n--- Sarja 2 (20.10.2026, dly = 0.02) ---")
    s2_c1x_dt = []
    s2_c0_dt = []
    s2_c1x_over = []
    s2_c0_over = []
    for r in s2_parsed:
        eb = r["eb"]
        tag = "c1x:1" if r["c1x"] else "c1x:0"
        print(f"  {r['file']}: {tag} p_cut={eb['p_cut']:.2f} bar, rate={eb['rate']:.2f} bar/s, rise={eb['rise']:.2f} bar -> dt={eb['dt']:.4f} s, over={eb['over']:.2f} bar")
        if r["c1x"]:
            s2_c1x_dt.append(eb["dt"])
            s2_c1x_over.append(eb["over"])
        else:
            s2_c0_dt.append(eb["dt"])
            s2_c0_over.append(eb["over"])
            
    print(f"  Sarja 2 c1x:1 dt ka = {stats.mean(s2_c1x_dt):.4f} s (sd = {stats.stdev(s2_c1x_dt):.4f})")
    print(f"  Sarja 2 c1x:0 dt ka = {stats.mean(s2_c0_dt):.4f} s (sd = {stats.stdev(s2_c0_dt):.4f})")
    diff2 = stats.mean(s2_c1x_dt) - stats.mean(s2_c0_dt)
    print(f"  Sarja 2 dt ero (c1x - c0) = {diff2:.4f} s ({diff2*1000:.1f} ms)")
    print(f"  Sarja 2 ylitys ka: c1x = {stats.mean(s2_c1x_over):.2f} bar, c0 = {stats.mean(s2_c0_over):.2f} bar (ero {stats.mean(s2_c1x_over)-stats.mean(s2_c0_over):+.2f} bar)")
    
    # Sarja 2 ilman sarjab1:tä (jossa rate oli matala 12.7 bar/s)
    s2_c1x_hot = [r["eb"]["dt"] for r in s2_parsed if r["c1x"] and r["eb"]["rate"] > 15.0]
    s2_c0_hot = [r["eb"]["dt"] for r in s2_parsed if not r["c1x"] and r["eb"]["rate"] > 15.0]
    print(f"  Sarja 2 (täysi nousunopeus ~21-24 bar/s): c1x={stats.mean(s2_c1x_hot):.4f} s, c0={stats.mean(s2_c0_hot):.4f} s -> ero = {stats.mean(s2_c1x_hot)-stats.mean(s2_c0_hot):.4f} s ({(stats.mean(s2_c1x_hot)-stats.mean(s2_c0_hot))*1000:.1f} ms)")
    
    # 3. Yhdistetty sovitus
    # Kaikki täyden nopeuden ajot:
    all_c1x_dt = s1_c1x_dt + s2_c1x_hot
    all_c0_dt = s1_c0_dt + s2_c0_hot
    diff_all = stats.mean(all_c1x_dt) - stats.mean(all_c0_dt)
    print("\n--- Yhteenveto ja sovitustulos ---")
    print(f"  Kaikki c1x (N={len(all_c1x_dt)}): ka = {stats.mean(all_c1x_dt):.4f} s ± {stats.stdev(all_c1x_dt):.4f} s")
    print(f"  Kaikki c0  (N={len(all_c0_dt)}): ka = {stats.mean(all_c0_dt):.4f} s ± {stats.stdev(all_c0_dt):.4f} s")
    print(f"  Mitattu lisäviive (delta t = c1x - c0): {diff_all:.4f} s = {diff_all*1000:.1f} ms")
    print(f"  Sarja 1 (dly=0): {diff1*1000:.1f} ms")
    print(f"  Sarja 2 (täysi nopeus): {(stats.mean(s2_c1x_hot)-stats.mean(s2_c0_hot))*1000:.1f} ms")
    print(f"  Kaikki parit keskimäärin: {diff_all*1000:.1f} ms -> pyöristys yhteen/puoleen verkkojaksoon tai sovitus:")
    
    # Analysoidaan lisäksi katkaisun ennusteen virhe
    # Kun dly = 0.02 (Sarja 2), ylitysero pieneni 0.36 barista (Sarja 1: 0.52 vs 0.16) 0.06 bariin (Sarja 2: 0.45 vs 0.39).
    # 0.06 bar / 21 bar/s = +0.0029 s (+2.9 ms).
    # Jos dly olisi ollut 0.02 + 0.003 = 0.023 s, ylitys olisi ollut identtinen.
    print(f"  Ylityksen jäännösvirhe Sarjassa 2: {stats.mean(s2_c1x_over)-stats.mean(s2_c0_over):+.2f} bar")
    rem_lag = (stats.mean(s2_c1x_over) - stats.mean(s2_c0_over)) / 21.5
    print(f"  Jäännösviive ylityksestä (21.5 bar/s): {rem_lag:.4f} s ({rem_lag*1000:.1f} ms)")
    opt_dly = 0.02 + rem_lag
    print(f"  Optimaalinen EU_C1X_LAG_S ylityksen tasaamiseksi: {opt_dly:.4f} s (~{round(opt_dly, 3)} s = {round(opt_dly*1000, 1)} ms)")

if __name__ == "__main__":
    main()
