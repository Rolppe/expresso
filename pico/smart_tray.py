# ============================================================================
# SMART TRAY & WEIGHT TRACKER (EXPRESSO-ALYKAS-PAINO, 26.10.2026)
# ============================================================================
# Kayttajan tilaus 26.10.2026 (KAYTTAJAN-TIEDOT.md §9 kohta 4):
# "painon tunnistus pitää kehittää älykkäämmäksi siten että se tunnistaa
#  paljonko vettä on tullut kaukaloon. Myös jos keittimen kaukalo on
#  tyhjennetty keittimen ollessa sammuksissa. Myös kupin paino ja ulkoisen
#  vaan paino täytyy olla tuttu ja tunnistettu kun ne lisätään keittimen
#  kaukalon päälle."
#
# Toiminnot:
# 1. Kaukaloon tulleen veden maaran seuranta (water_g, water_pct, max 400 g).
# 2. Kaukalon tyhjennyksen tunnistus sammuksissa (tray_state.json vertailu
#    boot-hetken painoon suhteessa tyhjan kaukalon perustasoon 454.5 g).
# 3. Kupin (nimellinen 293.9 g), ulkoisen vaa'an (nimellinen 130.0 g),
#    koeastin (50.7 g) seka niden yhdistelmien automaattinen tunnistus
#    kaukalolle asetettaessa ilman, etta niiden massaa luullaan vedeksi.
# ============================================================================

import json

# Perusvakiot
TRAY_REF_G = 454.5              # Tyhja kaukalo + ritila (scalecal.py, KAYTTAJAN-TIEDOT)
TRAY_MIN_PRESENT_G = 200.0      # Alle 200 g = kaukalo irti keittimesta
TRAY_MAX_WATER_G = 400.0        # Kaukalon tayttoraja (KAYTTAJAN-TIEDOT: ~400-450 g)
TRAY_WARN_WATER_G = 350.0       # Varoituskynnys (>87.5 % taynna)

# Tunnettujen esineiden nimellismassat ja oletustoleranssit (g)
DEFAULT_CUP_G = 293.9           # KAYTTAJAN-TIEDOT: "kuppi 293,9 g"
DEFAULT_CUP_TOL_G = 35.0        # 258.9 - 328.9 g

DEFAULT_SCALE_G = 130.0         # Ulkoinen tasku-/jeweller-vaaka
DEFAULT_SCALE_TOL_G = 35.0      # 95.0 - 165.0 g

DEFAULT_VESSEL_G = 50.7         # KAYTTAJAN-TIEDOT: "koeastia 50,7 g"
DEFAULT_VESSEL_TOL_G = 15.0     # 35.7 - 65.7 g

DEFAULT_COMBO_TOL_G = 50.0      # Vaaka + kuppi yhdistelma (~423.9 g)

STATE_FILE = 'tray_state.json'


