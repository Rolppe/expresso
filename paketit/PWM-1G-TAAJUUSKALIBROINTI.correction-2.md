# PWM-1G-TAAJUUSKALIBROINTI — korjaus 2 (suunnittelijan väite kumottu mittaamalla)

Spec kohta 3 sanoi: "Ikkunan pidentäminen parantaa tätä suhteessa `T^1,5`, ja vaiheessa 1h ikkuna
on koko paineennosto." **Väite on väärä sellaisenaan**, ja suunnittelijan oma luotaus kumosi sen
heti hyväksynnän jälkeen. Mitattu laitosmallilla, malli 50,30 Hz, kolme siementä:

| Hila | Ikkuna | keskivirhe | max virhe |
|---|---|---|---|
| 0,4 Hz | 2,0 s | +0,012 Hz | 0,033 Hz |
| 0,4 Hz | 5,0 s | −0,079 Hz | 0,083 Hz |
| 0,1 Hz | 5,0 s | −0,002 Hz | **0,005 Hz** |
| 0,1 Hz | 2,0 s | +0,029 Hz | 0,070 Hz |

Syy ei ole paineennosto: sama ero näkyy, kun ajo alkaa laitoksen tasapainopaineesta (5,4 bar),
jolloin amplitudi ei juuri muutu ikkunan aikana. Syy on hilassa. Goertzelin huipun leveys on
luokkaa `1/T`: 2,0 s:n ikkunassa 0,5 Hz, 5,0 s:n ikkunassa 0,2 Hz. Kun huippu kapenee hilaa
kapeammaksi, kolmen pisteen paraabeli sovitetaan huipun ohi ja tulos vinoutuu. Liian tiheä hila
lyhyellä ikkunalla on myös huonompi (0,070 vs 0,033 Hz): leveän huipun päällä kohina valitsee
naapuribinin.

**Sääntö, joka tästä seuraa vaiheelle 1h:** hilan askel johdetaan ikkunasta,
`askel ≈ 1 / (2T)` — 2,0 s → 0,25 Hz, 5,0 s → 0,10 Hz. `MCAL_GRID` ei siis ole vakio vaan
lasketaan pyydetystä kestosta. Kiinteä 0,4 Hz jää oikeaksi vain nykyiselle 2 s:n oletukselle.

Hyöty on TILAUS-F:n kannalta merkittävä: oikealla hilalla 5 s:n ikkuna antaa 0,005 Hz, eli
kaksi kertaluokkaa tarkemman verkkojakson kuin mihin vaiheen 1a kaistahaku ylsi.

Tätä ei korjattu 1G:hen jälkikäteen: 1G:n oletus on 2,0 s ja sillä hila on oikea. Korjaus
kuuluu vaiheeseen 1h, jossa ikkuna muuttuu paineennoston mittaiseksi.
