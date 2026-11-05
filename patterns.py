"""Chart pattern breakout / breakdown detection + candlestick signals.
bars: list of dicts d,o,h,l,c,v (oldest first). Sab index bars list ke hisaab se hain."""
from technical import avg, ema, pivots

DESC = {
    "Ascending triangle": "Upar resistance lagbhag flat hai aur neeche ke low badhte ja rahe hain. Buyers dabaav bana rahe hain; resistance ke upar close hone par aam taur par tezi aati hai.",
    "Descending triangle": "Neeche support flat hai aur upar ke high girte ja rahe hain. Sellers haavi hain; support tootne par giravat tez ho sakti hai.",
    "Symmetrical triangle": "High neeche aur low upar aa rahe hain, price tang ho raha hai. Jis taraf se line tootegi, usi taraf badi move aati hai.",
    "Rectangle (range)": "Price kuch hafte se ek upar-neeche ki patti (range) me ghoom raha hai. Range ke upar ya neeche close hone par move shuru hoti hai.",
    "Rising wedge": "Price upar ja raha hai par daayra tang ho raha hai, taaqat kam ho rahi hai. Aksar neeche toot-ta hai (bearish).",
    "Falling wedge": "Price gir raha hai par daayra tang ho raha hai, giravat ki taaqat kam ho rahi hai. Aksar upar breakout hota hai (bullish).",
    "Double bottom": "Price do baar lagbhag same support se wapas uthaa (W shape). Neckline ke upar close hone par tezi ki umeed.",
    "Double top": "Price do baar lagbhag same resistance se wapas gira (M shape). Neckline ke neeche close hone par giravat ki umeed.",
    "Head & shoulders": "Teen top: beech wala sabse ooncha (head). Neckline tootne par badi giravat aa sakti hai (bearish reversal).",
    "Inverse head & shoulders": "Teen bottom: beech wala sabse neecha (head). Neckline ke upar close hone par tezi ki umeed (bullish reversal).",
    "Bull flag": "Tez uchhal (pole) ke baad price thodi der chhoti range me aaram karta hai. Flag ke upar breakout hone par tezi aksar jaari rehti hai.",
    "Bear flag": "Tez giravat (pole) ke baad price thodi der chhoti range me rukta hai. Flag ke neeche toot-ne par giravat aksar jaari rehti hai.",
}


def _candles(b):
    """Aakhri 5 candles ke candlestick signals."""
    n = len(b)
    out = []
    for i in range(max(3, n - 5), n):
        o, h, l, c = b[i]["o"], b[i]["h"], b[i]["l"], b[i]["c"]
        rng = h - l
        if rng <= 0:
            continue
        body = abs(c - o)
        up = h - max(o, c)
        lo = min(o, c) - l
        po, pc = b[i - 1]["o"], b[i - 1]["c"]
        fell = b[i - 3]["c"] > b[i - 1]["c"]
        rose = b[i - 3]["c"] < b[i - 1]["c"]
        t = None
        if c > o and pc < po and c >= po and o <= pc and body > abs(pc - po):
            t = ("Bullish engulfing (khareedaar haavi)", "g")
        elif c < o and pc > po and c <= po and o >= pc and body > abs(pc - po):
            t = ("Bearish engulfing (bechne wale haavi)", "r")
        elif body > 0 and lo >= 2 * body and up <= body * .6 and fell:
            t = ("Hammer (neeche se khareedari, bullish)", "g")
        elif body > 0 and up >= 2 * body and lo <= body * .6 and rose:
            t = ("Shooting star (upar se bikwali, bearish)", "r")
        elif i >= 2 and b[i - 2]["c"] < b[i - 2]["o"] and abs(b[i - 1]["c"] - b[i - 1]["o"]) < abs(b[i - 2]["c"] - b[i - 2]["o"]) * .5 \
                and c > o and c > (b[i - 2]["o"] + b[i - 2]["c"]) / 2:
            t = ("Morning star (bottom ka sanket, bullish)", "g")
        elif i >= 2 and b[i - 2]["c"] > b[i - 2]["o"] and abs(b[i - 1]["c"] - b[i - 1]["o"]) < abs(b[i - 2]["c"] - b[i - 2]["o"]) * .5 \
                and c < o and c < (b[i - 2]["o"] + b[i - 2]["c"]) / 2:
            t = ("Evening star (top ka sanket, bearish)", "r")
        elif body <= rng * .1:
            t = ("Doji (dono taraf barabar, faisla baaki)", "y")
        elif body >= rng * .85 and c > o:
            t = ("Strong green candle (poori khareedari)", "g")
        elif body >= rng * .85 and c < o:
            t = ("Strong red candle (poori bikwali)", "r")
        if t:
            out.append({"i": i, "t": t[0], "k": t[1]})
    return out


