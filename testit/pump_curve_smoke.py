"""pico/pump_curve.py: CEME-taulukon pisteet, valit, rajat ja laitteesta mitattu pulssikerroin."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "pico"))
from pump_curve import PC_K_PULSED, PC_ML_TAB, flow_ml_min, stroke_ml, stroke_ml_tab

virheet = 0


def tarkista(nimi, ehto, tieto=""):
    global virheet
    print("%s %s %s" % ("OK  " if ehto else "FAIL", nimi, tieto))
    if not ehto:
        virheet += 1


TAULUKKO = {0: 650, 2: 520, 4: 420, 6: 350, 7: 330, 8: 300, 10: 210, 12: 140, 14: 60, 15: 0}
tarkista("C1 kaikki CEME-pisteet", all(flow_ml_min(float(p)) == q for p, q in TAULUKKO.items()))
tarkista("C2 9 bar pisteiden valissa", flow_ml_min(9.0) == 255.0, flow_ml_min(9.0))
tarkista("C3 5 bar pisteiden valissa", flow_ml_min(5.0) == 385.0, flow_ml_min(5.0))
tarkista("C4 alipaine = 0 bar", flow_ml_min(-0.5) == 650.0)
tarkista("C5 yli 15 bar = 0", flow_ml_min(20.0) == 0.0)
arvot = [flow_ml_min(i / 10.0) for i in range(0, 151)]
tarkista("C6 laskee koko alueella", all(a > b for a, b in zip(arvot, arvot[1:])))
tarkista("C7 isku jatkuvalla pumpulla 8 bar", abs(stroke_ml(8.0) - 0.100) < 1e-9, stroke_ml(8.0))
tarkista("C8 pulssi 8 bar (k 1,165) mitattu pidon loppu 0,118 +-2 %", abs(stroke_ml(8.0, PC_K_PULSED) - 0.118) < 0.118 * 0.02,
         stroke_ml(8.0, PC_K_PULSED))
tarkista("C9 pulssi 9 bar (k 1,165) mitattu pidon loppu 0,100 +-2 %", abs(stroke_ml(9.0, PC_K_PULSED) - 0.100) < 0.100 * 0.02,
         stroke_ml(9.0, PC_K_PULSED))
tarkista("C10 taulukko 151 arvoa = stroke_ml(k) 0,1 barin pisteissa", len(PC_ML_TAB) == 151 and
         all(abs(PC_ML_TAB[i] - stroke_ml(i / 10.0, PC_K_PULSED)) < 1e-6 for i in range(151)))
tarkista("C11 haku pyoristaa lahimpaan 0,1 bariin", stroke_ml_tab(8.04) == PC_ML_TAB[80] and stroke_ml_tab(8.06) == PC_ML_TAB[81])
tarkista("C12 haku rajaa alle 0 ja yli 15 bar", stroke_ml_tab(-1.0) == PC_ML_TAB[0] and stroke_ml_tab(20.0) == 0.0)

print("RESULT: %d failed" % virheet)
sys.exit(1 if virheet else 0)
