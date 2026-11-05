from functools import lru_cache
from pathlib import Path
from typing import Literal
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / ".env", extra="ignore")
    app_mode: Literal["demo", "local", "live"] = "demo"
    demo_allow_network: bool = False
    database_url: str = "sqlite:///./data/batore.db"
    web_origin: str = "http://localhost:5173"
    supabase_url: str = ""
    supabase_publishable_key: str = ""
    admin_user_ids: str = ""
    google_maps_api_key: str = ""
    gemini_api_key: str = ""
    gemini_model: str = ""
    brave_search_api_key: str = ""
    youtube_api_key: str = ""
    meta_access_token: str = ""
    meta_instagram_account_id: str = ""
    meta_graph_version: str = ""
    instagram_provider: Literal["disabled", "meta", "apify"] = "disabled"
    apify_api_token: str = ""
    apify_instagram_task_id: str = ""
    apify_max_charge_usd: float = 1.0
    research_max_sources: int = 5
    research_daily_limit: int = 5
    research_streaming: bool = True
    inventory_collection_enabled: bool = False
    media_max_seconds: int = 180
    media_max_frames: int = 12
    ffmpeg_binary: str = ""
    analysis_provider: Literal["gemini", "ollama"] = "gemini"
    ollama_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "qwen3-vl:2b-instruct"
    whisper_model: str = "base"
    local_search_enabled: bool = False
    instagram_browser_enabled: bool = False
    browser_daily_limit: int = Field(default=12, ge=1, le=100)
    browser_max_comments: int = Field(default=30, ge=1, le=50)
    browser_timeout_seconds: int = Field(default=35, ge=10, le=60)
    autonomous_discovery: bool = False
    web_evidence_hosts: list[str] = Field(
        default_factory=lambda: [
            "www.thefrenchdoorindia.com",
            "www.sreeannapoorna.com",
            "coimbatore.prozonemalls.com",
            "coastt.in",
            "www.vgpwaghoba.in",
            "apexkarting.in",
            "www.ccmc.gov.in",
            "coimbatore.nic.in",
        ]
    )
    release_stage: Literal["internal", "test", "public"] = "internal"
    test_user_ids: str = ""
    monthly_budget_inr: int = Field(default=3000, ge=0)
    provider_reserve_inr: dict[str, float] = Field(
        default_factory=lambda: {
            "gemini": 10,
            "google": 2,
            "brave": 2,
            "youtube": 1,
            "apify_start": 200,
            "other": 1,
        }
    )
    merchant_webhook_secret: str = ""
    max_provider_calls_per_day: int = 100
    max_media_mb: int = 12
    worker_poll_seconds: int = 5
    refresh_interval_hours: int = 24
    max_attempts: int = 3


@lru_cache
def settings():
    return Settings()
