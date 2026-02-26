import time
import random
from typing import List

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

def run():
    r = get_redis()
    _ensure_initialized(r)

    print("Simulator started. Writing ride events to Redis...")
    while True:
        now = int(time.time())

        ctrl = r.hgetall(CTRL_KEY)
        request_rate = int(ctrl.get("request_rate", settings.DEFAULT_EVENTS_PER_TICK))
        rush = ctrl.get("rush_hour", "0") == "1"
        rain = ctrl.get("rain", "0") == "1"
        event = ctrl.get("event", "0") == "1"

        weights = _zone_weights(rush, rain, event)

        # generate N events per tick
        for _ in range(max(0, request_rate)):
            z = random.choices(range(settings.N_ZONES), weights=weights, k=1)[0]
            zset_key = EVENT_ZSET_KEY_FMT.format(z=z)
            event_id = f"{now}-{random.getrandbits(32)}"
            # score = timestamp, member = unique event id
            r.zadd(zset_key, {event_id: now})

        # Small supply dynamics: supply decreases when demand high, recovers slowly
        for z in range(settings.N_ZONES):
            state_key = ZONE_STATE_KEY_FMT.format(z=z)
            supply_now = int(r.hget(state_key, "supply_now") or "20")
            # random walk
            supply_now += random.choice([-1, 0, 0, 1])
            supply_now = max(5, min(60, supply_now))
            r.hset(state_key, mapping={"supply_now": str(supply_now), "last_ts": str(now)})

        time.sleep(settings.TICK_SECONDS)

if __name__ == "__main__":
    run()