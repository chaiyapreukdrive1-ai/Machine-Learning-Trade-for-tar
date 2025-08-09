import os, argparse, json
import pandas as pd
import numpy as np
import yaml
from sklearn.model_selection import TimeSeriesSplit
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import classification_report, f1_score
import joblib

# เทรน baseline classifier ทำนาย "ดีลนี้ชนะไหม" ตามฉลาก TP/SL

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--config", required=True)
    args = ap.parse_args(); cfg = yaml.safe_load(open(args.config))

    feat_dir = cfg["feat_dir"]; model_dir = cfg["model_dir"]
    os.makedirs(model_dir, exist_ok=True)

    ds = pd.read_parquet(os.path.join(feat_dir, "dataset.parquet"))

    features = [
        "close","volume","number_of_trades",
        "trade_vwap","buy_vol","sell_vol",
        "best_bid","best_ask","bid_qty","ask_qty","spread","ob_imbalance",
        "ret_1","ret_5","vol_chg","ema_gap","bb_width","rsi_14"
    ]
    X = ds[features].replace([np.inf,-np.inf], np.nan).fillna(0.0).values
    y = ds["y"].astype(int).values

    pipe = Pipeline([
        ("scaler", StandardScaler(with_mean=False)),
        ("gb", GradientBoostingClassifier(random_state=42))
    ])

    tscv = TimeSeriesSplit(n_splits=5)
    best, best_f1 = None, -1
    for i, (tr, te) in enumerate(tscv.split(X)):
        pipe.fit(X[tr], y[tr])
        pred = pipe.predict(X[te])
        f1 = f1_score(y[te], pred)
        print(f"[Fold {i+1}] F1={f1:.4f}")
        print(classification_report(y[te], pred, digits=4))
        if f1 > best_f1:
            best_f1, best = f1, pipe

    joblib.dump(best, os.path.join(model_dir, "model.joblib"))
    with open(os.path.join(model_dir, "features.json"), "w") as f:
        json.dump(features, f, indent=2)
    print("Saved model + features.")

if __name__ == "__main__":
    main()