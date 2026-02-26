from dataclasses import dataclass
from typing import Dict

@dataclass
class ControlState:
    request_rate: int
    rush_hour: bool
    rain: bool
    event: bool

def default_controls() -> Dict[str, str]:
    return {
        "request_rate": "30",
        "rush_hour": "0",
        "rain": "0",
        "event": "0",
    }