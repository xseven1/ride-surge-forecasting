from dataclasses import dataclass

@dataclass(frozen=True)
class Settings:
    REDIS_URL: str = "redis://localhost:6379/0"
    N_ZONES: int = 20
    TICK_SECONDS: float = 1.0
    DEFAULT_EVENTS_PER_TICK: int = 30

    WIN_1M: int = 60
    WIN_5M: int = 300
    HORIZON_SEC: int = 300

    MODEL_PATH: str = "model/artifacts/demand_lgbm.joblib"

    # NEW: default run durations (set to 0 for infinite)
    SIMULATOR_RUN_MINUTES: int = 10
    AGGREGATOR_RUN_MINUTES: int = 10

settings = Settings()