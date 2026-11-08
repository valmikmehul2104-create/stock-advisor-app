# v6: Chart pattern ka poora engine (Day / Week / Month)

**Kya naya hai (sirf `patterns.py`, `app.py`, `index.html`, `requirements.txt` badle hain):**
- **28 chart pattern**: Ascending/Descending/Symmetrical triangle, Rectangle, Rising/Falling wedge, Ascending/Descending channel,
  Broadening (megaphone), Double top/bottom, Triple top/bottom, Head & shoulders (+inverse), Rounding bottom/top,
  Cup & handle, Bull/Bear flag, Bull/Bear pennant, Diamond top/bottom, V-top/V-bottom, Island reversal (top/bottom).
- **Candlestick aur gap**: Doji (4 tarah), Hammer, Hanging man, Inverted hammer, Shooting star, Marubozu, Spinning top, Engulfing,
  Harami (+cross), Piercing line, Dark cloud cover, Tweezer top/bottom, Kicker, Morning/Evening star, Abandoned baby,
  Three white soldiers, Three black crows, Three inside/outside up-down, Rising/Falling three methods, Inside/Outside bar,
  aur Gap (breakaway, runaway, exhaustion, common).
- **Timeframe**: har stock ke pattern **Day, Week aur Month** teeno chart par alag dikhte hain. Patterns tab me Day/Week/Month buttons hain
  aur ek list batati hai ki kaunsa pattern kis timeframe me ban raha hai.
- **Lines chart par**: upar/neeche ki trendline, neckline, cup ka curve, diamond ke chaaron kinare, island ka dabba, pole, pivot points (1,2,3 / LS-H-RS).
- **"Ban raha hai"** (forming) halat: jo pattern abhi complete nahi hua wo bhi dikhta hai (kam score ke saath).
- **Pattern scanner** me Timeframe (Day/Week/Month) ka option aur 4 lists: Breakout, Breakdown, Banne wale, Ban raha hai.

**Update kaise karein:** GitHub repo me **Add file > Upload files** se `patterns.py`, `app.py`, `index.html`, `requirements.txt`
(same naam se) upload karke Commit karo. Render 2-3 minute me khud update kar dega.

---

# Stock Advisor: phone par icon wala app (Yahoo Finance data, koi limit nahi)

**Naya:** Groww jaisa interface (candle chart, 1D-All range, Overview / Technicals / News / Events, Buy-Sell bar, bottom menu) aur (chahe to) username + password login.

Isme: stock search (suggestions), chart + volume, breakout/pattern analysis, buy zone/SL/targets,
multiple watchlist (har me 50 stocks), breakout scanner (Large + Mid + Small cap, ~430 NSE stocks),
10 saal ka backtest, price alerts (jab app khula ho). Watchlist aur alerts aapke phone ke browser me save hote hain.

====================================================================
## PART 1: GitHub par daalna
====================================================================
1. Zip ko phone me khol kar **Extract** karo (Files app > zip par tap > Extract). `stock-advisor-pro` folder banega.
2. Chrome me github.com kholo (Chrome menu > **Desktop site** on kar lo, aasan padta hai) aur login karo.
3. Upar **+** > **New repository**.
   - Repository name: `stock-advisor-app`
   - **Public** chuno (code me koi password nahi hai, isse Render ko connect karna aasan hota hai)
   - **Create repository** dabao.
4. Khuli hui khali repo me **uploading an existing file** link dabao.
5. **choose your files** dabao > extracted folder kholo > **saari files** select karo (long-press karke baaki par tap):
   `app.py, backtest.py, technical.py, patterns.py, universe.py, requirements.txt, index.html, login.html, manifest.json, sw.js, icon-192.png, icon-512.png, README.md`
   Dhyan rakho: `__pycache__` jaisa koi folder ho to use mat daalo.
