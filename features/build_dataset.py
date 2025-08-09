import os, argparse
import pandas as pd
import numpy as np
import yaml
from utils.indicators import compute_features
from utils.labeling import make_tp_sl_labels

# รวม OHLCV + bookTicker + aggTrades → ฟีเจอร์รายแท่ง 1m + labels

def load_klines(raw_dir):
    k = pd.read_parquet(os.path.join(raw_dir, "klines_1m.parquet"))
    k = k.rename(columns={
        "open_time":"open_time","close_time":"time",
        "open":"open","high":"high","low":"low","close":"close",
        "volume":"volume","trades":"number_of_trades"
    })
    k["time"] = pd.to_datetime(k["time"], utc=True)
    k = k.set_index("time").sort_index()
    return k[["open","high","low","close","volume","number_of_trades"]]


def load_bookticker(raw_dir):
    files = [f for f in os.listdir(raw_dir) if f.startswith("bookticker_")]
    parts = []
    for f in files:
        parts.append(pd.read_parquet(os.path.join(raw_dir, f)))
    if not parts:
        # ใช้ snapshot ถ้ายังไม่มีสตรีม
        snap_path = os.path.join(raw_dir, "bookticker_snapshot.parquet")
        if os.path.exists(snap_path):
            snap = pd.read_parquet(snap_path)
            snap = snap.set_index("time").sort_index()
            return snap
        else:
            return pd.DataFrame(columns=["time","best_bid","best_ask","bid_qty","ask_qty"]).set_index("time")
    bt = pd.concat(parts).set_index("time").sort_index()
    return bt


def load_aggtrades(raw_dir):
    files = [f for f in os.listdir(raw_dir) if f.startswith("aggtrades_")]
    if not files:
        return pd.DataFrame(columns=["trade_time","price","qty","is_buyer_maker"]).set_index("trade_time")
    parts = []
    for f in files:
        parts.append(pd.read_parquet(os.path.join(raw_dir, f)))
    tr = pd.concat(parts)
    tr = tr.set_index("trade_time").sort_index()
    return tr


def trades_to_bar(tr, bar_index):
    if tr.empty:
        return pd.DataFrame(index=bar_index, columns=["trade_vwap","buy_vol","sell_vol"]).fillna(0)
    turnover = (tr["price"]*tr["qty"]).resample("1min").sum()
    volume = tr["qty"].resample("1min").sum()
    trade_vwap = turnover / volume.replace(0, np.nan)
    sell_vol = tr.loc[tr["is_buyer_maker"]==True, "qty"].resample("1min").sum()
    buy_vol  = tr.loc[tr["is_buyer_maker"]==False, "qty"].resample("1min").sum()
    df = pd.DataFrame({"trade_vwap": trade_vwap, "buy_vol": buy_vol, "sell_vol": sell_vol})
    return df.reindex(bar_index)


def bookticker_to_bar(bt, bar_index):
    if bt.empty:
        return pd.DataFrame(index=bar_index, columns=["best_bid","best_ask","bid_qty","ask_qty"])
    # ใช้ค่า last ภายในนาที
    df = bt.resample("1min").last()
    return df.reindex(bar_index)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--config", required=True)
    args = ap.parse_args(); cfg = yaml.safe_load(open(args.config))

    raw_dir = cfg["raw_dir"]; feat_dir = cfg["feat_dir"]
    os.makedirs(feat_dir, exist_ok=True)

    k = load_klines(raw_dir)
    bt = load_bookticker(raw_dir)
    tr = load_aggtrades(raw_dir)

    bars = k.copy()
    bars.index.freq = "1min"

    # ผูกฟีเจอร์จาก streams
    tfeat = trades_to_bar(tr, bars.index)
    bfeat = bookticker_to_bar(bt, bars.index)
    merged = bars.join(tfeat).join(bfeat)

    # ฟีเจอร์เชิงเทคนิค
    feat = compute_features(merged)

    # สร้าง labels ตาม TP/SL
    ds = make_tp_sl_labels(
        feat,
        tp_pct=float(cfg["tp_pct"]),
        sl_pct=float(cfg["sl_pct"]),
        max_hold_bars=int(cfg["max_hold_bars"])
    )

    ds.to_parquet(os.path.join(feat_dir, "dataset.parquet"))
    print("Saved:", os.path.join(feat_dir, "dataset.parquet"))

if __name__ == "__main__":
    main()