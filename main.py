# ONLYGAFFLESTP - ONLYGAFFLES SAUCE (ALL CAPS) - FINAL - EVERY CALL STARTS WITH ONLYGAFFLES SAUCE
# Bot Name: ONLYGAFFLESTP - Every message first line is ONLYGAFFLES SAUCE
import time, requests, os
from collections import deque, defaultdict
from datetime import datetime, timezone

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "8701215869")
TWELVEDATA_API_KEY = os.getenv("TWELVEDATA_API_KEY", "733d0fe675c14e74ae20803982e1d9a7")

SYMBOLS = ["USOIL", "BTCUSD", "NAS100", "XAUUSD"]
YAHOO_MAP = {"USOIL": "CL=F", "BTCUSD": "BTC-USD", "NAS100": "NQ=F", "XAUUSD": "GC=F"}
TWELVEDATA_MAP = {"USOIL": "WTI/USD", "BTCUSD": "BTC/USD", "NAS100": "NDX", "XAUUSD": "XAU/USD"}
TWELVEDATA_ALT = {"USOIL": ["USOIL/USD"], "NAS100": ["QQQ"], "XAUUSD": ["GOLD"], "BTCUSD": ["BTCUSD"]}

candles_5m = defaultdict(lambda: deque(maxlen=100))
candles_1h = defaultdict(lambda: deque(maxlen=100))
candles_4h = defaultdict(lambda: deque(maxlen=100))
active_trades = {}
last_signal_time = {}
sl_streak = defaultdict(int)
paused_until = {}

def send_tg(text):
    # ENFORCE: Every message must start with ONLYGAFFLES SAUCE
    if not text.strip().startswith("ONLYGAFFLES SAUCE"):
        text = f"ONLYGAFFLES SAUCE 🧪\n{text}"
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        r = requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": text}, timeout=15)
        print(f"TG {r.status_code}")
    except Exception as e:
        print(f"TG err {e}")

def fetch_twelvedata_safe(sym, interval, target, min_candles=20):
    if not TWELVEDATA_API_KEY:
        return False
    target[sym].clear()
    for try_sym in [TWELVEDATA_MAP.get(sym,sym)] + TWELVEDATA_ALT.get(sym,[]):
        try:
            r = requests.get("https://api.twelvedata.com/time_series", params={"symbol": try_sym, "interval": interval, "outputsize": 100, "apikey": TWELVEDATA_API_KEY}, timeout=10)
            data = r.json()
            if "values" not in data or not data["values"]:
                continue
            vals = data["values"]; vals.reverse()
            if len(vals) < min_candles:
                continue
            for v in vals:
                target[sym].append({'c': float(v['close']), 'h': float(v['high']), 'l': float(v['low']), 'o': float(v['open']), 't': 0})
            return True
        except:
            continue
    target[sym].clear()
    return False

def fetch_yahoo_safe(sym, interval, target, min_candles=20):
    try:
        target[sym].clear()
        yahoo_interval = "5m" if interval=="5m" else "60m" if interval=="1h" else "240m"
        yahoo_range = "5d" if interval=="5m" else "1mo"
        r = requests.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{YAHOO_MAP[sym]}", params={"interval": yahoo_interval, "range": yahoo_range}, headers={"User-Agent":"Mozilla/5.0"}, timeout=12)
        result = r.json()['chart']['result'][0]
        quote = result['indicators']['quote'][0]
        for i in range(len(result['timestamp'])):
            if quote['close'][i] is None: continue
            target[sym].append({'c': float(quote['close'][i]), 'h': float(quote['high'][i]), 'l': float(quote['low'][i]), 'o': float(quote['open'][i]) if quote['open'][i] else float(quote['close'][i]), 't': result['timestamp'][i]})
        return len(target[sym]) >= min_candles
    except:
        target[sym].clear()
        return False

