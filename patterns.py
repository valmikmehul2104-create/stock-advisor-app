"""Chart pattern breakout / breakdown detection + candlestick signals.
bars: list of dicts d,o,h,l,c,v (oldest first). Sab index bars list ke hisaab se hain."""
from technical import avg, ema, pivots

"""Chart pattern breakout / breakdown / forming detection + candlestick + gap signals.
bars: list of dicts d,o,h,l,c,v (oldest first). Sab index bars list ke hisaab se hain.
Same engine daily, weekly aur monthly bars par chalta hai (tf sirf label hai)."""
import numpy as np

from technical import avg, ema, pivots

DESC = {
    "Ascending triangle": "Upar resistance lagbhag flat hai aur neeche ke low badhte ja rahe hain. Buyers dabaav bana rahe hain; resistance ke upar close hone par aam taur par tezi aati hai.",
    "Descending triangle": "Neeche support flat hai aur upar ke high girte ja rahe hain. Sellers haavi hain; support tootne par giravat tez ho sakti hai.",
    "Symmetrical triangle": "High neeche aur low upar aa rahe hain, price tang ho raha hai. Jis taraf se line tootegi, usi taraf badi move aati hai.",
    "Rectangle (range)": "Price kuch samay se ek upar-neeche ki patti (range) me ghoom raha hai. Range ke upar ya neeche close hone par move shuru hoti hai.",
    "Rising wedge": "Price upar ja raha hai par daayra tang ho raha hai, taaqat kam ho rahi hai. Aksar neeche toot-ta hai (bearish).",
    "Falling wedge": "Price gir raha hai par daayra tang ho raha hai, giravat ki taaqat kam ho rahi hai. Aksar upar breakout hota hai (bullish).",
    "Ascending channel": "Price do samantar (parallel) upar uthti lines ke beech chadh raha hai. Trend upar hai; neeche wali line tootne par trend kamzor padta hai, upar wali line ke upar close hone par tezi badhti hai.",
    "Descending channel": "Price do samantar (parallel) neeche jaati lines ke beech gir raha hai. Trend neeche hai; upar wali line ke upar close hone par trend palat sakta hai.",
    "Broadening formation (megaphone)": "High upar aur low neeche ja rahe hain, daayra chaura ho raha hai (megaphone). Bazaar me uljhan aur zyada utaar-chadhav; aksar top par banta hai, isliye risk zyada.",
    "Double bottom": "Price do baar lagbhag same support se wapas uthaa (W shape). Neckline ke upar close hone par tezi ki umeed.",
    "Double top": "Price do baar lagbhag same resistance se wapas gira (M shape). Neckline ke neeche close hone par giravat ki umeed.",
    "Triple bottom": "Price teen baar lagbhag same support se uthaa. Support bahut mazboot hai; neckline ke upar close hone par bada reversal (bullish).",
    "Triple top": "Price teen baar lagbhag same resistance se gira. Resistance bahut mazboot hai; neckline ke neeche close hone par bada reversal (bearish).",
    "Head & shoulders": "Teen top: beech wala sabse ooncha (head). Neckline tootne par badi giravat aa sakti hai (bearish reversal).",
    "Inverse head & shoulders": "Teen bottom: beech wala sabse neecha (head). Neckline ke upar close hone par tezi ki umeed (bullish reversal).",
    "Rounding bottom (saucer)": "Price dheere-dheere gir kar katore (saucer/U) jaisa mudkar wapas upar aa raha hai. Bikwali thak gayi aur khareedari badh rahi hai; kinare (rim) ke upar close hone par tezi.",
    "Rounding top": "Price dheere-dheere chadh kar ulte katore (arch) jaisa mudkar neeche aa raha hai. Khareedari thak gayi; neeche ki rim tootne par giravat (bearish).",
    "Cup & handle": "Pehle katore jaisa (cup) mudna, phir chhoti si giravat (handle). Handle ke upar close hone par tezi aksar aage badhti hai (bullish continuation).",
    "Bull flag": "Tez uchhal (pole) ke baad price thodi der chhoti range me aaram karta hai. Flag ke upar breakout hone par tezi aksar jaari rehti hai.",
    "Bear flag": "Tez giravat (pole) ke baad price thodi der chhoti range me rukta hai. Flag ke neeche toot-ne par giravat aksar jaari rehti hai.",
    "Bull pennant": "Tez uchhal (pole) ke baad price chhote tang triangle (pennant) me ruka hai. Upar breakout hone par tezi aksar jaari rehti hai.",
    "Bear pennant": "Tez giravat (pole) ke baad price chhote tang triangle (pennant) me ruka hai. Neeche breakdown hone par giravat aksar jaari rehti hai.",
    "Diamond top": "Pehle daayra chaura hua phir tang ho gaya (heere jaisa shape), upar ke trend ke baad. Neeche ki line tootne par giravat (bearish reversal). Ye pattern kam banta hai.",
    "Diamond bottom": "Pehle daayra chaura hua phir tang ho gaya (heere jaisa shape), giravat ke baad. Upar ki line ke upar close hone par tezi (bullish reversal). Ye pattern kam banta hai.",
    "V-bottom (sharp reversal)": "Tez giravat ke baad utni hi tezi se wapas uchhal (V shape). Pehle ke high ke upar close hone par reversal pakka hota hai.",
    "V-top (sharp reversal)": "Tez uchhal ke baad utni hi tezi se wapas giravat (ulta V). Pehle ke low ke neeche close hone par reversal pakka hota hai.",
    "Island reversal (top)": "Gap up ke baad kuch din ka tapu (island) aur phir gap down. Upar ke bhaav me phase hue buyers fas gaye; bearish reversal.",
    "Island reversal (bottom)": "Gap down ke baad kuch din ka tapu (island) aur phir gap up. Neeche ke bhaav me phase hue sellers fas gaye; bullish reversal.",
}

SHAPE_LABELS = ("Resistance", "Support")


