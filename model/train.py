import time
import pandas as pd
from typing import List, Dict
import joblib

from lightgbm import LGBMRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error

from common.config import settings
from common.redis_client import get_redis

EVENT_ZSET_KEY_FMT = "zone:{z}:events"
FEATURE_KEY_FMT = "zone:{z}:features"

FEATURE_COLS = [
    "demand_1m", "demand_5m", "demand_trend",
    "supply_now", "utilization",
    "rush_hour", "rain", "event",
    "hour", "dow",
]

def _future_count(r, z: int, t0: int) -> int:
    key = EVENT_ZSET_KEY_FMT.format(z=z)
    start = t0 + 1
    end = t0 + settings.HORIZON_SEC
    return r.zcount(key, start, end)

def collect_rows(duration_minutes: int = 10, sample_every_sec: int = 10) -> pd.DataFrame:
    r = get_redis()
    rows: List[Dict] = []
    end_time = time.time() + duration_minutes * 60

    print(f"Collecting training data for ~{duration_minutes} minutes...")
    while time.time() < end_time:
        t0 = int(time.time())
        for z in range(settings.N_ZONES):
            feats = r.hgetall(FEATURE_KEY_FMT.format(z=z))
            if not feats:
                continue

            # Build row
            row = {c: float(feats[c]) for c in FEATURE_COLS if c in feats}
            row["zone_id"] = z
            row["ts"] = t0

            # Label: count future events in next 5 minutes
            y = _future_count(r, z, t0)
            row["next_5m_demand"] = float(y)

            rows.append(row)

        time.sleep(sample_every_sec)

    df = pd.DataFrame(rows)
    return df

def train_and_save(df: pd.DataFrame):
    df = df.dropna()
    X = df[FEATURE_COLS]
    y = df["next_5m_demand"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    model = LGBMRegressor(
        n_estimators=400,
        learning_rate=0.05,
        num_leaves=31,
        subsample=0.9,
        colsample_bytree=0.9,
        random_state=42,
    )
    model.fit(X_train, y_train)

    preds = model.predict(X_test)
    mae = mean_absolute_error(y_test, preds)
    rmse = mean_squared_error(y_test, preds) ** 0.5

    print(f"MAE:  {mae:.4f}")
    print(f"RMSE: {rmse:.4f}")

    joblib.dump(model, settings.MODEL_PATH)
    print(f"Saved model -> {settings.MODEL_PATH}")

def main():
    df = collect_rows(duration_minutes=10, sample_every_sec=10)
    print("Rows collected:", len(df))
    df.to_csv("model/artifacts/training_data.csv", index=False)
    train_and_save(df)

if __name__ == "__main__":
    main()