def _line_fit(idx, ys):
    """Pivot points ko jodne wali line (pehle aur aakhri pivot se)."""
    return (idx[0], ys[0], idx[-1], ys[-1])


def _at(ln, i):
    return ln[1] if ln[2] == ln[0] else ln[1] + (ln[3] - ln[1]) * (i - ln[0]) / (ln[2] - ln[0])


def _flat(i1, y, i2):
    return (i1, y, i2, y)


def _eval(x, name, up, lo, h, bias, only=None, check=True, pts=None):
    """Ek pattern (upar aur neeche ki line) par breakout/breakdown dekho."""
    n, C, H, L, V = x["n"], x["C"], x["H"], x["L"], x["V"]
    i0 = n - 1
    cur = C[i0]
    u0, l0 = _at(up, i0), _at(lo, i0)
    if check and u0 <= l0:
        return None
    # kitne din se line ke bahar band ho raha hai
    ku = 0
    j = i0
    while j >= 0 and C[j] > _at(up, j) * 1.002:
        ku += 1
        j -= 1
    kd = 0
    j = i0
    while j >= 0 and C[j] < _at(lo, j) * .998:
        kd += 1
        j -= 1
    d = state = None
    k = 0
    if 1 <= ku <= 4 and only != "down":
        d, state, k = "up", "brk", ku
    elif 1 <= kd <= 4 and only != "up":
        d, state, k = "down", "brk", kd
    elif ku == 0 and kd == 0:
        if only != "down" and bias in ("up", "both") and 0 <= (u0 - cur) / cur <= .02:
            d, state = "up", "near"
        elif only != "up" and bias in ("down", "both") and 0 <= (cur - l0) / cur <= .02:
            d, state = "down", "near"
    if not d:
        return None
    level = u0 if d == "up" else l0
    ext = abs(cur - level) / level * 100
    if state == "brk" and ext > 7:
        return None
    s = min(up[0], lo[0])
    if check:  # break se pehle price lines ke andar rehna chahiye
        cnt = bad = 0
        for j in range(max(0, s), i0 - k + 1):
            cnt += 1
            if C[j] > _at(up, j) * 1.015 or C[j] < _at(lo, j) * .985:
                bad += 1
        if cnt < 12 or bad > max(1, int(cnt * .06)):
            return None
    atr = x["atr"]
    h = min(h, cur * .2)  # measured move bahut bada na ho
    if state == "brk":
        entry = cur if ext <= 2 else level
    else:
        entry = level * (1.002 if d == "up" else .998)
    if d == "up":
        sl = _at(lo, i0) - .5 * atr
        risk = entry - sl
        if risk > entry * .09:
            sl = entry * .91
        elif risk < 1.2 * atr:
            sl = entry - 1.2 * atr
        risk = entry - sl
        t1, t2 = level + .6 * h, level + h
        if t1 < entry + risk:  # pattern chhota ya break late ho gaya
            t1, t2 = entry + 1.5 * risk, entry + 2.5 * risk
        rr = (t1 - entry) / risk
    else:
        sl = _at(up, i0) + .5 * atr
        risk = sl - entry
        if risk > entry * .09:
            sl = entry * 1.09
        elif risk < 1.2 * atr:
            sl = entry + 1.2 * atr
        risk = sl - entry
        t1, t2 = level - .6 * h, level - h
        if t1 > entry - risk:
            t1, t2 = entry - 1.5 * risk, entry - 2.5 * risk
        t2 = max(t2, entry * .02)
        t1 = max(t1, entry * .03)
        rr = (entry - t1) / risk
    # volume
    vx = None
    if state == "brk":
        b0 = i0 - k
        av = avg([v for v in V[max(0, b0 - 19):b0 + 1] if v > 0])
        bs = V[i0 - k + 1:]
        if av and bs:
            vx = max(bs) / av
    cs = x["cand"]
    good = "g" if d == "up" else "r"
    bad_k = "r" if d == "up" else "g"
    cmatch = [c for c in cs if c["i"] >= i0 - 2 and c["k"] == good]
    cagainst = [c for c in cs if c["i"] >= i0 - 2 and c["k"] == bad_k]
    sc = 40 if state == "brk" else 25
    why = []
    nm = "resistance" if d == "up" else "support"
    if state == "brk":
        why.append("Price ne %s %s (%s) ke %s close diya (%d din se, %.1f%% door)." %
                   (nm, "{:,.0f}".format(level), name, "upar" if d == "up" else "neeche", k, ext))
        if k == 1:
            sc += 7
        if ext > 4:
            sc -= 8
    else:
        why.append("Price %s %s se sirf %.1f%% door hai, abhi %s nahi hua (close ka intezaar)." %
                   (nm, "{:,.0f}".format(level), ext, "breakout" if d == "up" else "breakdown"))
    if vx is not None:
        if vx >= 2:
            sc += 25
        elif vx >= 1.5:
            sc += 18
        elif vx >= 1.2:
            sc += 8
        elif vx < .9:
            sc -= 10
        why.append("Volume average ka %.1fx hai (%s)." % (vx, "confirmation mazboot" if vx >= 1.5 else "theek" if vx >= 1.2 else "kam, false move ka risk"))
    if cmatch:
        sc += 10
        why.append("Candle signal saath de raha hai: " + cmatch[-1]["t"] + ".")
    if cagainst:
        sc -= 8
        why.append("Dhyan: ulta candle signal bhi hai: " + cagainst[-1]["t"] + ".")
    e50 = x["e50"]
    if (d == "up" and cur > e50) or (d == "down" and cur < e50):
        sc += 8
        why.append("Bada trend (50 din EMA) is direction ke saath hai.")
    else:
        sc -= 5
        why.append("Bada trend (50 din EMA) is direction ke khilaf hai, risk zyada.")
    if rr >= 1.5:
        sc += 5
    if state == "brk" and ((d == "up" and cur >= t1 * .99) or (d == "down" and cur <= t1 * 1.01)):
        sc -= 15
        why.append("Dhyan: price Target 1 ke paas pahunch chuka hai, ab naya entry risky hai.")
    sc = max(0, min(100, int(round(sc))))
    lines = []
    for ln, kk in ((up, "u"), (lo, "l")):
        a = max(s, 0)
        lines.append({"k": kk, "a": [a, _at(ln, a)], "b": [i0, _at(ln, i0)]})
    return {"name": name, "dir": d, "state": state, "bias": bias, "level": level, "entry": entry, "sl": sl, "t1": t1, "t2": t2,
            "rr": rr, "h": h, "k": k, "vx": vx, "score": sc, "label": "Strong" if sc >= 70 else "Theek" if sc >= 50 else "Kamzor",
            "why": why, "lines": lines, "pts": pts or [], "start": s, "desc": DESC.get(name, ""),
            "candle": (cmatch or cs[-1:] or [{"t": None}])[-1]["t"]}