class SmartTrayTracker:
    def __init__(self, scale, utime=None, state_file=STATE_FILE):
        self.scale = scale
        self.utime = utime
        self.state_file = state_file

        # Konfiguraatio
        self.tray_base_g = TRAY_REF_G
        self.max_water_g = TRAY_MAX_WATER_G
        self.cup_g = DEFAULT_CUP_G
        self.cup_tol_g = DEFAULT_CUP_TOL_G
        self.scale_g = DEFAULT_SCALE_G
        self.scale_tol_g = DEFAULT_SCALE_TOL_G
        self.vessel_g = DEFAULT_VESSEL_G
        self.vessel_tol_g = DEFAULT_VESSEL_TOL_G
        self.combo_tol_g = DEFAULT_COMBO_TOL_G

        # Tilamuuttujat
        self.water_g = 0.0
        self.water_session_g = 0.0
        self.water_total_g = 0.0
        self.status = 'ok'              # 'ok', 'warning_full', 'full', 'no_tray', 'emptied_offline'
        self.emptied_offline = False

        # Esineen tunnistus
        self.detected_object = 'none'   # 'none', 'cup', 'external_scale', 'scale_and_cup', 'test_vessel', 'unknown_object'
        self.object_weight = 0.0
        self.object_present = False

        # Sisainen suodatus ja vakauden seuranta
        self._boot_settled = False
        self._boot_samples = []
        self._step_buf = []
        self._drop_buf = []
        self._last_saved_water = 0.0
        self._last_saved_time = 0
        self._dirty = False

        # Ladataan edellinen tila levylta
        self._saved_state = self.load_state()

    def load_state(self):
        """Lataa tallennetun tilan tiedostosta."""
        try:
            with open(self.state_file, 'r') as f:
                d = json.load(f)
            if 'tray_base_g' in d:
                self.tray_base_g = float(d['tray_base_g'])
            if 'max_water_g' in d:
                self.max_water_g = float(d['max_water_g'])
            if 'cup_g' in d:
                self.cup_g = float(d['cup_g'])
            if 'scale_g' in d:
                self.scale_g = float(d['scale_g'])
            if 'vessel_g' in d:
                self.vessel_g = float(d['vessel_g'])
            if 'water_total_g' in d:
                self.water_total_g = float(d['water_total_g'])
            return d
        except Exception:
            return None

    def save_state(self, force=False):
        """Tallentaa tilan tiedostoon atomisesti."""
        now = self._ticks_ms()
        if not force and not self._dirty and abs(self.water_g - self._last_saved_water) < 1.0:
            return False
        d = {
            'water_g': round(self.water_g, 2),
            'last_weight_abs': round(getattr(self, 'last_weight_abs', self.tray_base_g + self.water_g), 2),
            'tray_base_g': round(self.tray_base_g, 2),
            'max_water_g': round(self.max_water_g, 2),
            'cup_g': round(self.cup_g, 2),
            'scale_g': round(self.scale_g, 2),
            'vessel_g': round(self.vessel_g, 2),
            'water_total_g': round(self.water_total_g, 2),
            'emptied_offline': self.emptied_offline,
            'timestamp': now
        }
        try:
            tmp = self.state_file + '.tmp'
            with open(tmp, 'w') as f:
                json.dump(d, f)
            try:
                import os
                try:
                    os.remove(self.state_file)
                except Exception:
                    pass
                os.rename(tmp, self.state_file)
            except Exception:
                with open(self.state_file, 'w') as f:
                    json.dump(d, f)
            self._last_saved_water = self.water_g
            self._last_saved_time = now
            self._dirty = False
            return True
        except Exception:
            return False

    def _ticks_ms(self):
        if self.utime and hasattr(self.utime, 'ticks_ms'):
            return self.utime.ticks_ms()
        import time
        return int(time.time() * 1000)

    @property
    def water_pct(self):
        """Kaukalon vesimaara prosentteina tayttorajasta."""
        if self.max_water_g <= 0:
            return 0.0
        return min(100.0, max(0.0, (self.water_g / self.max_water_g) * 100.0))

    def _init_boot_settle(self, w_abs):
        """Tarkistaa kaynnistyksessa sammuksissa tapahtuneen tyhjennyksen."""
        self._boot_settled = True
        self.last_weight_abs = w_abs

        if w_abs < TRAY_MIN_PRESENT_G:
            self.status = 'no_tray'
            self.water_g = 0.0
            return

        saved = self._saved_state
        base = self.tray_base_g

        if saved is not None:
            prev_water = saved.get('water_g', 0.0)
            prev_weight = saved.get('last_weight_abs', base + prev_water)

            # Ehto 1: Kaukalossa oli sammutettaessa merkittavasti vetta (>=20 g),
            # mutta nyt paino on palannut lahelle tyhjan kaukalon perustasoa (<= base + 20 g).
            # Ehto 2: Kokonaispaino on pudonnut sammutuksen aikana yli 25 g kohti perustasoa.
            if prev_water >= 20.0 and w_abs <= base + 20.0:
                self.emptied_offline = True
                self.water_g = max(0.0, w_abs - base)
                self.status = 'emptied_offline'
                print('SMART_TRAY: tray emptied while powered off (was %.1fg water, now %.1fg)'
                      % (prev_water, self.water_g))
            elif prev_water >= 25.0 and (prev_weight - w_abs) >= 25.0:
                self.emptied_offline = True
                self.water_g = max(0.0, w_abs - base)
                self.status = 'emptied_offline'
                print('SMART_TRAY: tray emptied while powered off (weight dropped %.1fg -> %.1fg)'
                      % (prev_weight, w_abs))
            else:
                self.emptied_offline = False
                self.water_g = max(0.0, w_abs - base)
                self.status = 'ok'
        else:
            self.emptied_offline = False
            self.water_g = max(0.0, w_abs - base)
            self.status = 'ok'

        self._update_status()
        self.save_state(force=True)

    def classify_object(self, delta):
        """Tunnistaa kaukalolle asetetun esineen painonmuutoksen delta (g) perusteella."""
        # 1. Ulkoisen vaa'an ja kupin yhdistelma (~423.9 g)
        combo_nominal = self.scale_g + self.cup_g
        if abs(delta - combo_nominal) <= self.combo_tol_g:
            return 'scale_and_cup', delta

        # 2. Kuppi (~293.9 g)
        if abs(delta - self.cup_g) <= self.cup_tol_g:
            return 'cup', delta

        # 3. Ulkoinen vaaka (~130.0 g)
        if abs(delta - self.scale_g) <= self.scale_tol_g:
            return 'external_scale', delta

        # 4. Koeastia (~50.7 g)
        if abs(delta - self.vessel_g) <= self.vessel_tol_g:
            return 'test_vessel', delta

        # 5. Tuntematon esine (yli 30 g vakaa lisays)
        if delta >= 30.0:
            return 'unknown_object', delta

        return 'none', 0.0

    def update(self, w_abs, now_ms=None, is_idle=True, pump_on=False):
        """Kutsutaan joka kerta kun uusi vaakanayte valmistuu (scale_poll_once).
        Paivittaa kaukalon veden maaran ja esinetunnistuksen."""
        if w_abs is None:
            return

        self.last_weight_abs = w_abs
        if now_ms is None:
            now_ms = self._ticks_ms()

        # Kaynnistyksen stabilointi (5 naytetta)
        if not self._boot_settled:
            self._boot_samples.append(w_abs)
            if len(self._boot_samples) >= 5:
                s = sorted(self._boot_samples)
                med = s[len(s) // 2]
                self._init_boot_settle(med)
            return

        # Tarkistetaan onko kaukalo poistettu keittimesta
        if w_abs < TRAY_MIN_PRESENT_G:
            self.status = 'no_tray'
            self.object_present = False
            self.detected_object = 'none'
            self.object_weight = 0.0
            self._step_buf = []
            self._drop_buf = []
            return

        expected_tray = self.tray_base_g + self.water_g

        # ---- TILA 1: Esine asetettuna kaukalolle ----
        if self.object_present:
            # Tarkistetaan onko esine poistettu kaukalolta:
            # Paino putoaa lahelle kaukalon ja veden tasoa (tai pudotus vastaa esinetta)
            if w_abs <= expected_tray + 25.0:
                self._drop_buf.append(w_abs)
                if len(self._drop_buf) >= 3:
                    spread = max(self._drop_buf[-3:]) - min(self._drop_buf[-3:])
                    if spread < 2.0:
                        # Esineen poisto vahvistettu
                        self.object_present = False
                        self.detected_object = 'none'
                        self.object_weight = 0.0
                        self._drop_buf = []
                        self._step_buf = []
                        # Paivitetaan mahdollinen kaukaloon uuton aikana jaanyt vesi
                        new_water = max(0.0, w_abs - self.tray_base_g)
                        if new_water > self.water_g:
                            added = new_water - self.water_g
                            self.water_session_g += added
                            self.water_total_g += added
                        self.water_g = new_water
                        self._dirty = True
            else:
                self._drop_buf = []

        # ---- TILA 2: Ei esinetta kaukalolla ----
        else:
            delta = w_abs - expected_tray

            # Mahdollinen esineen asettaminen kaukalolle:
            # Merkittava nopea lisays (>= 30 g) lepotilassa pumpun ollessa pois paalta
            if delta >= 30.0 and is_idle and not pump_on:
                self._step_buf.append(w_abs)
                if len(self._step_buf) >= 3:
                    spread = max(self._step_buf[-3:]) - min(self._step_buf[-3:])
                    if spread < 2.0:
                        # Uusi taso on vakaa -> luokitellaan esine
                        step_val = (sum(self._step_buf[-3:]) / 3.0) - expected_tray
                        obj_type, obj_w = self.classify_object(step_val)
                        if obj_type != 'none':
                            self.detected_object = obj_type
                            self.object_weight = step_val
                            self.object_present = True
                            self._step_buf = []
                            self._dirty = True
                # Huom: delta >= 30.0 aikana sita EI lisata kaukalon vedeksi!

            # Veden kertyminen kaukaloon (pumppu kay, uutto, huuhtelu tai alle 30 g lisays)
            elif w_abs >= expected_tray:
                self._step_buf = []
                new_water = max(0.0, w_abs - self.tray_base_g)
                added = new_water - self.water_g
                if added > 0.15:  # Pieni kohinakynnys
                    self.water_session_g += added
                    self.water_total_g += added
                    self.water_g = new_water
                    if self.status == 'emptied_offline':
                        self.status = 'ok'
                    self._dirty = True

            # Painon pieneneminen ilman esinetta (manuaalinen kaukalon tyhjennys keittimen ollessa paalla)
            elif w_abs < expected_tray - 20.0:
                self._step_buf = []
                self.water_g = max(0.0, w_abs - self.tray_base_g)
                if self.status == 'emptied_offline':
                    self.status = 'ok'
                self._dirty = True
            else:
                self._step_buf = []

        self._update_status()

        # Periodinen tallennus (30 s valein jos muutoksia)
        if self._dirty and (now_ms - self._last_saved_time) > 30000:
            self.save_state()

    def _update_status(self):
        """Paivittaa kaukalon tilakoodin."""
        if hasattr(self, 'last_weight_abs') and self.last_weight_abs < TRAY_MIN_PRESENT_G:
            self.status = 'no_tray'
        elif self.status == 'emptied_offline' and self.emptied_offline:
            pass  # Pidetään kunnes ensimmäinen uusi vesilisäys tai kuittaus
        elif self.water_g >= self.max_water_g:
            self.status = 'full'
        elif self.water_g >= TRAY_WARN_WATER_G:
            self.status = 'warning_full'
        else:
            self.status = 'ok'

    # ---- Ohjaus- ja kalibrointikomennot ----

    def reset_water(self):
        """Nollaa kaukalon vesilaskurin (esim. manuaalisen tyhjennyksen jalkeen)."""
        self.water_g = 0.0
        self.emptied_offline = False
        self.status = 'ok'
        self._dirty = True
        self.save_state(force=True)
        return True

    def calibrate_empty(self, current_weight=None):
        """Kalibroi nykyisen painon tyhjan kaukalon perustasoksi."""
        w = current_weight if current_weight is not None else getattr(self, 'last_weight_abs', None)
        if w is None or w < TRAY_MIN_PRESENT_G:
            return False
        self.tray_base_g = w
        self.water_g = 0.0
        self.emptied_offline = False
        self.status = 'ok'
        self._dirty = True
        self.save_state(force=True)
        return True

    def set_object_weight(self, name, grams):
        """Asettaa tunnetun esineen nimellismassan."""
        try:
            g = float(grams)
            if g <= 0:
                return False
            if name == 'cup':
                self.cup_g = g
            elif name == 'scale':
                self.scale_g = g
            elif name == 'vessel':
                self.vessel_g = g
            else:
                return False
            self._dirty = True
            self.save_state(force=True)
            return True
        except (ValueError, TypeError):
            return False

    def set_max_water(self, grams):
        """Asettaa kaukalon maksimivesimaaran."""
        try:
            g = float(grams)
            if g < 50.0 or g > 1500.0:
                return False
            self.max_water_g = g
            self._dirty = True
            self.save_state(force=True)
            return True
        except (ValueError, TypeError):
            return False

    def status_dict(self):
        """Palauttaa tilasanakirjan telemetriaa ja rajapintoja varten."""
        return {
            'tray_water_g': round(self.water_g, 1),
            'tray_pct': round(self.water_pct, 1),
            'tray_status': self.status,
            'detected_object': self.detected_object,
            'object_weight_g': round(self.object_weight, 1) if self.object_present else 0.0,
            'emptied_offline': self.emptied_offline,
            'tray_base_g': round(self.tray_base_g, 1),
            'max_water_g': round(self.max_water_g, 1)
        }

    def info(self):
        """Yksirivinen infomerkkijono sarjalokille ja komennoille."""
        return ('TRAY status=%s water=%.1fg (%.0f%%/%.0fg) obj=%s(%.1fg) emptied_off=%s base=%.1fg'
                % (self.status, self.water_g, self.water_pct, self.max_water_g,
                   self.detected_object, self.object_weight if self.object_present else 0.0,
                   self.emptied_offline, self.tray_base_g))
