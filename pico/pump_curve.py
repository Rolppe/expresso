# Ulka EP5/EX5 (CEME E5, 230 V 50 Hz, 48 W): pumpattu vesimaara paineen funktiona.
#
# Lahde: CEME "Family pump E - high pressure", s. 2 taulukko Average Flow Rate, sarake E5 (malli EP5/EX5 s. 3):
# http://files.cemegroup.com/elettropompe/0/60/Scheda tecnica E high pressure.639070095522790454.pdf
# Pisteiden valilla suora, kuten valmistajan kaaviossa. Pumppu iskee kerran verkkojaksossa (diodi), joten
# jatkuvan kaynnin ml/isku = taulukon cc/min / 3000.
#
# PC_K_PULSED: talla laitteella pulssitettu pumppu (9-22 iskua/s) tuotti iskua kohden enemman kuin taulukko:
# 8,0 bar 0,118 g/isku (n=9) ja 9,0 bar 0,100 g/isku (n=4) eli 1,18 x taulukko molemmissa (uutot 20.10.-2.11.2026,
# pidon loppu, kaukalon nousu / iskut). Mitattu vain 8-9 barissa.

PC_BAR = (0.0, 2.0, 4.0, 6.0, 7.0, 8.0, 10.0, 12.0, 14.0, 15.0)
PC_CC_MIN = (650.0, 520.0, 420.0, 350.0, 330.0, 300.0, 210.0, 140.0, 60.0, 0.0)
PC_MAINS_HZ = 50.0       # iskua/s taydella pumpulla
PC_K_PULSED = 1.18       # kerroin stroke_ml:lle pulssitetulla pumpulla


def flow_ml_min(p_bar):
    """Valmistajan virtaus (ml/min) jatkuvalla pumpulla paineessa p_bar. Alle 0 bar = 0 bar, 15 bar ja yli = 0."""
    if p_bar <= PC_BAR[0]:
        return PC_CC_MIN[0]
    for i in range(1, len(PC_BAR)):
        if p_bar <= PC_BAR[i]:
            p0 = PC_BAR[i - 1]
            q0 = PC_CC_MIN[i - 1]
            return q0 + (PC_CC_MIN[i] - q0) * (p_bar - p0) / (PC_BAR[i] - p0)
    return 0.0


def stroke_ml(p_bar, k=1.0):
    """Yhden iskun tilavuus (ml) paineessa p_bar. Pulssitetulle pumpulle k=PC_K_PULSED."""
    return flow_ml_min(p_bar) / (PC_MAINS_HZ * 60.0) * k