def fetch_all_fixed(sym):
    if not fetch_twelvedata_safe(sym, "5min", candles_5m, 30):
        if sym == "BTCUSD":
            try:
                r = requests.get("https://api.binance.us/api/v3/klines", params={"symbol": "BTCUSD", "interval": "5m", "limit": 100}, timeout=10)
                candles_5m[sym].clear()
                for k in r.json():
                    candles_5m[sym].append({'c': float(k[4]), 'h': float(k[2]), 'l': float(k[3]), 'o': float(k[1]), 't': int(k[0]/1000)})
            except:
                fetch_yahoo_safe(sym, "5m", candles_5m, 30)
        else:
            fetch_yahoo_safe(sym, "5m", candles_5m, 30)
    if not fetch_twelvedata_safe(sym, "1h", candles_1h, 20):
        if not fetch_yahoo_safe(sym, "1h", candles_1h, 20):
            c5 = list(candles_5m[sym]); candles_1h[sym].clear()
            for i in range(0, len(c5), 12):
                chunk = c5[i:i+12]
                if len(chunk) < 6: continue
                candles_1h[sym].append({'c': chunk[-1]['c'], 'h': max(x['h'] for x in chunk), 'l': min(x['l'] for x in chunk), 'o': chunk[0]['o'], 't': 0})
    if not fetch_twelvedata_safe(sym, "4h", candles_4h, 15):
        if not fetch_yahoo_safe(sym, "4h", candles_4h, 15):
            c1 = list(candles_1h[sym]); candles_4h[sym].clear()
            for i in range(0, len(c1), 4):
                chunk = c1[i:i+4]
                if len(chunk) < 2: continue
                candles_4h[sym].append({'c': chunk[-1]['c'], 'h': max(x['h'] for x in chunk), 'l': min(x['l'] for x in chunk), 'o': chunk[0]['o'], 't': 0})

def get_live_price(sym):
    if sym=="BTCUSD":
        try:
            r=requests.get("https://api.binance.us/api/v3/ticker/price", params={"symbol":"BTCUSD"}, timeout=5)
            return float(r.json()['price'])
        except: pass
    if TWELVEDATA_API_KEY:
        for try_sym in [TWELVEDATA_MAP.get(sym,sym)] + TWELVEDATA_ALT.get(sym,[]):
            try:
                r=requests.get("https://api.twelvedata.com/price", params={"symbol":try_sym,"apikey":TWELVEDATA_API_KEY}, timeout=5)
                if "price" in r.json(): return float(r.json()["price"])
            except: continue
    try:
        r=requests.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{YAHOO_MAP[sym]}", params={"interval":"1m","range":"1d"}, headers={"User-Agent":"Mozilla/5.0"}, timeout=8)
        closes=[c for c in r.json()['chart']['result'][0]['indicators']['quote'][0]['close'] if c is not None]
        return closes[-1] if closes else None
    except:
        return list(candles_5m[sym])[-1]['c'] if candles_5m[sym] else None

def calc_atr(candles_list):
    if len(candles_list) < 15: return 0
    c=list(candles_list); trs=[]
    for i in range(1,len(c)):
        h,l,pc=c[i]['h'],c[i]['l'],c[i-1]['c']
        trs.append(max(h-l,abs(h-pc),abs(l-pc)))
    return sum(trs[-14:])/14 if trs else 0

def detect_swings(candles_list):
    c=list(candles_list); sh=[]; sl=[]
    for i in range(2,len(c)-2):
        if c[i]['h'] > c[i-1]['h'] and c[i]['h'] > c[i-2]['h'] and c[i]['h'] > c[i+1]['h'] and c[i]['h'] > c[i+2]['h']:
            sh.append((i, c[i]['h']))
        if c[i]['l'] < c[i-1]['l'] and c[i]['l'] < c[i-2]['l'] and c[i]['l'] < c[i+1]['l'] and c[i]['l'] < c[i+2]['l']:
            sl.append((i, c[i]['l']))
    return sh, sl

def detect_bos_choch(candles_list):
    sh, sl = detect_swings(candles_list); c=list(candles_list)
    if len(c)<10 or len(sh)<2 or len(sl)<2: return "choppy", "No structure"
    last_h=sh[-1][1]; prev_h=sh[-2][1]; last_l=sl[-1][1]; prev_l=sl[-2][1]
    if last_h > prev_h and last_l > prev_l: return "bullish_bos", f"BOS bullish HH {prev_h:.2f}->{last_h:.2f} HL {prev_l:.2f}->{last_l:.2f}"
    if last_h < prev_h and last_l < prev_l: return "bearish_bos", f"BOS bearish LH {prev_h:.2f}->{last_h:.2f} LL {prev_l:.2f}->{last_l:.2f}"
    if last_h > prev_h and last_l < prev_l: return "choch_bullish", f"CHoCH bullish sweep low then BOS high"
    if last_h < prev_h and last_l > prev_l: return "choch_bearish", f"CHoCH bearish sweep high then BOS low"
    return "choppy", "Choppy"

