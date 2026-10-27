#!/usr/bin/env python3
"""
Savutesti: EXPRESSO-TILAUS-INVARIANTIT
Varmistaa, että:
1. Kaikki tilauksen menetelmäkohdat (TILAUS-A...TILAUS-T, TILAUS-RELEET-ALAS, TILAUS-AUTONOMIA)
   on määritelty KAYTTAJAN-TIEDOT.md:ssä lainauksina ja viittein.
2. paketit/PUMPPU-PWM.md:n vaihetaulukossa (vaiheet 1a-1f, 2, 3, 4) on Tilauskohdan tunnus -sarake.
3. REKISTERI.md sisältää luvun '## Pysyvät vaatimukset (Tilauksen invariantit)'.
4. claude/siirto/tools/vaatimukset.mjs lukee kaikki vaatimukset (--rivi).
5. vaatimukset.mjs --tarkista hyväksyy oikein merkityn briefin ja kaatuu (exit 1), jos menetelmävalinta
   on tehty nimeämättä tilausvaatimusta.
"""

import os
import re
import subprocess
import sys
import tempfile

REPO_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ROOT_DIR = os.path.abspath(os.path.join(REPO_DIR, "..", "..", ".."))

PASSED = 0
FAILED = 0


def check(desc: str, cond: bool, err_msg: str = ""):
    global PASSED, FAILED
    if cond:
        PASSED += 1
        print(f"  OK: {desc}")
    else:
        FAILED += 1
        print(f"  FAIL: {desc} - {err_msg}")


