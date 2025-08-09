import os, argparse
import pandas as pd
from utils.binance_http import Http
import yaml

# ดึง OHLCV (klines) + aggTrades ย้อนหลังตามวันที่กำหนด และดึง bookTicker snapshot 1 ชุด

def fetch_klines(symbol, interval, start_ms, end_ms):
    out = []
    cur = start_ms
    limit = 1000
    while True:
        data = Http.get("/api/v3/klines", {
            "symbol": symbol,
            "interval": interval,
            "startTime": cur,
            "endTime": end_ms,
            "limit": limit
        })
        if not data:
            break
        out.extend(data)
        last_open = data[-1][0]
        cur = last_open + 1
        if last_open >= end_ms or len(data) < limit:
            break
    cols = ["open_time","open","high","low","close","volume","close_time","qav","trades","tbb","tbq","ignore"]
    df = pd.DataFrame(out, columns=cols)
    for c in ["open","high","low","close","volume","qav","tbb","tbq"]:
        df[c] = df[c].astype(float)
    df["open_time"] = pd.to_datetime(df["open_time"], unit="ms", utc=True)
    df["close_time"] = pd.to_datetime(df["close_time"], unit="ms", utc=True)
    return df


def fetch_aggtrades(symbol, start_ms, end_ms):
    out = []
    cur = start_ms
    # Binance อนุญาตดึงตามช่วงเวลา; เราเดินหน้าโดยอิง T ของ trade สุดท้าย
    while cur < end_ms:
        data = Http.get("/api/v3/aggTrades", {
            "symbol": symbol,
            "startTime": cur,
            "endTime": min(cur + 30*60*1000, end_ms),
            "limit": 1000
        })
        if not data:
            cur += 30*60*1000
            continue
        out.extend(data)
        cur = data[-1]["T"] + 1
    if not out:
        return pd.DataFrame(columns=["trade_time","price","qty","is_buyer_maker"])
    df = pd.DataFrame(out)
    df["trade_time"] = pd.to_datetime(df["T"], unit="ms", utc=True)
    df["price"] = df["p"].astype(float)
    df["qty"] = df["q"].astype(float)
    df["is_buyer_maker"] = df["m"].astype(bool)
    return df[["trade_time","price","qty","is_buyer_maker"]]


def fetch_bookticker(symbol):
    j = Http.get("/api/v3/ticker/bookTicker", {"symbol": symbol})
    ts = pd.Timestamp.utcnow()
    return pd.DataFrame({
        "time": [ts],
        "best_bid": [float(j["bidPrice"])],
        "best_ask": [float(j["askPrice"])],
        "bid_qty": [float(j["bidQty"])],
        "ask_qty": [float(j["askQty"])],
    })


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    args = ap.parse_args()
    cfg = yaml.safe_load(open(args.config))

    sym = cfg["symbol"]
    iv = cfg["interval"]
    days = int(cfg["history_days"])

    raw_dir = cfg["raw_dir"]
    os.makedirs(raw_dir, exist_ok=True)

    end = pd.Timestamp.utcnow()
    start = end - pd.Timedelta(days=days)
    s_ms = Http.ms(start); e_ms = Http.ms(end)

    print("Fetch klines...")
    kl = fetch_klines(sym, iv, s_ms, e_ms)
    kl.to_parquet(os.path.join(raw_dir, "klines_1m.parquet"))

    print("Fetch aggTrades (may take a while)...")
    tr = fetch_aggtrades(sym, s_ms, e_ms)
    if not tr.empty:
        tr["date"] = tr["trade_time"].dt.date.astype(str)
        for d, g in tr.groupby("date"):
            g.drop(columns=["date"]).to_parquet(os.path.join(raw_dir, f"aggtrades_{d}.parquet"))

    print("Fetch one-time bookTicker snapshot...")
    bt = fetch_bookticker(sym)
    bt.to_parquet(os.path.join(raw_dir, "bookticker_snapshot.parquet"))

    print("Done initial backfill.")

if __name__ == "__main__":
    main()