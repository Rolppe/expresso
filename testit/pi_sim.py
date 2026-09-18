# Fit a plant to shot 2 (bang-bang, 20 ms loop) and compare with PI + time-proportional pump duty.
import random, math, statistics as st
def sim(ctrl, rate_on, rate_off, delay, noise, T=12.0, target=8.0, seed=1, **k):
    random.seed(seed); dt=0.002; t=0; p=8.0; hist=[]; pump=0; samples=[]; pumpseq=[]; true=[]
    acts=[0]*int(delay/dt)  # actuator transport delay queue
    integ=0.0; win_start=0; duty=0.5; last_ctrl=-1; on_since=0
    ff=k.get('ff',0.5); kp=k.get('kp',0.15); ki=k.get('ki',0.3); window=k.get('window',0.1)
    while t<T:
        if t-last_ctrl>=0.023:  # loop period measured ~23 ms (incl 20 ms pressure window)
            last_ctrl=t
            meas=p+random.gauss(0,noise)
            if ctrl=='bang':
                if meas<target-0.15: pump=1
                elif meas>=target+0.15: pump=0
            else:
                e=target-meas
                integ=max(-1.5,min(1.5,integ+e*0.023))
                duty=max(0.0,min(1.0,ff+kp*e+ki*integ))
                if t-win_start>=window: win_start=t
                # 20 ms resolution inside the window (one mains cycle)
                pump=1 if (t-win_start) < round(duty*window/0.02)*0.02 else 0
            if t>2: samples.append(meas); pumpseq.append(pump); true.append(p)
        acts.append(pump); a=acts.pop(0)
        p+= (rate_on*(1-p/13.0)*13/5 if a else -rate_off*p/8.0)*dt  # ~+10 bar/s on, ~-10 bar/s off at 8 bar
        t+=dt
    s100=samples[::4]
    sw=sum(1 for i in range(1,len(pumpseq)) if pumpseq[i]!=pumpseq[i-1])
    return min(s100),max(s100),st.mean(samples),st.pstdev(samples),sw/(T-2),min(true),max(true),st.pstdev(true)

for name,kw in [("bang-bang",dict()),("PI w100 kp0.2 ki0.3",dict(kp=0.2,ki=0.3,window=0.1))]:
    for ron,roff in [(10,10),(14,8),(7,12)]:
        r=sim('bang' if name=='bang-bang' else 'pi',ron,roff,0.07,0.3,T=14,**kw)
        print("%-20s plant %2d/%2d  measured sd %.2f | TRUE pressure min %.1f max %.1f sd %.2f"%(name,ron,roff,r[3],r[5],r[6],r[7]))
