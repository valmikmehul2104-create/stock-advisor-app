# Stock Advisor (phone par icon wala app, Yahoo Finance data, koi limit nahi)

Isme: stock search (suggestions), chart + volume, breakout/pattern analysis, buy zone/SL/targets,
multiple watchlist (har me 50 stocks), breakout scanner (NSE ke ~100 bade stocks), backtest (10 saal),
price alerts (jab app khula ho). Watchlist aur alerts aapke phone ke browser me save hote hain.

## Render.com par chalao (free), ~10 minute
1. GitHub par naya repo banao (jaise `stock-advisor-app`) aur is zip ki SAARI files upload karo
   (Add file > Upload files). Isme koi hidden folder nahi hai, to sab upload ho jayega.
2. render.com par GitHub se sign up karo > **New +** > **Web Service** > apna repo chuno.
3. Ye bharo:
   - Runtime: **Python 3**
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn app:app --workers 1 --threads 4 --timeout 120`
   - Instance Type: **Free**
4. **Create Web Service** dabao. 3-5 minute me "Live" ho jayega aur upar ek https link milega
   (jaise https://stock-advisor-xxxx.onrender.com).
5. Wo link phone ke Chrome me kholo. Menu > **Install app** (ya Add to Home screen). Icon aa jayega.

## Jaan lo
- Free server 15 minute use na ho to so jata hai. Pehli baar kholne par 30-60 second lagte hain.
- Yahoo Finance ka data thoda delayed hota hai. Kabhi Yahoo cloud servers ko rok de to "Data nahi mila" aa sakta hai; thodi der baad chalega.
- NSE ke stocks `.NS` se, BSE ke `.BO` se chalte hain.
- Scanner ke stocks ki list `universe.py` me hai. Apne stocks jodne ke liye wahan naam daalo (jaise `SUZLON.NS`).
- Ye analysis hai, financial advice nahi. Breakout fail bhi hote hain, stop-loss zaroor lagao.