def detect_sweep(candles_list):
    c=list(candles_list)
    if len(c)<20: return None
    atr=calc_atr(candles_list)
    if atr==0: return None
    recent=c[-20:]; min_low=min(x['l'] for x in recent)
    cnt_low=sum(1 for x in recent if abs(x['l']-min_low) < atr*0.15)
    if cnt_low>=2 and c[-1]['c'] > min_low + atr*0.3:
        return f"sell_side_swept", f"Sell-side swept {min_low:.2f} - {cnt_low} equal lows (turtle soup)"
    max_high=max(x['h'] for x in recent)
    cnt_high=sum(1 for x in recent if abs(x['h']-max_high) < atr*0.15)
    if cnt_high>=2 and c[-1]['c'] < max_high - atr*0.3:
        return f"buy_side_swept", f"Buy-side swept {max_high:.2f} - {cnt_high} equal highs (turtle soup)"
    return None

def find_opposing_liquidity(sym, direction):
    c5 = list(candles_5m[sym])
    sh_5m, sl_5m = detect_swings(candles_5m[sym])
    sh_1h, sl_1h = detect_swings(candles_1h[sym]) if len(candles_1h[sym])>10 else (sh_5m, sl_5m)
    if direction == "long":
        tp1 = max(x['h'] for x in c5[-20:]) if c5 else c5[-1]['c']*1.01
        tp2 = max(x[1] for x in sh_1h[-3:]) if sh_1h else max(x[1] for x in sh_5m[-3:]) if sh_5m else tp1*1.002
        highs = [x['h'] for x in c5[-30:]]
        atr = calc_atr(candles_5m[sym])
        highs_sorted = sorted(highs, reverse=True)
        cluster = [highs_sorted[0]] if highs_sorted else [tp2]
        for h in highs_sorted[1:]:
            if abs(h - cluster[-1]) < atr*0.25:
                cluster.append(h)
            else:
                break
        buy_side_pool = max(cluster) if cluster else tp2
        tp3 = buy_side_pool
        tp4 = tp3 + atr*1.5
        tp5 = tp3 + atr*3.0
        return [tp1, tp2, tp3, tp4, tp5], f"Buy-side pool {buy_side_pool:.2f}"
    else:
        tp1 = min(x['l'] for x in c5[-20:]) if c5 else c5[-1]['c']*0.99
        tp2 = min(x[1] for x in sl_1h[-3:]) if sl_1h else min(x[1] for x in sl_5m[-3:]) if sl_5m else tp1*0.998
        lows = [x['l'] for x in c5[-30:]]
        atr = calc_atr(candles_5m[sym])
        lows_sorted = sorted(lows)
        cluster = [lows_sorted[0]] if lows_sorted else [tp2]
        for l in lows_sorted[1:]:
            if abs(l - cluster[-1]) < atr*0.25:
                cluster.append(l)
            else:
                break
        sell_side_pool = min(cluster) if cluster else tp2
        tp3 = sell_side_pool
        tp4 = tp3 - atr*1.5
        tp5 = tp3 - atr*3.0
        return [tp1, tp2, tp3, tp4, tp5], f"Sell-side pool {sell_side_pool:.2f}"

def premium_discount(curr, rh, rl):
    if rh==rl: return "equilibrium", 50
    pos=(curr-rl)/(rh-rl)*100
    if pos<40: return "discount", pos
    if pos>60: return "premium", pos
    return "equilibrium", pos

def htf_bias(sym):
    if len(candles_4h[sym])<10 or len(candles_1h[sym])<10: 
        return "neutral", "HTF insufficient"
    b4,d4=detect_bos_choch(candles_4h[sym]); b1,d1=detect_bos_choch(candles_1h[sym])
    c4=list(candles_4h[sym]); curr=c4[-1]['c']; rh=max(x['h'] for x in c4[-10:]); rl=min(x['l'] for x in c4[-10:])
    pd,pct=premium_discount(curr,rh,rl)
    if "bullish" in b4 and "bullish" in b1 and pd=="discount": return "bullish", f"4H {b4} +1H {b1} | Discount {pct:.0f}%"
    if "bearish" in b4 and "bearish" in b1 and pd=="premium": return "bearish", f"4H {b4} +1H {b1} | Premium {pct:.0f}%"
    return "neutral", f"4H {b4}/1H {b1} {pd} {pct:.0f}%"

def is_killzone():
    h=datetime.now(timezone.utc).hour
    if 8<=h<=11 or 13<=h<=16: return True, f"Killzone ACTIVE {h} UTC"
    return False, f"Outside killzone {h} UTC"

