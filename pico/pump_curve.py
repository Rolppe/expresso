# Ulka EP5/EX5 (CEME E5, 230 V 50 Hz, 48 W): pumpattu vesimaara paineen funktiona.
#
# Lahde: CEME "Family pump E - high pressure", s. 2 taulukko Average Flow Rate, sarake E5 (malli EP5/EX5 s. 3):
# http://files.cemegroup.com/elettropompe/0/60/Scheda tecnica E high pressure.639070095522790454.pdf
# Pisteiden valilla suora, kuten valmistajan kaaviossa. Pumppu iskee kerran verkkojaksossa (diodi), joten
# jatkuvan kaynnin ml/isku = taulukon cc/min / 3000.
#
# PC_K_PULSED: talla laitteella pulssitettu pumppu (9-22 iskua/s) tuotti iskua kohden enemman kuin taulukko:
# 8,0 bar 0,118 g/isku (n=9) ja 9,0 bar 0,100 g/isku (n=4) pidon lopussa (uutot 20.10.-2.11.2026, kaukalon nousu /
# iskut). Koko uutosta EB_RAMP_DONE-rivista alkaen (V = iskujen stroke_ml(p) summa, k=1): paino ~ 1,165 x V + 1,5 g,
# loppupaino ~ 1,165 x V + 7,6 g. Kertoimen syy auki (pumppuyksilo tai vaa'an vahvistus). Mitattu vain 8-9 barissa.
#
# PC_ML_TAB: iskun ml kertoimella PC_K_PULSED 0,1 barin valein 0-15 bar (151 arvoa), uuttosilmukkaan yksi haku iskua
# kohden (TILAUS-O: ei silmukkaa jakson sisalla).

from array import array

PC_BAR = (0.0, 2.0, 4.0, 6.0, 7.0, 8.0, 10.0, 12.0, 14.0, 15.0)
PC_CC_MIN = (650.0, 520.0, 420.0, 350.0, 330.0, 300.0, 210.0, 140.0, 60.0, 0.0)
PC_MAINS_HZ = 50.0       # iskua/s taydella pumpulla
PC_K_PULSED = 1.165      # kerroin stroke_ml:lle pulssitetulla pumpulla
PC_W_OFS_G = 1.5         # paino ~ ml (RAMP_DONE:sta) + tama
PC_W_END_OFS_G = 7.6     # loppupaino ~ ml (RAMP_DONE:sta) + tama


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


PC_ML_TAB = array('f', [stroke_ml(i / 10.0, PC_K_PULSED) for i in range(151)])


def stroke_ml_tab(p_bar):
    """stroke_ml(p_bar, PC_K_PULSED) taulukosta lahimmasta 0,1 barista; alle 0 = 0 bar, yli 15 = 15 bar."""
    i = int(p_bar * 10.0 + 0.5)
    return PC_ML_TAB[0 if i < 0 else (150 if i > 150 else i)]
