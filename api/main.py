import time
from typing import Dict, Any
import joblib
from fastapi import FastAPI
from pydantic import BaseModel

from common.config import settings
from common.redis_client import get_redis

CTRL_KEY = "controls"
FEATURE_KEY_FMT = "zone:{z}:features"
STATE_KEY_FMT = "zone:{z}:state"

FEATURE_COLS = [
    "demand_1m", "demand_5m", "demand_trend",
    "supply_now", "utilization",
    "rush_hour", "rain", "event",
    "hour", "dow",
]

app = FastAPI(title="Real-Time Demand Forecasting API")
r = get_redis()

try:
    model = joblib.load(settings.MODEL_PATH)
except Exception:
    model = None

class ControlsIn(BaseModel):
    request_rate: int | None = None
    rush_hour: bool | None = None
    rain: bool | None = None
    event: bool | None = None

def clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))

def surge_policy(pred_demand: float, supply_now: float, rain: int, event: int) -> float:
    ratio = pred_demand / (supply_now + 1.0)
    surge = 1.0 + 0.6 * ratio + 0.25 * rain + 0.35 * event
    return clamp(surge, 1.0, 3.0)

def _get_zone_features(z: int) -> Dict[str, Any]:
    feats = r.hgetall(FEATURE_KEY_FMT.format(z=z))
    if not feats:
        return {}
    # Cast
    out: Dict[str, Any] = {}
    for k, v in feats.items():
        if k in ("zone_id", "ts"):
            out[k] = int(float(v))
        else:
            out[k] = float(v)
    return out

@app.get("/health")
def health():
    return {"ok": True, "model_loaded": model is not None}

@app.post("/control")
def set_controls(ctrl: ControlsIn):
    current = r.hgetall(CTRL_KEY)
    if not current:
        r.hset(CTRL_KEY, mapping={"request_rate": "30", "rush_hour": "0", "rain": "0", "event": "0"})
        current = r.hgetall(CTRL_KEY)

    updates = {}
    if ctrl.request_rate is not None:
        updates["request_rate"] = str(max(0, int(ctrl.request_rate)))
    if ctrl.rush_hour is not None:
        updates["rush_hour"] = "1" if ctrl.rush_hour else "0"
    if ctrl.rain is not None:
        updates["rain"] = "1" if ctrl.rain else "0"
    if ctrl.event is not None:
        updates["event"] = "1" if ctrl.event else "0"

    if updates:
        r.hset(CTRL_KEY, mapping=updates)

    return {"controls": r.hgetall(CTRL_KEY)}

@app.get("/zones/state")
def zones_state():
    zones = []
    for z in range(settings.N_ZONES):
        feats = _get_zone_features(z)
        if not feats:
            continue

        pred = None
        surge = None
        if model is not None:
            x = [[feats[c] for c in FEATURE_COLS]]
            pred = float(model.predict(x)[0])
            surge = surge_policy(pred, feats["supply_now"], int(feats["rain"]), int(feats["event"]))

        zones.append({
            "zone_id": z,
            "ts": feats.get("ts", int(time.time())),
            "features": feats,
            "pred_next_5m_demand": pred,
            "surge_multiplier": surge,
        })
    return {"zones": zones}

@app.get("/zones/{zone_id}")
def zone_detail(zone_id: int):
    feats = _get_zone_features(zone_id)
    if not feats:
        return {"zone_id": zone_id, "error": "no features yet"}

    pred = None
    surge = None
    if model is not None:
        x = [[feats[c] for c in FEATURE_COLS]]
        pred = float(model.predict(x)[0])
        surge = surge_policy(pred, feats["supply_now"], int(feats["rain"]), int(feats["event"]))

    return {
        "zone_id": zone_id,
        "features": feats,
        "pred_next_5m_demand": pred,
        "surge_multiplier": surge,
    }