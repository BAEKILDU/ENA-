"""환경 변수 로드 (.env)."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

_ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_ENV_PATH)


def get_openai_api_key() -> str:
    return (os.getenv("OPENAI_API_KEY") or "").strip()


def get_supabase_url() -> str:
    return (os.getenv("SUPABASE_URL") or "").strip()


def get_supabase_anon_key() -> str:
    return (os.getenv("SUPABASE_ANON_KEY") or "").strip()


def env_status() -> dict[str, bool]:
    """키가 설정되어 있는지 여부만 반환 (값은 노출하지 않음)."""
    return {
        "OPENAI_API_KEY": bool(get_openai_api_key()),
        "SUPABASE_URL": bool(get_supabase_url()),
        "SUPABASE_ANON_KEY": bool(get_supabase_anon_key()),
    }
