import os, asyncio, argparse, json
import pandas as pd
import websockets
import yaml

# เก็บ real-time streams: bookTicker (best bid/ask) + aggTrade
# เขียนเป็นไฟล์รายช่วงใน data/raw/ (ตั้งชื่อด้วย timestamp เพื่อหลีกเลี่ยงการ append Parquet)

async def bookticker_task(url, rows):
    while True:
        try:
            async with websockets.connect(url, ping_interval=20) as ws:
                while True:
                    msg = await ws.recv()
                    j = json.loads(msg)
                    ts = pd.Timestamp.utcnow()
                    rows.append({
                        "time": ts,
                        "best_bid": float(j["b"]),
                        "best_ask": float(j["a"]),
                        "bid_qty": float(j["B"]),
                        "ask_qty": float(j["A"]),
                    })
        except Exception:
            await asyncio.sleep(1.0)  # reconnect backoff


async def aggtrade_task(url, rows):
    while True:
        try:
            async with websockets.connect(url, ping_interval=20) as ws:
                while True:
                    msg = await ws.recv()
                    j = json.loads(msg)
                    rows.append({
                        "trade_time": pd.to_datetime(j["T"], unit="ms", utc=True),
                        "price": float(j["p"]),
                        "qty": float(j["q"]),
                        "is_buyer_maker": bool(j["m"])
                    })
        except Exception:
            await asyncio.sleep(1.0)  # reconnect backoff


async def saver_task(cfg, book_rows, trade_rows):
    raw_dir = cfg["raw_dir"]
    os.makedirs(raw_dir, exist_ok=True)
    save_every = int(cfg["ws"]["save_every_sec"]) or 60

    while True:
        await asyncio.sleep(save_every)
        now = pd.Timestamp.utcnow()
        stamp = now.strftime("%Y-%m-%d_%H%M%S")
        if book_rows:
            dfb = pd.DataFrame(book_rows)
            book_rows.clear()
            dfb.to_parquet(os.path.join(raw_dir, f"bookticker_{stamp}.parquet"))
        if trade_rows:
            dft = pd.DataFrame(trade_rows)
            trade_rows.clear()
            dft.to_parquet(os.path.join(raw_dir, f"aggtrades_{stamp}.parquet"))


async def run(cfg):
    sym = cfg["symbol"].lower()
    bt_url = f"wss://stream.binance.com:9443/ws/{sym}@bookTicker"
    at_url = f"wss://stream.binance.com:9443/ws/{sym}@aggTrade"

    book_rows = []
    trade_rows = []

    await asyncio.gather(
        bookticker_task(bt_url, book_rows),
        aggtrade_task(at_url, trade_rows),
        saver_task(cfg, book_rows, trade_rows),
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    args = ap.parse_args()
    cfg = yaml.safe_load(open(args.config))
    asyncio.run(run(cfg))

if __name__ == "__main__":
    main()