def get_ai_confluence(sym):
    c5=candles_5m[sym]
    if len(c5)<30: return 0,"",None,None,{}, "Need 30+ candles"
    if sym in paused_until and time.time() < paused_until[sym]: return 0,"",None,None,{}, "Paused 4h after 2SL"
    curr=list(c5)[-1]['c']; atr=calc_atr(c5)
    if atr==0: return 0,"",None,None,{}, "ATR zero"
    bias_htf,bias_desc=htf_bias(sym)
    ltf_bias,ltf_desc=detect_bos_choch(c5)
    sweep=detect_sweep(c5)
    sh,sl=detect_swings(c5)
    recent_high=max(x['h'] for x in list(c5)[-30:]); recent_low=min(x['l'] for x in list(c5)[-30:])
    pd,pct=premium_discount(curr,recent_high,recent_low)
    kz_active,kz_desc=is_killzone()
    def cluster_low():
        lows=[x[1] for x in sl[-5:]] if sl else [recent_low]
        lows.sort(); cl=[lows[0]]
        for l in lows[1:]:
            if abs(l-cl[-1])<atr*0.6: cl.append(l)
            else: break
        return min(cl)
    def cluster_high():
        highs=[x[1] for x in sh[-5:]] if sh else [recent_high]
        highs.sort(reverse=True); cl=[highs[0]]
        for h in highs[1:]:
            if abs(h-cl[-1])<atr*0.6: cl.append(h)
            else: break
        return max(cl)
    cl_low=cluster_low(); cl_high=cluster_high()
    long_score=0; short_score=0; reasons=[]
    if "bullish" in bias_htf: long_score+=30; reasons.append(f"HTF Bullish {bias_desc}")
    elif "bearish" in bias_htf: short_score+=30; reasons.append(f"HTF Bearish {bias_desc}")
    if sweep and "sell_side" in sweep[0]: long_score+=25; reasons.append(f"Liquidity: {sweep[1]}")
    if sweep and "buy_side" in sweep[0]: short_score+=25; reasons.append(f"Liquidity: {sweep[1]}")
    if "bullish" in ltf_bias: long_score+=20; reasons.append(f"Structure: {ltf_desc}")
    if "bearish" in ltf_bias: short_score+=20; reasons.append(f"Structure: {ltf_desc}")
    if pd=="discount": long_score+=10; reasons.append(f"Discount {pct:.0f}%")
    if pd=="premium": short_score+=10; reasons.append(f"Premium {pct:.0f}%")
    if kz_active: long_score+=5; short_score+=5; reasons.append(kz_desc)
    
    if long_score>=80 and long_score>short_score+15:
        sl=cl_low-atr*1.2; risk=curr-sl
        if risk<atr*0.8 or risk>atr*3.5: return 0,"",None,None,{}, f"Risk filter {risk/atr:.1f} ATR"
        tps, pool_desc = find_opposing_liquidity(sym, "long")
        if (tps[0] - curr) < risk*0.5:
            tps[0] = curr + risk*0.8
        data={"bias_htf":bias_desc,"ltf":ltf_desc,"sweep":sweep[1] if sweep else "No sweep","prem_disc":f"{pd} {pct:.0f}%","killzone":kz_desc,"reasons":reasons,"pool":pool_desc}
        return long_score,"long",curr,sl,{"tps":tps,"data":data,"reasons":reasons},f"LONG {long_score}"
    if short_score>=80 and short_score>long_score+15:
        sl=cl_high+atr*1.2; risk=sl-curr
        if risk<atr*0.8 or risk>atr*3.5: return 0,"",None,None,{}, f"Risk filter {risk/atr:.1f} ATR"
        tps, pool_desc = find_opposing_liquidity(sym, "short")
        if (curr - tps[0]) < risk*0.5:
            tps[0] = curr - risk*0.8
        data={"bias_htf":bias_desc,"ltf":ltf_desc,"sweep":sweep[1] if sweep else "No sweep","prem_disc":f"{pd} {pct:.0f}%","killzone":kz_desc,"reasons":reasons,"pool":pool_desc}
        return short_score,"short",curr,sl,{"tps":tps,"data":data,"reasons":reasons},f"SHORT {short_score}"
    return 0,"",None,None,{},f"No A+ Long {long_score} Short {short_score}"

def fmt(sym,p): return f"{p:.1f}" if sym=="NAS100" else f"{p:.2f}"

