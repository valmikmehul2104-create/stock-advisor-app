"""History par breakout rule ka accuracy test (same logic as the app)."""
from technical import analyse, avg


def sim(b, i, T, hold):
    if i + hold >= len(b):
        return None
    e, sl, t1 = b[i]["c"], T["sl"], T["t1"]
    x, out, jx = None, "time", i + hold
    for j in range(i + 1, i + hold + 1):
        if b[j]["o"] <= sl:
            x, out, jx = b[j]["o"], "SL", j
            break
        if b[j]["o"] >= t1:
            x, out, jx = b[j]["o"], "T1", j
            break
        if b[j]["l"] <= sl:
            x, out, jx = sl, "SL", j
            break
        if b[j]["h"] >= t1:
            x, out, jx = t1, "T1", j
            break
    if x is None:
        x = b[i + hold]["c"]
    return {"d": b[i]["d"], "out": out, "jx": jx, "ret": (x - e) / e * 100, "R": (x - e) / (e - sl)}


def run(b, min_sc, min_vol, hold):
    sig, bas, free = [], [], 0
    for i in range(60, len(b) - hold - 1):
        sample = i % 4 == 0
        if not sample:  # cheap pre-check: breakouts need close above the old 20-day high
            base = max(x["h"] for x in b[max(0, i - 25):i - 5]) if i >= 25 else None
            if base is None or b[i]["c"] <= base:
                continue
        T = analyse(b[max(0, i - 119):i + 1])
        if not T:
            continue
        hit = T["state"] == "brk" and T["score"] >= min_sc and (T["volX"] or 0) >= min_vol
        if hit:
            if i >= free:
                r = sim(b, i, T, hold)
                if r:
                    sig.append(r)
                    free = r["jx"] + 1
        elif sample:
            r = sim(b, i, T, hold)
            if r:
                bas.append(r)
    return sig, bas


def stats(a):
    n = len(a)
    if not n:
        return None
    f = lambda k: sum(1 for x in a if x["out"] == k) / n * 100
    return {"n": n, "win": f("T1"), "sl": f("SL"), "pos": sum(1 for x in a if x["ret"] > 0) / n * 100,
            "avg": avg([x["ret"] for x in a]), "R": avg([x["R"] for x in a]), "worst": min(x["ret"] for x in a)}
