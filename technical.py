"""Breakout / volume / pattern analysis (same logic as the Stock Advisor app)."""
import math


def avg(a):
    a = list(a)
    return sum(a) / len(a) if a else 0.0


def ema(a, n):
    k = 2 / (n + 1)
    e = a[0]
    out = []
    for i, v in enumerate(a):
        if i:
            e = v * k + e * (1 - k)
        out.append(e)
    return out


def rsi14(c):
    if len(c) < 16:
        return None
    g = l = 0.0
    for i in range(1, 15):
        d = c[i] - c[i - 1]
        if d > 0:
            g += d
        else:
            l -= d
    g /= 14
    l /= 14
    for i in range(15, len(c)):
        d = c[i] - c[i - 1]
        g = (g * 13 + max(d, 0)) / 14
        l = (l * 13 + max(-d, 0)) / 14
    return 100.0 if l == 0 else 100 - 100 / (1 + g / l)


def pivots(H, L, w):
    hi, lo = [], []
    for i in range(w, len(H) - w):
        h = l = True
        for j in range(i - w, i + w + 1):
            if H[j] > H[i]:
                h = False
            if L[j] < L[i]:
                l = False
        if h:
            hi.append(i)
        if l:
            lo.append(i)
    return hi, lo


def analyse(bars):
    """bars: list of dicts d,h,l,c,v (oldest first). Returns dict or None."""
    n = len(bars)
    if n < 40:
        return None
    C = [b["c"] for b in bars]
    H = [b["h"] for b in bars]
    L = [b["l"] for b in bars]
    V = [b.get("v") or 0 for b in bars]
    i0 = n - 1
    cur = C[i0]

    def mx(a, f, t):
        return max(a[max(0, f):t])

    def mn(a, f, t):
        return min(a[max(0, f):t])

    base = mx(H, i0 - 25, i0 - 5)
    lvl50 = mx(H, i0 - 50, i0) if n >= 52 else None
    low20 = mn(L, i0 - 20, i0)
    above = cur > base
    near = (not above) and cur >= base * .98
    breakdown = cur < mn(C, i0 - 20, i0)
    run = 0
    while run <= i0 and C[i0 - run] > base:
        run += 1
    fresh = above and run <= 5
    ext = (cur - base) / base * 100
    vi = i0
    while vi > 20 and (bars[vi].get("live") or not V[vi]):
        vi -= 1
    av20 = avg([v for v in V[vi - 20:vi] if v > 0])
    vol_x = V[vi] / av20 if av20 else None
    bs = V[max(0, i0 - run + 1):vi + 1]
    bvx = max(bs) / av20 if (fresh and av20 and bs) else None
    vx = bvx or vol_x
    up = dn = 0.0
    for i in range(max(1, vi - 19), vi + 1):
        if C[i] >= C[i - 1]:
            up += V[i]
        else:
            dn += V[i]
    udr = up / dn if dn else None
    o = 0
    obv = [0]
    for i in range(1, n):
        o += V[i] if C[i] > C[i - 1] else (-V[i] if C[i] < C[i - 1] else 0)
        obv.append(o)
    obv_up = obv[vi] > obv[max(0, vi - 20)]
    bw = []
    for i in range(19, n):
        w = C[i - 19:i + 1]
        m = avg(w)
        sd = math.sqrt(avg([(x - m) ** 2 for x in w]))
        bw.append(4 * sd / m if m else 0)
    q25 = sorted(bw)[int(len(bw) * .25)]
    sqz = min(bw[-10:]) <= q25
    tr = [max(H[i] - L[i], abs(H[i] - C[i - 1]), abs(L[i] - C[i - 1])) for i in range(n - 14, n)]
    atr = avg(tr)
    e20 = ema(C, 20)[i0]
    e50 = ema(C, 50)[i0]
    m12, m26 = ema(C, 12), ema(C, 26)
    mac = [a - b for a, b in zip(m12, m26)]
    sg = ema(mac, 9)
    hist, hist_p = mac[i0] - sg[i0], mac[i0 - 1] - sg[i0 - 1]

    phi, plo = pivots(H, L, 3)
    ph = [i for i in phi if i >= n - 60][-2:]
    pl = [i for i in plo if i >= n - 60][-2:]
    pat = []

    def nr(x, y, t):
        return abs(x - y) / y <= t

    if len(ph) == 2 and len(pl) == 2:
        ft = nr(H[ph[0]], H[ph[1]], .015)
        fb = nr(L[pl[0]], L[pl[1]], .015)
        rl = L[pl[1]] > L[pl[0]] * 1.01
        fh = H[ph[1]] < H[ph[0]] * .99
        if ft and rl:
            pat.append(("Ascending triangle", "g"))
        elif fb and fh:
            pat.append(("Descending triangle", "r"))
        elif fh and rl:
            pat.append(("Symmetrical triangle", "y"))
        if H[ph[1]] > H[ph[0]] * 1.005 and L[pl[1]] > L[pl[0]] * 1.005:
            pat.append(("Higher highs / higher lows", "g"))
        if H[ph[1]] < H[ph[0]] * .995 and L[pl[1]] < L[pl[0]] * .995:
            pat.append(("Lower highs / lower lows", "r"))
    if len(pl) == 2 and pl[1] - pl[0] >= 8 and nr(L[pl[0]], L[pl[1]], .03):
        nk = mx(H, pl[0], pl[1] + 1)
        if pl[1] >= n - 25 and nk > L[pl[1]] * 1.06:
            pat.append(("Double bottom neckline %d" % round(nk), "g" if cur >= nk * .98 else "y"))
    if len(ph) == 2 and ph[1] - ph[0] >= 8 and nr(H[ph[0]], H[ph[1]], .03):
        vl = mn(L, ph[0], ph[1] + 1)
        if ph[1] >= n - 25 and vl < H[ph[1]] * .94:
            pat.append(("Double top neckline %d" % round(vl), "r" if cur <= vl * 1.02 else "y"))
    rng = (mx(H, i0 - 14, n) - mn(L, i0 - 14, n)) / cur
    if rng <= .08:
        pat.append(("Consolidation box %.1f%%" % (rng * 100), "y"))
    for k in range(5, 13):
        pe = i0 - k
        ps = mn(C, pe - 10, pe)
        pole = C[pe] / ps - 1
        if pole >= .10:
            fl, fh = mn(L, pe, n), mx(H, pe, n)
            ret = (C[pe] - fl) / (C[pe] - ps)
            if (fh - fl) / cur <= .08 and ret < .5:
                pat.append(("Bull flag after %d%% rise" % round(pole * 100), "g"))
                break
    res_up = sorted([H[i] for i in phi if H[i] > cur * 1.002])
    sup_dn = sorted([L[i] for i in plo if L[i] < cur * .998], reverse=True)
    res_up = res_up[0] if res_up else None
    sup_dn = sup_dn[0] if sup_dn else None

    sc = 30
    if breakdown:
        sc -= 40
    elif above:
        if fresh:
            sc += 35
        else:
            sc += 8
        if lvl50 and cur > lvl50:
            sc += 8
        if ext > 8:
            sc -= 12
    elif near:
        sc += 15
    if vx is not None:
        if vx >= 2:
            sc += 20
        elif vx >= 1.5:
            sc += 14
        elif vx >= 1.2:
            sc += 6
        elif above and fresh:
            sc -= 8
    if udr is not None:
        if udr >= 1.3:
            sc += 5
        elif udr < .77:
            sc -= 5
    if obv_up:
        sc += 4
    if cur > e20 and e20 > e50:
        sc += 10
    elif cur > e50:
        sc += 4
    else:
        sc -= 6
    if sqz:
        sc += 8
    if hist > 0:
        sc += 4
    pg = 0
    for _, k in pat:
        if k == "g" and pg < 12:
            sc += 6
            pg += 6
        elif k == "r":
            sc -= 8
    r = rsi14(C)
    if r is not None:
        if r > 78:
            sc -= 6
        elif r >= 55:
            sc += 4
        elif r < 40:
            sc -= 4
    sc = max(0, min(100, round(sc)))
    state = "bd" if breakdown else "brk" if (above and fresh) else "near" if near else "none"
    if state == "bd":
        label = "Breakdown"
    elif state == "brk":
        label = "Strong breakout" if sc >= 75 else "Achha breakout" if sc >= 60 else "Kamzor breakout"
    elif state == "near" and sc >= 45:
        label = "Breakout ke kareeb"
    else:
        label = "Koi breakout nahi"
    sl = max(cur - 2 * atr, (sup_dn or low20) * .995)
    if not sl < cur * .99:
        sl = cur - 1.5 * atr
    risk = cur - sl
    k = "r" if state == "bd" else ("g" if (state == "brk" and sc >= 60) else "y")
    head = ("Breakout %d ke upar" % round(base) if state == "brk"
            else "Level %d ke paas" % round(base) if state == "near" else "Level %d" % round(base))
    summ = head + " | Volume " + (("%.1fx" % vx) if vx else "-") + ((" | " + pat[0][0].split(" (")[0].split(":")[0]) if pat else "")
    return {
        "score": sc, "label": label, "k": k, "sum": summ, "state": state, "base": base, "ext": ext,
        "vol_x": vx, "volX": vx, "patterns": [t for t, _ in pat], "atr": atr, "entry": cur,
        "sl": sl, "t1": cur + 2 * risk, "t2": max(base + (base - low20), cur + 3 * risk),
        "res_up": res_up, "sup_dn": sup_dn,
    }