6. Upload poora hone do, neeche **Commit changes** dabao.
7. Repo ke page par saari 13 files dikhni chahiye (`login.html` bhi). Dikh gayi to ye part ho gaya.

====================================================================
## PART 2: Render.com par chalana (free)
====================================================================
1. render.com kholo > **Get Started** > **GitHub** se sign up karo > Authorize karo.
2. Dashboard me upar **+ New** > **Web Service**.
3. **Git Provider** list me `stock-advisor-app` dikhega, use chuno > **Connect**.
   (Na dikhe to **Configure account** > repo ko access do > wapas aao.)
4. Ye fields bharo:
   - **Name:** `stock-advisor` (aapka link isi naam se banega)
   - **Region:** Singapore (India ke sabse paas)
   - **Branch:** `main`
   - **Root Directory:** khali chhodo
   - **Language/Runtime:** Python 3
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn app:app --workers 1 --threads 4 --timeout 300`
   - **Instance Type:** **Free**
5. Neeche **Deploy Web Service** (ya Create Web Service) dabao.
6. Logs me kaam chalta dikhega. 3-5 minute me "Your service is live" aa jayega.
   Upar ek link hoga jaise `https://stock-advisor.onrender.com`.
   Agar build me Python version ka error aaye: **Environment** tab > Add Environment Variable >
   Key `PYTHON_VERSION`, Value `3.11.9` > Save, phir **Manual Deploy > Deploy latest commit**.
7. Wo link phone ke **Chrome** me kholo. Menu (teen dots) > **Install app** (ya **Add to Home screen**). Icon aa gaya.

====================================================================
## Login ke baare me
====================================================================
- Abhi login **band** hai: link kholte hi app khul jata hai (koi username/password nahi).
- Dhyan rakho: link jiske paas ho wo app use kar sakta hai. Link kisi ko mat bhejo.
- Baad me login chahiye to Render > **Environment** me `APP_USERNAME` aur `APP_PASSWORD` daalo (kai users: `APP_USERS` = `ram:pass1;shyam:pass2`). Save karte hi login chalu ho jayega.
- Watchlist, holdings (Buy/Sell record) aur alerts us phone ke browser me save hote hain.
- **Buy / Sell** asli order nahi lagate, sirf aapka portfolio record hai.

====================================================================
## Naye features
====================================================================
- **Chart:** purana line chart (buy zone, stop-loss, targets, breakout level, volume).
- **Teji ya giravat ki vajah:** technical signals, fundamentals, analyst target aur news se "upar le jane wale" aur "niche le jane wale" karan alag-alag.
- **News tab:** positive aur negative news alag, har headline ke saath "stock upar/niche ja sakta hai". News yfinance aur Google News se aati hai. Sentiment headline ke shabdon se automatic nikalta hai, isliye kabhi galat ho sakta hai.
- **Kitne time ke liye khareedein:** BTST (1 din), Swing (3-15 din), Short term (1-3 mahine), Long term (1 saal+). Har ek ka score, wajah, entry, stop-loss aur target.

====================================================================
## NAYA (v5): Chart Pattern interface + phone notification
====================================================================
**Patterns tab (neeche menu me):** sirf chart ke pattern par stocks ki alag list.
- 3 list: **Breakout ↑** (upar toota), **Breakdown ↓** (neeche toota), **Banne wale** (line ke paas, abhi toota nahi).
- Pattern jo pakde jaate hain: Ascending / Descending / Symmetrical triangle, Rectangle (range), Rising / Falling wedge,
  Double top / bottom, Head & shoulders (aur ulta), Bull / Bear flag.
- Har stock par: pattern ka naam, Score, Entry, Stop-loss, Target 1/2, Risk:Reward, volume.
- **Chart + analysis** dabao: candlestick chart, pattern ki lines, breakout candle ka nishan, aur Entry/SL/Target ka hara-lal dabba (figure).
  Neeche: pattern kya hai, kyun, trade plan, aakhri 5 din ke candlestick signals (Engulfing, Hammer, Doji...).
