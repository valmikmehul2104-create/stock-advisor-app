"""Trade signals: BUY / SELL points (chart par tag), signal ka track record aur aaj ka Trade Idea.

Rule (breakout system, technical.analyse par based):
  BUY  : price ne pichhle resistance ke upar close diya + volume average se zyada + score 60+  (bar ke close par entry)
  SELL : (1) stop-loss lage  (2) Target 2 mile  (3) Target 1 ke baad price 20 EMA ke neeche band ho  (4) 40 din se zyada ho jaye
"""
from technical import analyse, avg, ema, rsi14


def _why(bars, i, T):
    C = [b["c"] for b in bars[:i + 1]]
    cur = C[-1]
    e20, e50 = ema(C, 20)[-1], ema(C, 50)[-1] if len(C) >= 50 else ema(C, 20)[-1]
    r = rsi14(C)
    out = ["Price %s ke upar breakout (%.1f%% upar)" % ("{:,.0f}".format(T["base"]), T["ext"])]
    if T.get("volX"):
        out.append("Volume average ka %.1fx" % T["volX"])
    if cur > e20 > e50:
        out.append("Trend majboot: price 20 aur 50 EMA ke upar")
    elif cur > e50:
        out.append("Price 50 EMA ke upar")
    if r is not None and 50 <= r <= 75:
        out.append("RSI %.0f: momentum achha" % r)
    if T.get("patterns"):
        out.append("Pattern: " + T["patterns"][0])
    return out[:4]


def trades(bars, min_score=60, min_vol=1.2, max_hold=40, start=60):
    """History me jahan jahan rule se BUY / SELL banta, unki list (aakhri trade open ho sakta hai)."""
    n = len(bars)
    C = [b["c"] for b in bars]
    H = [b["h"] for b in bars]
    e20 = ema(C, 20)
    out, i = [], max(start, 30)
    while i < n:
        if C[i] <= max(H[i - 25:i - 5]):  # sasta pre-check: breakout ke liye purane high ke upar band hona zaroori
            i += 1
            continue
        T = analyse(bars[max(0, i - 119):i + 1])
        if not (T and T["state"] == "brk" and T["score"] >= min_score and (T["volX"] or 0) >= min_vol and T["t1"] > C[i] * 1.02):
            i += 1
            continue
        entry, sl, t1, t2 = C[i], T["sl"], T["t1"], T["t2"]
        tr = {"bi": i, "bd": bars[i]["d"], "bp": entry, "sl": sl, "t1": t1, "t2": t2, "score": T["score"], "why": _why(bars, i, T),
              "open": True, "si": None, "sd": None, "sp": None, "sw": None, "ret": None, "days": None}
        hit1 = False
        for j in range(i + 1, n):
            b = bars[j]
            ex = None
            if b["o"] <= sl:
                ex = (b["o"], "Stop-loss (gap down)")
            elif b["l"] <= sl:
                ex = (sl, "Stop-loss")
            elif b["h"] >= t2:
                ex = (t2, "Target 2 mila")
            else:
                if b["h"] >= t1:
                    hit1 = True
                if hit1 and b["c"] < e20[j]:
                    ex = (b["c"], "Target 1 ke baad trend toota (20 EMA)")
                elif j - i >= max_hold:
                    ex = (b["c"], "Time exit (%d din)" % max_hold)
            if ex:
                tr.update(open=False, si=j, sd=b["d"], sp=ex[0], sw=ex[1], ret=(ex[0] / entry - 1) * 100, days=j - i)
                break
        out.append(tr)
        if tr["open"]:
            break
        i = tr["si"] + 1
    return out


def stats(trs, bars, start=60):
    closed = [t for t in trs if not t["open"]]
    bh = (bars[-1]["c"] / bars[start]["c"] - 1) * 100 if len(bars) > start else None
    if not closed:
        return {"n": 0, "bh": bh}
    rets = [t["ret"] for t in closed]
    tot = 1.0
    for r in rets:
        tot *= 1 + r / 100
    return {"n": len(closed), "win": sum(1 for r in rets if r > 0) / len(rets) * 100, "avg": avg(rets), "best": max(rets), "worst": min(rets),
            "days": avg([t["days"] for t in closed]), "total": (tot - 1) * 100, "bh": bh}


def idea(bars, trs, T=None):
    """Aaj ka Trade Idea (BUY / SELL / WAIT) aur potential upside."""
    n, cur = len(bars), bars[-1]["c"]
    T = T or analyse(bars[-120:])
    pct = lambda a, b: (a / b - 1) * 100
    op = next((t for t in trs if t["open"]), None)
    if op:
        return {"type": "BUY", "status": "Naya BUY signal" if op["bi"] >= n - 2 else "BUY signal active (hold)", "entry": op["bp"], "date": op["bd"],
                "sl": op["sl"], "t1": op["t1"], "t2": op["t2"], "pnl": pct(cur, op["bp"]), "up1": pct(op["t1"], cur), "up2": pct(op["t2"], cur),
                "risk": pct(cur, op["sl"]), "score": op["score"], "why": op["why"]}
    last = trs[-1] if trs else None
    if last and not last["open"] and last["si"] >= n - 3:
        return {"type": "SELL", "status": "SELL / exit signal: " + last["sw"], "entry": last["bp"], "date": last["sd"], "sl": None, "t1": None, "t2": None,
                "pnl": last["ret"], "why": ["%s ko %s par kharida tha, %s par exit" % (last["bd"], "{:,.0f}".format(last["bp"]), "{:,.0f}".format(last["sp"]))]}
    if T and T["state"] == "bd":
        return {"type": "SELL", "status": "Breakdown: naya mat kharido, holding ho to exit dekho", "entry": cur, "sl": None, "t1": None, "t2": None,
                "why": ["Price 20 din ke closing low ke neeche gaya (breakdown)"]}
    if T and T["state"] == "near" and T["score"] >= 45:
        e = T["base"]
        return {"type": "WAIT", "status": "BUY ka intezaar: %s ke upar close hone par" % "{:,.0f}".format(e), "trigger": e, "entry": e, "sl": T["sl"], "t1": T["t1"],
                "t2": T["t2"], "up1": pct(T["t1"], cur), "up2": pct(T["t2"], cur), "score": T["score"],
                "why": ["Price breakout level se %.1f%% neeche hai" % ((e - cur) / e * 100)]}
    return {"type": "WAIT", "status": "Abhi koi saaf BUY/SELL signal nahi", "why": []}
