"""Stock Advisor: Flask server. Data Yahoo Finance (yfinance) se, bina key ke."""
import hashlib
import math
import os
import time
from datetime import datetime, timedelta, timezone

import pandas as pd
import yfinance as yf
from flask import Flask, jsonify, redirect, request, send_from_directory, session
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.security import check_password_hash, generate_password_hash

from backtest import run as bt_run, stats as bt_stats
from technical import analyse
from universe import CAP, SECTORS, UNIVERSE

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)  # Render ke proxy ke peeche asli IP/https
HERE = os.path.dirname(os.path.abspath(__file__))
STATIC = {"manifest.json", "sw.js", "icon-192.png", "icon-512.png"}  # bina login ke bhi khulti hain
_cache = {}

# ---------------------------------------------------------------- login
# Username/password Render ke Environment variables se aate hain (README dekho):
#   APP_USERNAME + APP_PASSWORD           -> ek user
#   APP_USERS = "ram:pass1;shyam:pass2"   -> kai users (alag karne ke liye ; )
# Kuch set nahi kiya to demo login chalta hai: admin / admin123 (isse jaldi badal do).


def _load_users():
    raw = []
    if os.getenv("APP_USERNAME") and os.getenv("APP_PASSWORD"):
        raw.append((os.environ["APP_USERNAME"].strip(), os.environ["APP_PASSWORD"]))
    for part in os.getenv("APP_USERS", "").split(";"):
        if ":" in part:
            u, p = part.split(":", 1)
            if u.strip() and p:
                raw.append((u.strip(), p))
    default = False
    users = {u.lower(): (u, generate_password_hash(p)) for u, p in raw}
    seed = "|".join(sorted("%s:%s" % (u.lower(), p) for u, p in raw))
    return users, default, seed


USERS, DEFAULT_LOGIN, _SEED = _load_users()
AUTH_ON = bool(USERS)  # APP_USERNAME/APP_PASSWORD set nahi hai to login band, app seedha khulta hai
DUMMY_HASH = generate_password_hash("not-a-real-password")
app.secret_key = os.getenv("SECRET_KEY") or hashlib.sha256(("sa-session-v1|" + _SEED).encode()).hexdigest()
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax",
                  SESSION_COOKIE_SECURE=bool(os.getenv("RENDER")),
                  PERMANENT_SESSION_LIFETIME=timedelta(days=30))
if not AUTH_ON:
    print("INFO: login band hai (koi bhi app khol sakta hai). Login chahiye to APP_USERNAME aur APP_PASSWORD set karo.")

_fails = {}  # ip -> [kitni galti, pehli galti ka time, lock khatam hone ka time]
MAX_FAILS, FAIL_WINDOW, LOCK_SECS = 5, 600, 300


def _locked(ip):
    f = _fails.get(ip)
    return bool(f and f[2] > time.time())


def _fail(ip):
    now = time.time()
    f = _fails.get(ip)
    if not f or now - f[1] > FAIL_WINDOW:
        f = [0, now, 0]
    f[0] += 1
    if f[0] >= MAX_FAILS:
        f[2] = now + LOCK_SECS
        f[0], f[1] = 0, now
    _fails[ip] = f
    if len(_fails) > 2000:
        for k in [k for k, v in _fails.items() if v[2] < now and now - v[1] > FAIL_WINDOW]:
            _fails.pop(k, None)


def current_user():
    if not AUTH_ON:
        return "Me"
    u = session.get("u")
    return u if u and u.lower() in USERS else None


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


@app.before_request
def gate():
    p = request.path
    if p in ("/login", "/api/login") or p.lstrip("/") in STATIC or current_user():
        return None
    if p.startswith("/api/"):
        return err("Pehle login karo.", 401)
    return redirect("/login")


@app.after_request
def headers(r):
    r.headers["X-Content-Type-Options"] = "nosniff"
    r.headers["Referrer-Policy"] = "same-origin"
    if request.path.startswith("/api/") or request.path in ("/", "/login"):
        r.headers["Cache-Control"] = "no-store"
    return r


