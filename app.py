"""Stock Advisor: Flask server. Data Yahoo Finance (yfinance) se, bina key ke."""
import math
import os
import time
from datetime import datetime, timedelta, timezone

import pandas as pd
import yfinance as yf
from flask import Flask, jsonify, request, send_from_directory

from backtest import run as bt_run, stats as bt_stats
from technical import analyse
from universe import SECTORS, UNIVERSE

app = Flask(__name__)
HERE = os.path.dirname(os.path.abspath(__file__))
STATIC = {"manifest.json", "sw.js", "icon-192.png", "icon-512.png"}
_cache = {}


def cached(key, ttl, fn):
    hit = _cache.get(key)
    if hit and time.time() - hit[0] < ttl:
        return hit[1]
    val = fn()
    _cache[key] = (time.time(), val)
    if len(_cache) > 400:  # keep memory small on the free server
        for k in sorted(_cache, key=lambda x: _cache[x][0])[:100]:
            _cache.pop(k, None)
    return val


def ist_now():
    return datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)


def market_open():
    t = ist_now()
    m = t.hour * 60 + t.minute
    return t.weekday() < 5 and 555 <= m <= 930


def clean(o):
    """JSON mein NaN/inf nahi chalta, unhe None bana do."""
    if isinstance(o, float):
        return None if (math.isnan(o) or math.isinf(o)) else o
    if isinstance(o, dict):
        return {k: clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [clean(v) for v in o]
    return o


def reply(o, code=200):
    return jsonify(clean(o)), code


def err(msg, code=400):
    return reply({"error": msg}, code)


def fnum(x):
    try:
        v = float(x)
        return None if math.isnan(v) else v
    except Exception:
        return None


def to_bars(df, project=False):
    bars = []
    for ts, r in df.iterrows():
        c = fnum(r.get("Close"))
        if c is None:
            continue
        bars.append({"d": str(ts)[:10], "o": fnum(r.get("Open")) or c, "h": fnum(r.get("High")) or c,
                     "l": fnum(r.get("Low")) or c, "c": c, "v": fnum(r.get("Volume")) or 0.0})
    if project and bars and bars[-1]["d"] == ist_now().strftime("%Y-%m-%d"):
        t = ist_now()  # aaj ka volume adhura hota hai, poore din ke hisaab se scale karo
        frac = min(1.0, max(0.2, ((t.hour * 60 + t.minute) - 555) / 375))
        bars[-1]["v"] = bars[-1]["v"] / frac
    return bars


def frames(symbols, period="6mo"):
    out = {}
    for i in range(0, len(symbols), 60):
        chunk = symbols[i:i + 60]
        try:
            data = yf.download(chunk, period=period, interval="1d", group_by="ticker",
                               auto_adjust=False, threads=True, progress=False)
        except Exception:
            continue
        for s in chunk:
            try:
                df = data[s] if isinstance(data.columns, pd.MultiIndex) else data
                df = df.dropna(subset=["Close"])
                if len(df):
                    out[s] = df
            except Exception:
                pass
    return out


def quotes(symbols):
    fr = cached("q:" + ",".join(sorted(symbols)), 25, lambda: frames(symbols, "5d"))
    out = {}
    for s, df in fr.items():
        c = df["Close"].dropna()
        price = float(c.iloc[-1])
        prev = float(c.iloc[-2]) if len(c) > 1 else price
        out[s] = {"price": price, "chg": (price / prev - 1) * 100 if prev else 0.0, "asOf": str(df.index[-1])[:16]}
    return out


def get_info(sym):
    def f():
        try:
            return yf.Ticker(sym).info or {}
        except Exception:
            return {}
    return cached("i:" + sym, 900, f)


def sentiment(sym):
    try:
        from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
        titles = []
        for it in (yf.Ticker(sym).news or [])[:15]:
            c = it.get("content") or it
            if c.get("title"):
                titles.append(c["title"])
        if not titles:
            return None
        a = SentimentIntensityAnalyzer()
        return round(sum(a.polarity_scores(t)["compound"] for t in titles) / len(titles), 2)
    except Exception:
        return None


# ---------------------------------------------------------------- pages
@app.route("/")
def index():
    r = send_from_directory(HERE, "index.html")
    r.headers["Cache-Control"] = "no-cache"
    return r


@app.route("/<path:name>")
def static_files(name):
    if name in STATIC:
        return send_from_directory(HERE, name)
    return err("Not found", 404)


# ---------------------------------------------------------------- api
@app.route("/api/search")
def api_search():
    q = request.args.get("q", "").strip()
    if len(q) < 2:
        return reply([])
    out, seen = [], set()
    try:
        qs = cached("s:" + q.lower(), 600, lambda: yf.Search(q, max_results=15).quotes)
    except Exception:
        qs = []
    for suffix in (".NS", ".BO"):
        for r in qs:
            sym = r.get("symbol", "")
            base = sym.rsplit(".", 1)[0]
            if sym.endswith(suffix) and base not in seen and r.get("quoteType") in (None, "EQUITY"):
                seen.add(base)
                out.append({"id": sym, "name": r.get("longname") or r.get("shortname") or base})
    up = q.upper().replace(" ", "")
    for s in UNIVERSE:  # local help: type RELI -> RELIANCE
        base = s.rsplit(".", 1)[0]
        if base.startswith(up) and base not in seen:
            seen.add(base)
            out.append({"id": s, "name": base})
    if not out and up.replace("-", "").replace("&", "").isalnum():
        out.append({"id": up if "." in up else up + ".NS", "name": up})
    return reply(out[:6])


@app.route("/api/stock")
def api_stock():
    sym = request.args.get("symbol", "").strip().upper()
    if not sym:
        return err("Symbol do.")

    def build():
        t = yf.Ticker(sym)
        h = t.history(period="1y", interval="1d", auto_adjust=False)
        if h is None or h.empty:
            return None
        h = h.dropna(subset=["Close"])
        allb = to_bars(h, market_open())
        raw = to_bars(h)
        info = get_info(sym)
        closes = [b["c"] for b in raw]
        price = closes[-1]
        prev = closes[-2] if len(closes) > 1 else price

        def ret(n):
            return (price / closes[-1 - n] - 1) * 100 if len(closes) > n else None
        pe = lambda k: fnum(info.get(k))
        pct = lambda v: None if v is None else "%.2f%%" % (v * 100)
        two = lambda v: None if v is None else "%.2f" % v
        dy = fnum(info.get("dividendRate"))
        rat = [r for r in [
            ["P/E", two(pe("trailingPE"))], ["Forward P/E", two(pe("forwardPE"))], ["Price to Book", two(pe("priceToBook"))],
            ["Net margin", pct(pe("profitMargins"))], ["ROE", pct(pe("returnOnEquity"))],
            ["Debt to Equity", two(pe("debtToEquity"))],
            ["Dividend yield", None if not dy else "%.2f%%" % (dy / price * 100)],
            ["Beta", two(pe("beta"))], ["EPS (TTM)", two(pe("trailingEps"))]] if r[1]]
        officers = info.get("companyOfficers") or []
        return {
            "symbol": sym, "name": info.get("longName") or info.get("shortName") or sym.rsplit(".", 1)[0],
            "price": price, "chg": (price / prev - 1) * 100 if prev else 0.0, "asOf": str(h.index[-1])[:16],
            "hi": max(b["h"] for b in raw[-252:]), "lo": min(b["l"] for b in raw[-252:]),
            "dma": sum(closes[-50:]) / 50 if len(closes) >= 50 else None,
            "dma200": sum(closes[-200:]) / 200 if len(closes) >= 200 else None,
            "target": fnum(info.get("targetMeanPrice")), "mcap": fnum(info.get("marketCap")),
            "sector": info.get("sector"), "industry": info.get("industry"),
            "exch": "NSE" if sym.endswith(".NS") else "BSE" if sym.endswith(".BO") else info.get("exchange"),
            "ceo": officers[0].get("name") if officers else None, "emp": info.get("fullTimeEmployees"),
            "web": info.get("website"), "desc": info.get("longBusinessSummary"),
            "ret": {k: v for k, v in {"1 Din": ret(1), "1 Hafta": ret(5), "1 Mahina": ret(21), "3 Mahine": ret(63),
                                      "6 Mahine": ret(126), "1 Saal": ret(len(closes) - 1)}.items() if v is not None},
            "rat": rat, "sentiment": sentiment(sym), "bars": allb[-120:],
        }
    try:
        d = cached("st:" + sym, 60, build)
    except Exception:
        return err("Data lene me dikkat aayi, thodi der baad try karo.", 502)
    if not d:
        return err("Is symbol ka data nahi mila.", 404)
    return reply(d)


@app.route("/api/quote")
def api_quote():
    syms = [s.strip().upper() for s in request.args.get("symbols", "").split(",") if s.strip()][:60]
    if not syms:
        return reply({})
    try:
        return reply(quotes(syms))
    except Exception:
        return err("Price nahi mila, thodi der baad try karo.", 502)


@app.route("/api/peers")
def api_peers():
    sym = request.args.get("symbol", "").strip().upper()
    sector = SECTORS.get(sym) or get_info(sym).get("sector")
    if not sector:
        return reply([])
    peers = [s for s in UNIVERSE if SECTORS[s] == sector and s != sym][:8]
    try:
        qs = quotes(peers)
    except Exception:
        qs = {}
    return reply([{"id": s, "name": s.rsplit(".", 1)[0], "price": qs.get(s, {}).get("price")} for s in peers][:6])


@app.route("/api/scan")
def api_scan():
    src = request.args.get("src", "nse")
    n = max(1, min(int(request.args.get("n", "20") or 20), 50))
    if src == "wl":
        syms = [s.strip().upper() for s in request.args.get("symbols", "").split(",") if s.strip()][:50]
        if not syms:
            return err("Watchlist khali hai.")
    else:
        syms = UNIVERSE
    key = "scan:" + (",".join(syms) if src == "wl" else "nse")
    try:
        fr = cached(key, 300, lambda: frames(syms, "6mo"))
    except Exception:
        return err("Data lene me dikkat aayi.", 502)
    open_ = market_open()
    res = []
    for s, df in fr.items():
        T = analyse(to_bars(df, open_))
        if not T:
            continue
        c = df["Close"].dropna()
        price = float(c.iloc[-1])
        prev = float(c.iloc[-2]) if len(c) > 1 else price
        if src == "wl" or T["state"] == "brk" or (T["state"] == "near" and T["score"] >= 45):
            res.append({"id": s, "name": s.rsplit(".", 1)[0], "price": price,
                        "chg": (price / prev - 1) * 100 if prev else 0.0,
                        "T": {k: T[k] for k in ("score", "label", "k", "sum", "state", "base", "entry", "sl", "t1", "t2")}})
    res.sort(key=lambda r: -r["T"]["score"])
    return reply({"checked": len(fr), "results": res[:n]})


@app.route("/api/backtest")
def api_backtest():
    syms = [s.strip().upper() for s in request.args.get("symbols", "").split(",") if s.strip()][:10]
    if not syms:
        return err("Koi stock nahi chuna.")
    hold = int(request.args.get("hold", "20") or 20)
    score = float(request.args.get("score", "70") or 70)
    vol = float(request.args.get("vol", "1.5") or 1.5)
    sig_all, bas_all, rows = [], [], []
    for s in syms:
        try:
            df = cached("h10:" + s, 3600, lambda s=s: yf.Ticker(s).history(period="10y", interval="1d", auto_adjust=False))
            bars = to_bars(df.dropna(subset=["Close"]))
        except Exception:
            continue
        if len(bars) < 200:
            continue
        sig, bas = bt_run(bars, score, vol, hold)
        sig_all += sig
        bas_all += bas
        rows.append({"name": s.rsplit(".", 1)[0], "yrs": "%.1f" % (len(bars) / 250), "s": bt_stats(sig)})
    if not rows:
        return err("History data nahi mila.", 502)
    return reply({"s": bt_stats(sig_all), "b": bt_stats(bas_all), "rows": rows})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")))