def analyse(bars):
    """Return {"all": [pattern...], "candles": [...]} ya None. all: score ke hisaab se sorted."""
    n = len(bars)
    if n < 45:
        return None
    C = [b["c"] for b in bars]
    H = [b["h"] for b in bars]
    L = [b["l"] for b in bars]
    V = [b.get("v") or 0 for b in bars]
    i0 = n - 1
    cur = C[i0]
    tr = [max(H[i] - L[i], abs(H[i] - C[i - 1]), abs(L[i] - C[i - 1])) for i in range(n - 14, n)]
    x = {"n": n, "C": C, "H": H, "L": L, "V": V, "atr": avg(tr) or cur * .01, "e50": ema(C, 50)[i0], "cand": _candles(bars)}
    phi, plo = pivots(H, L, 3)

    def dedupe(idx, arr, hi):  # barabar wale paas-paas pivots me se ek rakho
        out = []
        for i in idx:
            if i < n - 95:
                continue
            if out and i - out[-1] < 4:
                if (arr[i] > arr[out[-1]]) == hi:
                    out[-1] = i
            else:
                out.append(i)
        return out
    phi, plo = dedupe(phi, H, True), dedupe(plo, L, False)
    res = []

    def add(r):
        if r:
            res.append(r)

    # 1) triangle / wedge / rectangle: trendline se
    T = .0008
    seen = set()
    for nh in (3, 2):
        for nl in (3, 2):
            if len(phi) < nh or len(plo) < nl:
                continue
            ph, pl = phi[-nh:], plo[-nl:]
            key = (tuple(ph), tuple(pl))
            if key in seen or ph[-1] - ph[0] < 6 or pl[-1] - pl[0] < 6:
                continue
            seen.add(key)
            up = _line_fit(ph, [H[i] for i in ph])
            lo = _line_fit(pl, [L[i] for i in pl])
            su = (up[3] - up[1]) / (up[2] - up[0]) / cur
            sl_ = (lo[3] - lo[1]) / (lo[2] - lo[0]) / cur
            uf, lf = abs(su) < T, abs(sl_) < T
            s0 = min(ph[0], pl[0])
            w0 = _at(up, s0) - _at(lo, s0)
            w1 = _at(up, i0) - _at(lo, i0)
            conv = 0 < w1 < w0 * .95
            nm = bias = None
            if uf and sl_ >= T and conv:
                nm, bias = "Ascending triangle", "up"
            elif lf and su <= -T and conv:
                nm, bias = "Descending triangle", "down"
            elif su <= -T and sl_ >= T and conv:
                nm, bias = "Symmetrical triangle", "both"
            elif uf and lf and .03 <= w0 / cur <= .16:
                nm, bias = "Rectangle (range)", "both"
            elif su >= T and sl_ >= T and sl_ > su and conv:
                nm, bias = "Rising wedge", "down"
            elif su <= -T and sl_ <= -T and su < sl_ and conv:
                nm, bias = "Falling wedge", "up"
            if nm:
                pts = [{"i": i, "y": H[i], "t": ""} for i in ph] + [{"i": i, "y": L[i], "t": ""} for i in pl]
                add(_eval(x, nm, up, lo, max(w0, cur * .02), bias, pts=pts))

    # 2) double top / double bottom
    if len(plo) >= 2:
        a, b = plo[-2], plo[-1]
        if b - a >= 8 and abs(L[a] - L[b]) / L[b] <= .03 and b >= n - 40:
            nk = max(H[a:b + 1])
            low = min(L[a], L[b])
            if nk > low * 1.05:
                add(_eval(x, "Double bottom", _flat(a, nk, i0), _flat(a, low, i0), nk - low, "up", only="up", check=False,
                          pts=[{"i": a, "y": L[a], "t": "1"}, {"i": b, "y": L[b], "t": "2"}]))
    if len(phi) >= 2:
        a, b = phi[-2], phi[-1]
        if b - a >= 8 and abs(H[a] - H[b]) / H[b] <= .03 and b >= n - 40:
            nk = min(L[a:b + 1])
            top = max(H[a], H[b])
            if nk < top * .95:
                add(_eval(x, "Double top", _flat(a, top, i0), _flat(a, nk, i0), top - nk, "down", only="down", check=False,
                          pts=[{"i": a, "y": H[a], "t": "1"}, {"i": b, "y": H[b], "t": "2"}]))

    # 3) head & shoulders (aur ulta)
    if len(phi) >= 3:
        a, b, c = phi[-3:]
        if b > a + 3 and c > b + 3 and c >= n - 35 and H[b] > H[a] * 1.02 and H[b] > H[c] * 1.02 and abs(H[a] - H[c]) <= H[b] * .05:
            ta = min(range(a, b + 1), key=lambda i: L[i])
            tb = min(range(b, c + 1), key=lambda i: L[i])
            neck = (ta, L[ta], tb, L[tb])
            hh = H[b] - _at(neck, b)
            if hh > cur * .03:
                add(_eval(x, "Head & shoulders", _flat(c, H[c], i0), (ta, L[ta], i0, _at(neck, i0)), hh, "down", only="down", check=False,
                          pts=[{"i": a, "y": H[a], "t": "LS"}, {"i": b, "y": H[b], "t": "H"}, {"i": c, "y": H[c], "t": "RS"}]))
    if len(plo) >= 3:
        a, b, c = plo[-3:]
        if b > a + 3 and c > b + 3 and c >= n - 35 and L[b] < L[a] * .98 and L[b] < L[c] * .98 and abs(L[a] - L[c]) <= L[b] * .05:
            pa = max(range(a, b + 1), key=lambda i: H[i])
            pb = max(range(b, c + 1), key=lambda i: H[i])
            neck = (pa, H[pa], pb, H[pb])
            hh = _at(neck, b) - L[b]
            if hh > cur * .03:
                add(_eval(x, "Inverse head & shoulders", (pa, H[pa], i0, _at(neck, i0)), _flat(c, L[c], i0), hh, "up", only="up", check=False,
                          pts=[{"i": a, "y": L[a], "t": "LS"}, {"i": b, "y": L[b], "t": "H"}, {"i": c, "y": L[c], "t": "RS"}]))

    # 4) bull flag / bear flag (flag ke baad 1-4 candle me break)
    for sgn, nm in ((1, "Bull flag"), (-1, "Bear flag")):
        done = False
        for k in range(5, 18):
            pe = i0 - k
            if pe < 12 or done:
                break
            ps = min(C[pe - 10:pe]) if sgn > 0 else max(C[pe - 10:pe])
            pole = sgn * (C[pe] / ps - 1)
            if pole < .10:
                continue
            for j in range(1, 5):
                e = i0 - j
                if e - pe < 4:
                    break
                fh, fl = max(H[pe:e + 1]), min(L[pe:e + 1])
                drift_ok = C[e] <= C[pe] * 1.01 if sgn > 0 else C[e] >= C[pe] * .99
                ret = (C[pe] - fl) / (C[pe] - ps) if sgn > 0 else (fh - C[pe]) / (ps - C[pe])
                if (fh - fl) / cur <= .09 and ret < .5 and drift_ok:
                    r = _eval(x, nm, _flat(pe, fh, i0), _flat(pe, fl, i0), abs(C[pe] - ps), "up" if sgn > 0 else "down",
                              only="up" if sgn > 0 else "down", check=False,
                              pts=[{"i": pe, "y": H[pe] if sgn > 0 else L[pe], "t": "Pole %d%%" % round(sgn * pole * 100)}])
                    if r:
                        add(r)
                        done = True
                        break

    # same naam + direction ke duplicate hatao (sabse achha score rakho)
    uniq = {}
    for r in res:
        kk = (r["name"], r["dir"])
        if kk not in uniq or r["score"] > uniq[kk]["score"]:
            uniq[kk] = r
    res = list(uniq.values())

    res.sort(key=lambda r: (r["state"] != "brk", -r["score"]))
    return {"all": res, "candles": x["cand"]}


def best(bars):
    """Scanner ke liye: sabse achha pattern (bina geometry ke)."""
    a = analyse(bars)
    if not a or not a["all"]:
        return None
    r = dict(a["all"][0])
    for k in ("lines", "pts", "desc", "start"):
        r.pop(k, None)
    r["why"] = r["why"][:2]
    return r