def build_onlygaffles_sauce(trade):
    # THIS ALWAYS STARTS WITH ONLYGAFFLES SAUCE ALL CAPS
    emoji="🟢" if trade['side']=="BUY" else "🔴"
    data=trade['ai_data']; reasons="\n".join([f"• {r}" for r in data['reasons'][:6]])
    return f"""ONLYGAFFLES SAUCE 🧪
{emoji} ONLYGAFFLES SAUCE — {trade['side']}{trade['symbol']}

🎯 Entry: {fmt(trade['symbol'],trade['entry'])}
🛑 SL: {fmt(trade['symbol'],trade['sl'])} (Cluster +1.2ATR)
1️⃣ TP1: {fmt(trade['symbol'],trade['tps'][0])} (LTF Structure)
2️⃣ TP2: {fmt(trade['symbol'],trade['tps'][1])} (1H Liquidity)
3️⃣ TP3: {fmt(trade['symbol'],trade['tps'][2])} (Opposing Pool - {data.get('pool','')} - MAX PROFIT)
4️⃣ TP4: {fmt(trade['symbol'],trade['tps'][3])}
5️⃣ TP5: {fmt(trade['symbol'],trade['tps'][4])} (Full Print)
📊 Confluence: {trade['confluence']}/100 - A+ SCI MODEL
📡 Source: {trade['source']}
🛡️ SL: Cluster +1.2ATR outside hunt zone

🧠 AI MARKET STRUCTURE:
{reasons}

HTF: {data.get('bias_htf','')}
LTF: {data.get('ltf','')}
Liquidity: {data.get('sweep','')}
Premium/Discount: {data.get('prem_disc','')}
Pool: {data.get('pool','')}
Killzone: {data.get('killzone','')}

ONLYGAFFLESTP 🧪"""

def run():
    print("=== ONLYGAFFLESTP - EVERY CALL STARTS WITH ONLYGAFFLES SAUCE ===")
    for s in SYMBOLS: 
        fetch_all_fixed(s)
        print(f"{s} - 5m:{len(candles_5m[s])} 1h:{len(candles_1h[s])} 4h:{len(candles_4h[s])}")
    # LIVE MESSAGE - MUST START WITH ONLYGAFFLES SAUCE ALL CAPS
    send_tg("""ONLYGAFFLES SAUCE 🧪
ONLYGAFFLESTP LIVE — GOD MODE v2.1 FIXED
Every call starts with ONLYGAFFLES SAUCE
USOIL | BTCUSD | NAS100 | XAUUSD 5m/1h/4h SMC
Liquidity + CHoCH/BOS + Premium/Discount + Killzone
80+ A+ only | Cluster SL 1.2ATR | Max profit to pools""")
    loop=0
    while True:
        try:
            loop+=1
            if loop % 5 == 0:
                for s in SYMBOLS: fetch_all_fixed(s)
            for sym in SYMBOLS:
                price=get_live_price(sym)
                if price is None: continue
                if sym in active_trades:
                    tr=active_trades[sym]
                    for i in range(5):
                        if tr['hits'][i]: continue
                        if (tr['side']=="BUY" and price>=tr['tps'][i]) or (tr['side']=="SELL" and price<=tr['tps'][i]):
                            tr['hits'][i]=True
                            # TP HIT - MUST START WITH ONLYGAFFLES SAUCE
                            send_tg(f"""ONLYGAFFLES SAUCE 🧪
✅ TP{i+1} HIT {sym} {tr['side']} @ {fmt(sym,tr['tps'][i])} - {tr['ai_data'].get('pool','')}""")
                            if i==4:
                                sl_streak[sym]=0
                                del active_trades[sym]
                            break
                    if sym in active_trades and ((tr['side']=="BUY" and price<=tr['sl']) or (tr['side']=="SELL" and price>=tr['sl'])):
                        # SL HIT - MUST START WITH ONLYGAFFLES SAUCE
                        send_tg(f"""ONLYGAFFLES SAUCE 🧪
🛑 SL HIT {sym} {tr['side']} @ {fmt(sym,price)} - Cluster SL protected""")
                        sl_streak[sym]+=1
                        if sl_streak[sym]>=2:
                            paused_until[sym]=time.time()+4*3600
                        del active_trades[sym]
                else:
                    score,dir,entry,sl,extra,msg = get_ai_confluence(sym)
                    if score>=80 and dir:
                        now=time.time()
                        if sym not in last_signal_time or now-last_signal_time[sym]>3600:
                            side="BUY" if dir=="long" else "SELL"
                            src="TWELVEDATA" if TWELVEDATA_API_KEY else "YAHOO"
                            tr={'symbol':sym,'side':side,'entry':entry,'sl':sl,'tps':extra['tps'],'confluence':int(score),'hits':[False]*5,'source':src,'ai_data':extra['data']}
                            tr['ai_data']['reasons']=extra['reasons']
                            active_trades[sym]=tr
                            last_signal_time[sym]=now
                            send_tg(build_onlygaffles_sauce(tr))
            time.sleep(30)
        except Exception as e:
            print(f"Loop error {e}"); import traceback; traceback.print_exc(); time.sleep(10)

if __name__=="__main__":
    run()
