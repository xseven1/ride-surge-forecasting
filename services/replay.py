import time
import pandas as pd
import random
from common.config import settings
from common.redis_client import get_redis
from common.schemas import default_controls

CTRL_KEY = "controls"
EVENT_ZSET_KEY_FMT = "zone:{z}:events"
STATE_KEY_FMT = "zone:{z}:state"

def run(parquet_path: str, speed: float = 60.0, run_minutes: int = 10):
    r = get_redis()

    if not r.exists(CTRL_KEY):
        r.hset(CTRL_KEY, mapping=default_controls())

    for z in range(settings.N_ZONES):
        key = STATE_KEY_FMT.format(z=z)
        if not r.exists(key):
            r.hset(key, mapping={"supply_now": str(random.randint(10, 40)), "last_ts": str(int(time.time()))})

    print(f"Loading {parquet_path}...")
    df = pd.read_parquet(parquet_path, columns=["tpep_pickup_datetime", "PULocationID"])
    df = df.dropna(subset=["tpep_pickup_datetime", "PULocationID"])
    df = df.sort_values("tpep_pickup_datetime").reset_index(drop=True)

    df["zone_id"] = (df["PULocationID"] % settings.N_ZONES)

    sim_start = df["tpep_pickup_datetime"].iloc[0]
    real_start = time.time()
    run_seconds = run_minutes * 60

    print(f"Replaying {len(df):,} events starting from {sim_start}")
    print(f"Speed: {speed}x | Will stop after {run_minutes} minute(s).")

    try:
        for _, row in df.iterrows():
            if time.time() - real_start >= run_seconds:
                print("Replay finished (time limit reached).")
                break

            sim_elapsed = (row["tpep_pickup_datetime"] - sim_start).total_seconds()
            real_elapsed = sim_elapsed / speed
            sleep_time = (real_start + real_elapsed) - time.time()
            if sleep_time > 0:
                time.sleep(sleep_time)

            now = int(time.time())
            z = int(row["zone_id"])
            zset_key = EVENT_ZSET_KEY_FMT.format(z=z)
            event_id = f"{now}-{random.getrandbits(32)}"
            r.zadd(zset_key, {event_id: now})

    except KeyboardInterrupt:
        print("Replay stopped by user.")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--path", type=str, default="yellow_tripdata_2024-01.parquet")
    parser.add_argument("--speed", type=float, default=60.0)
    parser.add_argument("--minutes", type=int, default=10)
    args = parser.parse_args()
    run(args.path, args.speed, args.minutes)