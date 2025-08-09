import time
import requests
import pandas as pd
from datetime import datetime, timezone

BINANCE_API = "https://api.binance.com"
UTC = timezone.utc

class Http:
    @staticmethod
    def get(path, params=None, retries=3, sleep=1.0):
        url = f"{BINANCE_API}{path}"
        for i in range(retries):
            r = requests.get(url, params=params, timeout=20)
            if r.status_code == 200:
                return r.json()
            time.sleep(sleep * (i+1))
        r.raise_for_status()

    @staticmethod
    def ms(ts):
        if isinstance(ts, (int, float)):
            return int(ts)
        if isinstance(ts, str):
            return int(pd.Timestamp(ts, tz=UTC).timestamp() * 1000)
        if isinstance(ts, (pd.Timestamp, datetime)):
            if ts.tz is None:
                return int(pd.Timestamp(ts, tz=UTC).timestamp() * 1000)
            else:
                return int(ts.timestamp() * 1000)
        raise ValueError("Unsupported ts type")