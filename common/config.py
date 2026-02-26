from dataclasses import dataclass

@dataclass(frozen=True)
class Settings:
    REDIS_URL: str = "redis://localhost:6379/0"
    N_ZONES: int = 20
    TICK_SECONDS: float = 1.0
    DEFAULT_EVENTS_PER_TICK: int = 30

    # Rolling windows in seconds
    WIN_1M: int = 60
    WIN_5M: int = 300

    # Demand forecasting horizon (label): next 5 minutes
    HORIZON_SEC: int = 300

    # Model
    MODEL_PATH: str = "model/artifacts/demand_lgbm.joblib"

settings = Settings()