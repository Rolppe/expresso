import re, statistics as st, sys
lines = open(sys.argv[1], encoding='utf-8', errors='replace').read().splitlines()
pi = [l.split() for l in lines if re.match(r'^PI \d', l)]
ts = [l.split() for l in lines if l.startswith('TS ')]
print('PI', len(pi), 'TS', len(ts), [l for l in lines if re.search(r'TS_END|PI_END|CMD_OK', l)])
if pi:
    t0 = int(pi[0][1]); ps = [float(x[2]) for x in pi]
    print('PI: max %.1f' % max(ps), ' '.join('%.1f:%s' % ((int(x[1]) - t0) / 1000, x[2]) for x in pi[::3]))
if ts:
    v = [(float(x[1]), float(x[2]), float(x[3]), float(x[5]), float(x[6]) if len(x) > 6 else float(x[2])) for x in ts]
    reach = [i for i, x in enumerate(v) if x[4] >= x[2] - 0.5]
    if reach:
        a = v[reach[0]:]
        raw = [x[1] for x in a]; filt = [x[4] for x in a]
        print('brew from %.1f s: raw min %.1f max %.1f mean %.2f sd %.2f | filtered min %.1f max %.1f sd %.2f | duty mean %.2f' % (
            a[0][0] / 1000, min(raw), max(raw), st.mean(raw), st.pstdev(raw), min(filt), max(filt), st.pstdev(filt), st.mean(x[3] for x in a)))
        late = [x for x in a if x[0] >= a[0][0] + 5000]
        if late:
            r = [x[1] for x in late]
            print('from +5 s: raw min %.1f max %.1f mean %.2f sd %.2f' % (min(r), max(r), st.mean(r), st.pstdev(r)))