def main():
    print("=== Savutesti: EXPRESSO-TILAUS-INVARIANTIT ===")

    # 1. Tarkista KAYTTAJAN-TIEDOT.md
    kayttajan_tiedot_path = os.path.join(REPO_DIR, "KAYTTAJAN-TIEDOT.md")
    check("KAYTTAJAN-TIEDOT.md on olemassa", os.path.exists(kayttajan_tiedot_path))

    with open(kayttajan_tiedot_path, "r", encoding="utf-8") as f:
        kt_content = f.read()

    expected_orders = [
        "TILAUS-A", "TILAUS-B", "TILAUS-C", "TILAUS-D", "TILAUS-E",
        "TILAUS-F", "TILAUS-G", "TILAUS-H", "TILAUS-I", "TILAUS-J",
        "TILAUS-K", "TILAUS-L", "TILAUS-M", "TILAUS-N", "TILAUS-O",
        "TILAUS-P", "TILAUS-Q", "TILAUS-R", "TILAUS-S", "TILAUS-T",
        "TILAUS-RELEET-ALAS", "TILAUS-AUTONOMIA"
    ]

    for order_id in expected_orders:
        pattern = rf"\*\*{re.escape(order_id)} — .*?\*\*"
        m = re.search(pattern, kt_content, re.DOTALL)
        check(f"KAYTTAJAN-TIEDOT.md sisältää vaatimusrivin {order_id}", bool(m))

    # Tarkista viitteet PUMPPU-PWM.md:hen
    check("TILAUS-A viittaa PUMPPU-PWM.md:hen", "paketit/PUMPPU-PWM.md:13-14" in kt_content)
    check("TILAUS-B viittaa PUMPPU-PWM.md:hen", "paketit/PUMPPU-PWM.md:14-16" in kt_content)
    check("TILAUS-C viittaa PUMPPU-PWM.md:hen", "paketit/PUMPPU-PWM.md:16-18" in kt_content)
    check("TILAUS-D viittaa PUMPPU-PWM.md:hen", "paketit/PUMPPU-PWM.md:18" in kt_content)
    check("TILAUS-E viittaa PUMPPU-PWM.md:hen", "paketit/PUMPPU-PWM.md:19-20" in kt_content)
    check("TILAUS-S viittaa PUMPPU-PWM.md:hen", "paketit/PUMPPU-PWM.md:21" in kt_content)
    check("TILAUS-T viittaa PUMPPU-PWM.md:hen", "paketit/PUMPPU-PWM.md:22" in kt_content)

    # 2. Tarkista paketit/PUMPPU-PWM.md
    pud_path = os.path.join(REPO_DIR, "paketit", "PUMPPU-PWM.md")
    check("PUMPPU-PWM.md on olemassa", os.path.exists(pud_path))
    with open(pud_path, "r", encoding="utf-8") as f:
        pud_content = f.read()

    check("PUMPPU-PWM.md sisältää 'Tilauskohdan tunnus' -sarakkeen", "| Tilauskohdan tunnus |" in pud_content)
    check("PUMPPU-PWM.md vaihe 1c sisältää TILAUS-L", re.search(r"\|\s*1c\s*\|\s*`TILAUS-L`\s*\|", pud_content) is not None)
    check("PUMPPU-PWM.md vaihe 1d sisältää TILAUS-L", re.search(r"\|\s*1d\s*\|\s*`TILAUS-L`\s*\|", pud_content) is not None)
    check("PUMPPU-PWM.md vaihe 1e sisältää TILAUS-C", re.search(r"\|\s*1e\s*\|\s*`TILAUS-C`", pud_content) is not None)
    check("PUMPPU-PWM.md vaihe 1f sisältää TILAUS-D", re.search(r"\|\s*1f\s*\|\s*`TILAUS-D`\s*\|", pud_content) is not None)
    check("PUMPPU-PWM.md vaihe 2 sisältää TILAUS-E", re.search(r"\|\s*2\s*\|\s*`TILAUS-E`\s*\|", pud_content) is not None)
    check("PUMPPU-PWM.md vaihe 3 sisältää TILAUS-S", re.search(r"\|\s*3\s*\|\s*`TILAUS-S`\s*\|", pud_content) is not None)
    check("PUMPPU-PWM.md vaihe 4 sisältää TILAUS-T", re.search(r"\|\s*4\s*\|\s*`TILAUS-T`\s*\|", pud_content) is not None)

    # 3. Tarkista REKISTERI.md
    rekisteri_path = os.path.join(REPO_DIR, "REKISTERI.md")
    with open(rekisteri_path, "r", encoding="utf-8") as f:
        rek_content = f.read()

    check("REKISTERI.md sisältää luvun 'Pysyvät vaatimukset (Tilauksen invariantit)'",
          "## Pysyvät vaatimukset (Tilauksen invariantit)" in rek_content or
          re.search(r"^## (Pysyvät vaatimukset|Luettava joka purussa)\b", rek_content, re.MULTILINE) is not None)

    # 4. Tarkista vaatimukset.mjs --rivi "infra expresso"
    node_bin = "/opt/homebrew/bin/node" if os.path.exists("/opt/homebrew/bin/node") else "node"
    vaatimukset_tool = os.path.join(ROOT_DIR, "claude", "siirto", "tools", "vaatimukset.mjs")
    check("vaatimukset.mjs on olemassa", os.path.exists(vaatimukset_tool))

    env = dict(os.environ)
    env["PATH"] = f"/opt/homebrew/bin:{env.get('PATH', '')}"

    res = subprocess.run([node_bin, vaatimukset_tool, "--rivi", "infra expresso"],
                         cwd=ROOT_DIR, env=env, capture_output=True, text=True)
    check("vaatimukset.mjs --rivi poistui koodilla 0", res.returncode == 0)
    for order_id in expected_orders:
        check(f"vaatimukset.mjs --rivi tulostaa {order_id}", f"**{order_id} — " in res.stdout)

    # 5. Tarkista vaatimukset.mjs --tarkista läpäisevällä ja hylkäävällä syötteellä
    valid_brief_path = os.path.join(REPO_DIR, "paketit", "TILAUS-INVARIANTIT.brief.md")
    res_valid = subprocess.run([node_bin, vaatimukset_tool, "--tarkista", "infra expresso", valid_brief_path],
                               cwd=ROOT_DIR, env=env, capture_output=True, text=True)
    check("vaatimukset.mjs hyväksyy oikean briefin (exit 0)", res_valid.returncode == 0)

    # Luodaan väliaikainen brief, jossa valitaan menetelmä ilman VAATIMUS-riviä
    with tempfile.NamedTemporaryFile("w", suffix=".brief.md", delete=False, encoding="utf-8") as tf:
        tf.write("""# TEST-FAIL-BRIEF

## Menetelmä
Tässä briefissä valitaan menetelmäksi jokin uusi keino ilman vaatimusta.
""")
        temp_fail_path = tf.name

    try:
        res_fail = subprocess.run([node_bin, vaatimukset_tool, "--tarkista", "infra expresso", temp_fail_path],
                                  cwd=ROOT_DIR, env=env, capture_output=True, text=True)
        check("vaatimukset.mjs kaataa briefin ilman VAATIMUS-riviä (exit 1)", res_fail.returncode == 1)
        check("vaatimukset.mjs tulostaa virheen 'menetelmävalinta ilman vaatimusviittausta'",
              "menetelmävalinta ilman vaatimusviittausta" in res_fail.stderr)
    finally:
        if os.path.exists(temp_fail_path):
            os.remove(temp_fail_path)

    # Luodaan väliaikainen brief, jossa on hyväksytty menetelmävalinta ja VAATIMUS-rivi
    with tempfile.NamedTemporaryFile("w", suffix=".brief.md", delete=False, encoding="utf-8") as tf:
        tf.write("""# TEST-PASS-BRIEF

VAATIMUS: TILAUS-A

## Menetelmä
Tässä briefissä valitaan menetelmäksi menetelmä A.
""")
        temp_pass_path = tf.name

    try:
        res_pass = subprocess.run([node_bin, vaatimukset_tool, "--tarkista", "infra expresso", temp_pass_path],
                                  cwd=ROOT_DIR, env=env, capture_output=True, text=True)
        check("vaatimukset.mjs hyväksyy menetelmävalinnan VAATIMUS-rivillä (exit 0)", res_pass.returncode == 0)
    finally:
        if os.path.exists(temp_pass_path):
            os.remove(temp_pass_path)

    print(f"\nRESULT: {FAILED} failed, {PASSED} passed")
    sys.exit(1 if FAILED > 0 else 0)


if __name__ == "__main__":
    main()
