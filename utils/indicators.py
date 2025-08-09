import numpy as np
import pandas as pd

def rsi(close: pd.Series, period=14):
    delta = close.diff()
    up = delta.clip(lower=0)
    down = -delta.clip(upper=0)
    ma_up = up.ewm(alpha=1/period, adjust=False).mean()
    ma_down = down.ewm(alpha=1/period, adjust=False).mean()
    rs = ma_up / ma_down.replace(0, np.nan)
    return 100 - (100/(1+rs))

def compute_features(df: pd.DataFrame):
    out = df.copy()
    out["ret_1"] = out["close"].pct_change()
    out["ret_5"] = out["close"].pct_change(5)
    out["vol_chg"] = out["volume"].pct_change()
    out["ema_9"] = out["close"].ewm(span=9, adjust=False).mean()
    out["ema_21"] = out["close"].ewm(span=21, adjust=False).mean()
    out["ema_gap"] = (out["ema_9"] - out["ema_21"]) / out["close"]
    out["bb_mid"] = out["close"].rolling(20).mean()
    out["bb_std"] = out["close"].rolling(20).std()
    out["bb_width"] = (2*out["bb_std"]) / out["bb_mid"]
    out["rsi_14"] = rsi(out["close"], 14)
    # หากมี bookticker
    if {"best_bid","best_ask","bid_qty","ask_qty"}.issubset(out.columns):
        out["spread"] = out["best_ask"] - out["best_bid"]
        denom = (out["bid_qty"] + out["ask_qty"]).replace(0, np.nan)
        out["ob_imbalance"] = (out["bid_qty"] - out["ask_qty"]) / denom
    return out