# ====================================================================== candlesticks + gaps
def _cand_parts(b, i, C):
    z = b[i]
    o, h, l, c = z["o"], z["h"], z["l"], z["c"]
    rng = h - l
    body = abs(c - o)
    us, lw = h - max(o, c), min(o, c) - l
    p = b[i - 1]
    po, pc, ph, pl = p["o"], p["c"], p["h"], p["l"]
    pbody, prng = abs(pc - po), ph - pl
    dn, upt = C[i - 1] < C[i - 5] * .98, C[i - 1] > C[i - 5] * 1.02
    return z, o, h, l, c, rng, body, us, lw, p, po, pc, ph, pl, pbody, prng, dn, upt, c > o, c < o, pc > po, pc < po


def _cand_multi(b, i, C):
    """Do ya zyada candle wale pattern (5 bar > 3 bar > 2 bar)."""
    (z, o, h, l, c, rng, body, us, lw, p, po, pc, ph, pl, pbody, prng, dn, upt, green, red, pg, pr) = _cand_parts(b, i, C)
    if rng <= 0:
        return None
    if i >= 4:  # rising / falling three methods
        a = b[i - 4]
        ao, ac, ah, al = a["o"], a["c"], a["h"], a["l"]
        abody, arng = abs(ac - ao), ah - al
        mids = b[i - 3:i]
        inside = all(m["h"] <= ah * 1.001 and m["l"] >= al * .999 and abs(m["c"] - m["o"]) <= .5 * abody for m in mids)
        if arng > 0 and abody >= .6 * arng and inside:
            if ac > ao and green and body >= .6 * rng and c > ac and sum(1 for m in mids if m["c"] < m["o"]) >= 2:
                return ("Rising three methods (uptrend jaari, bullish)", "g")
            if ac < ao and red and body >= .6 * rng and c < ac and sum(1 for m in mids if m["c"] > m["o"]) >= 2:
                return ("Falling three methods (downtrend jaari, bearish)", "r")
    if i >= 2:
        q = b[i - 2]
        qo, qc, qh, ql = q["o"], q["c"], q["h"], q["l"]
        qbody, qrng = abs(qc - qo), qh - ql
        qr, qg = qc < qo, qc > qo
        dojip = prng > 0 and pbody <= .1 * prng
        if qr and dojip and ph < ql and green and l > ph:
            return ("Bullish abandoned baby (bahut mazboot bottom, bullish)", "g")
        if qg and dojip and pl > qh and red and h < pl:
            return ("Bearish abandoned baby (bahut mazboot top, bearish)", "r")
        if qr and qrng > 0 and qbody >= .5 * qrng and pg and po >= qc and pc <= qo and pbody < qbody and green and c > qo:
            return ("Three inside up (bottom ki pushti, bullish)", "g")
        if qg and qrng > 0 and qbody >= .5 * qrng and pr and po <= qc and pc >= qo and pbody < qbody and red and c < qo:
            return ("Three inside down (top ki pushti, bearish)", "r")
        if qr and pg and pc >= qo and po <= qc and pbody > qbody and green and c > pc:
            return ("Three outside up (bullish engulfing ke baad pushti)", "g")
        if qg and pr and pc <= qo and po >= qc and pbody > qbody and red and c < pc:
            return ("Three outside down (bearish engulfing ke baad pushti)", "r")
        if qr and qrng > 0 and qbody >= .5 * qrng and pbody <= .5 * qbody and green and c > (qo + qc) / 2 and body >= .4 * rng and (dn or C[i - 2] < C[i - 6] * .99):
            return ("Morning doji star (bottom ka sanket, bullish)" if dojip else "Morning star (bottom ka sanket, bullish)", "g")
        if qg and qrng > 0 and qbody >= .5 * qrng and pbody <= .5 * qbody and red and c < (qo + qc) / 2 and body >= .4 * rng and (upt or C[i - 2] > C[i - 6] * 1.01):
            return ("Evening doji star (top ka sanket, bearish)" if dojip else "Evening star (top ka sanket, bearish)", "r")
        if (qg and pg and green and qc < pc < c and qo <= po <= qc and po <= o <= pc and
                all(abs(t["c"] - t["o"]) >= .5 * (t["h"] - t["l"]) and (t["h"] - max(t["o"], t["c"])) <= .35 * abs(t["c"] - t["o"]) for t in (q, p, z))):
            return ("Three white soldiers (lagatar teen hari candle, bullish)", "g")
        if (qr and pr and red and qc > pc > c and qc <= po <= qo and pc <= o <= po and
                all(abs(t["c"] - t["o"]) >= .5 * (t["h"] - t["l"]) and (min(t["o"], t["c"]) - t["l"]) <= .35 * abs(t["c"] - t["o"]) for t in (q, p, z))):
            return ("Three black crows (lagatar teen lal candle, bearish)", "r")
    if green and pr and c >= po and o <= pc and body > pbody:
        return ("Bullish engulfing (khareedaar haavi)", "g")
    if red and pg and c <= po and o >= pc and body > pbody:
        return ("Bearish engulfing (bechne wale haavi)", "r")
    if prng > 0 and pbody >= .5 * prng:
        if pr and green and o <= pc and (po + pc) / 2 < c < po:
            return ("Piercing line (neeche se wapsi, bullish)", "g")
        if pg and red and o >= pc and po < c < (po + pc) / 2:
            return ("Dark cloud cover (upar se palat, bearish)", "r")
        if pr and green and o >= po and body >= .6 * rng:
            return ("Bullish kicker (achanak palat, bullish)", "g")
        if pg and red and o <= po and body >= .6 * rng:
            return ("Bearish kicker (achanak palat, bearish)", "r")
    if abs(l - pl) <= .0015 * c and pr and green and dn:
        return ("Tweezer bottom (same low do baar, bullish)", "g")
    if abs(h - ph) <= .0015 * c and pg and red and upt:
        return ("Tweezer top (same high do baar, bearish)", "r")
    if prng > 0 and pbody >= .5 * prng and body <= .6 * pbody and max(o, c) <= max(po, pc) and min(o, c) >= min(po, pc):
        cross = body <= .1 * rng
        if pr and (green or cross):
            return ("Bullish harami cross (giravat ruk rahi hai)" if cross else "Bullish harami (giravat ruk rahi hai, bullish)", "g")
        if pg and (red or cross):
            return ("Bearish harami cross (tezi ruk rahi hai)" if cross else "Bearish harami (tezi ruk rahi hai, bearish)", "r")
    return None