# ---------------------------------------------------------------- pages
@app.route("/")
def index():
    return send_from_directory(HERE, "index.html")


@app.route("/login")
def login_page():
    if current_user():
        return redirect("/")
    return send_from_directory(HERE, "login.html")


@app.route("/api/login", methods=["POST"])
def api_login():
    d = request.get_json(silent=True) or {}
    ip = request.remote_addr or "?"
    if _locked(ip):
        return err("Bahut galat koshish hui. 5 minute baad dobara try karo.", 429)
    u = str(d.get("username", "")).strip()
    p = str(d.get("password", ""))
    rec = USERS.get(u.lower())
    ok = check_password_hash(rec[1] if rec else DUMMY_HASH, p) and rec is not None
    if not ok:
        _fail(ip)
        return err("Username ya password galat hai.", 401)
    _fails.pop(ip, None)
    session.clear()
    session["u"] = rec[0]
    session.permanent = True
    return reply({"user": rec[0]})


@app.route("/api/logout", methods=["POST"])
def api_logout():
    session.clear()
    return reply({"ok": True})


@app.route("/api/me")
def api_me():
    return reply({"user": current_user(), "auth": AUTH_ON})


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
    same = [s for s in UNIVERSE if SECTORS[s] == sector and s != sym]
    mine = CAP.get(sym)  # pehle usi cap size ke stocks (mid ke saath mid), phir baaki
    peers = ([s for s in same if CAP.get(s) == mine] + [s for s in same if CAP.get(s) != mine])[:8]
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
        syms = [s for s in UNIVERSE if src in ("all", "nse") or CAP.get(s) == src]
        if not syms:
            return err("Ye option sahi nahi hai.")
    key = "scan:" + (",".join(syms) if src == "wl" else src)
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
        liq = float(df["Volume"].fillna(0).tail(20).mean()) * price / 1e7  # roz ka average turnover (crore)
        if src != "wl" and liq < 1.0:  # bahut kam liquidity: SL par bahut slippage hota hai, skip
            continue
        if src == "wl" or T["state"] == "brk" or (T["state"] == "near" and T["score"] >= 45):
            res.append({"id": s, "name": s.rsplit(".", 1)[0], "cap": CAP.get(s, "").capitalize(), "price": price, "liq": round(liq, 1),
                        "chg": (price / prev - 1) * 100 if prev else 0.0,
                        "T": {k: T[k] for k in ("score", "label", "k", "sum", "state", "base", "entry", "sl", "t1", "t2")}})
    res.sort(key=lambda r: -r["T"]["score"])
    return reply({"checked": len(fr), "results": res[:n]})


RANGES = {"1D": ("5d", "5m", 60), "1W": ("5d", "15m", 120), "1M": ("1mo", "1h", 300), "3M": ("3mo", "1d", 600),
          "6M": ("6mo", "1d", 600), "1Y": ("1y", "1d", 600), "5Y": ("5y", "1wk", 900), "All": ("max", "1mo", 900)}


def to_bars_t(df, intraday):
    fmt = "%Y-%m-%d %H:%M" if intraday else "%Y-%m-%d"
    bars = []
    for ts, r in df.iterrows():
        c = fnum(r.get("Close"))
        if c is None:
            continue
        bars.append({"d": ts.strftime(fmt), "o": fnum(r.get("Open")) or c, "h": fnum(r.get("High")) or c,
                     "l": fnum(r.get("Low")) or c, "c": c, "v": fnum(r.get("Volume")) or 0.0})
    return bars


@app.route("/api/chart")
def api_chart():
    sym = request.args.get("symbol", "").strip().upper()
    rng = request.args.get("range", "1D")
    cfg = RANGES.get(rng)
    if not sym or not cfg:
        return err("Symbol ya range sahi nahi.")
    intraday = cfg[1] in ("5m", "15m", "1h")

    def build():
        h = yf.Ticker(sym).history(period=cfg[0], interval=cfg[1], auto_adjust=False)
        if h is None or h.empty:
            return None
        bars = to_bars_t(h.dropna(subset=["Close"]), intraday)
        prev = None
        if rng == "1D" and bars:  # sirf aakhri trading din, aur usse pehle ka close
            last = bars[-1]["d"][:10]
            old = [b for b in bars if b["d"][:10] != last]
            prev = old[-1]["c"] if old else None
            bars = [b for b in bars if b["d"][:10] == last]
        return {"range": rng, "bars": bars[-400:], "prev": prev}
    try:
        d = cached("ch:%s:%s" % (sym, rng), cfg[2], build)
    except Exception:
        return err("Chart data lene me dikkat aayi.", 502)
    return reply(d or {"range": rng, "bars": [], "prev": None})


