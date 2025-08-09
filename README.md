# Binance ML 1m Pipeline (BTCUSDT)

ครบชุด: ดึงข้อมูล → รวมฟีเจอร์ → ทำฉลาก (TP/SL) → เทรนโมเดล
รองรับ Mac/Windows/Linux ด้วยไฟล์/สคริปต์ในโปรเจกต์

## ขั้นตอนใช้งานแบบเร็ว (Quick Start)
1) ติดตั้งไลบรารี
```bash
pip install -r requirements.txt
```

2) ตั้งค่า `config.yaml` (เช็ค tp_pct/sl_pct) แล้วสร้างโฟลเดอร์ข้อมูล
```bash
mkdir -p data/raw data/features data/models
```

3) ดึงย้อนหลังรอบแรก (OHLCV + AggTrades + Snapshot BookTicker) ตาม `history_days`
```bash
python data_pipeline/fetch_klines.py --config config.yaml
```

4) เริ่มเก็บเรียลไทม์ (BookTicker + AggTrades) รันค้างไว้
```bash
python data_pipeline/realtime_book_trades.py --config config.yaml
```
สคริปต์นี้จะเขียนไฟล์ `.parquet` ลงใน `data/raw/...` เป็นไฟล์ย่อยตามช่วงเวลา (เช่น `bookticker_2025-08-09_032500.parquet`) เพื่อหลีกเลี่ยงการ append Parquet

5) สร้างฟีเจอร์ + รวมชุดข้อมูลพร้อมฉลาก (จาก TP/SL)
```bash
python features/build_dataset.py --config config.yaml
```

6) เทรนโมเดลพื้นฐาน + รายงานผลแบบ TimeSeries split
```bash
python models/train.py --config config.yaml
```

7) โมเดลถูกบันทึกที่ `data/models/model.joblib` พร้อมไฟล์รายชื่อฟีเจอร์ `features.json`

## โครงสร้างข้อมูลที่ได้
- `data/raw/klines_1m.parquet` — OHLCV 1 นาที
- `data/raw/aggtrades_*.parquet` — Tick (aggTrades) แบบเรียลไทม์/รายช่วง
- `data/raw/bookticker_*.parquet` — Top-of-book (best bid/ask) แบบเรียลไทม์/รายช่วง
- `data/features/dataset.parquet` — ชุดฟีเจอร์ต่อแท่ง 1 นาที + labels
- `data/models/model.joblib` — โมเดลที่เทรนแล้ว

## หมายเหตุสำคัญ
- Binance ไม่ให้ประวัติ order book ลึกๆ ทาง REST — เราเก็บ `bookTicker` (best bid/ask) แบบเรียลไทม์เพื่อใช้ spread/imbalance ในการทำฟีเจอร์
- ถ้าต้องการ Order Book Depth เต็มๆ + การประกอบบอร์ดตาม diff สามารถเพิ่มภายหลังได้
- `tp_pct`/`sl_pct` รับค่าเป็นทศนิยมของเปอร์เซ็นต์ เช่น 0.003 = 0.3%

## To-do รอบต่อไป
- เพิ่ม Open Interest / Funding Rate (Futures)
- เพิ่มฟีเจอร์จากความลึกของออเดอร์บุ๊ค (orderbook depth diffs)
- เพิ่ม backtester ที่ทวน path ในแท่ง
- ทำ inference script รับสัญญาณแบบเรียลไทม์