def _cand_single(b, i, C):
    """Ek candle wale pattern. Returns (text, color, special): special=True matlab hamesha dikhao."""
    (z, o, h, l, c, rng, body, us, lw, p, po, pc, ph, pl, pbody, prng, dn, upt, green, red, pg, pr) = _cand_parts(b, i, C)
    if rng <= 0:
        return None
    if body <= .1 * rng:
        if lw >= .6 * rng and us <= .1 * rng:
            return ("Dragonfly doji (neeche se kharidari, bullish)" if dn else "Dragonfly doji (neeche se khareedari)", "g" if dn else "y", True)
        if us >= .6 * rng and lw <= .1 * rng:
            return ("Gravestone doji (upar se bikwali, bearish)" if upt else "Gravestone doji (upar se bikwali)", "r" if upt else "y", True)
        if us >= .35 * rng and lw >= .35 * rng:
            return ("Long-legged doji (bahut uljhan, faisla baaki)", "y", True)
        return ("Doji (dono taraf barabar, faisla baaki)", "y", True)
    if body > 0 and lw >= 2 * body and us <= max(.6 * body, .12 * rng):
        if dn:
            return ("Hammer (neeche se khareedari, bullish)", "g", True)
        if upt:
            return ("Hanging man (upar ke trend me, bearish chetavni)", "r", True)
    if body > 0 and us >= 2 * body and lw <= max(.6 * body, .12 * rng):
        if upt:
            return ("Shooting star (upar se bikwali, bearish)", "r", True)
        if dn:
            return ("Inverted hammer (bottom ki koshish, pushti chahiye)", "g", True)
    if body >= .95 * rng:
        return ("Bullish marubozu (poori khareedari)" if green else "Bearish marubozu (poori bikwali)", "g" if green else "r", True)
    if body >= .85 * rng:
        return ("Strong green candle (poori khareedari)" if green else "Strong red candle (poori bikwali)", "g" if green else "r", False)
    if h <= ph and l >= pl:
        return ("Inside bar (price sikud raha hai, breakout aa sakta hai)", "y", False)
    if body <= .3 * rng and us >= .25 * rng and lw >= .25 * rng:
        return ("Spinning top (kamzor momentum, uljhan)", "y", False)
    if h > ph and l < pl:
        return ("Outside bar (badi hulchul)" + (", hari" if green else ", lal" if red else ""), "g" if green else "r" if red else "y", False)
    return None


def _gap(b, i):
    z, p = b[i], b[i - 1]
    up = z["l"] > p["h"] * 1.003
    dn = z["h"] < p["l"] * .997
    if not (up or dn):
        return None
    seg = b[max(0, i - 20):i]
    va = avg([t["v"] for t in seg if t.get("v")])
    vr = (z.get("v") or 0) / va if va else 0
    ch10 = b[i - 1]["c"] / b[max(0, i - 11)]["c"] - 1
    ch20 = b[i - 1]["c"] / b[max(0, i - 21)]["c"] - 1
    if up:
        pct = (z["l"] / p["h"] - 1) * 100
        if ch20 > .2 and vr >= 1.8:
            return ("Exhaustion gap up %.1f%% (tezi thakne ka sanket, bearish chetavni)" % pct, "r")
        if z["c"] > max(t["h"] for t in seg) and vr >= 1.3 and ch10 < .08:
            return ("Breakaway gap up %.1f%% (naye uchhaal ki shuruaat, bullish)" % pct, "g")
        if ch10 > .05:
            return ("Runaway gap up %.1f%% (trend jaari, bullish)" % pct, "g")
        return ("Gap up %.1f%% (common gap, aksar bhar jata hai)" % pct, "y")
    pct = (1 - z["h"] / p["l"]) * 100
    if ch20 < -.2 and vr >= 1.8:
        return ("Exhaustion gap down %.1f%% (giravat thakne ka sanket, bullish chetavni)" % pct, "g")
    if z["c"] < min(t["l"] for t in seg) and vr >= 1.3 and ch10 > -.08:
        return ("Breakaway gap down %.1f%% (naye girav ki shuruaat, bearish)" % pct, "r")
    if ch10 < -.05:
        return ("Runaway gap down %.1f%% (trend jaari, bearish)" % pct, "r")
    return ("Gap down %.1f%% (common gap, aksar bhar jata hai)" % pct, "y")


def _candles(b):
    """Aakhri 5 candles ke candlestick aur gap signals (ek bar par ek se zyada bhi ho sakte hain)."""
    n = len(b)
    C = [z["c"] for z in b]
    out = []
    for i in range(max(6, n - 5), n):
        m = _cand_multi(b, i, C)
        sg = _cand_single(b, i, C)
        if m:
            out.append({"i": i, "t": m[0], "k": m[1]})
            if sg and sg[2]:
                out.append({"i": i, "t": sg[0], "k": sg[1]})
        elif sg:
            out.append({"i": i, "t": sg[0], "k": sg[1]})
        g = _gap(b, i)
        if g:
            out.append({"i": i, "t": g[0], "k": g[1]})
    return out


# ====================================================================== geometry
def _line_fit(idx, ys):
    """Pivot points ko jodne wali line (pehle aur aakhri pivot se)."""
    return (idx[0], ys[0], idx[-1], ys[-1])


def _at(ln, i):
    return ln[1] if ln[2] == ln[0] else ln[1] + (ln[3] - ln[1]) * (i - ln[0]) / (ln[2] - ln[0])


def _flat(i1, y, i2):
    return (i1, y, i2, y)


