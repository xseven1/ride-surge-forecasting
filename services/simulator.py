import time
import random
from typing import List
import datetime

from common.config import settings
from common.redis_client import get_redis
from common.schemas import default_controls

CTRL_KEY = "controls"
EVENT_ZSET_KEY_FMT = "zone:{z}:events"          # sorted set of timestamps (score=ts)
ZONE_STATE_KEY_FMT = "zone:{z}:state"           # hash of current zone state (supply etc.)

def _ensure_initialized(r):
    # Controls
    if not r.exists(CTRL_KEY):
        r.hset(CTRL_KEY, mapping=default_controls())

    # Initialize zone supplies once
    for z in range(settings.N_ZONES):
        key = ZONE_STATE_KEY_FMT.format(z=z)
        if not r.exists(key):
            supply = random.randint(10, 40)
            r.hset(key, mapping={
                "supply_now": str(supply),
                "last_ts": str(int(time.time())),
            })

def _zone_weights(rush: bool, rain: bool, event: bool) -> List[float]:
    # Simple weight pattern: some zones are "downtown"
    base = [1.0] * settings.N_ZONES
    downtown = set(range(0, max(2, settings.N_ZONES // 4)))  # first quarter
    for z in range(settings.N_ZONES):
        if z in downtown:
            base[z] *= 2.0
    if rush:
        for z in downtown:
            base[z] *= 1.7
    if rain:
        base = [w * 1.2 for w in base]
    if event:
        # spike a couple zones
        hot = [settings.N_ZONES // 2, min(settings.N_ZONES - 1, settings.N_ZONES // 2 + 1)]
        for z in hot:
            base[z] *= 2.0
    s = sum(base)
    return [w / s for w in base]

def run(run_minutes: int | None = None):
    r = get_redis()
    _ensure_initialized(r)

    # Determine run duration
    if run_minutes is None:
        run_minutes = settings.SIMULATOR_RUN_MINUTES
    run_seconds = 0 if not run_minutes else int(run_minutes * 60)

    start = time.time()
    start_ts = int(start)
    print(f"Simulator started at {datetime.datetime.fromtimestamp(start_ts)}")
    if run_seconds:
        print(f"Simulator will stop after {run_minutes} minute(s). Press Ctrl+C to stop earlier.")
    else:
        print("Simulator will run until you stop it (Ctrl+C).")

    try:
        while True:
            now = int(time.time())

            # Stop condition
            if run_seconds and (time.time() - start) >= run_seconds:
                print("Simulator reached time limit. Stopping.")
                break

            ctrl = r.hgetall(CTRL_KEY)
            request_rate = int(ctrl.get("request_rate", settings.DEFAULT_EVENTS_PER_TICK))
            rush = ctrl.get("rush_hour", "0") == "1"
            rain = ctrl.get("rain", "0") == "1"
            event = ctrl.get("event", "0") == "1"

            weights = _zone_weights(rush, rain, event)

            for _ in range(max(0, request_rate)):
                z = random.choices(range(settings.N_ZONES), weights=weights, k=1)[0]
                zset_key = EVENT_ZSET_KEY_FMT.format(z=z)
                event_id = f"{now}-{random.getrandbits(32)}"
                r.zadd(zset_key, {event_id: now})

            for z in range(settings.N_ZONES):
                state_key = ZONE_STATE_KEY_FMT.format(z=z)
                supply_now = int(r.hget(state_key, "supply_now") or "20")
                supply_now += random.choice([-1, 0, 0, 1])
                supply_now = max(5, min(60, supply_now))
                r.hset(state_key, mapping={"supply_now": str(supply_now), "last_ts": str(now)})

            # Progress print every 10 seconds
            elapsed = int(time.time() - start)
            if elapsed % 10 == 0:
                remaining = None if not run_seconds else max(0, run_seconds - elapsed)
                msg = f"[sim] elapsed={elapsed}s"
                if remaining is not None:
                    msg += f" remaining={remaining}s"
                msg += f" rate={request_rate}/s rush={int(rush)} rain={int(rain)} event={int(event)}"
                print(msg)

            time.sleep(settings.TICK_SECONDS)

    except KeyboardInterrupt:
        print("Simulator stopped by user (Ctrl+C).")

if __name__ == "__main__":
    run()