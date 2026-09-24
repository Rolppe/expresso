#!/usr/bin/env python3
"""vkello_dpdt_replay.py — TILAUS-G 24.9.2026: kiintea nousunopeuskorjaus delta = a + b*dp (dp > 0,5 bar/s)
sovitetaan yhden paivan ajoista ja replay toisen paivan lokeilla: base (nykyiset portit), corr (korjaus +
portit), nopgate (korjaus ilman paineporttia). Aja projektin juuresta: python3 testit/vkello_dpdt_replay.py"""
import io, os, sys, statistics as S
from contextlib import redirect_stdout
sys.path.insert(0,'testit')
import vkello_analyysi as A, vkello_dpdt as D
vk=A.load_fw()
def fitcoef(paths):
    data=[]
    for p in paths:
        with redirect_stdout(io.StringIO()): data+=D.windows(vk,'testit/'+p)
    X=[[1.0,x['dp']] for x in data if x['dp']>0.5]; y=[x['res'] for x in data if x['dp']>0.5]
    return D.lstsq(X,y)
def delta(dp,b): return 0.0 if dp<=0.5 else b[0]+b[1]*dp
def replay(path,b,mode):
    with redirect_stdout(io.StringIO()): st=A.analyse(vk,'testit/'+path)
    rows=st['rows']
    # curve: rebuild as analyse did: E - res
    c=vk.Verkkokello(0); bad=mx=lk=acc=0; errs=[]
    prev=None
    for i,r in enumerate(rows):
        curve=r['E']-r['res'] if 'res' in r else None
        ti=int(round(r['t']))
        if i and c.locked(ti) and curve is not None:
            e=abs(A.wrap(c.edge(ti)-(r['E']-r['res']))); lk+=1; mx=max(mx,e); bad+=e>vk.LOCK_US; errs.append(e)
        dp=0.0
        if prev is not None and prev['seg']==r['seg']: dp=(r['p']-prev['p'])/((r['t']-prev['t'])/1e6)
        prev=r
        E=r['E']-(delta(dp,b) if mode!='base' else 0.0)
        z=A.wrap(E-c.edge(ti),c.T)
        if mode=='nopgate': g=0 if c.gate(r['amp']) else 1
        else: g=c.accept(r['amp'],r['p'])
        if g==0: c.update(ti,z); acc+=1
    return bad,mx,lk,acc,len(rows)
logs=['vkello-20260923-e.log','vkello-20260923-g.log','vkello-20260923-h.log','vkello-20260924-b.log']
for train,test in ((logs[:3],logs[3:]),(logs[3:],logs[:3]),(logs,logs)):
    b=fitcoef(train); print('sovitus %s: delta = %.0f %+.0f*dp (dp>0.5)'%('+'.join(t[6:16] for t in train),b[0],b[1]))
    for t in test:
        out=[]
        for mode in ('base','corr','nopgate'):
            bad,mx,lk,acc,n=replay(t,b,mode); out.append('%s >1000us %2d/%3d max %4.0f lupa %3d/%d'%(mode,bad,lk,mx,acc,n))
        print('  ',t[6:17],' | '.join(out))
