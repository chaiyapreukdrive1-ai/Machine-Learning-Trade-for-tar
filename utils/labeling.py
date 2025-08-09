import numpy as np
import pandas as pd

# สร้าง label ตามกลยุทธ์: เข้าออเดอร์ที่ราคา close ของแท่งปัจจุบัน และดูแท่งถัดๆ ไปจนกว่าโดน TP/SL หรือครบ max_hold_bars
# NOTE: ใช้ high/low แทน path ในแท่ง (ประมาณการ)

def make_tp_sl_labels(bars: pd.DataFrame, tp_pct: float, sl_pct: float, max_hold_bars: int):
    df = bars.copy()
    closes = df["close"].values
    highs  = df["high"].values
    lows   = df["low"].values

    n = len(df)
    y = np.full(n, np.nan)
    hold = np.full(n, np.nan)  # กี่แท่งกว่าจะจบดีล

    for i in range(n-1):
        entry = closes[i]
        tp = entry * (1 + tp_pct)
        sl = entry * (1 - sl_pct)
        outcome = np.nan
        bars_used = np.nan
        horizon = min(max_hold_bars, n - i - 1)
        for h in range(1, horizon+1):
            hi = highs[i+h]
            lo = lows[i+h]
            hit_tp = hi >= tp
            hit_sl = lo <= sl
            if hit_tp and hit_sl:
                # อนุมานแบบอนุรักษ์นิยม: โดน SL ก่อน
                outcome = 0
                bars_used = h
                break
            elif hit_tp:
                outcome = 1
                bars_used = h
                break
            elif hit_sl:
                outcome = 0
                bars_used = h
                break
        if np.isnan(outcome):
            # ไม่โดนอะไรเลย ปิดที่แท่งสุดท้ายของ horizon
            final = closes[i + horizon]
            outcome = 1 if final > entry else 0
            bars_used = horizon
        y[i] = outcome
        hold[i] = bars_used

    df["y"] = y
    df["bars_to_exit"] = hold
    return df.dropna(subset=["y"])  # ตัดแท่งท้ายที่ไม่มีข้อมูลอนาคต