@app.route("/api/news")
def api_news():
    sym = request.args.get("symbol", "").strip().upper()
    if not sym:
        return err("Symbol do.")

    def build():
        try:
            raw = yf.Ticker(sym).news or []
        except Exception:
            raw = []
        try:
            from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
            an = SentimentIntensityAnalyzer()
        except Exception:
            an = None
        out = []
        for it in raw[:20]:
            c = it.get("content") or it
            title = c.get("title")
            if not title:
                continue
            url = ((c.get("canonicalUrl") or {}).get("url") or (c.get("clickThroughUrl") or {}).get("url")
                   or c.get("link") or "")
            if not str(url).startswith(("http://", "https://")):
                url = ""
            pub = (c.get("provider") or {}).get("displayName") or c.get("publisher") or ""
            when = c.get("pubDate") or c.get("displayTime") or ""
            if not when and it.get("providerPublishTime"):
                when = datetime.fromtimestamp(it["providerPublishTime"], timezone.utc).isoformat()
            sc = round(an.polarity_scores(title)["compound"], 2) if an else None
            out.append({"title": title, "url": url, "pub": pub, "t": str(when), "s": sc,
                        "sum": (c.get("summary") or "")[:220]})
        return out
    try:
        return reply(cached("n:" + sym, 600, build))
    except Exception:
        return err("News nahi mili, thodi der baad try karo.", 502)


@app.route("/api/events")
def api_events():
    sym = request.args.get("symbol", "").strip().upper()
    if not sym:
        return err("Symbol do.")

    def dstr(x):
        try:
            return str(x)[:10]
        except Exception:
            return None

    def build():
        t = yf.Ticker(sym)
        up = []
        try:
            cal = t.calendar
            cal = cal.to_dict() if hasattr(cal, "to_dict") else (cal or {})
            for k, v in cal.items():
                vals = v if isinstance(v, (list, tuple)) else [v]
                if k.lower().endswith("date") and vals and vals[0] is not None:
                    up.append({"label": k, "d": dstr(vals[0]) + (" se " + dstr(vals[-1]) if len(vals) > 1 else "")})
        except Exception:
            pass
        divs, splits = [], []
        try:
            ds = t.dividends
            divs = [{"d": dstr(i), "v": fnum(v)} for i, v in list(ds.items())[-8:]][::-1]
        except Exception:
            pass
        try:
            sp = t.splits
            splits = [{"d": dstr(i), "v": fnum(v)} for i, v in list(sp.items())[-5:]][::-1]
        except Exception:
            pass
        return {"upcoming": up, "dividends": divs, "splits": splits}
    try:
        return reply(cached("e:" + sym, 1800, build))
    except Exception:
        return err("Events nahi mile, thodi der baad try karo.", 502)


INDICES = [("^NSEI", "NIFTY 50"), ("^BSESN", "SENSEX"), ("^NSEBANK", "BANK NIFTY")]


@app.route("/api/explore")
def api_explore():
    big = [s for s in UNIVERSE if CAP.get(s) == "large"][:40]
    try:
        qs = quotes([i for i, _ in INDICES] + big)
    except Exception:
        return err("Market data nahi mila, thodi der baad try karo.", 502)
    idx = [{"id": i, "name": n, **qs[i]} for i, n in INDICES if i in qs]
    stocks = [{"id": s, "name": s.rsplit(".", 1)[0], **qs[s]} for s in big if s in qs]
    stocks.sort(key=lambda x: -x["chg"])
    return reply({"indices": idx, "gainers": stocks[:6], "losers": stocks[::-1][:6]})


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
