# OHJEVAHTI — korjaus 1

**Vika (suunnittelijan spec, kohta 3):** "osa on pico-ajo, jos jokin sana päättyy `pico_dev.py`"
tekee lukukomennoista laiteajoja. Mitattu: `grep -n pgap pico_dev.py` ja
`sed -n 1,5p Infra/iot/expresso/pico_dev.py` → `ask`, syy `Laiteajo: ` (tyhjä), ja `ask` kirjoittaa
`viimeisin_ajo`:n, joten seuraava oikea ajo saisi väärän VÄLIVAIHE-kiellon.

**Uusi sääntö, korvaa kohdan 3 ensimmäisen kappaleen:** osa on pico-ajo vain, kun sana, joka
päättyy `pico_dev.py`, on joko osan ensimmäinen sana tai sitä edeltää sana, jonka perusnimi
(`os.path.basename`) alkaa `python`. Edeltävät `NIMI=arvo`-sanat ja `timeout <luku>` ohitetaan
ensimmäistä sanaa etsittäessä. Jos `pico_dev.py`:n jälkeen ei ole sanaa (ei op:ta), osa ei ole
pico-ajo.

**Holdout:** `testit/ohjevahti_smoke.py` tapaukset 13b-13d lisätty (suunnittelija). Älä muuta
holdoutia. Aja brieffin Acceptance ja Budget uudelleen; raportoi samassa kuusirivimuodossa.
