"""Round 52 data: Yahoo daily bars for India (NSE large caps) and GCC ex-Saudi (Qatar, Dubai, Kuwait) large caps."""
import os, sys, json
HERE = os.path.dirname(os.path.abspath(__file__)); SP = os.path.dirname(HERE); sys.path.insert(0, os.path.join(SP, "edge26")); import yf
LISTS = {
 "india": "RELIANCE TCS HDFCBANK INFY ICICIBANK HINDUNILVR ITC SBIN BHARTIARTL KOTAKBANK LT AXISBANK ASIANPAINT MARUTI SUNPHARMA TITAN ULTRACEMCO BAJFINANCE WIPRO NESTLEIND HCLTECH TECHM POWERGRID NTPC ONGC TATASTEEL JSWSTEEL HINDALCO COALINDIA M&M BAJAJ-AUTO HEROMOTOCO EICHERMOT DRREDDY CIPLA DIVISLAB GRASIM BPCL IOC GAIL ADANIPORTS ADANIENT BRITANNIA DABUR GODREJCP PIDILITIND SHREECEM INDUSINDBK BANKBARODA PNB CANBK VEDL SAIL BHEL TATAPOWER AMBUJACEM ACC LUPIN AUROPHARMA SIEMENS ABB HAVELLS BERGEPAINT COLPAL MARICO TATACONSUM BAJAJFINSV DLF ASHOKLEY TVSMOTOR BOSCHLTD MRF APOLLOHOSP UPL PETRONET NMDC HINDPETRO BEL CUMMINSIND TORNTPHARM BIOCON GLENMARK IDFCFIRSTB FEDERALBNK JINDALSTEL TATACHEM VOLTAS EXIDEIND ZEEL".split(),
 "qatar": "QNBK IQCD QIBK ORDS MARK CBQK DUBK QEWS QIGD MPHC QGTS BRES ERES QATI VFQS GISS QNNS UDCD ABQK KCBK AHCS QFLS QAMC MERS BLDN DHBK MCGS QIIK".split(),
 "dubai": "EMAAR DIB EMIRATESNBD DEWA DU ARMX AIRARABIA DFM EMAARDEV GFH TABREED UPP AMANAT DSI SHUAA ALANSARI CBD MASQ ERC NGI".split(),
 "kuwait": "NBK KFH ZAIN AGLTY BOUBYAN GBK CBK MABANEE HUMANSOFT ALIMTIAZ BURGAN KIB WARBABANK ABK GFH KPROJ JAZEERA BOURSA ALG NIND OOREDOO SOLIDARITY ALMANAR KRE".split()}
SUF = {"india": ".NS", "qatar": ".QA", "dubai": ".AE", "kuwait": ".KW"}
if __name__ == "__main__":
    got = {}
    for mk, L in LISTS.items():
        d = os.path.join(HERE, "data", mk); os.makedirs(d, exist_ok=True); got[mk] = []
        for s in L:
            try:
                r = yf.daily(s + SUF[mk], d)
                if r and r.get("rows", 0) >= 500: got[mk].append((s, r["first"], r["rows"]))
            except Exception as e: print(mk, s, "ERR", str(e)[:80])
        print(mk, len(got[mk]), "of", len(L), "fetched with >= 500 rows; earliest", min(x[1] for x in got[mk]) if got[mk] else None, flush=True)
    json.dump(got, open(os.path.join(HERE, "mk52_fetched.json"), "w"), indent=1)