def _eval(x, name, up, lo, h, bias, only=None, check=True, pts=None, shapes=None, labels=SHAPE_LABELS, form=True):
    """Ek pattern (upar aur neeche ki line) par breakout / breakdown / banne ki halat dekho."""
    n, C, H, L, V = x["n"], x["C"], x["H"], x["L"], x["V"]
    i0 = n - 1
    cur = C[i0]
    u0, l0 = _at(up, i0), _at(lo, i0)
    if check and u0 <= l0:
        return None
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
        elif form:
            d = only or (bias if bias in ("up", "down") else ("up" if (u0 - cur) <= (cur - l0) else "down"))
            state = "forming"
    if not d:
        return None
    level = u0 if d == "up" else l0
    if level <= 0:
        return None
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
    sc = 40 if state == "brk" else 25 if state == "near" else 12
    why = []
    nm = "resistance" if d == "up" else "support"
    if state == "brk":
        why.append("Price ne %s %s (%s) ke %s close diya (%d candle se, %.1f%% door)." %
                   (nm, "{:,.0f}".format(level), name, "upar" if d == "up" else "neeche", k, ext))
        if k == 1:
            sc += 7
        if ext > 4:
            sc -= 8
    elif state == "near":
        why.append("Price %s %s se sirf %.1f%% door hai, abhi %s nahi hua (close ka intezaar)." %
                   (nm, "{:,.0f}".format(level), ext, "breakout" if d == "up" else "breakdown"))
    else:
        why.append("Pattern abhi ban raha hai (complete nahi). Price %s %s se %.1f%% door hai; %s ka intezaar karo." %
                   (nm, "{:,.0f}".format(level), ext, "upar breakout" if d == "up" else "neeche breakdown"))
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
        why.append("Bada trend (50 EMA) is direction ke saath hai.")
    else:
        sc -= 5
        why.append("Bada trend (50 EMA) is direction ke khilaf hai, risk zyada.")
    if rr >= 1.5:
        sc += 5
    if state == "brk" and ((d == "up" and cur >= t1 * .99) or (d == "down" and cur <= t1 * 1.01)):
        sc -= 15
        why.append("Dhyan: price Target 1 ke paas pahunch chuka hai, ab naya entry risky hai.")
    if state == "forming":
        sc = min(sc, 55)
        why.append("Plan tab valid hoga jab price level ke %s close ho." % ("upar" if d == "up" else "neeche"))
    sc = max(0, min(100, int(round(sc))))
    a0 = max(s, 0)
    shp = [{"t": "line", "a": [a0, _at(ln, a0)], "b": [i0, _at(ln, i0)], "c": kk, "l": lab}
           for ln, kk, lab in ((up, "u", labels[0]), (lo, "l", labels[1]))]
    lines = [{"k": t["c"], "a": t["a"], "b": t["b"]} for t in shp]
    shp += shapes or []
    return {"name": name, "dir": d, "state": state, "bias": bias, "level": level, "entry": entry, "sl": sl, "t1": t1, "t2": t2,
            "rr": rr, "h": h, "k": k, "vx": vx, "score": sc, "label": "Strong" if sc >= 70 else "Theek" if sc >= 50 else "Kamzor",
            "why": why, "lines": lines, "shapes": shp, "pts": pts or [], "start": s, "u0": u0, "l0": l0, "desc": DESC.get(name, ""),
            "candle": (cmatch or cs[-1:] or [{"t": None}])[-1]["t"]}


def _combos(piv, k, look=6):
    """Aakhri `look` pivots me se k pivots ke sab combination, sabse naye pehle (noise wale chhote pivot ignore ho jaate hain)."""
    from itertools import combinations
    cs = list(combinations(piv[-look:], k))
    cs.sort(key=lambda t: (t[-1], t[0]), reverse=True)
    return cs


def _ln(a, ya, b, yb, c="t", l=""):
    return {"t": "line", "a": [a, ya], "b": [b, yb], "c": c, "l": l}


# ====================================================================== special detectors
def _triple(x, phi, plo, add):
    n, H, L = x["n"], x["H"], x["L"]
    i0 = n - 1
    for a, b, c in _combos(plo, 3):
        lv = [L[a], L[b], L[c]]
        if b - a >= 6 and c - b >= 6 and c >= n - 50 and (max(lv) - min(lv)) / min(lv) <= .025:
            nk, low = max(H[a:c + 1]), min(lv)
            if nk > low * 1.05 and nk - low >= 4 * x["atr"]:
                r = _eval(x, "Triple bottom", _flat(a, nk, i0), _flat(a, low, i0), nk - low, "up", only="up", check=False,
                          pts=[{"i": a, "y": L[a], "t": "1"}, {"i": b, "y": L[b], "t": "2"}, {"i": c, "y": L[c], "t": "3"}],
                          labels=("Neckline", "Support"))
                if r:
                    add(r)
                    break
    for a, b, c in _combos(phi, 3):
        hv = [H[a], H[b], H[c]]
        if b - a >= 6 and c - b >= 6 and c >= n - 50 and (max(hv) - min(hv)) / min(hv) <= .025:
            nk, top = min(L[a:c + 1]), max(hv)
            if nk < top * .95 and top - nk >= 4 * x["atr"]:
                r = _eval(x, "Triple top", _flat(a, top, i0), _flat(a, nk, i0), top - nk, "down", only="down", check=False,
                          pts=[{"i": a, "y": H[a], "t": "1"}, {"i": b, "y": H[b], "t": "2"}, {"i": c, "y": H[c], "t": "3"}],
                          labels=("Resistance", "Neckline"))
                if r:
                    add(r)
                    break


