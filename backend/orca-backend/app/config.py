import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()
ROOT = Path(__file__).resolve().parent.parent


def _b(name: str, default: bool) -> bool:
    return os.getenv(name, str(default)).strip().lower() in ("1", "true", "yes", "on")


class Settings:
    def __init__(self) -> None:
        self.cache_dir = Path(os.getenv("CACHE_DIR", ROOT / "cache"))
        self.cache_ttl_s = int(os.getenv("CACHE_TTL_MIN", "30")) * 60
        self.stale_max_s = int(os.getenv("STALE_MAX_HOURS", "72")) * 3600
        self.http_timeout = float(os.getenv("HTTP_TIMEOUT_S", "8"))
        self.force_mock = _b("FORCE_MOCK", False)
        self.demo_scenarios = _b("DEMO_SCENARIOS", True)
        self.default_place = os.getenv("DEFAULT_PLACE", "veraval")
        self.boundary_dir = Path(os.getenv("BOUNDARY_DIR", ROOT / "data" / "boundaries"))
        self.boundary_alert_km = float(os.getenv("BOUNDARY_ALERT_KM", "15"))
        self.cors_origins = [
            o.strip()
            for o in os.getenv(
                "CORS_ORIGINS", "http://localhost:3000,http://localhost:5173,http://localhost:8080"
            ).split(",")
            if o.strip()
        ]
        self.llm_base_url = os.getenv("LLM_BASE_URL", "").rstrip("/")
        self.llm_model = os.getenv("LLM_MODEL", "")
        self.llm_api_key = os.getenv("LLM_API_KEY", "")


settings = Settings()
