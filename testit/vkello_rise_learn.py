#!/usr/bin/env python3
"""vkello_rise_learn.py — TILAUS-G 24.9.2026: kello oppii ajon b nousun ikkunoista (VKELLO_R, p >= 1 bar,
amplitudiportti) korjattuna ja korjaamatta; tulostaa virheen nousun lopussa ja tasanteen alussa.
Aja projektin juuresta: python3 testit/vkello_rise_learn.py"""
import io, sys, statistics as S
from contextlib import redirect_stdout
sys.path.insert(0,'testit')
import vkello_analyysi as A
vk=A.load_fw()
with redirect_stdout(io.StringIO()): st=A.analyse(vk,'testit/vkello-20260924-b.log')
rise=[r for r in st['rise'] if 'res' in r]; rows=st['rows']
for b,label in (((0,0),'ei korjausta'),((164,-175),'korjaus 164-175*dp'),((231,-198),'korjaus 23.9-sovitus')):
    c=vk.Verkkokello(0); prev=None; used=0
    for r in rise:
        dp=(r['p']-prev['p'])/((r['t']-prev['t'])/1e6) if prev else 0.0; prev=r
        if r['p']<1.0: continue   # tayttovaihe
        d=0.0 if dp<=0.5 else b[0]+b[1]*dp
        ti=int(round(r['t'])); z=A.wrap(r['E']-d-c.edge(ti),c.T)
        if c.gate(r['amp']): c.update(ti,z); used+=1
    # kellon virhe nousun lopussa ja ensimmaisissa tasanneikkunoissa (tosi kayra = E - res)
    t_end=int(round(rise[-1]['t'])); e_end=A.wrap(c.edge(t_end)-(rise[-1]['E']-rise[-1]['res']))
    errs=[]
    for r in rows[:10]:
        ti=int(round(r['t'])); errs.append(A.wrap(c.edge(ti)-(r['E']-r['res'])))
    print('%-22s ikkunoita %2d  lukittu %s  virhe nousun lopussa %+5.0f us  tasanne k0-9 %s  T %.2f'%(
        label,used,c.locked(t_end),e_end,' '.join('%+.0f'%e for e in errs),c.T))
