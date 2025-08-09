#!/usr/bin/env bash
set -e

# 1) backfill
python data_pipeline/fetch_klines.py --config config.yaml

# 2) start realtime collectors (แนะนำเปิดอีก terminal)
# python data_pipeline/realtime_book_trades.py --config config.yaml

# 3) build dataset + labels
python features/build_dataset.py --config config.yaml

# 4) train model
python models/train.py --config config.yaml