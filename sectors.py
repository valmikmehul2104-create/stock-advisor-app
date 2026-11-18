"""Sector-wise teji/mandi ke liye: har stock ko Indian-style sector me daalo (Bank, IT, Pharma, Auto...).
universe.py ke Yahoo sector ko aadhar banakar kuch sector (Bank, Defence, Railways, Cement, Metal...) alag kiye hain.
Naya stock jodna ho to neeche kisi list me naam space de kar likh do (jaise SUZLON)."""
from universe import SECTORS as _YAHOO

SECTOR_LIST = ["Bank", "NBFC & Insurance", "IT", "Pharma & Healthcare", "Auto", "FMCG", "Retail & Consumer",
               "Metals & Mining", "Cement & Building", "Chemicals & Paints", "Oil & Gas", "Power",
               "Capital Goods & Infra", "Defence", "Railways", "Realty", "Telecom & Media"]

_OVER = {
    "Bank": "HDFCBANK ICICIBANK SBIN KOTAKBANK AXISBANK PNB BANKBARODA CANBK INDUSINDBK FEDERALBNK IDFCFIRSTB AUBANK BANDHANBNK YESBANK UNIONBANK INDIANB BANKINDIA RBLBANK DCBBANK CSBBANK EQUITASBNK UJJIVANSFB SOUTHBANK TMB KTKBANK KARURVYSYA CUB IDBI PSB UCOBANK IOB CENTRALBK MAHABANK J&KBANK",
    "Auto": "MARUTI M&M TATAMOTORS BAJAJ-AUTO EICHERMOT HEROMOTOCO TVSMOTOR ASHOKLEY MOTHERSON BOSCHLTD BHARATFORG ESCORTS BALKRISIND APOLLOTYRE MRF CEATLTD SONACOMS UNOMINDA EXIDEIND ENDURANCE GABRIEL SUNDRMFAST CRAFTSMAN",
    "Metals & Mining": "TATASTEEL JSWSTEEL HINDALCO VEDL JINDALSTEL HINDZINC JSL NMDC NATIONALUM SAIL HINDCOPPER WELCORP RATNAMANI COALINDIA APLAPOLLO MOIL GMDCLTD GRAPHITE",
    "Cement & Building": "ULTRACEMCO GRASIM SHREECEM AMBUJACEM JKCEMENT RAMCOCEM DALBHARAT NUVOCO JKLAKSHMI ACC STARCEMENT HEIDELBERG ORIENTCEM CENTURYPLY GREENPANEL GREENLAM",
    "Defence": "HAL BEL BDL MAZDOCK COCHINSHIP GRSE BEML DATAPATTNS ASTRAMICRO ZENTEC",
    "Railways": "RVNL IRCON RAILTEL TITAGARH IRCTC RITES IRFC TEXRAIL JWL",
}
_BY_YAHOO = {
    "Financial Services": "NBFC & Insurance", "Technology": "IT", "Healthcare": "Pharma & Healthcare",
    "Consumer Defensive": "FMCG", "Consumer Cyclical": "Retail & Consumer", "Basic Materials": "Chemicals & Paints",
    "Energy": "Oil & Gas", "Utilities": "Power", "Industrials": "Capital Goods & Infra",
    "Real Estate": "Realty", "Communication Services": "Telecom & Media",
}

SECTOR_OF = {}
for _sec, _names in _OVER.items():
    for _n in _names.split():
        SECTOR_OF[_n + ".NS"] = _sec
for _sym, _y in _YAHOO.items():
    SECTOR_OF.setdefault(_sym, _BY_YAHOO.get(_y, "Capital Goods & Infra"))


def stocks_of(sector):
    return [s for s, v in SECTOR_OF.items() if v == sector]