- Kisi bhi stock ke andar bhi naya **Patterns** tab hai (Overview / Technicals / Patterns / News / Events).
- Score 70+ = strong, 50-69 = theek, 50 se kam = kamzor. Pattern fail bhi hote hain, stop-loss zaroor lagao.

**Phone notification (breakout / breakdown alert):**
1. App ko Chrome se **Install app / Add to Home screen** karke icon se kholo.
2. Patterns tab ke neeche **Notification chalu karo** dabao > **Allow**. **Test notification bhejo** se check karo.
3. Ab watchlist ke stocks me naya breakout/breakdown hone par, aur aapke lagaye alerts (breakout / stop-loss / target) par notification aayegi, app band ho tab bhi.
4. **Zaroori (free cron):** free Render server 15 minute me so jata hai aur soye hue server se notification nahi jaati. Isliye:
   - cron-job.org kholo > free sign up > **Create cronjob**.
   - URL: `https://aapka-naam.onrender.com/ping` (apna Render link) > Schedule: **Every 10 minutes** > Save.
   - Ye server ko jaga rakhta hai aur market ke samay (9 se 4 baje, Somvar-Shukravar) har 5-10 minute me check chalata hai.
5. Jab bhi GitHub me update karo (Render dobara deploy kare), app ek baar kholo, taaki notification dobara register ho jaye.
- Notification ke liye `pywebpush` install hota hai (requirements.txt me hai). Deploy me 1-2 minute zyada lag sakte hain.
- Notification ki chabi (VAPID) apne aap ban jaati hai. Chaho to Render Environment me `VAPID_PUBLIC` aur `VAPID_PRIVATE` khud daal sakte ho.

====================================================================
## UPDATE kaise karein (baad me kuch badalna ho)
====================================================================
Render GitHub se judaa hai. GitHub me file badli, to Render apne aap naya version chala deta hai (2-3 minute).

**A. Mujhse nayi file mile (sabse aasan):**
1. GitHub me apni repo kholo > **Add file** > **Upload files**.
2. Nayi file usi naam se upload karo (jaise `index.html` ya `app.py`). Purani file apne aap badal jati hai.
3. **Commit changes** dabao. Bas. Render 2-3 minute me update kar dega.

**B. Chhota badlav khud karna (jaise naya stock jodna):**
1. Repo me `universe.py` par tap karo > upar **pencil (Edit)** dabao.
2. Kisi line me naam space de kar jod do. Jaise Small cap ki line me `SUZLON` ya `IRFC` likh do (NSE ka naam, aage `.NS` mat lagao).
3. **Commit changes** dabao.

**Update aaya ya nahi dekhne ke liye:** Render dashboard > apni service > **Events**. "Deploy live" dikhe to ho gaya.
Phir app ko ek baar band karke kholo. Purana dikhe to page ko neeche kheench kar refresh karo.

Auto-deploy band ho gaya ho to Render me **Manual Deploy > Deploy latest commit** dabao.

====================================================================
## Jaan lo
====================================================================
- Free server 15 minute use na ho to so jata hai. Pehli baar kholne par 30-60 second lagte hain.
- "Sab" scan (430 stocks) pehli baar 1-2 minute le sakta hai. Phir 5 minute tak jaldi aata hai.
- Stocks ki list lagbhag sahi hai (index badalte rehte hain). Jo symbol Yahoo par nahi milta wo apne aap skip ho jata hai.
- Small cap me liquidity kam hoti hai, isliye jo stock roz ₹1 Cr se kam ka trade hota hai use scanner dikhata hi nahi.
- Yahoo ka data thoda delayed hota hai. Kabhi Yahoo cloud servers ko rok de to "Data nahi mila" aa sakta hai; thodi der baad chalega.
- Ye analysis hai, financial advice nahi. Breakout fail bhi hote hain, stop-loss zaroor lagao.