def _cups(x, add):
    """Rounding bottom / Cup & handle / Rounding top: closes par parabola fit."""
    n, C, H, L = x["n"], x["C"], x["H"], x["L"]
    i0 = n - 1
    best = {"bot": None, "cup": None, "top": None}
    for hl in (0, 4, 7, 10, 14, 18, 22):
        e = i0 - hl
        for W in (28, 36, 45, 55, 70, 85):
            s = e - W + 1
            if s < 0:
                continue
            ys = np.array(C[s:e + 1], dtype=float)
            xs = np.arange(W, dtype=float)
            try:
                a, b, c0 = np.polyfit(xs, ys, 2)
            except Exception:
                continue
            if a == 0:
                continue
            fit = a * xs ** 2 + b * xs + c0
            ss = ((ys - ys.mean()) ** 2).sum()
            if ss <= 0:
                continue
            r2 = 1 - ((ys - fit) ** 2).sum() / ss
            vtx = -b / (2 * a)
            if r2 < .75 or not (.25 * W <= vtx <= .75 * W) or float(np.abs(ys - fit).max()) > .06 * float(ys.mean()):
                continue
            curve = [[s + j, float(fit[j])] for j in range(0, W, 2)] + [[e, float(fit[-1])]]
            if a > 0:  # U shape: bottom / cup
                rl, rr_ = max(H[s:s + max(3, W // 8)]), max(H[e - 3:e + 1])
                rim, low = min(rl, rr_), min(L[s:e + 1])
                depth = (rim - low) / rim
                nb = sum(1 for y in ys if y <= low + .35 * (rim - low))  # katore ka tala chaura hona chahiye (V nahi)
                if not (.07 <= depth <= .45) or rim - low < 4 * x["atr"] or abs(rl - rr_) / rl > .08 or C[e] < low + .85 * (rim - low) or nb < max(5, .2 * W):
                    continue
                lvl = max(rl, rr_)
                if hl == 0:
                    key = "bot"
                    cand = {"r2": r2, "name": "Rounding bottom (saucer)", "s": s, "e": e, "lvl": lvl, "low": low, "curve": curve,
                            "up": _flat(s, lvl, i0), "lo": _flat(s, low, i0), "h": lvl - low, "vx": vtx}
                else:
                    ku_ = 0
                    while ku_ < hl and C[i0 - ku_] > lvl * 1.002:
                        ku_ += 1
                    he = i0 - ku_  # handle yahan tak (breakout wali candles hata kar)
                    if ku_ > 4 or he - e < 3:
                        continue
                    hseg_h, hseg_l = max(H[e:he + 1]), min(L[e:he + 1])
                    hd = (hseg_h - hseg_l) / hseg_h
                    imin = int(np.argmin(L[e:he + 1]))
                    if imin < max(1, .2 * (he - e)) or hd < .02 or hd > .12 or hd > .5 * depth or hseg_l < low + .5 * (rim - low) or C[he] > C[e] * 1.03 or hseg_h > lvl * 1.04 \
                            :
                        continue
                    key = "cup"
                    lvl2 = max(lvl, hseg_h)
                    cand = {"r2": r2, "name": "Cup & handle", "s": s, "e": e, "lvl": lvl2, "low": low, "curve": curve,
                            "up": _flat(s, lvl2, i0), "lo": _flat(e, hseg_l, i0), "h": lvl2 - low, "vx": vtx, "hl": hseg_l}
                vi = int(np.argmin(fit))
                cand["pts"] = [{"i": s, "y": rl, "t": "L"}, {"i": s + vi, "y": L[s + vi], "t": "Cup"}, {"i": e, "y": rr_, "t": "R"}]
                labs = ("Breakout level (rim)", "Cup ka low" if hl == 0 else "Handle ka low")
            else:  # arch / top
                rl, rr_ = min(L[s:s + max(3, W // 8)]), min(L[e - 3:e + 1])
                rim, top = max(rl, rr_), max(H[s:e + 1])
                depth = (top - rim) / top
                nb = sum(1 for y in ys if y >= top - .35 * (top - rim))
                if not (.07 <= depth <= .45) or top - rim < 4 * x["atr"] or abs(rl - rr_) / rl > .08 or hl != 0 or C[e] > top - .85 * (top - rim) or nb < max(5, .2 * W):
                    continue
                key = "top"
                lvl = min(rl, rr_)
                cand = {"r2": r2, "name": "Rounding top", "s": s, "e": e, "lvl": lvl, "low": top, "curve": curve,
                        "up": _flat(s, top, i0), "lo": _flat(s, lvl, i0), "h": top - lvl, "vx": vtx}
                vi = int(np.argmax(fit))
                cand["pts"] = [{"i": s, "y": rl, "t": "L"}, {"i": s + vi, "y": H[s + vi], "t": "Top"}, {"i": e, "y": rr_, "t": "R"}]
                labs = ("Rounding top ka high", "Neckline (rim)")
            cand["labs"] = labs
            if best[key] is None or r2 > best[key]["r2"]:
                best[key] = cand
    for key, only in (("bot", "up"), ("cup", "up"), ("top", "down")):
        c = best[key]
        if not c:
            continue
        sh = [{"t": "curve", "p": c["curve"], "c": "y", "l": ""}]
        add(_eval(x, c["name"], c["up"], c["lo"], c["h"], only, only=only, check=False, pts=c["pts"], shapes=sh, labels=c["labs"]))


def _vshape(x, add):
    n, H, L, C = x["n"], x["H"], x["L"], x["C"]
    i0 = n - 1
    lo_rng = range(max(8, n - 26), n - 2)
    if len(lo_rng):
        il = min(lo_rng, key=lambda i: L[i])
        pk = max(range(max(0, il - 12), il), key=lambda i: H[i]) if il > 0 else None
        if pk is not None and (H[pk] - L[il]) / H[pk] >= .10 and H[pk] - L[il] >= 5 * x["atr"] and il - pk <= 12 and i0 - il <= 12 and \
                C[i0] >= L[il] + .6 * (H[pk] - L[il]):
            add(_eval(x, "V-bottom (sharp reversal)", _flat(pk, H[pk], i0), _flat(il, L[il], i0), H[pk] - L[il], "up", only="up",
                      check=False, pts=[{"i": pk, "y": H[pk], "t": "Peak"}, {"i": il, "y": L[il], "t": "V"}], labels=("Pehle ka high", "V ka low")))
    hi_rng = range(max(8, n - 26), n - 2)
    if len(hi_rng):
        ih = max(hi_rng, key=lambda i: H[i])
        tr = min(range(max(0, ih - 12), ih), key=lambda i: L[i]) if ih > 0 else None
        if tr is not None and (H[ih] - L[tr]) / H[ih] >= .10 and H[ih] - L[tr] >= 5 * x["atr"] and ih - tr <= 12 and i0 - ih <= 12 and \
                C[i0] <= H[ih] - .6 * (H[ih] - L[tr]):
            add(_eval(x, "V-top (sharp reversal)", _flat(ih, H[ih], i0), _flat(tr, L[tr], i0), H[ih] - L[tr], "down", only="down",
                      check=False, pts=[{"i": tr, "y": L[tr], "t": "Base"}, {"i": ih, "y": H[ih], "t": "V"}], labels=("V ka high", "Pehle ka low")))


def _custom(x, name, d, state, k, level, sl, shapes, pts, start, bias=None):
    """Island jaise pattern ke liye seedha result (entry, SL, targets)."""
    i0 = x["n"] - 1
    cur = x["C"][i0]
    atr = x["atr"]
    entry = cur
    risk = abs(entry - sl)
    risk = max(risk, 1.2 * atr)
    sl = entry - risk if d == "up" else entry + risk
    t1, t2 = (entry + 1.5 * risk, entry + 2.5 * risk) if d == "up" else (max(entry - 1.5 * risk, entry * .03), max(entry - 2.5 * risk, entry * .02))
    sc = 55 + (8 if k == 1 else 0) + (6 if (d == "up") == (cur > x["e50"]) else -4)
    why = ["%s: pattern poora ho gaya (%d candle pehle). Level %s." % (name, k, "{:,.0f}".format(level)),
           "Island reversal me stop-loss island ke dusre kinare par rakha hai."]
    return {"name": name, "dir": d, "state": state, "bias": bias or d, "level": level, "entry": entry, "sl": sl, "t1": t1, "t2": t2,
            "rr": abs(t1 - entry) / risk, "h": abs(t1 - entry), "k": k, "vx": None, "score": max(0, min(100, sc)),
            "label": "Strong" if sc >= 70 else "Theek" if sc >= 50 else "Kamzor", "why": why,
            "lines": [], "shapes": shapes, "pts": pts, "start": start, "u0": level, "l0": level, "desc": DESC.get(name, ""), "candle": None}


def _island(x, add):
    n, H, L = x["n"], x["H"], x["L"]
    i0 = n - 1
    for j in range(max(2, n - 14), n - 1):
        if L[j] > H[j - 1] * 1.002:  # gap up at j  -> top island ho sakta hai
            for k in range(j + 1, min(n, j + 11)):
                if k < n - 5:
                    continue
                if H[k] < L[k - 1] * .998 and min(L[j:k]) > max(H[j - 1], H[k]):
                    top = max(H[j:k])
                    bot = min(L[j:k])
                    sh = [{"t": "box", "a": [j, top], "b": [k - 1, bot], "c": "r", "l": "Island"},
                          _ln(max(0, j - 3), H[j - 1], k + 2, H[j - 1], "u", ""), _ln(max(0, k - 3), L[k - 1], i0, L[k - 1], "l", "")]
                    add(_custom(x, "Island reversal (top)", "down", "brk", i0 - k + 1, bot, top + .3 * x["atr"], sh,
                                [{"i": j, "y": H[j], "t": "Gap up"}, {"i": k, "y": L[k], "t": "Gap down"}], j - 1))
                    break
        if H[j] < L[j - 1] * .998:  # gap down at j -> bottom island
            for k in range(j + 1, min(n, j + 11)):
                if k < n - 5:
                    continue
                if L[k] > H[k - 1] * 1.002 and max(H[j:k]) < min(L[j - 1], L[k]):
                    top = max(H[j:k])
                    bot = min(L[j:k])
                    sh = [{"t": "box", "a": [j, top], "b": [k - 1, bot], "c": "g", "l": "Island"},
                          _ln(max(0, j - 3), L[j - 1], k + 2, L[j - 1], "l", ""), _ln(max(0, k - 3), H[k - 1], i0, H[k - 1], "u", "")]
                    add(_custom(x, "Island reversal (bottom)", "up", "brk", i0 - k + 1, top, bot - .3 * x["atr"], sh,
                                [{"i": j, "y": L[j], "t": "Gap down"}, {"i": k, "y": H[k], "t": "Gap up"}], j - 1))
                    break


def _diamond(x, add):
    n, H, L, C = x["n"], x["H"], x["L"], x["C"]
    i0 = n - 1
    for W in (45, 60):
        s = n - W
        if s < 22:
            continue
        a, b, c = s + W // 3, s + 2 * W // 3, n
        r1 = max(H[s:a]) - min(L[s:a])
        r2 = max(H[a:b]) - min(L[a:b])
        r3 = max(H[b:c]) - min(L[b:c])
        if not (r2 >= 1.25 * r1 and r2 >= 1.25 * r3 and r3 <= .8 * r2) or r2 < 5 * x["atr"]:
            continue
        before = C[s] / C[s - 20] - 1
        if abs(before) < .06:
            continue
        top_i = max(range(a, b), key=lambda i: H[i])
        bot_i = min(range(a, b), key=lambda i: L[i])
        lv_i, rv_i = s + W // 6, n - 1 - W // 6
        lv_y = (max(H[s:a]) + min(L[s:a])) / 2
        rv_y = (max(H[b:c]) + min(L[b:c])) / 2
        sh = [_ln(lv_i, lv_y, top_i, H[top_i], "t", ""), _ln(lv_i, lv_y, bot_i, L[bot_i], "t", ""),
              _ln(top_i, H[top_i], rv_i, rv_y, "u", ""), _ln(bot_i, L[bot_i], rv_i, rv_y, "l", "")]
        # diamond poora hone ke baad ki chhoti range (aakhri hissa): isi ke toot-ne par breakout/breakdown
        if n - 3 - b < 5:
            continue
        up_l, lo_l = max(H[b:n - 3]), min(L[b:n - 3])
        up = _flat(b, up_l, i0)
        lo = _flat(b, lo_l, i0)
        h = H[top_i] - L[bot_i]
        labs = ("Chhoti range ka high", "Chhoti range ka low")
        pts = [{"i": top_i, "y": H[top_i], "t": "Top"}, {"i": bot_i, "y": L[bot_i], "t": "Bottom"}]
        if before > 0:
            add(_eval(x, "Diamond top", up, lo, h, "down", only="down", check=False, shapes=sh, form=False, pts=pts, labels=labs))
        else:
            add(_eval(x, "Diamond bottom", up, lo, h, "up", only="up", check=False, shapes=sh, form=False, pts=pts, labels=labs))
        break


# ====================================================================== main
def analyse(bars, tf="D"):
    """Return {"all": [pattern...], "candles": [...]} ya None. all: brk > near > forming, phir score."""
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
            if i < n - 100:
                continue
            if out and i - out[-1] < 4:
                if (arr[i] > arr[out[-1]]) == hi:
                    out[-1] = i
            else:
                out.append(i)
        return out
    phi, plo = dedupe(phi, H, True), dedupe(plo, L, False)
    atr_ = x["atr"]
    res = []

    def add(r):
        if r:
            res.append(r)

    # 1) triangle / wedge / channel / megaphone / rectangle: trendlines se
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
            span = max(ph[-1], pl[-1]) - s0
            par = abs(su - sl_) <= .3 * max(abs(su), abs(sl_), 1e-9)
            wok = w0 > 0 and .8 <= w1 / w0 <= 1.25
            nm = bias = None
            if uf and sl_ >= T and conv:
                nm, bias = "Ascending triangle", "up"
            elif lf and su <= -T and conv:
                nm, bias = "Descending triangle", "down"
            elif su <= -T and sl_ >= T and conv:
                nm, bias = "Symmetrical triangle", "both"
            elif uf and lf and .03 <= w0 / cur <= .16:
                nm, bias = "Rectangle (range)", "both"
            elif su >= T and sl_ >= T and sl_ > su and 0 < w1 < w0 * .85:
                nm, bias = "Rising wedge", "down"
            elif su <= -T and sl_ <= -T and su < sl_ and 0 < w1 < w0 * .85:
                nm, bias = "Falling wedge", "up"
            elif su >= T and sl_ >= T and par and wok and span >= 20 and .03 <= w0 / cur <= .2:
                nm, bias = "Ascending channel", "both"
            elif su <= -T and sl_ <= -T and par and wok and span >= 20 and .03 <= w0 / cur <= .2:
                nm, bias = "Descending channel", "both"
            elif su >= T and sl_ <= -T and w0 > 0 and w1 > w0 * 1.15 and span >= 20 and w1 / cur <= .4:
                nm, bias = "Broadening formation (megaphone)", "both"
            if nm and w0 < (4 if nh + nl < 5 else 3) * atr_:
                nm = None
            if nm:
                pts = [{"i": i, "y": H[i], "t": ""} for i in ph] + [{"i": i, "y": L[i], "t": ""} for i in pl]
                add(_eval(x, nm, up, lo, max(w0, cur * .02), bias, pts=pts))

    # 2) double top / double bottom
    for a, b in _combos(plo, 2, 5):
        if b - a >= 8 and abs(L[a] - L[b]) / L[b] <= .03 and b >= n - 45:
            nk = max(H[a:b + 1])
            low = min(L[a], L[b])
            if nk > low * 1.05 and nk - low >= 4 * atr_:
                r = _eval(x, "Double bottom", _flat(a, nk, i0), _flat(a, low, i0), nk - low, "up", only="up", check=False,
                          pts=[{"i": a, "y": L[a], "t": "1"}, {"i": b, "y": L[b], "t": "2"}], labels=("Neckline", "Support"))
                if r:
                    add(r)
                    break
    for a, b in _combos(phi, 2, 5):
        if b - a >= 8 and abs(H[a] - H[b]) / H[b] <= .03 and b >= n - 45:
            nk = min(L[a:b + 1])
            top = max(H[a], H[b])
            if nk < top * .95 and top - nk >= 4 * atr_:
                r = _eval(x, "Double top", _flat(a, top, i0), _flat(a, nk, i0), top - nk, "down", only="down", check=False,
                          pts=[{"i": a, "y": H[a], "t": "1"}, {"i": b, "y": H[b], "t": "2"}], labels=("Resistance", "Neckline"))
                if r:
                    add(r)
                    break
    _triple(x, phi, plo, add)

    # 3) head & shoulders (aur ulta)
    for a, b, c in _combos(phi, 3):
        if b > a + 3 and c > b + 3 and c >= n - 40 and H[b] > H[a] * 1.02 and H[b] > H[c] * 1.02 and abs(H[a] - H[c]) <= H[b] * .05:
            ta = min(range(a, b + 1), key=lambda i: L[i])
            tb = min(range(b, c + 1), key=lambda i: L[i])
            neck = (ta, L[ta], tb, L[tb])
            hh = H[b] - _at(neck, b)
            if hh > cur * .03 and hh >= 4 * atr_:
                r = _eval(x, "Head & shoulders", _flat(c, H[c], i0), (ta, L[ta], i0, _at(neck, i0)), hh, "down", only="down", check=False,
                          pts=[{"i": a, "y": H[a], "t": "LS"}, {"i": b, "y": H[b], "t": "H"}, {"i": c, "y": H[c], "t": "RS"}],
                          labels=("Right shoulder", "Neckline"),
                          shapes=[_ln(a, H[a], b, H[b], "t", ""), _ln(b, H[b], c, H[c], "t", "")])
                if r:
                    add(r)
                    break
    for a, b, c in _combos(plo, 3):
        if b > a + 3 and c > b + 3 and c >= n - 40 and L[b] < L[a] * .98 and L[b] < L[c] * .98 and abs(L[a] - L[c]) <= L[b] * .05:
            pa = max(range(a, b + 1), key=lambda i: H[i])
            pb = max(range(b, c + 1), key=lambda i: H[i])
            neck = (pa, H[pa], pb, H[pb])
            hh = _at(neck, b) - L[b]
            if hh > cur * .03 and hh >= 4 * atr_:
                r = _eval(x, "Inverse head & shoulders", (pa, H[pa], i0, _at(neck, i0)), _flat(c, L[c], i0), hh, "up", only="up", check=False,
                          pts=[{"i": a, "y": L[a], "t": "LS"}, {"i": b, "y": L[b], "t": "H"}, {"i": c, "y": L[c], "t": "RS"}],
                          labels=("Neckline", "Right shoulder"),
                          shapes=[_ln(a, L[a], b, L[b], "t", ""), _ln(b, L[b], c, L[c], "t", "")])
                if r:
                    add(r)
                    break

    # 4) rounding bottom / top, cup & handle
    _cups(x, add)

    # 5) bull / bear flag aur pennant (pole ke baad consolidation)
    for sgn, nm_f, nm_p in ((1, "Bull flag", "Bull pennant"), (-1, "Bear flag", "Bear pennant")):
        done = False
        for k in range(5, 18):
            pe = i0 - k
            if pe < 12 or done:
                break
            ps = min(C[pe - 10:pe]) if sgn > 0 else max(C[pe - 10:pe])
            pole = sgn * (C[pe] / ps - 1)
            if pole < .10 or pole * cur < 5 * atr_:
                continue
            for j in range(0, 5):
                e = i0 - j
                if e - pe < 4:
                    break
                fh, fl = max(H[pe:e + 1]), min(L[pe:e + 1])
                drift_ok = C[e] <= C[pe] * 1.01 if sgn > 0 else C[e] >= C[pe] * .99
                ret = (C[pe] - fl) / (C[pe] - ps) if sgn > 0 else (fh - C[pe]) / (ps - C[pe])
                if not ((fh - fl) / cur <= .09 and ret < .5 and drift_ok):
                    continue
                pt0 = [{"i": pe, "y": H[pe] if sgn > 0 else L[pe], "t": "Pole %d%%" % round(sgn * pole * 100)}]
                mid = pe + (e - pe) // 2
                pen = False
                if e - pe >= 6:
                    h1 = max(range(pe, mid + 1), key=lambda t: H[t])
                    h2 = max(range(mid, e + 1), key=lambda t: H[t])
                    l1 = min(range(pe, mid + 1), key=lambda t: L[t])
                    l2 = min(range(mid, e + 1), key=lambda t: L[t])
                    pen = (h2 > h1 and l2 > l1 and H[h2] < H[h1] * .995 and L[l2] > L[l1] * 1.005 and
                           (H[h2] - L[l2]) < (H[h1] - L[l1]) * .7)
                if pen:
                    r = _eval(x, nm_p, (h1, H[h1], h2, H[h2]), (l1, L[l1], l2, L[l2]), abs(C[pe] - ps), "up" if sgn > 0 else "down",
                              only="up" if sgn > 0 else "down", check=False, pts=pt0,
                              shapes=[_ln(ps_i, ps, pe, C[pe], "t", "Pole") for ps_i in [pe - 10 + (C[pe - 10:pe].index(ps))]])
                else:
                    r = _eval(x, nm_f, _flat(pe, fh, i0), _flat(pe, fl, i0), abs(C[pe] - ps), "up" if sgn > 0 else "down",
                              only="up" if sgn > 0 else "down", check=False, pts=pt0,
                              shapes=[_ln(pe - 10 + (C[pe - 10:pe].index(ps)), ps, pe, C[pe], "t", "Pole")])
                if r:
                    add(r)
                    done = True
                    break

    # 6) V reversal, island, diamond
    _vshape(x, add)
    _island(x, add)
    _diamond(x, add)

    # same naam + direction ke duplicate hatao (sabse achha score rakho)
    uniq = {}
    for r in res:
        kk = (r["name"], r["dir"])
        if kk not in uniq or r["score"] > uniq[kk]["score"]:
            uniq[kk] = r
    res = list(uniq.values())
    drop = set()
    for r in res:  # bade pattern ke saath chhota (same direction) hata do
        if r["name"] == "Double bottom" and any(q["name"] == "Triple bottom" for q in res):
            drop.add(id(r))
        if r["name"] == "Double top" and any(q["name"] == "Triple top" for q in res):
            drop.add(id(r))
        if r["name"] == "Rounding bottom (saucer)" and any(q["name"] == "Cup & handle" for q in res):
            drop.add(id(r))
        # W / M / H&S jaise reversal ka ek hissa katora (cup) ya arch jaisa dikhta hai: tabhi hatao jab bada pattern zyada score wala ho
        if r["name"] in ("Cup & handle", "Rounding bottom (saucer)"):
            rv = [q["score"] for q in res if q["name"] in ("Double bottom", "Triple bottom", "Inverse head & shoulders") and q["dir"] == "up"]
            if rv and max(rv) > r["score"]:
                drop.add(id(r))
        if r["name"] == "Rounding top":
            rv = [q["score"] for q in res if q["name"] in ("Double top", "Triple top", "Head & shoulders") and q["dir"] == "down"]
            if rv and max(rv) > r["score"]:
                drop.add(id(r))
    res = [r for r in res if id(r) not in drop]
    order = {"brk": 0, "near": 1, "forming": 2}
    res.sort(key=lambda r: (order.get(r["state"], 3), -r["score"]))
    for r in res:
        r["tf"] = tf
    return {"all": res, "candles": x["cand"]}


def best(bars, forming=False, tf="D"):
    """Scanner ke liye: sabse achha pattern (bina geometry ke). forming=False: banne wale pattern chhod do."""
    a = analyse(bars, tf)
    if not a:
        return None
    L = [r for r in a["all"] if forming or r["state"] != "forming"]
    if not L:
        return None
    r = dict(L[0])
    for k in ("lines", "shapes", "pts", "desc", "start"):
        r.pop(k, None)
    r["why"] = r["why"][:2]
    return r
