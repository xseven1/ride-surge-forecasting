import time
from typing import Dict
import datetime

from common.config import settings
from common.redis_client import get_redis

CTRL_KEY = "controls"
EVENT_ZSET_KEY_FMT = "zone:{z}:events"
STATE_KEY_FMT = "zone:{z}:state"
FEATURE_KEY_FMT = "zone:{z}:features"

def _count_in_window(r, z: int, now: int, window_sec: int) -> int:
    key = EVENT_ZSET_KEY_FMT.format(z=z)
    start = now - window_sec
    return r.zcount(key, start, now)

def _cleanup_old(r, z: int, now: int):
    # keep some buffer beyond the largest window/horizon
    key = EVENT_ZSET_KEY_FMT.format(z=z)
    cutoff = now - (settings.WIN_5M + settings.HORIZON_SEC + 60)
    r.zremrangebyscore(key, 0, cutoff)

def compute_features(r, z: int, now: int) -> Dict[str, str]:
    demand_1m = _count_in_window(r, z, now, settings.WIN_1M)
    demand_5m = _count_in_window(r, z, now, settings.WIN_5M)

    state_key = STATE_KEY_FMT.format(z=z)
    supply_now = int(r.hget(state_key, "supply_now") or "20")

    trend = demand_1m - (demand_5m / 5.0)
    utilization = demand_5m / float(supply_now + 1)

    ctrl = r.hgetall(CTRL_KEY)
    rush = 1 if ctrl.get("rush_hour", "0") == "1" else 0
    rain = 1 if ctrl.get("rain", "0") == "1" else 0
    event = 1 if ctrl.get("event", "0") == "1" else 0

    hour = time.localtime(now).tm_hour
    dow = time.localtime(now).tm_wday

    return {
        "ts": str(now),
        "zone_id": str(z),
        "demand_1m": str(demand_1m),
        "demand_5m": str(demand_5m),
        "demand_trend": f"{trend:.4f}",
        "supply_now": str(supply_now),
        "utilization": f"{utilization:.4f}",
        "rush_hour": str(rush),
        "rain": str(rain),
        "event": str(event),
        "hour": str(hour),
        "dow": str(dow),
    }

def run(run_minutes: int | None = None):
    r = get_redis()

    if run_minutes is None:
        run_minutes = settings.AGGREGATOR_RUN_MINUTES
    run_seconds = 0 if not run_minutes else int(run_minutes * 60)

    start = time.time()
    start_ts = int(start)
    print(f"Aggregator started at {datetime.datetime.fromtimestamp(start_ts)}")
    if run_seconds:
        print(f"Aggregator will stop after {run_minutes} minute(s). Press Ctrl+C to stop earlier.")
    else:
        print("Aggregator will run until you stop it (Ctrl+C).")

    try:
        while True:
            now = int(time.time())

            if run_seconds and (time.time() - start) >= run_seconds:
                print("Aggregator reached time limit. Stopping.")
                break

            for z in range(settings.N_ZONES):
                _cleanup_old(r, z, now)
                feats = compute_features(r, z, now)
                r.hset(FEATURE_KEY_FMT.format(z=z), mapping=feats)

            elapsed = int(time.time() - start)
            if elapsed % 10 == 0:
                remaining = None if not run_seconds else max(0, run_seconds - elapsed)
                msg = f"[agg] elapsed={elapsed}s"
                if remaining is not None:
                    msg += f" remaining={remaining}s"
                print(msg)

            time.sleep(settings.TICK_SECONDS)

    except KeyboardInterrupt:
        print("Aggregator stopped by user (Ctrl+C).")

if __name__ == "__main__":
    run()